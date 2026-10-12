"""Pemicu tugas terjadwal dari DALAM container (Coolify → Scheduled Tasks).

Pemakaian (Command di Coolify Scheduled Task, container: aplikasi ini):
    python scripts/cron_call.py daily-summary      # 0 20 * * *   Ringkasan Harian WA 20:00 WITA
    python scripts/cron_call.py wa-outbox-retry    # */30 * * * * Kirim ulang pesan WA yang gagal sementara
    python scripts/cron_call.py piutang-reminder   # 0 * * * *    Cek jadwal Pengingat Piutang (maks 1x/hari)
    python scripts/cron_call.py weekly-report      # 0 8 * * 1    Laporan Mingguan Pemilik (Senin 08:00 WITA)

Memanggil http://127.0.0.1:$PORT/api/cron/<nama> dengan header Authorization: Bearer $WEBHOOK_CRON_SECRET.
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

JOBS = {"daily-summary", "wa-outbox-retry", "piutang-reminder", "weekly-report"}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in JOBS:
        print(f"Pemakaian: python scripts/cron_call.py <{'|'.join(sorted(JOBS))}>")
        return 2
    job = sys.argv[1]
    secret = (os.environ.get("WEBHOOK_CRON_SECRET") or "").strip()
    if not secret:
        print("WEBHOOK_CRON_SECRET belum di-set di Environment Variables")
        return 1
    port = os.environ.get("PORT", "8000")
    run_id = f"coolify-{job}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M')}-{uuid.uuid4().hex[:6]}"
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/cron/{job}",
        data=json.dumps({"run_id": run_id}).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json", "X-Webhook-Id": run_id},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"[{job}] {r.status} {r.read().decode()[:300]}")
            return 0
    except urllib.error.HTTPError as e:
        print(f"[{job}] HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:  # noqa: BLE001
        print(f"[{job}] gagal: {type(e).__name__}: {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
