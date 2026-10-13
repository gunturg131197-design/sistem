"""Test run.py production simulation.

Tests:
1. run.py with empty env (should get 503 with DB error hints)
2. run.py with correct DB env (should work)
3. Port conflict handling (EXTRA_PORTS already in use)
4. Multiple ports serving same app
"""
import subprocess
import time
import requests
import os
import shutil
import tempfile
import signal

def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
    print(f"{prefix} {msg}")

def find_free_port(start=8700):
    """Find a free port starting from start."""
    import socket
    for port in range(start, start + 100):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except OSError:
            continue
    raise RuntimeError("No free ports found")

def test_run_py_empty_env():
    """Test run.py with empty env (should get 503 with DB error)."""
    log("\n=== Test 1: run.py with empty env (DB error expected) ===", "INFO")
    
    # Copy backend to temp dir
    temp_dir = tempfile.mkdtemp(prefix="runpy_test_")
    log(f"Temp dir: {temp_dir}", "INFO")
    
    try:
        # Copy backend files
        for item in os.listdir("/app/backend"):
            src = os.path.join("/app/backend", item)
            dst = os.path.join(temp_dir, item)
            if os.path.isfile(src) and item != ".env":
                shutil.copy2(src, dst)
            elif os.path.isdir(src) and item not in ["__pycache__", ".pytest_cache"]:
                shutil.copytree(src, dst)
        
        # Find free ports
        port1 = find_free_port(8700)
        port2 = find_free_port(port1 + 1)
        log(f"Using ports: {port1} (main), {port2} (extra)", "INFO")
        
        # Start run.py with minimal env (no DB credentials)
        env = {
            "PATH": f"/tmp/prodsim/venv/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "PORT": str(port1),
            "EXTRA_PORTS": str(port2),
            "PYTHONUNBUFFERED": "1"
        }
        
        log("Starting run.py with empty DB env...", "INFO")
        proc = subprocess.Popen(
            ["python", "run.py"],
            cwd=temp_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        time.sleep(8)
        
        # Test /api/health/live on both ports (should return 200)
        for port in [port1, port2]:
            try:
                r = requests.get(f"http://127.0.0.1:{port}/api/health/live", timeout=5)
                if r.status_code == 200:
                    log(f"✅ Port {port}: /api/health/live returns 200", "PASS")
                else:
                    log(f"❌ Port {port}: /api/health/live returns {r.status_code}", "FAIL")
            except Exception as e:
                log(f"❌ Port {port}: /api/health/live failed: {e}", "FAIL")
        
        # Test /api/health (should return 503 with DB error)
        try:
            r = requests.get(f"http://127.0.0.1:{port1}/api/health", timeout=5)
            if r.status_code == 503:
                data = r.json()
                log(f"✅ /api/health returns 503 (expected)", "PASS")
                log(f"  Detail: {data.get('detail', '')[:100]}", "INFO")
                log(f"  Hint: {data.get('hint', '')[:100]}", "INFO")
                
                # Check for helpful error message
                if "DB_HOST" in data.get("hint", "") or "DB_" in str(data):
                    log(f"✅ Error message contains DB hints", "PASS")
                else:
                    log(f"⚠️  Error message should mention DB_HOST/DB_PORT/etc", "WARN")
            else:
                log(f"❌ /api/health should return 503, got {r.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ /api/health failed: {e}", "FAIL")
        
        # Test /api/units (should return 503 with guard message)
        try:
            r = requests.get(f"http://127.0.0.1:{port1}/api/units", timeout=5)
            if r.status_code == 503:
                data = r.json()
                log(f"✅ /api/units returns 503 (DB not ready guard)", "PASS")
                if "menyiapkan database" in data.get("detail", "").lower():
                    log(f"✅ Guard message correct: {data.get('detail', '')}", "PASS")
                else:
                    log(f"⚠️  Guard message: {data.get('detail', '')}", "WARN")
            else:
                log(f"❌ /api/units should return 503, got {r.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ /api/units failed: {e}", "FAIL")
        
        # Check process count (should be only 1 python process)
        try:
            ps_output = subprocess.check_output(
                ["ps", "aux"], text=True
            )
            python_procs = [line for line in ps_output.split("\n") if "run.py" in line and str(port1) in line]
            if len(python_procs) == 1:
                log(f"✅ Only 1 python process serving both ports", "PASS")
            else:
                log(f"⚠️  Found {len(python_procs)} python processes", "WARN")
        except Exception as e:
            log(f"⚠️  Could not check process count: {e}", "WARN")
        
        return True
        
    finally:
        # Cleanup
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        log("Cleanup done", "INFO")

def test_run_py_correct_db():
    """Test run.py with correct DB env (should work)."""
    log("\n=== Test 2: run.py with correct DB env ===", "INFO")
    
    # Copy backend to temp dir
    temp_dir = tempfile.mkdtemp(prefix="runpy_test_db_")
    log(f"Temp dir: {temp_dir}", "INFO")
    
    try:
        # Copy backend files
        for item in os.listdir("/app/backend"):
            src = os.path.join("/app/backend", item)
            dst = os.path.join(temp_dir, item)
            if os.path.isfile(src) and item != ".env":
                shutil.copy2(src, dst)
            elif os.path.isdir(src) and item not in ["__pycache__", ".pytest_cache"]:
                shutil.copytree(src, dst)
        
        # Find free ports
        port1 = find_free_port(8750)
        port2 = find_free_port(port1 + 1)
        log(f"Using ports: {port1} (main), {port2} (extra)", "INFO")
        
        # Start run.py with correct DB env
        env = {
            "PATH": f"/tmp/prodsim/venv/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "PORT": str(port1),
            "EXTRA_PORTS": str(port2),
            "MARIADB_URL": "mysql+asyncmy://trirara:trirara_dev@127.0.0.1:3306/trirara?charset=utf8mb4",
            "PYTHONUNBUFFERED": "1",
            "ADMIN_USERNAME": "admintest",
            "ADMIN_PASSWORD": "admin123"
        }
        
        log("Starting run.py with correct DB env...", "INFO")
        proc = subprocess.Popen(
            ["python", "run.py"],
            cwd=temp_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
        
        # Wait for startup (DB connection takes time)
        log("Waiting for DB connection...", "INFO")
        time.sleep(12)
        
        # Test /api/health (should return 200 with startup_ready=true)
        try:
            r = requests.get(f"http://127.0.0.1:{port1}/api/health", timeout=10)
            if r.status_code == 200:
                data = r.json()
                log(f"✅ /api/health returns 200", "PASS")
                log(f"  Status: {data.get('status')}, startup_ready: {data.get('startup_ready')}", "INFO")
                if data.get("startup_ready"):
                    log(f"✅ startup_ready is True", "PASS")
                else:
                    log(f"⚠️  startup_ready is False (DB might still be connecting)", "WARN")
            else:
                log(f"❌ /api/health returns {r.status_code}", "FAIL")
                log(f"  Response: {r.text[:200]}", "FAIL")
        except Exception as e:
            log(f"❌ /api/health failed: {e}", "FAIL")
        
        # Test login
        try:
            r = requests.post(
                f"http://127.0.0.1:{port1}/api/auth/login",
                json={"username": "admintest", "password": "admin123"},
                timeout=10
            )
            if r.status_code == 200:
                log(f"✅ Login successful", "PASS")
            else:
                log(f"❌ Login failed: {r.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ Login failed: {e}", "FAIL")
        
        return True
        
    finally:
        # Cleanup
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        log("Cleanup done", "INFO")

def test_run_py_port_conflict():
    """Test run.py with port conflict (EXTRA_PORTS already in use)."""
    log("\n=== Test 3: run.py with port conflict ===", "INFO")
    
    # Copy backend to temp dir
    temp_dir = tempfile.mkdtemp(prefix="runpy_test_conflict_")
    log(f"Temp dir: {temp_dir}", "INFO")
    
    try:
        # Copy backend files
        for item in os.listdir("/app/backend"):
            src = os.path.join("/app/backend", item)
            dst = os.path.join(temp_dir, item)
            if os.path.isfile(src) and item != ".env":
                shutil.copy2(src, dst)
            elif os.path.isdir(src) and item not in ["__pycache__", ".pytest_cache"]:
                shutil.copytree(src, dst)
        
        # Find free port for main
        port1 = find_free_port(8800)
        log(f"Using port: {port1} (main), EXTRA_PORTS=8001 (already in use by supervisor)", "INFO")
        
        # Start run.py with EXTRA_PORTS pointing to already-used port
        env = {
            "PATH": f"/tmp/prodsim/venv/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "PORT": str(port1),
            "EXTRA_PORTS": "8001",  # This port is used by supervisor backend
            "PYTHONUNBUFFERED": "1"
        }
        
        log("Starting run.py with conflicting EXTRA_PORTS...", "INFO")
        proc = subprocess.Popen(
            ["python", "run.py"],
            cwd=temp_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        time.sleep(5)
        
        # Check if main port still works
        try:
            r = requests.get(f"http://127.0.0.1:{port1}/api/health/live", timeout=5)
            if r.status_code == 200:
                log(f"✅ Main port {port1} works despite EXTRA_PORTS conflict", "PASS")
            else:
                log(f"❌ Main port {port1} returns {r.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ Main port {port1} failed: {e}", "FAIL")
        
        # Check logs for "dilewati" message
        try:
            proc.terminate()
            output, _ = proc.communicate(timeout=3)
            if "dilewati" in output or "skipped" in output.lower():
                log(f"✅ Log shows conflicting port was skipped", "PASS")
            else:
                log(f"⚠️  Log doesn't show skip message (might have crashed)", "WARN")
        except:
            pass
        
        return True
        
    finally:
        # Cleanup
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        log("Cleanup done", "INFO")

def main():
    log("\n" + "="*70, "INFO")
    log("run.py Production Simulation Tests", "INFO")
    log("="*70 + "\n", "INFO")
    
    try:
        test_run_py_empty_env()
        test_run_py_correct_db()
        test_run_py_port_conflict()
        
        log("\n" + "="*70, "INFO")
        log("All run.py simulation tests completed", "INFO")
        log("="*70 + "\n", "INFO")
        
    except Exception as e:
        log(f"\n❌ Test suite failed: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
