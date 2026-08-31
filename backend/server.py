from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Cookie, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
import os
import logging
import uuid
import bcrypt
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def normalize_username(u: str) -> str:
    return (u or "").strip().lower()


# Admin allowlist (owner)
ADMIN_EMAILS = {"shanchidean@gmail.com"}


# ---------- Models ----------
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: str = ""
    role: str = "operator"  # admin | operator
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionRequest(BaseModel):
    session_id: str


class Unit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit_name: str  # unit excavator (e.g. CAT 320D)
    nomor_lambung: str
    serial_number: str
    operator_id: Optional[str] = None  # assigned operator user_id
    operator_name: Optional[str] = None
    pengurus: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UnitCreate(BaseModel):
    unit_name: str
    nomor_lambung: str
    serial_number: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    pengurus: Optional[str] = ""


class Operation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit_id: str
    unit_label: str = ""
    operator_id: str
    operator_name: str = ""
    tanggal: str  # ISO date string YYYY-MM-DD
    hour_meter_awal: float
    hour_meter_akhir: float
    jumlah_cars: int
    pengurus: Optional[str] = ""
    total_jam: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OperationCreate(BaseModel):
    unit_id: str
    tanggal: str
    hour_meter_awal: float
    hour_meter_akhir: float
    jumlah_cars: int
    pengurus: Optional[str] = ""


