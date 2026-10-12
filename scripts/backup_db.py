#!/usr/bin/env python3
"""Pembungkus: script asli ada di backend/scripts/backup_db.py (ikut ter-build ke image backend)."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "backup_db.py"
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
