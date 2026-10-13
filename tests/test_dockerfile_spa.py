"""Static review of /app/Dockerfile and SPA serving test.

Checks:
1. Dockerfile has curl & wget installed
2. HEALTHCHECK uses curl on /api/health/live with ${PORT}
3. CMD is python run.py
4. run.py is copied to /app/
5. EXPOSE includes 8000 and 3000
6. Test SPA serving with STATIC_DIR
"""
import subprocess
import os
import tempfile
import shutil
import time
import requests
import signal

def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
    print(f"{prefix} {msg}")

def review_dockerfile():
    log("\n=== Static Dockerfile Review ===", "INFO")
    
    with open("/app/Dockerfile", "r") as f:
        content = f.read()
    
    # Check 1: curl & wget installed
    if "curl" in content and "wget" in content:
        log("✅ Dockerfile installs curl & wget", "PASS")
    else:
        log("❌ Dockerfile missing curl or wget installation", "FAIL")
    
    # Check 2: HEALTHCHECK uses curl on /api/health/live
    if "HEALTHCHECK" in content and "/api/health/live" in content and "curl" in content:
        log("✅ HEALTHCHECK uses curl on /api/health/live", "PASS")
        if "${PORT" in content or "$PORT" in content:
            log("✅ HEALTHCHECK uses ${PORT} variable", "PASS")
        else:
            log("⚠️  HEALTHCHECK should use ${PORT} variable", "WARN")
    else:
        log("❌ HEALTHCHECK not configured correctly", "FAIL")
    
    # Check 3: CMD is python run.py
    if 'CMD ["python", "run.py"]' in content:
        log("✅ CMD is python run.py", "PASS")
    else:
        log("❌ CMD should be python run.py", "FAIL")
    
    # Check 4: run.py is copied
    if "COPY" in content and "run.py" in content:
        log("✅ run.py is copied to image", "PASS")
    elif "COPY" in content and "backend/" in content:
        log("✅ backend/ directory (including run.py) is copied", "PASS")
    else:
        log("⚠️  Cannot verify run.py is copied", "WARN")
    
    # Check 5: EXPOSE includes 8000 and 3000
    if "EXPOSE 8000" in content or "EXPOSE 8000 3000" in content:
        log("✅ EXPOSE includes 8000", "PASS")
    else:
        log("❌ EXPOSE should include 8000", "FAIL")
    
    if "3000" in content:
        log("✅ EXPOSE includes 3000", "PASS")
    else:
        log("⚠️  EXPOSE should include 3000 for backward compatibility", "WARN")

def find_free_port(start=8850):
    """Find a free port."""
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

def test_spa_serving():
    log("\n=== Test SPA Serving with STATIC_DIR ===", "INFO")
    
    # Check if frontend build exists
    if not os.path.exists("/app/frontend/build/index.html"):
        log("⚠️  Frontend build not found at /app/frontend/build", "WARN")
        log("  Skipping SPA serving test", "WARN")
        return
    
    # Copy backend to temp dir
    temp_dir = tempfile.mkdtemp(prefix="spa_test_")
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
        
        # Find free port
        port = find_free_port(8850)
        log(f"Using port: {port}", "INFO")
        
        # Start run.py with STATIC_DIR pointing to frontend build
        env = {
            "PATH": f"/tmp/prodsim/venv/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "PORT": str(port),
            "EXTRA_PORTS": "",  # Disable extra ports
            "STATIC_DIR": "/app/frontend/build",
            "MARIADB_URL": "mysql+asyncmy://trirara:trirara_dev@127.0.0.1:3306/trirara?charset=utf8mb4",
            "PYTHONUNBUFFERED": "1",
            "ADMIN_USERNAME": "admintest",
            "ADMIN_PASSWORD": "admin123"
        }
        
        log("Starting run.py with STATIC_DIR=/app/frontend/build...", "INFO")
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
        time.sleep(10)
        
        # Test 1: Root path / should return index.html
        try:
            r = requests.get(f"http://127.0.0.1:{port}/", timeout=5)
            if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
                log(f"✅ GET / returns 200 text/html", "PASS")
                if "<div id=\"root\">" in r.text or "<!DOCTYPE html>" in r.text:
                    log(f"✅ Response contains HTML content", "PASS")
            else:
                log(f"❌ GET / returns {r.status_code} {r.headers.get('Content-Type')}", "FAIL")
        except Exception as e:
            log(f"❌ GET / failed: {e}", "FAIL")
        
        # Test 2: React Router path /dashboard should return index.html
        try:
            r = requests.get(f"http://127.0.0.1:{port}/dashboard", timeout=5)
            if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
                log(f"✅ GET /dashboard returns 200 text/html (SPA routing)", "PASS")
            else:
                log(f"❌ GET /dashboard returns {r.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ GET /dashboard failed: {e}", "FAIL")
        
        # Test 3: /bonus-admin path should return index.html
        try:
            r = requests.get(f"http://127.0.0.1:{port}/bonus-admin", timeout=5)
            if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
                log(f"✅ GET /bonus-admin returns 200 text/html (SPA routing)", "PASS")
            else:
                log(f"❌ GET /bonus-admin returns {r.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ GET /bonus-admin failed: {e}", "FAIL")
        
        # Test 4: /api/tidakada should return 404 JSON (not index.html)
        try:
            r = requests.get(f"http://127.0.0.1:{port}/api/tidakada", timeout=5)
            if r.status_code == 404:
                log(f"✅ GET /api/tidakada returns 404 (API route)", "PASS")
                if "application/json" in r.headers.get("Content-Type", ""):
                    log(f"✅ Response is JSON, not HTML", "PASS")
                else:
                    log(f"⚠️  Response Content-Type: {r.headers.get('Content-Type')}", "WARN")
            else:
                log(f"❌ GET /api/tidakada returns {r.status_code} (expected 404)", "FAIL")
        except Exception as e:
            log(f"❌ GET /api/tidakada failed: {e}", "FAIL")
        
        # Test 5: Static asset should return with correct Content-Type
        try:
            # Find a JS file in build/static/js/
            js_files = []
            static_js_dir = "/app/frontend/build/static/js"
            if os.path.exists(static_js_dir):
                js_files = [f for f in os.listdir(static_js_dir) if f.endswith(".js")]
            
            if js_files:
                js_file = js_files[0]
                r = requests.get(f"http://127.0.0.1:{port}/static/js/{js_file}", timeout=5)
                if r.status_code == 200:
                    log(f"✅ GET /static/js/{js_file} returns 200", "PASS")
                    content_type = r.headers.get("Content-Type", "")
                    if "javascript" in content_type or "application/octet-stream" in content_type:
                        log(f"✅ Content-Type is appropriate: {content_type}", "PASS")
                    else:
                        log(f"⚠️  Content-Type: {content_type}", "WARN")
                else:
                    log(f"❌ GET /static/js/{js_file} returns {r.status_code}", "FAIL")
            else:
                log(f"⚠️  No JS files found in build/static/js/", "WARN")
        except Exception as e:
            log(f"⚠️  Static asset test failed: {e}", "WARN")
        
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
    log("Dockerfile Review & SPA Serving Tests", "INFO")
    log("="*70 + "\n", "INFO")
    
    try:
        review_dockerfile()
        test_spa_serving()
        
        log("\n" + "="*70, "INFO")
        log("All Dockerfile & SPA tests completed", "INFO")
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