class Payroll(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operator_id: str
    operator_name: str = ""
    unit_id: str = ""
    unit_label: str = ""
    periode: str  # YYYY-MM
    tarif_per_jam: float = 0.0
    jam_kerja: float = 0.0     # snapshot total jam kerja operator+unit saat dibuat
    jam_dibayar: float = 0.0   # jam yang dibayarkan pada payroll ini
    gaji: float = 0.0          # = jam_dibayar * tarif_per_jam
    kasbon: float = 0.0
    gaji_bersih: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PayrollCreate(BaseModel):
    operator_id: str
    unit_id: str
    periode: str
    tarif_per_jam: float = 0.0
    jam_dibayar: float = 0.0
    kasbon: float = 0.0


class SparepartItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nama_sparepart: str
    qty: float = 1.0
    harga_satuan: float = 0.0
    total: float = 0.0


class Sparepart(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit_id: str
    unit_label: str = ""
    nomor_nota: str
    nama_sparepart: str = ""  # ringkasan gabungan nama item (legacy/summary)
    hm_service: Optional[float] = None  # HM saat service dilakukan (kelipatan 250 jam)
    items: List[SparepartItem] = []
    tanggal: str  # YYYY-MM-DD
    biaya: float = 0.0  # total nota (jumlah semua item)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SparepartCreate(BaseModel):
    unit_id: str
    nomor_nota: str
    tanggal: str
    hm_service: Optional[float] = None
    items: List[SparepartItem] = []


class PengurusExcavator(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nama: str
    kontak: Optional[str] = ""
    catatan: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PengurusExcavatorCreate(BaseModel):
    nama: str
    kontak: Optional[str] = ""
    catatan: Optional[str] = ""


class RoleUpdate(BaseModel):
    role: str


class ManualOperatorCreate(BaseModel):
    name: str
    email: Optional[str] = None
    role: str = "operator"
    pin: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class PasswordUpdate(BaseModel):
    password: str


class UsernameLogin(BaseModel):
    username: str
    password: str


class PinUpdate(BaseModel):
    pin: Optional[str] = None  # empty/None to clear


class PinVerify(BaseModel):
    user_id: str
    pin: str


def _validate_pin(pin: Optional[str]) -> Optional[str]:
    if pin is None or pin == "":
        return None
    p = pin.strip()
    if not (p.isdigit() and 4 <= len(p) <= 6):
        raise HTTPException(status_code=400, detail="PIN harus 4-6 digit angka")
    return p


# ---------- Auth helpers ----------
async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> User:
    token = session_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ---------- Auth Endpoints ----------
@api_router.post("/auth/session")
async def create_session(body: SessionRequest, response: Response):
    async with httpx.AsyncClient(timeout=15.0) as hc:
        r = await hc.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": body.session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session id")
    data = r.json()
    email = data["email"]
    name = data.get("name", email.split("@")[0])
    picture = data.get("picture", "")
    session_token = data["session_token"]

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        role = existing.get("role", "operator")
        if email in ADMIN_EMAILS and role != "admin":
            await db.users.update_one({"user_id": user_id}, {"$set": {"role": "admin"}})
            role = "admin"
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        role = "admin" if email in ADMIN_EMAILS else "operator"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "role": role,
    }


@api_router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return user.model_dump()


@api_router.post("/auth/logout")
async def logout(
    response: Response,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    token = session_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


# ---------- Users (admin) ----------
@api_router.get("/users")
async def list_users(user: User = Depends(get_current_user)):
    if user.role != "admin":
        # operator can only see themselves
        return [user.model_dump()]
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    return users


@api_router.patch("/users/{user_id}/role")
async def update_role(user_id: str, body: RoleUpdate, admin: User = Depends(require_admin)):
    if body.role not in {"admin", "operator"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": body.role}})
    return {"ok": True}


@api_router.post("/users/manual")
async def create_manual_operator(body: ManualOperatorCreate, admin: User = Depends(require_admin)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nama wajib diisi")
    if body.role not in {"admin", "operator"}:
        raise HTTPException(status_code=400, detail="Role tidak valid")
    pin = _validate_pin(body.pin)

    username = normalize_username(body.username) if body.username else None
    password_hash = None
    if username or body.password:
        if not username:
            raise HTTPException(status_code=400, detail="Username wajib diisi jika password diberikan")
        if not body.password or len(body.password) < 4:
            raise HTTPException(status_code=400, detail="Password minimal 4 karakter")
        if not username.replace("_", "").replace(".", "").replace("-", "").isalnum():
            raise HTTPException(status_code=400, detail="Username hanya boleh huruf, angka, . _ -")
        taken = await db.users.find_one({"username": username}, {"_id": 0})
        if taken:
            raise HTTPException(status_code=400, detail="Username sudah dipakai")
        password_hash = hash_password(body.password)

    user_id = f"user_manual_{uuid.uuid4().hex[:10]}"
    email = (body.email or f"{user_id}@manual.local").strip().lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    doc = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": "",
        "role": body.role,
        "manual": True,
        "pin": pin,
        "username": username,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


@api_router.patch("/users/{user_id}/password")
async def update_password(user_id: str, body: PasswordUpdate, admin: User = Depends(require_admin)):
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if not user_doc.get("manual"):
        raise HTTPException(status_code=400, detail="Password hanya untuk operator manual")
    if not user_doc.get("username"):
        raise HTTPException(status_code=400, detail="Set username lebih dulu")
    if not body.password or len(body.password) < 4:
        raise HTTPException(status_code=400, detail="Password minimal 4 karakter")
    await db.users.update_one({"user_id": user_id}, {"$set": {"password_hash": hash_password(body.password)}})
    return {"ok": True}


@api_router.post("/auth/login")
async def login_with_password(body: UsernameLogin, response: Response):
    username = normalize_username(body.username)
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="Username & password wajib diisi")
    user_doc = await db.users.find_one({"username": username}, {"_id": 0})
    if not user_doc or not user_doc.get("password_hash"):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    if not verify_password(body.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Username atau password salah")

    session_token = f"local_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_doc["user_id"],
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return {
        "user_id": user_doc["user_id"],
        "email": user_doc.get("email", ""),
        "name": user_doc["name"],
        "picture": user_doc.get("picture", ""),
        "role": user_doc.get("role", "operator"),
    }


@api_router.patch("/users/{user_id}/pin")
async def update_pin(user_id: str, body: PinUpdate, admin: User = Depends(require_admin)):
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if not user_doc.get("manual"):
        raise HTTPException(status_code=400, detail="PIN hanya untuk operator manual")
    pin = _validate_pin(body.pin)
    await db.users.update_one({"user_id": user_id}, {"$set": {"pin": pin}})
    return {"ok": True, "pin": pin}


@api_router.post("/users/verify-pin")
async def verify_pin(body: PinVerify, user: User = Depends(get_current_user)):
    target = await db.users.find_one({"user_id": body.user_id}, {"_id": 0})
    if not target or not target.get("manual"):
        raise HTTPException(status_code=404, detail="Operator manual tidak ditemukan")
    stored = target.get("pin")
    if not stored:
        raise HTTPException(status_code=400, detail="Operator ini belum punya PIN")
    ok = stored == body.pin.strip()
    return {
        "ok": ok,
        "user_id": target["user_id"],
        "name": target["name"],
    }


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin)):
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if not user_doc.get("manual"):
        raise HTTPException(status_code=400, detail="Hanya operator manual yang bisa dihapus")
    await db.users.delete_one({"user_id": user_id})
    return {"ok": True}


# ---------- Units ----------
@api_router.get("/units", response_model=List[Unit])
async def list_units(user: User = Depends(get_current_user)):
    query = {} if user.role == "admin" else {"operator_id": user.user_id}
    docs = await db.units.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
    return docs


@api_router.post("/units", response_model=Unit)
async def create_unit(body: UnitCreate, admin: User = Depends(require_admin)):
    unit = Unit(**body.model_dump())
    doc = unit.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.units.insert_one(doc)
    return unit


@api_router.patch("/units/{unit_id}", response_model=Unit)
async def update_unit(unit_id: str, body: UnitCreate, admin: User = Depends(require_admin)):
    update = body.model_dump()
    await db.units.update_one({"id": unit_id}, {"$set": update})
    doc = await db.units.find_one({"id": unit_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


@api_router.delete("/units/{unit_id}")
async def delete_unit(unit_id: str, admin: User = Depends(require_admin)):
    await db.units.delete_one({"id": unit_id})
    return {"ok": True}


@api_router.get("/pengurus")
async def list_pengurus(user: User = Depends(get_current_user)):
    """Distinct pengurus names across registry + units + operations (case-insensitive)."""
    names_registry = await db.pengurus_excavator.distinct("nama")
    names_units = await db.units.distinct("pengurus")
    names_ops = await db.operations.distinct("pengurus")
    seen = {}
    for n in list(names_registry) + list(names_units) + list(names_ops):
        if not n or not isinstance(n, str):
            continue
        key = n.strip().lower()
        if key and key not in seen:
            seen[key] = n.strip()
    return sorted(seen.values(), key=lambda s: s.lower())


# ---------- Pengurus Excavator Registry ----------
@api_router.get("/pengurus-excavator", response_model=List[PengurusExcavator])
async def list_pengurus_excavator(user: User = Depends(get_current_user)):
    docs = await db.pengurus_excavator.find({}, {"_id": 0}).sort("nama", 1).to_list(1000)
    # count usage across units + operations
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
    return docs


@api_router.get("/pengurus-excavator/{pid}/stats")
async def pengurus_stats(pid: str, user: User = Depends(get_current_user)):
    doc = await db.pengurus_excavator.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pengurus tidak ditemukan")
    nama = doc["nama"]
    # case-insensitive match
    regex = {"$regex": f"^{nama}$", "$options": "i"}
    units_count = await db.units.count_documents({"pengurus": regex})
    ops = await db.operations.find({"pengurus": regex}, {"_id": 0}).to_list(5000)
    total_cars = sum(o.get("jumlah_cars", 0) for o in ops)
    total_jam = sum(o.get("total_jam", 0) for o in ops)
    return {
        "nama": nama,
        "units_count": units_count,
        "ops_count": len(ops),
        "total_cars": total_cars,
        "total_jam": round(total_jam, 2),
    }


@api_router.get("/pengurus-excavator/{pid}/monthly")
async def pengurus_monthly(pid: str, months: int = 12, user: User = Depends(get_current_user)):
    """Return monthly breakdown of cars & jam for the pengurus (last N months)."""
    doc = await db.pengurus_excavator.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pengurus tidak ditemukan")
    nama = doc["nama"]
    regex = {"$regex": f"^{nama}$", "$options": "i"}
    ops = await db.operations.find({"pengurus": regex}, {"_id": 0}).to_list(10000)

    # Group by YYYY-MM
    monthly = {}
    for o in ops:
        d = o.get("tanggal", "")
        if not d or len(d) < 7:
            continue
        key = d[:7]  # YYYY-MM
        monthly.setdefault(key, {"month": key, "cars": 0, "jam": 0.0, "ops": 0})
        monthly[key]["cars"] += o.get("jumlah_cars", 0)
        monthly[key]["jam"] += o.get("total_jam", 0)
        monthly[key]["ops"] += 1

    # Build continuous last N months window ending at latest month with data or now
    from datetime import date as _date
    today = datetime.now(timezone.utc).date()
    result = []
    year, month = today.year, today.month
    keys = []
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    keys.reverse()
    for k in keys:
        row = monthly.get(k, {"month": k, "cars": 0, "jam": 0.0, "ops": 0})
        row["jam"] = round(row["jam"], 2)
        result.append(row)

    return {"nama": nama, "monthly": result}


@api_router.post("/pengurus-excavator", response_model=PengurusExcavator)
async def create_pengurus_excavator(body: PengurusExcavatorCreate, admin: User = Depends(require_admin)):
    nama = body.nama.strip()
    if not nama:
        raise HTTPException(status_code=400, detail="Nama wajib diisi")
    existing = await db.pengurus_excavator.find_one(
        {"nama": {"$regex": f"^{nama}$", "$options": "i"}}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Pengurus dengan nama ini sudah ada")
    obj = PengurusExcavator(nama=nama, kontak=(body.kontak or "").strip(), catatan=(body.catatan or "").strip())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.pengurus_excavator.insert_one(doc)
    return obj


@api_router.patch("/pengurus-excavator/{pid}", response_model=PengurusExcavator)
async def update_pengurus_excavator(pid: str, body: PengurusExcavatorCreate, admin: User = Depends(require_admin)):
    current = await db.pengurus_excavator.find_one({"id": pid}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Pengurus tidak ditemukan")
    new_nama = body.nama.strip()
    if not new_nama:
        raise HTTPException(status_code=400, detail="Nama wajib diisi")
    old_nama = current["nama"]
    await db.pengurus_excavator.update_one(
        {"id": pid},
        {"$set": {"nama": new_nama, "kontak": (body.kontak or "").strip(), "catatan": (body.catatan or "").strip()}},
    )
    # Cascade rename in units + operations (case-insensitive)
    if new_nama != old_nama:
        regex = {"$regex": f"^{old_nama}$", "$options": "i"}
        await db.units.update_many({"pengurus": regex}, {"$set": {"pengurus": new_nama}})
        await db.operations.update_many({"pengurus": regex}, {"$set": {"pengurus": new_nama}})
    doc = await db.pengurus_excavator.find_one({"id": pid}, {"_id": 0})
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


@api_router.delete("/pengurus-excavator/{pid}")
async def delete_pengurus_excavator(pid: str, admin: User = Depends(require_admin)):
    doc = await db.pengurus_excavator.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pengurus tidak ditemukan")
    await db.pengurus_excavator.delete_one({"id": pid})
    return {"ok": True}


# ---------- Operations ----------
@api_router.get("/operations", response_model=List[Operation])
async def list_operations(user: User = Depends(get_current_user)):
    query = {} if user.role == "admin" else {"operator_id": user.user_id}
    docs = await db.operations.find(query, {"_id": 0}).sort("tanggal", -1).to_list(2000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
    return docs


@api_router.post("/operations", response_model=Operation)
async def create_operation(body: OperationCreate, user: User = Depends(get_current_user)):
    unit = await db.units.find_one({"id": body.unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit tidak ditemukan")
    total_jam = max(0.0, body.hour_meter_akhir - body.hour_meter_awal)
    op = Operation(
        **body.model_dump(),
        unit_label=f"{unit['unit_name']} - {unit['nomor_lambung']}",
        operator_id=user.user_id,
        operator_name=user.name,
        total_jam=round(total_jam, 2),
    )
    doc = op.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.operations.insert_one(doc)
    return op


@api_router.delete("/operations/{op_id}")
async def delete_operation(op_id: str, user: User = Depends(get_current_user)):
    query = {"id": op_id} if user.role == "admin" else {"id": op_id, "operator_id": user.user_id}
    res = await db.operations.delete_one(query)
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ---------- Payroll ----------
@api_router.get("/payroll", response_model=List[Payroll])
async def list_payroll(user: User = Depends(get_current_user)):
    query = {} if user.role == "admin" else {"operator_id": user.user_id}
    docs = await db.payroll.find(query, {"_id": 0}).sort("periode", -1).to_list(1000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
    return docs


async def _compute_operator_hours(operator_id: str, unit_id: str):
    """Total jam kerja (HM akhir - HM awal) untuk operator+unit & jam yang sudah dibayar."""
    ops = await db.operations.find(
        {"operator_id": operator_id, "unit_id": unit_id}, {"_id": 0}
    ).to_list(10000)
    total_jam_kerja = sum(o.get("total_jam", 0) for o in ops)
    pays = await db.payroll.find(
        {"operator_id": operator_id, "unit_id": unit_id}, {"_id": 0}
    ).to_list(10000)
    total_jam_dibayar = sum(p.get("jam_dibayar", 0) for p in pays)
    return round(total_jam_kerja, 2), round(total_jam_dibayar, 2)


@api_router.get("/payroll/hours")
async def payroll_hours(operator_id: str, unit_id: str, user: User = Depends(get_current_user)):
    total_jam_kerja, total_jam_dibayar = await _compute_operator_hours(operator_id, unit_id)
    return {
        "total_jam_kerja": total_jam_kerja,
        "total_jam_dibayar": total_jam_dibayar,
        "jam_belum_dibayar": round(max(0.0, total_jam_kerja - total_jam_dibayar), 2),
    }


@api_router.post("/payroll", response_model=Payroll)
async def create_payroll(body: PayrollCreate, admin: User = Depends(require_admin)):
    op_user = await db.users.find_one({"user_id": body.operator_id}, {"_id": 0})
    op_name = op_user["name"] if op_user else ""
    unit = await db.units.find_one({"id": body.unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit tidak ditemukan")
    unit_label = f"{unit['unit_name']} - {unit['nomor_lambung']}"
    total_jam_kerja, _ = await _compute_operator_hours(body.operator_id, body.unit_id)
    gaji = round(body.jam_dibayar * body.tarif_per_jam, 2)
    payroll = Payroll(
        **body.model_dump(),
        operator_name=op_name,
        unit_label=unit_label,
        jam_kerja=total_jam_kerja,
        gaji=gaji,
        gaji_bersih=round(gaji - body.kasbon, 2),
    )
    doc = payroll.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.payroll.insert_one(doc)
    return payroll


@api_router.delete("/payroll/{pid}")
async def delete_payroll(pid: str, admin: User = Depends(require_admin)):
    await db.payroll.delete_one({"id": pid})
    return {"ok": True}


# ---------- Sparepart ----------
@api_router.get("/spareparts", response_model=List[Sparepart])
async def list_spareparts(user: User = Depends(get_current_user)):
    docs = await db.spareparts.find({}, {"_id": 0}).sort("tanggal", -1).to_list(2000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
    return docs


@api_router.post("/spareparts", response_model=Sparepart)
async def create_sparepart(body: SparepartCreate, admin: User = Depends(require_admin)):
    unit = await db.units.find_one({"id": body.unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit tidak ditemukan")
    if not body.items:
        raise HTTPException(status_code=400, detail="Minimal 1 sparepart harus ditambahkan")
    # Hitung total tiap item & total nota
    items = []
    total_biaya = 0.0
    for it in body.items:
        line_total = round((it.qty or 0) * (it.harga_satuan or 0), 2)
        items.append(SparepartItem(
            nama_sparepart=it.nama_sparepart,
            qty=it.qty,
            harga_satuan=it.harga_satuan,
            total=line_total,
        ))
        total_biaya += line_total
    nama_ringkas = ", ".join(i.nama_sparepart for i in items)
    sp = Sparepart(
        unit_id=body.unit_id,
        nomor_nota=body.nomor_nota,
        tanggal=body.tanggal,
        hm_service=body.hm_service,
        items=items,
        nama_sparepart=nama_ringkas,
        biaya=round(total_biaya, 2),
        unit_label=f"{unit['unit_name']} - {unit['nomor_lambung']}",
    )
    doc = sp.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.spareparts.insert_one(doc)
    return sp


@api_router.delete("/spareparts/{sid}")
async def delete_sparepart(sid: str, admin: User = Depends(require_admin)):
    await db.spareparts.delete_one({"id": sid})
    return {"ok": True}


# ---------- Dashboard Summary ----------
@api_router.get("/dashboard/summary")
async def dashboard_summary(user: User = Depends(get_current_user)):
    op_query = {} if user.role == "admin" else {"operator_id": user.user_id}
    ops = await db.operations.find(op_query, {"_id": 0}).to_list(5000)
    units = await db.units.find({}, {"_id": 0}).to_list(1000)
    spareparts = await db.spareparts.find({}, {"_id": 0}).to_list(5000)

    total_jam = sum(o.get("total_jam", 0) for o in ops)
    total_cars = sum(o.get("jumlah_cars", 0) for o in ops)
    total_biaya_sparepart = sum(s.get("biaya", 0) for s in spareparts)

    # Cost & hours per unit
    per_unit = {}
    for u in units:
        per_unit[u["id"]] = {
            "unit_id": u["id"],
            "unit_label": f"{u['unit_name']} - {u['nomor_lambung']}",
            "total_jam": 0.0,
            "total_cars": 0,
            "total_biaya_sparepart": 0.0,
        }
    for o in ops:
        uid = o.get("unit_id")
        if uid in per_unit:
            per_unit[uid]["total_jam"] += o.get("total_jam", 0)
            per_unit[uid]["total_cars"] += o.get("jumlah_cars", 0)
    for s in spareparts:
        uid = s.get("unit_id")
        if uid in per_unit:
            per_unit[uid]["total_biaya_sparepart"] += s.get("biaya", 0)

    # Daily cars trend (last 14 days aggregated)
    daily = {}
    for o in ops:
        d = o.get("tanggal", "")
        if not d:
            continue
        daily.setdefault(d, {"tanggal": d, "cars": 0, "jam": 0.0})
        daily[d]["cars"] += o.get("jumlah_cars", 0)
        daily[d]["jam"] += o.get("total_jam", 0)
    daily_list = sorted(daily.values(), key=lambda x: x["tanggal"])[-14:]

    return {
        "totals": {
            "total_jam": round(total_jam, 2),
            "total_cars": total_cars,
            "total_biaya_sparepart": round(total_biaya_sparepart, 2),
            "total_units": len(units),
        },
        "per_unit": list(per_unit.values()),
        "daily": daily_list,
    }


# ---------- Reports per Unit ----------
ROMAN_MONTHS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

REPORT_NO_BASE = 199  # nomor urut pertama yang diterbitkan = 200


class ReportNumberRequest(BaseModel):
    month: int
    year: int


@api_router.post("/reports/number")
async def issue_report_number(body: ReportNumberRequest, user: User = Depends(get_current_user)):
    """Terbitkan nomor laporan berurutan otomatis: LP/TTP/{seq}/{romawi bulan}/{tahun}."""
    month = body.month if 1 <= body.month <= 12 else datetime.now(timezone.utc).month
    year = body.year or datetime.now(timezone.utc).year
    doc = await db.app_counters.find_one_and_update(
        {"key": "report_no"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = REPORT_NO_BASE + int(doc.get("value", 1))
    nomor = f"LP/TTP/{seq}/{ROMAN_MONTHS[month]}/{year}"
    return {"nomor": nomor, "seq": seq, "month": month, "year": year}


@api_router.get("/reports/units")
async def reports_units(periode: Optional[str] = None, user: User = Depends(get_current_user)):
    """Laporan lengkap per unit: cars baru, operator, gaji operator, HM awal/akhir,
    total HM, dan penggantian sparepart. Opsional filter periode (YYYY-MM)."""
    unit_query = {} if user.role == "admin" else {"operator_id": user.user_id}
    units = await db.units.find(unit_query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    op_query = {} if user.role == "admin" else {"operator_id": user.user_id}
    all_ops = await db.operations.find(op_query, {"_id": 0}).to_list(20000)
    all_pays = await db.payroll.find({}, {"_id": 0}).to_list(20000)
    all_sp = await db.spareparts.find({}, {"_id": 0}).to_list(20000)

    # Filter periode (YYYY-MM) bila diberikan
    if periode:
        all_ops = [o for o in all_ops if (o.get("tanggal", "") or "").startswith(periode)]
        all_sp = [s for s in all_sp if (s.get("tanggal", "") or "").startswith(periode)]
        all_pays = [p for p in all_pays if (p.get("periode", "") or "") == periode]

    reports = []
    for u in units:
        uid = u["id"]
        unit_label = f"{u['unit_name']} - {u['nomor_lambung']}"
        ops = [o for o in all_ops if o.get("unit_id") == uid]
        ops_sorted = sorted(ops, key=lambda o: o.get("tanggal", ""))
        pays = [p for p in all_pays if p.get("unit_id") == uid]
        sps = [s for s in all_sp if s.get("unit_id") == uid]

        total_cars = sum(o.get("jumlah_cars", 0) for o in ops)
        total_hm = round(sum(o.get("total_jam", 0) for o in ops), 2)
        hm_awal = min((o.get("hour_meter_awal", 0) for o in ops), default=0)
        hm_akhir = max((o.get("hour_meter_akhir", 0) for o in ops), default=0)
        operators = sorted({o.get("operator_name", "") for o in ops if o.get("operator_name")})
        total_gaji = round(sum(p.get("gaji", 0) for p in pays), 2)
        total_kasbon = round(sum(p.get("kasbon", 0) for p in pays), 2)
        total_gaji_bersih = round(sum(p.get("gaji_bersih", 0) for p in pays), 2)
        total_sparepart = round(sum(s.get("biaya", 0) for s in sps), 2)

        reports.append({
            "unit_id": uid,
            "unit_name": u["unit_name"],
            "nomor_lambung": u["nomor_lambung"],
            "serial_number": u.get("serial_number", ""),
            "unit_label": unit_label,
            "operator_utama": u.get("operator_name", ""),
            "operators": operators,
            "total_cars": total_cars,
            "hm_awal": hm_awal,
            "hm_akhir": hm_akhir,
            "total_hm": total_hm,
            "total_gaji": total_gaji,
            "total_kasbon": total_kasbon,
            "total_gaji_bersih": total_gaji_bersih,
            "total_sparepart": total_sparepart,
            "ops_count": len(ops),
            "operations": ops_sorted,
            "payroll": pays,
            "spareparts": sps,
        })

    return reports


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
