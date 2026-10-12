"""AI pembaca gambar (Gemini via emergentintegrations) untuk bukti transfer & foto layar Hour Meter."""
import asyncio
import base64
import io
import json
import os
import re
import uuid

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

AI_PROVIDER = os.environ.get("WA_AI_PROVIDER", "gemini")
AI_MODEL = os.environ.get("WA_AI_MODEL", "gemini-3-flash-preview")

SYSTEM = (
    "Anda adalah sistem OCR untuk perusahaan sewa excavator di Indonesia. "
    "Tugas Anda membaca gambar dan mengembalikan HANYA JSON valid tanpa markdown."
)

PROMPT = """Klasifikasikan gambar ini lalu ekstrak datanya.

Jenis gambar:
- "transfer": bukti transfer / struk mobile banking / bukti pembayaran.
- "hour_meter": foto layar / panel monitor alat berat (excavator) yang menampilkan angka hour meter (jam operasi, biasanya diakhiri "h").
- "lainnya": selain itu.

Keterangan/caption dari pengirim WhatsApp: "{caption}"

Kembalikan JSON persis dengan struktur:
{{
  "jenis": "transfer" | "hour_meter" | "lainnya",
  "keyakinan": angka 0-1,
  "transfer": {{
    "nominal": angka rupiah tanpa titik (nominal pokok yang ditransfer, BUKAN termasuk biaya admin) atau null,
    "total": angka total transaksi atau null,
    "biaya_admin": angka atau null,
    "tanggal": "YYYY-MM-DD" atau null,
    "jam": "HH:MM:SS" atau null,
    "no_ref": "string nomor referensi" atau null,
    "bank_pengirim": string atau null,
    "nama_pengirim": string atau null,
    "rekening_pengirim": string atau null,
    "bank_tujuan": string atau null,
    "nama_tujuan": string atau null,
    "rekening_tujuan": string atau null,
    "jenis_transaksi": string atau null,
    "catatan": string catatan pada bukti atau null
  }},
  "hour_meter": {{
    "hm": angka hour meter (contoh 527.6) atau null,
    "tanggal": "YYYY-MM-DD" tanggal pada layar alat (atau watermark foto) atau null,
    "jam": "HH:MM:SS" atau null,
    "merek": merek alat yang terlihat (mis. ZOOMLION, SDLG, KOMATSU) atau null
  }}
}}
Isi bagian yang tidak relevan dengan null. Angka desimal pakai titik."""


def normalize_image(data: bytes, max_side: int = 1600) -> bytes:
    """Konversi apa pun (webp/png/heic-ish) -> JPEG RGB, diperkecil agar hemat token."""
    img = Image.open(io.BytesIO(data))
    try:
        img.seek(0)
    except Exception:
        pass
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


def _parse_json(text: str) -> dict:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0) if m else t)


_AI_LOCK = asyncio.Semaphore(int(os.environ.get("WA_AI_CONCURRENCY", "1")))


async def extract_image(data: bytes, caption: str = "") -> dict:
    """Antre (1 permintaan AI sekaligus) + retry otomatis bila kena batas 429."""
    last = None
    for attempt in range(4):
        async with _AI_LOCK:
            try:
                return await _extract_once(data, caption)
            except Exception as e:  # noqa: BLE001
                last = e
                msg = str(e).lower()
                if not ("429" in msg or "rate" in msg or "concurrent" in msg or "timeout" in msg or "503" in msg):
                    raise
        await asyncio.sleep(3 * (attempt + 1))
    raise last


async def _extract_once(data: bytes, caption: str = "") -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY belum diset")
    jpeg = normalize_image(data)
    chat = LlmChat(api_key=key, session_id=f"wa-ocr-{uuid.uuid4()}", system_message=SYSTEM).with_model(AI_PROVIDER, AI_MODEL)
    msg = UserMessage(
        text=PROMPT.format(caption=(caption or "").replace('"', "'")[:300]),
        file_contents=[ImageContent(image_base64=base64.b64encode(jpeg).decode())],
    )
    resp = await chat.send_message(msg)
    parsed = _parse_json(resp if isinstance(resp, str) else str(resp))
    parsed.setdefault("jenis", "lainnya")
    return parsed


# ---------- Pencocokan keterangan "Sdlg 10" ke unit ----------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def match_unit(caption: str, units: list) -> dict | None:
    """Cocokkan caption (mis. 'Sdlg 10', 'SDLG-230', 'EX-01') dengan unit_name / nomor_lambung / merek_type."""
    cap = (caption or "").strip()
    if not cap or not units:
        return None
    capn = _norm(cap)
    best, best_score = None, 0
    nums_cap = re.findall(r"\d+", cap)
    for u in units:
        cands = [u.get("nomor_lambung", ""), u.get("unit_name", ""), f"{u.get('unit_name', '')} {u.get('nomor_lambung', '')}",
                 u.get("merek_type", ""), f"{u.get('merek_type', '')} {u.get('nomor_lambung', '')}"] + [a.strip() for a in (u.get("kode_wa") or "").split(",") if a.strip()]
        score = 0
        for c in cands:
            cn = _norm(c)
            if not cn:
                continue
            if cn == capn:
                score = max(score, 100)
            elif len(cn) >= 3 and cn in capn:
                score = max(score, 60 + len(cn))
            elif len(capn) >= 3 and capn in cn:
                score = max(score, 50 + len(capn))
        # token kata + angka (mis. "sdlg" & "10")
        words = [w for w in re.findall(r"[a-zA-Z]+", cap.lower()) if len(w) >= 3]
        blob = _norm(" ".join(cands))
        nums_u = set(re.findall(r"\d+", " ".join([u.get("nomor_lambung", ""), u.get("unit_name", ""), u.get("kode_wa", "") or ""])))
        if words and nums_cap and any(w in blob for w in words) and any(n in nums_u for n in nums_cap):
            score = max(score, 80)
        if score > best_score:
            best, best_score = u, score
    return best if best_score >= 55 else None
