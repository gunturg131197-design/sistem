#!/usr/bin/env python3
"""Test backend API untuk fitur System Status dan regresi endpoint lain."""
import requests
import sys
import json

BASE_URL = "https://admin-bonus-unit.preview.emergentagent.com/api"
def _load_secrets():
    """Nilai rahasia dibaca dari backend/.env saat tes (tidak di-hardcode di repo)."""
    keys = ("MARIADB_URL", "DB_PASSWORD", "MARIADB_PASSWORD", "WEBHOOK_CRON_SECRET", "EMERGENT_LLM_KEY", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_APP_SECRET")
    vals = []
    try:
        for line in open("/app/backend/.env"):
            k, _, v = line.strip().partition("=")
            v = v.strip().strip('"').strip("'")
            if k in keys and len(v) >= 6:
                if k == "MARIADB_URL" and "://" in v and "@" in v:
                    v = v.split("://", 1)[1].split("@", 1)[0].split(":", 1)[-1]  # ambil password saja
                vals.append(v)
    except OSError:
        pass
    return [v for v in vals if v]


SECRETS = _load_secrets()

class APITester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.issues = []

    def test(self, name, fn):
        """Run a test function and track results."""
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        try:
            fn()
            self.tests_passed += 1
            print(f"✅ PASSED")
            return True
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            self.issues.append({"test": name, "error": str(e), "type": "assertion"})
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.issues.append({"test": name, "error": str(e), "type": "exception"})
            return False

    def check_no_secrets(self, data, endpoint):
        """Check that response doesn't contain secrets."""
        text = json.dumps(data)
        for secret in SECRETS:
            if secret in text:
                raise AssertionError(f"Secret ditemukan dalam response {endpoint}: {secret[:10]}...")

    def test_health_live(self):
        """Test /api/health/live (public, no auth)."""
        def run():
            r = requests.get(f"{BASE_URL}/health/live", timeout=10)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            print(f"   Response: {data}")
            assert "status" in data, "Missing 'status' field"
            assert data["status"] == "alive", f"Expected status=alive, got {data['status']}"
            assert "startup_ready" in data, "Missing 'startup_ready' field"
            assert "version" in data, "Missing 'version' field"
            assert "uptime_seconds" in data, "Missing 'uptime_seconds' field"
            assert isinstance(data["uptime_seconds"], int), "uptime_seconds should be int"
            assert data["uptime_seconds"] > 0, "uptime_seconds should be positive"
            # Version should be 7 char commit or null
            if data["version"]:
                assert len(data["version"]) == 7, f"version should be 7 chars, got {len(data['version'])}"
            self.check_no_secrets(data, "/api/health/live")
        self.test("GET /api/health/live (public)", run)

    def test_login(self):
        """Test login with admintest/admin123."""
        def run():
            r = requests.post(f"{BASE_URL}/auth/login", json={"username": "admintest", "password": "admin123"}, timeout=10)
            assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
            data = r.json()
            print(f"   Logged in as: {data.get('name')} ({data.get('role')})")
            assert data.get("role") == "admin", f"Expected admin role, got {data.get('role')}"
            # Extract token from cookie or response
            cookies = r.cookies.get_dict()
            if "session_token" in cookies:
                self.token = cookies["session_token"]
            else:
                # Try to get from response (some APIs return token in body)
                self.token = data.get("session_token") or data.get("token")
            assert self.token, "No session token received"
            print(f"   Token: {self.token[:20]}...")
        self.test("POST /api/auth/login (admintest/admin123)", run)

    def test_system_status_unauthorized(self):
        """Test /api/admin/system-status without auth (should be 401/403)."""
        def run():
            r = requests.get(f"{BASE_URL}/admin/system-status", timeout=10)
            assert r.status_code in [401, 403], f"Expected 401/403 without auth, got {r.status_code}"
            print(f"   Correctly rejected: {r.status_code}")
        self.test("GET /api/admin/system-status (no auth) → 401/403", run)

    def test_system_status_authorized(self):
        """Test /api/admin/system-status with admin auth."""
        def run():
            assert self.token, "No token available (login first)"
            headers = {"Cookie": f"session_token={self.token}"}
            r = requests.get(f"{BASE_URL}/admin/system-status", headers=headers, timeout=10)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            print(f"   Response keys: {list(data.keys())}")
            
            # Check structure
            assert "checked_at" in data, "Missing 'checked_at'"
            assert "version" in data, "Missing 'version'"
            assert "startup" in data, "Missing 'startup'"
            assert "database" in data, "Missing 'database'"
            assert "runtime" in data, "Missing 'runtime'"
            
            # Check version structure
            v = data["version"]
            assert "commit" in v, "Missing version.commit"
            assert "commit_short" in v, "Missing version.commit_short"
            assert "commit_source" in v, "Missing version.commit_source"
            assert "branch" in v, "Missing version.branch"
            assert "message" in v, "Missing version.message"
            assert "committed_at" in v, "Missing version.committed_at"
            assert "built_at" in v, "Missing version.built_at"
            assert "repo_url" in v, "Missing version.repo_url"
            if v["commit_short"]:
                assert len(v["commit_short"]) == 7, f"commit_short should be 7 chars, got {len(v['commit_short'])}"
            print(f"   Version: {v['commit_short']} from {v['commit_source']}, branch {v['branch']}")
            
            # Check startup structure
            st = data["startup"]
            assert "started_at" in st, "Missing startup.started_at"
            assert "ready_at" in st, "Missing startup.ready_at"
            assert "ready" in st, "Missing startup.ready"
            assert "startup_seconds" in st, "Missing startup.startup_seconds"
            assert "uptime_seconds" in st, "Missing startup.uptime_seconds"
            assert isinstance(st["uptime_seconds"], int), "uptime_seconds should be int"
            print(f"   Startup: ready={st['ready']}, uptime={st['uptime_seconds']}s")
            
            # Check database structure
            db = data["database"]
            assert "engine" in db, "Missing database.engine"
            assert "name" in db, "Missing database.name"
            assert "target" in db, "Missing database.target"
            assert "ok" in db, "Missing database.ok"
            assert "latency_ms" in db, "Missing database.latency_ms"
            assert "server_version" in db, "Missing database.server_version"
            assert "tables" in db, "Missing database.tables"
            assert "error" in db, "Missing database.error"
            assert "attempts" in db, "Missing database.attempts"
            assert db["engine"] == "MariaDB", f"Expected MariaDB, got {db['engine']}"
            print(f"   Database: {db['engine']} {db['server_version']}, {db['tables']} tables, ok={db['ok']}")
            
            # Check runtime structure
            rt = data["runtime"]
            assert "platform" in rt, "Missing runtime.platform"
            assert "domain" in rt, "Missing runtime.domain"
            assert "python" in rt, "Missing runtime.python"
            assert "timezone" in rt, "Missing runtime.timezone"
            assert "port" in rt, "Missing runtime.port"
            assert "extra_ports" in rt, "Missing runtime.extra_ports"
            print(f"   Runtime: {rt['platform']}, domain={rt['domain']}, Python {rt['python']}, port {rt['port']}")
            
            # Check no secrets
            self.check_no_secrets(data, "/api/admin/system-status")
            
        self.test("GET /api/admin/system-status (admin) → 200 with full structure", run)

    def test_regression_endpoints(self):
        """Test regression endpoints to ensure they still work."""
        assert self.token, "No token available (login first)"
        headers = {"Cookie": f"session_token={self.token}"}
        
        endpoints = [
            ("/units", "GET"),
            ("/operations", "GET"),
            ("/bonus-admin", "GET"),
            ("/admin/backup/info", "GET"),
        ]
        
        for path, method in endpoints:
            def run():
                url = f"{BASE_URL}{path}"
                r = requests.request(method, url, headers=headers, timeout=10)
                assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
                data = r.json()
                print(f"   Response type: {type(data)}, length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
            self.test(f"{method} /api{path} → 200", run)

    def run_all(self):
        """Run all tests in order."""
        print("=" * 60)
        print("BACKEND API TESTING - System Status Feature")
        print("=" * 60)
        
        # Test health/live first (public)
        self.test_health_live()
        
        # Test system-status without auth
        self.test_system_status_unauthorized()
        
        # Login
        self.test_login()
        
        # Test system-status with auth
        if self.token:
            self.test_system_status_authorized()
            self.test_regression_endpoints()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 60)
        
        if self.issues:
            print("\n❌ ISSUES FOUND:")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue['test']}: {issue['error']}")
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    tester = APITester()
    sys.exit(tester.run_all())
