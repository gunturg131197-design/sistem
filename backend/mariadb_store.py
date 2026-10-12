"""Lapisan akses data MariaDB untuk TRIRARA.

Menyediakan API async bergaya dokumen (find / find_one / insert_one / update_one / find_one_and_update / delete /
count_documents / distinct) di atas tabel relasional MariaDB (lihat db_schema.py), sehingga logika bisnis tetap sama
tetapi seluruh data disimpan di MariaDB.

Prinsip:
- Filter diterjemahkan ke WHERE SQL (indeks dipakai) lalu DIVERIFIKASI ulang di Python dengan semantik yang sama
  persis seperti sebelumnya ($in, $ne, $regex, rentang, None = kosong/tidak ada, dll.).
- Update (read-modify-write) berjalan dalam transaksi dengan SELECT ... FOR UPDATE, sehingga penomoran bukti
  ($inc), kunci anti-duplikat ($setOnInsert + upsert) dan klaim antrian WA tetap atomik.
- Kolom per field; nilai yang tidak cocok tipe / field baru disimpan di kolom _extra (JSON) => tidak ada data hilang.
- Pembedaan "field bernilai None" vs "field tidak ada" dipertahankan.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
import math
import re
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from bson import json_util
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from db_schema import TABLES

log = logging.getLogger("mariadb_store")
import warnings as _warnings  # noqa: E402

_warnings.filterwarnings("ignore", message=r".*already exists.*")
logging.getLogger("asyncmy").setLevel(logging.ERROR)

_MISSING = object()
_NULLS = "__nulls__"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SQL_TYPES = {"s": "VARCHAR({n})", "ts": "VARCHAR(40)", "txt": "MEDIUMTEXT", "date": "DATE", "f": "DOUBLE", "i": "BIGINT",
              "b": "BOOLEAN", "j": "LONGTEXT", "blob": "LONGBLOB"}
_PUSHABLE = {"s", "ts", "date", "f", "i", "b"}


# ======================================================================= hasil & error
class DuplicateKeyError(Exception):
    """Pelanggaran indeks unik (mis. dedupe_key outbox WA, pembayaran bonus ganda)."""


class ReturnDocument:
    BEFORE = False
    AFTER = True


class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.acknowledged = True


class UpdateResult:
    def __init__(self, matched: int, modified: int, upserted_id=None):
        self.matched_count, self.modified_count, self.upserted_id = matched, modified, upserted_id
        self.acknowledged = True


class DeleteResult:
    def __init__(self, deleted: int):
        self.deleted_count = deleted
        self.acknowledged = True


# ======================================================================= util tipe
def _q(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _valid_date(v) -> bool:
    if not isinstance(v, str) or not _DATE_RE.match(v):
        return False
    try:
        _dt.date.fromisoformat(v)
        return True
    except ValueError:
        return False


def _fits(kind: str, n: int, v) -> bool:
    if kind in ("s", "ts"):
        return isinstance(v, str) and len(v) <= n
    if kind == "txt":
        return isinstance(v, str) and len(v) <= 16_000_000
    if kind == "date":
        return _valid_date(v)
    if kind == "f":
        return _is_num(v) and math.isfinite(float(v)) and (isinstance(v, float) or abs(v) < 2 ** 53)
    if kind == "i":
        return isinstance(v, int) and not isinstance(v, bool) and -(2 ** 63) <= v < 2 ** 63
    if kind == "b":
        return isinstance(v, bool)
    if kind == "j":
        return isinstance(v, (dict, list))
    if kind == "blob":
        return isinstance(v, (bytes, bytearray))
    return False


def _to_db(kind: str, v):
    if kind == "date":
        return _dt.date.fromisoformat(v)
    if kind == "j":
        return json_util.dumps(v)
    if kind == "blob":
        return bytes(v)
    if kind == "f":
        return float(v)
    if kind == "b":
        return 1 if v else 0
    return v


def _from_db(kind: str, v):
    if kind == "date":
        return v.isoformat() if isinstance(v, (_dt.date, _dt.datetime)) else str(v)
    if kind == "j":
        return json_util.loads(v)
    if kind == "b":
        return bool(v)
    if kind == "f":
        return float(v)
    if kind == "i":
        return int(v)
    if kind == "blob":
        return bytes(v)
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8")
    return v


# ======================================================================= evaluasi filter (Python)
def get_path(doc, path: str):
    cur = doc
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
            cur = cur[int(p)]
        else:
            return _MISSING
    return cur


def _same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_num(a) and _is_num(b):
        return a == b
    if type(a) is not type(b) and not (isinstance(a, str) and isinstance(b, str)):
        if isinstance(a, (bytes, bytearray)) and isinstance(b, (bytes, bytearray)):
            return bytes(a) == bytes(b)
        return False
    return a == b


def _eq(v, c) -> bool:
    if isinstance(c, re.Pattern):
        return _regex(v, c)
    if c is None:
        return v is _MISSING or v is None
    if v is _MISSING:
        return False
    if _same(v, c):
        return True
    if isinstance(v, list) and not isinstance(c, list):
        return any(_same(x, c) for x in v)
    return False


def _cmp(v, c, op: str) -> bool:
    if v is _MISSING or v is None or c is None:
        return False
    if isinstance(v, list):
        return any(_cmp(x, c, op) for x in v)
    if (_is_num(v) and _is_num(c)) or (isinstance(v, str) and isinstance(c, str)):
        return {"$gt": v > c, "$gte": v >= c, "$lt": v < c, "$lte": v <= c}[op]
    return False


def _regex(v, pat, options: str = "") -> bool:
    flags = 0
    for ch in options or "":
        flags |= {"i": re.I, "m": re.M, "s": re.S, "x": re.X}.get(ch, 0)
    rx = pat if isinstance(pat, re.Pattern) else re.compile(pat, flags)
    if isinstance(v, str):
        return rx.search(v) is not None
    if isinstance(v, list):
        return any(isinstance(x, str) and rx.search(x) for x in v)
    return False


def _ops(v, c: dict) -> bool:
    for op, arg in c.items():
        if op == "$options":
            continue
        if op == "$eq":
            ok = _eq(v, arg)
        elif op == "$ne":
            ok = not _eq(v, arg)
        elif op in ("$gt", "$gte", "$lt", "$lte"):
            ok = _cmp(v, arg, op)
        elif op == "$in":
            ok = any(_eq(v, x) for x in arg)
        elif op == "$nin":
            ok = not any(_eq(v, x) for x in arg)
        elif op == "$exists":
            ok = (v is not _MISSING) == bool(arg)
        elif op == "$regex":
            ok = _regex(v, arg, c.get("$options", ""))
        elif op == "$not":
            ok = not (_ops(v, arg) if isinstance(arg, dict) else _eq(v, arg))
        elif op == "$size":
            ok = isinstance(v, list) and len(v) == arg
        else:
            raise NotImplementedError(f"Operator filter {op} belum didukung")
        if not ok:
            return False
    return True


def _is_opdict(c) -> bool:
    return isinstance(c, dict) and bool(c) and all(isinstance(k, str) and k.startswith("$") for k in c)


def match(doc: dict, flt: Optional[dict]) -> bool:
    for k, c in (flt or {}).items():
        if k == "$or":
            if not any(match(doc, s) for s in c):
                return False
        elif k == "$and":
            if not all(match(doc, s) for s in c):
                return False
        elif k == "$nor":
            if any(match(doc, s) for s in c):
                return False
        else:
            v = get_path(doc, k)
            if not (_ops(v, c) if _is_opdict(c) else _eq(v, c)):
                return False
    return True


def _sort_val(v):
    if v is _MISSING or v is None:
        return (0, 0)
    if isinstance(v, bool):
        return (5, v)
    if _is_num(v):
        return (1, v)
    if isinstance(v, str):
        return (2, v)
    if isinstance(v, dict):
        return (3, json_util.dumps(v, sort_keys=True))
    if isinstance(v, list):
        return (4, json_util.dumps(v, sort_keys=True))
    return (6, str(v))


def _norm_sort(key_or_list, direction=None) -> list:
    if key_or_list is None:
        return []
    if isinstance(key_or_list, str):
        return [(key_or_list, 1 if direction is None else int(direction))]
    return [(k, int(d)) for k, d in key_or_list]


def _py_sort(docs: list, spec: list) -> list:
    for k, d in reversed(spec):
        docs.sort(key=lambda x, k=k: _sort_val(get_path(x, k)), reverse=d < 0)
    return docs


def _project(doc: dict, proj) -> dict:
    if not proj:
        return doc
    if isinstance(proj, (list, tuple)):
        proj = {k: 1 for k in proj}
    inc = [k for k, v in proj.items() if v and k != "_id"]
    if inc:
        out = {}
        for k in inc:
            v = get_path(doc, k)
            if v is _MISSING:
                continue
            if "." in k:
                _set_path(out, k, v)
            else:
                out[k] = v
        return out
    out = dict(doc)
    for k, v in proj.items():
        if not v and k != "_id":
            _unset_path(out, k)
    return out


# ======================================================================= update operators
def _set_path(doc: dict, path: str, value):
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        nxt = cur.get(p) if isinstance(cur, dict) else None
        if not isinstance(nxt, (dict, list)):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    if isinstance(cur, list) and parts[-1].isdigit():
        i = int(parts[-1])
        while len(cur) <= i:
            cur.append(None)
        cur[i] = value
    else:
        cur[parts[-1]] = value


def _unset_path(doc: dict, path: str):
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        cur = cur.get(p) if isinstance(cur, dict) else None
        if not isinstance(cur, dict):
            return
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


def _copy(v):
    if isinstance(v, dict):
        return {k: _copy(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_copy(x) for x in v]
    return v


def apply_update(doc: dict, upd: dict, inserting: bool = False) -> dict:
    new = _copy(doc)
    if not any(k.startswith("$") for k in upd):  # replacement document
        rep = {k: _copy(v) for k, v in upd.items() if k != "_id"}
        return rep
    for op, fields in upd.items():
        if op == "$set":
            for k, v in fields.items():
                _set_path(new, k, _copy(v))
        elif op == "$setOnInsert":
            if inserting:
                for k, v in fields.items():
                    _set_path(new, k, _copy(v))
        elif op == "$unset":
            for k in fields:
                _unset_path(new, k)
        elif op == "$inc":
            for k, v in fields.items():
                cur = get_path(new, k)
                _set_path(new, k, (0 if cur in (_MISSING, None) else cur) + v)
        elif op == "$push":
            for k, v in fields.items():
                cur = get_path(new, k)
                arr = list(cur) if isinstance(cur, list) else []
                if isinstance(v, dict) and "$each" in v:
                    arr.extend(_copy(v["$each"]))
                    if "$slice" in v:
                        s = int(v["$slice"])
                        arr = arr[s:] if s < 0 else arr[:s]
                else:
                    arr.append(_copy(v))
                _set_path(new, k, arr)
        elif op == "$addToSet":
            for k, v in fields.items():
                cur = get_path(new, k)
                arr = list(cur) if isinstance(cur, list) else []
                for x in (v["$each"] if isinstance(v, dict) and "$each" in v else [v]):
                    if not any(_same(x, y) for y in arr):
                        arr.append(_copy(x))
                _set_path(new, k, arr)
        elif op == "$pull":
            for k, v in fields.items():
                cur = get_path(new, k)
                if isinstance(cur, list):
                    _set_path(new, k, [x for x in cur if not (match(x, v) if isinstance(v, dict) and isinstance(x, dict) else _eq(x, v))])
        elif op == "$max" or op == "$min":
            for k, v in fields.items():
                cur = get_path(new, k)
                if cur in (_MISSING, None) or (_cmp(v, cur, "$gt") if op == "$max" else _cmp(v, cur, "$lt")):
                    _set_path(new, k, v)
        else:
            raise NotImplementedError(f"Operator update {op} belum didukung")
    return new


def _upsert_seed(flt: dict) -> dict:
    seed = {}
    for k, c in (flt or {}).items():
        if k.startswith("$"):
            continue
        if _is_opdict(c):
            if "$eq" in c:
                _set_path(seed, k, _copy(c["$eq"]))
        elif not isinstance(c, re.Pattern):
            _set_path(seed, k, _copy(c))
    return seed


# ======================================================================= tabel
class _Table:
    def __init__(self, name: str, spec: dict):
        self.name = name
        self.cols = [(c[0], c[1], (c[2] if len(c) > 2 else 255)) for c in spec.get("cols", [])]
        self.colmap = {c[0]: c for c in self.cols}
        self.unique = spec.get("unique", [])
        self.index = spec.get("index", [])
        self.key = spec.get("key", [])

    def ddl(self) -> str:
        parts = ["`_pk` BIGINT NOT NULL AUTO_INCREMENT"]
        for n, k, ln in self.cols:
            parts.append(f"{_q(n)} {_SQL_TYPES[k].format(n=ln)} NULL")
        parts.append("`_extra` LONGTEXT NULL")
        parts.append("PRIMARY KEY (`_pk`)")
        for i, u in enumerate(self.unique):
            parts.append(f"UNIQUE KEY {_q('uq_' + '_'.join(u))[:66]} ({', '.join(_q(c) for c in u)})")
        for ix in self.index:
            parts.append(f"KEY {_q('ix_' + '_'.join(ix))[:66]} ({', '.join(_q(c) for c in ix)})")
        return (f"CREATE TABLE IF NOT EXISTS {_q(self.name)} (\n  " + ",\n  ".join(parts) +
                "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin")

    def encode(self, doc: dict) -> dict:
        row = {n: None for n, _, _ in self.cols}
        extra, nulls = {}, []
        for k, v in doc.items():
            if k == "_id":
                continue
            col = self.colmap.get(k)
            if col is None:
                extra[k] = v
            elif v is None:
                nulls.append(k)
            elif _fits(col[1], col[2], v):
                row[k] = _to_db(col[1], v)
            else:
                extra[k] = v
        if nulls:
            extra[_NULLS] = nulls
        row["_extra"] = json_util.dumps(extra) if extra else None
        return row

    def decode(self, row) -> dict:
        m = row._mapping if hasattr(row, "_mapping") else row
        extra = json_util.loads(m["_extra"]) if m.get("_extra") else {}
        nulls = set(extra.pop(_NULLS, []) or [])
        doc = {}
        for n, k, _ in self.cols:
            v = m.get(n)
            if v is None:
                if n in nulls:
                    doc[n] = None
            else:
                doc[n] = _from_db(k, v)
        doc.update(extra)
        return doc

    # ---- terjemahan filter -> SQL (superset); exact=True bila hasil SQL == hasil Python
    def where(self, flt: Optional[dict], params: dict) -> tuple[str, bool]:
        conds, exact = [], True
        for k, c in (flt or {}).items():
            if k.startswith("$"):
                exact = False  # $or/$and diverifikasi di Python
                continue
            col = self.colmap.get(k)
            if col is None or col[1] not in _PUSHABLE:
                exact = False
                continue
            _, kind, n = col
            items = c.items() if _is_opdict(c) else [("$eq", c)]
            for op, arg in items:
                sql, ex = self._cond(k, kind, n, op, arg, c, params)
                if sql:
                    conds.append(sql)
                exact = exact and ex
        return (" AND ".join(conds) if conds else "1=1"), exact

    def _cond(self, k, kind, n, op, arg, whole, params):
        p = lambda v: self._param(params, v)  # noqa: E731
        col = _q(k)
        if op == "$eq":
            if arg is None:
                return f"{col} IS NULL", False
            if isinstance(arg, (dict, list)) or not _fits(kind, n, arg):
                return "", False
            return f"{col} = {p(_to_db(kind, arg))}", True
        if op == "$ne":
            if arg is None:
                return f"{col} IS NOT NULL", False
            if not _fits(kind, n, arg):
                return "", False
            return f"({col} <> {p(_to_db(kind, arg))} OR {col} IS NULL)", True
        if op in ("$in", "$nin"):
            vals = list(arg)
            fit = [v for v in vals if v is not None and _fits(kind, n, v)]
            if len(fit) + sum(1 for v in vals if v is None) != len(vals):
                return "", False
            has_none = any(v is None for v in vals)
            if op == "$in":
                parts = []
                if fit:
                    parts.append(f"{col} IN ({', '.join(p(_to_db(kind, v)) for v in fit)})")
                if has_none:
                    parts.append(f"{col} IS NULL")
                return ("(" + " OR ".join(parts) + ")") if parts else "1=0", not has_none
            if has_none:
                return (f"{col} NOT IN ({', '.join(p(_to_db(kind, v)) for v in fit)}) AND {col} IS NOT NULL" if fit
                        else f"{col} IS NOT NULL"), False
            return (f"({col} NOT IN ({', '.join(p(_to_db(kind, v)) for v in fit)}) OR {col} IS NULL)" if fit else "1=1"), True
        if op in ("$gt", "$gte", "$lt", "$lte"):
            if arg is None or not _fits(kind, n, arg):
                return "", False
            if kind in ("s", "ts") and not isinstance(arg, str):
                return "", False
            sym = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}[op]
            return f"{col} {sym} {p(_to_db(kind, arg))}", True
        if op == "$regex" and isinstance(arg, str) and kind in ("s", "ts", "date"):
            m = re.match(r"^\^([A-Za-z0-9 _\-:./|]*)$", arg) if "i" not in (whole.get("$options", "") if isinstance(whole, dict) else "") else None
            lit = m.group(1) if m else None
            if lit and "|" not in lit and "." not in lit:
                esc = lit.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                return f"{col} LIKE {p(esc + '%')}", False
            return "", False
        if op == "$exists":
            return ("", False)
        return "", False

    @staticmethod
    def _param(params: dict, v) -> str:
        name = f"p{len(params)}"
        params[name] = v
        return f":{name}"


# ======================================================================= cursor
class Cursor:
    def __init__(self, coll: "Collection", flt, projection):
        self._c, self._f, self._p = coll, flt or {}, projection
        self._sort, self._limit, self._skip = [], 0, 0
        self._buf = None

    def sort(self, key_or_list, direction=None):
        self._sort = _norm_sort(key_or_list, direction)
        return self

    def limit(self, n: int):
        self._limit = int(n or 0)
        return self

    def skip(self, n: int):
        self._skip = int(n or 0)
        return self

    async def to_list(self, length: Optional[int] = None):
        n = self._limit or 0
        if length:
            n = min(n, int(length)) if n else int(length)
        docs = await self._c._select(self._f, self._sort, n, self._skip)
        return [_project(d, self._p) for d in docs]

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for d in await self.to_list(None):
            yield d


# ======================================================================= collection
class Collection:
    def __init__(self, store: "Store", name: str):
        self.store, self.name = store, name

    @property
    def t(self) -> _Table:
        return self.store.table(self.name)

    # ---------- baca
    async def _select(self, flt, sort, limit=0, skip=0, conn=None, for_update=False) -> list:
        await self.store.ensure(self.name)
        t = self.t
        params: dict = {}
        where, exact = t.where(flt, params)
        sql_sort = all(k in t.colmap and t.colmap[k][1] in _PUSHABLE for k, _ in sort)
        sql = f"SELECT * FROM {_q(t.name)} WHERE {where}"
        if sort and sql_sort:
            sql += " ORDER BY " + ", ".join(f"{_q(k)} {'DESC' if d < 0 else 'ASC'}" for k, d in sort) + ", `_pk` ASC"
        elif not sort:
            sql += " ORDER BY `_pk` ASC"
        pushed_limit = exact and (sql_sort or not sort) and limit
        if pushed_limit:
            sql += f" LIMIT {int(limit)} OFFSET {int(skip)}"
        if for_update:
            sql += " FOR UPDATE"
        rows = await self.store._fetch(sql, params, conn)
        docs = [t.decode(r) for r in rows]
        if not exact:
            docs = [d for d in docs if match(d, flt)]
        if sort:
            docs = _py_sort(docs, sort)  # stabil; menyamakan urutan untuk nilai bertipe campuran / di _extra
        if not pushed_limit:
            if skip:
                docs = docs[skip:]
            if limit:
                docs = docs[:limit]
        return docs

    async def _select_pk(self, flt, sort, limit, conn):
        """Seperti _select tetapi menyertakan _pk untuk update/delete (dengan kunci baris)."""
        await self.store.ensure(self.name)
        t = self.t
        params: dict = {}
        where, exact = t.where(flt, params)
        sql_sort = all(k in t.colmap and t.colmap[k][1] in _PUSHABLE for k, _ in sort)
        sql = f"SELECT * FROM {_q(t.name)} WHERE {where}"
        if sort and sql_sort:
            sql += " ORDER BY " + ", ".join(f"{_q(k)} {'DESC' if d < 0 else 'ASC'}" for k, d in sort) + ", `_pk` ASC"
        else:
            sql += " ORDER BY `_pk` ASC"
        if exact and (sql_sort or not sort) and limit:
            sql += f" LIMIT {int(limit)}"
        sql += " FOR UPDATE"
        rows = await self.store._fetch(sql, params, conn)
        out = []
        for r in rows:
            d = t.decode(r)
            if exact or match(d, flt):
                out.append((r._mapping["_pk"], d))
        if sort and not sql_sort:
            keyed = _py_sort([dict(d, __pk__=pk) for pk, d in out], sort)
            out = [(d.pop("__pk__"), d) for d in keyed]
        return out[:limit] if limit else out

    def find(self, filter=None, projection=None, sort=None, limit=0, **_kw):
        cur = Cursor(self, filter, projection)
        if sort:
            cur.sort(sort)
        if limit:
            cur.limit(limit)
        return cur

    async def find_one(self, filter=None, projection=None, sort=None, **_kw):
        if filter is not None and not isinstance(filter, dict):
            filter = {"_id": filter}
        res = await self.find(filter, projection, sort=sort).to_list(1)
        return res[0] if res else None

    async def count_documents(self, filter=None, **_kw) -> int:
        await self.store.ensure(self.name)
        params: dict = {}
        where, exact = self.t.where(filter, params)
        if exact:
            rows = await self.store._fetch(f"SELECT COUNT(*) AS n FROM {_q(self.name)} WHERE {where}", params)
            return int(rows[0]._mapping["n"])
        return len(await self._select(filter, []))

    async def estimated_document_count(self, **_kw) -> int:
        return await self.count_documents({})

    async def distinct(self, key: str, filter=None, **_kw) -> list:
        out = []
        for d in await self._select(filter, []):
            v = get_path(d, key)
            for x in (v if isinstance(v, list) else [v]):
                if x is _MISSING:
                    continue
                if not any(_same(x, y) for y in out):
                    out.append(x)
        return sorted(out, key=_sort_val)

    # ---------- tulis
    async def _insert_row(self, conn, doc: dict):
        row = self.t.encode(doc)
        cols = list(row.keys())
        sql = f"INSERT INTO {_q(self.name)} ({', '.join(_q(c) for c in cols)}) VALUES ({', '.join(':' + 'v' + str(i) for i in range(len(cols)))})"
        try:
            await conn.execute(text(sql), {f"v{i}": row[c] for i, c in enumerate(cols)})
        except IntegrityError as e:
            raise DuplicateKeyError(str(e.orig) if getattr(e, "orig", None) else str(e)) from None

    async def _write_row(self, conn, pk, doc: dict):
        row = self.t.encode(doc)
        sets = ", ".join(f"{_q(c)} = :v{i}" for i, c in enumerate(row))
        params = {f"v{i}": row[c] for i, c in enumerate(row)}
        params["pk"] = pk
        try:
            await conn.execute(text(f"UPDATE {_q(self.name)} SET {sets} WHERE `_pk` = :pk"), params)
        except IntegrityError as e:
            raise DuplicateKeyError(str(e.orig) if getattr(e, "orig", None) else str(e)) from None

    async def insert_one(self, doc: dict, **_kw) -> InsertOneResult:
        await self.store.ensure(self.name)
        async with self.store.tx() as conn:
            await self._insert_row(conn, doc)
        return InsertOneResult(doc.get("id") or doc.get("key") or doc.get("_id"))

    async def insert_many(self, docs: Iterable[dict], ordered: bool = True, **_kw):
        ids = []
        for d in docs:
            try:
                ids.append((await self.insert_one(d)).inserted_id)
            except DuplicateKeyError:
                if ordered:
                    raise
        r = InsertOneResult(None)
        r.inserted_ids = ids
        return r

    async def _update(self, flt, upd, upsert=False, many=False, sort=None, return_doc=None, projection=None):
        await self.store.ensure(self.name)
        sort = _norm_sort(sort) if sort else []
        for attempt in range(4):
            try:
                async with self.store.tx() as conn:
                    found = await self._select_pk(flt, sort, 0 if many else 1, conn)
                    if found:
                        modified, before, after = 0, None, None
                        for pk, d in found:
                            new = apply_update(d, upd)
                            if new != d:
                                await self._write_row(conn, pk, new)
                                modified += 1
                            before, after = before or d, after or new
                        res = UpdateResult(len(found), modified)
                        res._before, res._after = before, after
                        return res
                    if not upsert:
                        res = UpdateResult(0, 0)
                        res._before = res._after = None
                        return res
                    new = apply_update(_upsert_seed(flt), upd, inserting=True)
                    await self._insert_row(conn, new)
                    res = UpdateResult(0, 0, upserted_id=new.get("id") or new.get("key") or new.get("run_id") or True)
                    res._before, res._after = None, new
                    return res
            except DuplicateKeyError:
                if upsert and attempt < 3:  # baris dibuat proses lain di saat bersamaan -> ulangi sebagai update
                    continue
                raise
            except OperationalError as e:
                if attempt < 3 and _is_retryable(e):
                    await asyncio.sleep(0.05 * (attempt + 1))
                    continue
                raise

    async def update_one(self, filter, update, upsert: bool = False, **_kw) -> UpdateResult:
        return await self._update(filter, update, upsert=upsert)

    async def update_many(self, filter, update, upsert: bool = False, **_kw) -> UpdateResult:
        return await self._update(filter, update, upsert=upsert, many=True)

    async def replace_one(self, filter, replacement, upsert: bool = False, **_kw) -> UpdateResult:
        return await self._update(filter, {k: v for k, v in replacement.items() if k != "_id"}, upsert=upsert)

    async def find_one_and_update(self, filter, update, projection=None, sort=None, upsert: bool = False,
                                  return_document=ReturnDocument.BEFORE, **_kw):
        res = await self._update(filter, update, upsert=upsert, sort=sort)
        doc = res._after if return_document else res._before
        return _project(doc, projection) if doc is not None else None

    async def _delete(self, flt, many: bool) -> DeleteResult:
        await self.store.ensure(self.name)
        for attempt in range(4):
            try:
                async with self.store.tx() as conn:
                    found = await self._select_pk(flt, [], 0 if many else 1, conn)
                    if found:
                        pks = [pk for pk, _ in found]
                        for i in range(0, len(pks), 500):
                            chunk = pks[i:i + 500]
                            await conn.execute(text(f"DELETE FROM {_q(self.name)} WHERE `_pk` IN ({', '.join(str(int(x)) for x in chunk)})"))
                    return DeleteResult(len(found))
            except OperationalError as e:
                if attempt < 3 and _is_retryable(e):
                    await asyncio.sleep(0.05 * (attempt + 1))
                    continue
                raise

    async def delete_one(self, filter, **_kw) -> DeleteResult:
        return await self._delete(filter, False)

    async def delete_many(self, filter, **_kw) -> DeleteResult:
        return await self._delete(filter, True)

    async def find_one_and_delete(self, filter, projection=None, **_kw):
        doc = await self.find_one(filter)
        if doc is None:
            return None
        await self.delete_one(filter)
        return _project(doc, projection)

    async def create_index(self, keys, unique: bool = False, **_kw) -> str:
        """Indeks didefinisikan di db_schema.py (dibuat saat tabel dibuat). Fungsi ini sengaja tanpa efek."""
        await self.store.ensure(self.name)
        return "schema-managed"

    async def drop(self):  # pragma: no cover - tidak dipakai aplikasi (sengaja tidak menghapus)
        raise RuntimeError("drop() dinonaktifkan demi keamanan data")


def _is_retryable(e: Exception) -> bool:
    code = getattr(getattr(e, "orig", None), "args", [None])[0]
    return code in (1213, 1205)  # deadlock / lock wait timeout


# ======================================================================= store (database)
class Store:
    def __init__(self, url: str, **engine_kw):
        scheme, rest = url.split("://", 1)
        if scheme in ("mysql", "mariadb", "mysql+aiomysql", "mysql+pymysql", "mariadb+asyncmy", "mysql+mysqldb"):
            url = "mysql+asyncmy://" + rest  # driver async: asyncmy
        self.url = url
        self.name = (urlparse(url).path or "/").lstrip("/").split("?")[0] or "trirara"
        self.engine: AsyncEngine = create_async_engine(
            url, pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=20,
            isolation_level="READ COMMITTED", connect_args={"charset": "utf8mb4"}, **engine_kw)
        self._tables: dict[str, _Table] = {n: _Table(n, s) for n, s in TABLES.items()}
        self._ready: set[str] = set()
        self._lock = asyncio.Lock()

    def table(self, name: str) -> _Table:
        if name not in self._tables:
            self._tables[name] = _Table(name, {"cols": [], "key": []})
        return self._tables[name]

    def __getattr__(self, name: str) -> Collection:
        if name.startswith("_"):
            raise AttributeError(name)
        return Collection(self, name)

    def __getitem__(self, name: str) -> Collection:
        return Collection(self, name)

    def tx(self):
        return self.engine.begin()

    async def _fetch(self, sql: str, params: dict, conn=None):
        if conn is not None:
            return (await conn.execute(text(sql), params)).fetchall()
        async with self.engine.connect() as c:
            return (await c.execute(text(sql), params)).fetchall()

    async def ensure(self, name: str):
        if name in self._ready:
            return
        async with self._lock:
            if name in self._ready:
                return
            t = self.table(name)
            async with self.engine.begin() as conn:
                await conn.execute(text(t.ddl()))
                rows = (await conn.execute(text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"), {"t": name})).fetchall()
                have = {r[0] for r in rows}
                added = []
                for n, k, ln in t.cols:
                    if n not in have:
                        await conn.execute(text(f"ALTER TABLE {_q(name)} ADD COLUMN {_q(n)} {_SQL_TYPES[k].format(n=ln)} NULL"))
                        added.append(n)
            if added:
                log.info(f"[mariadb] kolom baru {name}: {added} — memindahkan nilai dari _extra")
                await self._backfill(name, added)
            self._ready.add(name)

    async def _backfill(self, name: str, cols: list):
        t = self.table(name)
        async with self.engine.begin() as conn:
            rows = (await conn.execute(text(f"SELECT * FROM {_q(name)} WHERE `_extra` IS NOT NULL FOR UPDATE"))).fetchall()
            coll = Collection(self, name)
            for r in rows:
                extra = json_util.loads(r._mapping["_extra"])
                if any(c in extra or c in (extra.get(_NULLS) or []) for c in cols):
                    await coll._write_row(conn, r._mapping["_pk"], t.decode(r))

    async def init_schema(self):
        for n in TABLES:
            await self.ensure(n)

    async def list_collection_names(self) -> list:
        rows = await self._fetch("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()", {})
        return sorted(r[0] for r in rows)

    async def ping(self) -> bool:
        await self._fetch("SELECT 1", {})
        return True

    async def close(self):
        await self.engine.dispose()

    # kompatibilitas: client.close()
    def close_sync(self):
        try:
            asyncio.get_event_loop().create_task(self.engine.dispose())
        except Exception:  # noqa: BLE001
            pass


def build_url_from_env(env: dict) -> str:
    """MARIADB_URL / DATABASE_URL, atau rakit dari MARIADB_HOST/PORT/USER/PASSWORD/DATABASE."""
    url = env.get("MARIADB_URL") or env.get("DATABASE_URL") or ""
    if url:
        return url
    from urllib.parse import quote_plus
    host = env.get("MARIADB_HOST", "127.0.0.1")
    port = env.get("MARIADB_PORT", "3306")
    user = env.get("MARIADB_USER", "trirara")
    pwd = env.get("MARIADB_PASSWORD", "")
    name = env.get("MARIADB_DATABASE", "trirara")
    return f"mysql+asyncmy://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}/{name}?charset=utf8mb4"
