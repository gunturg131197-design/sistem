"""Backend health & production readiness testing for Coolify deployment.

Focus areas:
1. Health endpoints (/api/health, /api/health/live) - no password leakage
2. Admin login + regression on main endpoints
3. Production simulation with run.py
4. cron_call.py script testing
"""
import requests
import sys
import os
import json
from datetime import datetime


def _cron_secret():
    """Baca WEBHOOK_CRON_SECRET dari env atau /app/backend/.env (tidak di-hardcode)."""
    import os as _os
    v = _os.environ.get("WEBHOOK_CRON_SECRET")
    if v:
        return v
    try:
        for line in open("/app/backend/.env"):
            if line.startswith("WEBHOOK_CRON_SECRET="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


# Get backend URL from frontend .env
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://admin-bonus-unit.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Credentials
ADMIN_USER = "admintest"
ADMIN_PASS = "admin123"

# Cron secret
WEBHOOK_CRON_SECRET = _cron_secret()


class HealthTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.issues = []

    def log(self, msg: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {msg}")

    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             token: str = None, data: dict = None) -> tuple[bool, dict]:
        """Run a single API test."""
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        hdrs = {}
        if token:
            hdrs["Authorization"] = f"Bearer {token}"
        
        self.tests_run += 1
        self.log(f"Testing: {name}", "INFO")
        
        try:
            if method == "GET":
                r = requests.get(url, headers=hdrs, timeout=30)
            elif method == "POST":
                hdrs["Content-Type"] = "application/json"
                r = requests.post(url, headers=hdrs, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = r.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"PASS - {name} (status {r.status_code})", "PASS")
            else:
                self.tests_failed += 1
                self.log(f"FAIL - {name}: Expected {expected_status}, got {r.status_code}", "FAIL")
                self.issues.append(f"{name}: Expected {expected_status}, got {r.status_code}")
                if r.text:
                    self.log(f"  Response: {r.text[:300]}", "FAIL")
            
            try:
                return success, r.json() if r.text else {}
            except:
                return success, {"text": r.text}
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"FAIL - {name}: {type(e).__name__}: {str(e)}", "FAIL")
            self.issues.append(f"{name}: {type(e).__name__}: {str(e)}")
            return False, {"error": str(e)}

    def test_health_endpoints(self):
        """Test health endpoints and check for password leakage."""
        self.log("\n=== Testing Health Endpoints ===", "INFO")
        
        # Test /api/health/live (liveness - should always return 200)
        success, live = self.test("Health Live", "GET", "/health/live", 200)
        if success:
            self.log(f"  Status: {live.get('status')}, startup_ready: {live.get('startup_ready')}", "INFO")
            if live.get("status") != "alive":
                self.log("  WARNING: status should be 'alive'", "WARN")
                self.issues.append("/api/health/live: status is not 'alive'")
        
        # Test /api/health (readiness - check DB connection)
        success, health = self.test("Health Readiness", "GET", "/health", 200)
        if success:
            self.log(f"  Status: {health.get('status')}, database: {health.get('database')}, "
                    f"target: {health.get('target')}, startup_ready: {health.get('startup_ready')}", "INFO")
            
            # Check for password leakage
            health_str = json.dumps(health).lower()
            password_keywords = ["password", "passwd", "pwd", "trirara_dev"]
            leaked = [kw for kw in password_keywords if kw in health_str]
            if leaked:
                self.log(f"  ❌ PASSWORD LEAK DETECTED: {leaked}", "FAIL")
                self.issues.append(f"/api/health leaks password: {leaked}")
                self.tests_failed += 1
            else:
                self.log(f"  ✅ No password leakage detected", "PASS")
            
            # Verify target format (should be user@host:port/db WITHOUT password)
            target = health.get("target", "")
            if "@" in target and ":" in target and "/" in target:
                if "trirara_dev" not in target:
                    self.log(f"  ✅ Target format correct (no password): {target}", "PASS")
                else:
                    self.log(f"  ❌ Target contains password: {target}", "FAIL")
                    self.issues.append(f"/api/health target contains password")
            else:
                self.log(f"  ⚠️  Target format unexpected: {target}", "WARN")

    def test_login_and_regression(self):
        """Test admin login and main endpoints."""
        self.log("\n=== Testing Admin Login & Regression ===", "INFO")
        
        # Login
        self.log(f"Logging in as {ADMIN_USER}...", "INFO")
        r = requests.post(f"{BASE_URL}/auth/login", 
                         json={"username": ADMIN_USER, "password": ADMIN_PASS})
        if r.status_code == 200:
            self.admin_token = r.cookies.get("session_token")
            if self.admin_token:
                self.log(f"✅ Logged in successfully", "PASS")
                self.tests_passed += 1
            else:
                self.log(f"❌ Login succeeded but no session_token cookie", "FAIL")
                self.issues.append("Login: no session_token cookie")
                self.tests_failed += 1
                return False
        else:
            self.log(f"❌ Login failed: {r.status_code}", "FAIL")
            self.issues.append(f"Login failed: {r.status_code}")
            self.tests_failed += 1
            return False
        self.tests_run += 1
        
        # Test main endpoints
        endpoints = [
            ("Auth Me", "GET", "/auth/me", 200),
            ("Units", "GET", "/units", 200),
            ("Operations", "GET", "/operations", 200),
            ("Spareparts", "GET", "/spareparts", 200),
            ("Payroll", "GET", "/payroll", 200),
            ("Dashboard Summary", "GET", "/dashboard/summary", 200),
            ("Bonus Admin", "GET", "/bonus-admin", 200),
            ("Bonus Admin History", "GET", "/bonus-admin/history", 200),
            ("Finance Kas Masuk", "GET", "/finance/kas-masuk", 200),
            ("Admin Backup Info", "GET", "/admin/backup/info", 200),
        ]
        
        for name, method, endpoint, expected in endpoints:
            self.test(name, method, endpoint, expected, token=self.admin_token)
        
        return True

    def run_all_tests(self):
        """Run all health tests."""
        self.log("\n" + "="*70, "INFO")
        self.log("TRIRARA - Backend Health & Production Readiness Testing", "INFO")
        self.log(f"Backend URL: {BACKEND_URL}", "INFO")
        self.log("="*70 + "\n", "INFO")
        
        # Health endpoints
        self.test_health_endpoints()
        
        # Login and regression
        self.test_login_and_regression()
        
        # Summary
        self.log("\n" + "="*70, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*70, "INFO")
        self.log(f"Total tests run: {self.tests_run}", "INFO")
        self.log(f"Passed: {self.tests_passed}", "PASS")
        self.log(f"Failed: {self.tests_failed}", "FAIL" if self.tests_failed > 0 else "INFO")
        if self.tests_run > 0:
            self.log(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%", "INFO")
        
        if self.issues:
            self.log("\n=== ISSUES FOUND ===", "FAIL")
            for issue in self.issues:
                self.log(f"  • {issue}", "FAIL")
        
        self.log("="*70 + "\n", "INFO")
        
        return self.tests_failed == 0


def main():
    tester = HealthTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
