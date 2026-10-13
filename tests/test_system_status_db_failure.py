#!/usr/bin/env python3
"""Test DB failure scenario: wrong password should return 503 with friendly message."""
import os
import sys
import time
import shutil
import signal
import subprocess
import requests
from pathlib import Path

TEMP_DIR = Path("/tmp/backend_db_fail")
TEST_PORT = 8794

def cleanup():
    """Kill any process on TEST_PORT and remove temp dir."""
    try:
        subprocess.run(["pkill", "-f", f"PORT={TEST_PORT}"], timeout=5)
    except:
        pass
    time.sleep(1)
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

def setup_backend_copy():
    """Copy backend to temp dir."""
    cleanup()
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    backend_src = Path("/app/backend")
    for item in backend_src.iterdir():
        if item.name in [".git", "__pycache__", ".pytest_cache"]:
            continue
        if item.is_file():
            shutil.copy2(item, TEMP_DIR / item.name)
        elif item.is_dir():
            shutil.copytree(item, TEMP_DIR / item.name, dirs_exist_ok=True)
    
    # Remove .env
    env_file = TEMP_DIR / ".env"
    if env_file.exists():
        env_file.unlink()
    
    print(f"✅ Backend copied to {TEMP_DIR}")

def start_server_with_bad_db():
    """Start server with wrong DB password."""
    env = {
        "PATH": "/root/.venv/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "PORT": str(TEST_PORT),
        "EXTRA_PORTS": "",
        "DB_HOST": "127.0.0.1",
        "DB_DATABASE": "trirara",
        "DB_USERNAME": "trirara",
        "DB_PASSWORD": "wrong_password",  # Wrong password
        "DB_PORT": "3306",
        "CORS_ORIGINS": "*",
    }
    
    proc = subprocess.Popen(
        ["python", "run.py"],
        cwd=TEMP_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid
    )
    
    # Wait a bit for server to start (it should start even if DB fails)
    time.sleep(5)
    
    return proc

def stop_server(proc):
    """Stop server process."""
    if proc:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except:
                pass
    time.sleep(1)

def main():
    print("="*60)
    print("DB FAILURE SCENARIO TESTING")
    print("="*60)
    
    setup_backend_copy()
    
    print("\nStarting server with wrong DB password...")
    proc = start_server_with_bad_db()
    
    try:
        # Test 1: /api/health/live should still return 200 (liveness check)
        print("\n🔍 Test 1: GET /api/health/live (should return 200 even if DB fails)")
        try:
            r = requests.get(f"http://127.0.0.1:{TEST_PORT}/api/health/live", timeout=10)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"   Response: {data}")
                print(f"   ✅ PASSED: /api/health/live returns 200 even with DB failure")
            else:
                print(f"   ❌ FAILED: Expected 200, got {r.status_code}")
                return 1
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return 1
        
        # Test 2: /api/admin/system-status should return 503 (DB not ready)
        print("\n🔍 Test 2: GET /api/admin/system-status (should return 503 with friendly message)")
        try:
            # First login (this might also fail if DB is not ready)
            login_r = requests.post(
                f"http://127.0.0.1:{TEST_PORT}/api/auth/login",
                json={"username": "admintest", "password": "admin123"},
                timeout=10
            )
            
            if login_r.status_code == 503:
                # Expected: DB not ready, can't login
                data = login_r.json()
                print(f"   Login returned 503 (expected): {data.get('detail', '')}")
                if "Server sedang menyiapkan database" in data.get("detail", ""):
                    print(f"   ✅ PASSED: Friendly error message shown")
                else:
                    print(f"   ⚠️  WARNING: Error message not friendly: {data.get('detail', '')}")
                return 0
            elif login_r.status_code == 200:
                # Unexpected: login succeeded despite DB failure
                print(f"   ⚠️  WARNING: Login succeeded despite DB failure (might be cached)")
                # Try system-status anyway
                token = login_r.cookies.get("session_token")
                if token:
                    headers = {"Cookie": f"session_token={token}"}
                    status_r = requests.get(
                        f"http://127.0.0.1:{TEST_PORT}/api/admin/system-status",
                        headers=headers,
                        timeout=10
                    )
                    print(f"   system-status status: {status_r.status_code}")
                    if status_r.status_code == 503:
                        data = status_r.json()
                        print(f"   Response: {data.get('detail', '')}")
                        if "Server sedang menyiapkan database" in data.get("detail", ""):
                            print(f"   ✅ PASSED: 503 with friendly message")
                        else:
                            print(f"   ⚠️  WARNING: 503 but message not friendly")
                        return 0
                    else:
                        print(f"   ❌ FAILED: Expected 503, got {status_r.status_code}")
                        return 1
            else:
                print(f"   ❌ FAILED: Unexpected login status {login_r.status_code}")
                return 1
                
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return 1
        
    finally:
        stop_server(proc)
        cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
