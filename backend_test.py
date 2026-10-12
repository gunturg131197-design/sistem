"""Comprehensive backend API testing for TRIRARA TUNGGAL PUTRA.

Tests:
1. Authentication (admin/admin123, operator budi/budi123)
2. HM Janggal detection & settings
3. Pengingat Piutang (aging, settings, preview, run, history, cron)
4. Laporan Mingguan (settings, preview, run, history, cron)
5. WA Simulation (inbound text/image)
6. Outbox simulation
7. Backup & restore
8. Security (admin vs operator access)
9. Regression (stable features)
"""
import requests
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Get backend URL from frontend .env
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://theme-logo-studio.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Credentials from /app/memory/test_credentials.md
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
OPERATOR_USER = "budi"
OPERATOR_PASS = "budi123"

# Cron secret from backend/.env
WEBHOOK_CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET", "NVPcg0VxXn9FrHRhtF0PKCqFht7-vRWE5fssbXZtPhogyZ66uZfuJA")


class APITester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.operator_token = None
        self.test_data_ids = []  # Track created test data for cleanup

    def log(self, msg: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {msg}")

    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             token: Optional[str] = None, data: Optional[dict] = None, 
             headers: Optional[dict] = None, files: Optional[dict] = None) -> tuple[bool, dict]:
        """Run a single API test."""
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        hdrs = headers or {}
        if token:
            hdrs["Authorization"] = f"Bearer {token}"
        
        self.tests_run += 1
        self.log(f"Testing: {name}", "INFO")
        
        try:
            if method == "GET":
                r = requests.get(url, headers=hdrs, timeout=30)
            elif method == "POST":
                if files:
                    r = requests.post(url, headers=hdrs, data=data, files=files, timeout=30)
                else:
                    hdrs["Content-Type"] = "application/json"
                    r = requests.post(url, headers=hdrs, json=data, timeout=30)
            elif method == "PUT":
                hdrs["Content-Type"] = "application/json"
                r = requests.put(url, headers=hdrs, json=data, timeout=30)
            elif method == "PATCH":
                hdrs["Content-Type"] = "application/json"
                r = requests.patch(url, headers=hdrs, json=data, timeout=30)
            elif method == "DELETE":
                r = requests.delete(url, headers=hdrs, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = r.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"PASS - {name} (status {r.status_code})", "PASS")
            else:
                self.tests_failed += 1
                self.log(f"FAIL - {name}: Expected {expected_status}, got {r.status_code}", "FAIL")
                if r.text:
                    self.log(f"  Response: {r.text[:200]}", "FAIL")
            
            try:
                return success, r.json() if r.text else {}
            except:
                return success, {"text": r.text}
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"FAIL - {name}: {type(e).__name__}: {str(e)}", "FAIL")
            return False, {"error": str(e)}

    def login(self, username: str, password: str) -> Optional[str]:
        """Login and return session token."""
        self.log(f"Logging in as {username}...", "INFO")
        success, resp = self.test(
            f"Login as {username}",
            "POST",
            "/auth/login",
            200,
            data={"username": username, "password": password}
        )
        if success:
            # Extract token from Set-Cookie header or response
            # For now, we'll make another request to get the token
            r = requests.post(f"{BASE_URL}/auth/login", 
                            json={"username": username, "password": password})
            if r.status_code == 200:
                # Check if session_token is in cookies
                token = r.cookies.get("session_token")
                if token:
                    self.log(f"Logged in successfully as {username}", "PASS")
                    return token
        return None

    def test_auth(self):
        """Test authentication."""
        self.log("\n=== Testing Authentication ===", "INFO")
        
        # Login as admin
        self.admin_token = self.login(ADMIN_USER, ADMIN_PASS)
        if not self.admin_token:
            self.log("Failed to login as admin - cannot continue", "FAIL")
            return False
        
        # Login as operator
        self.operator_token = self.login(OPERATOR_USER, OPERATOR_PASS)
        if not self.operator_token:
            self.log("Failed to login as operator", "FAIL")
        
        # Test /auth/me
        self.test("Get current user (admin)", "GET", "/auth/me", 200, token=self.admin_token)
        
        return True

    def test_security(self):
        """Test security: operator should not access admin endpoints."""
        self.log("\n=== Testing Security (Admin vs Operator) ===", "INFO")
        
        if not self.operator_token:
            self.log("Skipping security tests - no operator token", "WARN")
            return
        
        # Operator should get 403 on admin endpoints
        self.test("Operator access to /wa/status (should fail)", "GET", "/wa/status", 403, 
                 token=self.operator_token)
        self.test("Operator access to /admin/backup/info (should fail)", "GET", "/admin/backup/info", 403,
                 token=self.operator_token)
        
        # Unauthenticated should get 401
        self.test("Unauthenticated access to /wa/status", "GET", "/wa/status", 401)

    def test_hm_janggal(self):
        """Test HM Janggal (abnormal hour meter) detection."""
        self.log("\n=== Testing HM Janggal Detection ===", "INFO")
        
        # Get current auto settings
        success, settings = self.test("Get auto settings", "GET", "/wa/auto-settings", 200, 
                                     token=self.admin_token)
        if success:
            self.log(f"  Current HM settings: spike_check={settings.get('hm_spike_check')}, "
                    f"max_per_day={settings.get('hm_max_per_day')}, "
                    f"min_confidence={settings.get('min_confidence')}", "INFO")
        
        # Test updating HM settings
        self.test("Update HM settings (valid)", "PUT", "/wa/auto-settings", 200,
                 token=self.admin_token,
                 data={
                     "transfer_enabled": False,
                     "hm_enabled": False,
                     "min_confidence": 0.9,
                     "hm_spike_check": True,
                     "hm_max_per_day": 20.0
                 })
        
        # Test invalid hm_max_per_day (> 24)
        self.test("Update HM settings (invalid max > 24)", "PUT", "/wa/auto-settings", 400,
                 token=self.admin_token,
                 data={
                     "transfer_enabled": False,
                     "hm_enabled": False,
                     "min_confidence": 0.9,
                     "hm_max_per_day": 25.0
                 })
        
        # Test invalid min_confidence (< 0.9)
        self.test("Update HM settings (invalid confidence < 0.9)", "PUT", "/wa/auto-settings", 400,
                 token=self.admin_token,
                 data={
                     "transfer_enabled": False,
                     "hm_enabled": False,
                     "min_confidence": 0.85,
                     "hm_max_per_day": 20.0
                 })
        
        # Get inbox with HM flag filter
        self.test("Get inbox with HM flag filter", "GET", "/wa/inbox?status=pending,duplicate&flag=hm", 200,
                 token=self.admin_token)
        
        # Get WA status (should include hm_flag count)
        success, status = self.test("Get WA status", "GET", "/wa/status", 200, token=self.admin_token)
        if success:
            counts = status.get("counts", {})
            self.log(f"  WA status counts: {counts}", "INFO")

    def test_piutang_aging(self):
        """Test Pengingat Piutang (debt reminders) - aging calculation."""
        self.log("\n=== Testing Piutang Aging ===", "INFO")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get aging report
        success, aging = self.test("Get piutang aging", "GET", f"/wa/piutang/aging?as_of={today}", 200,
                                  token=self.admin_token)
        if success:
            items = aging.get("items", [])
            self.log(f"  Found {len(items)} pengurus with piutang data", "INFO")
            if items:
                sample = items[0]
                self.log(f"  Sample: {sample.get('pengurus')} - piutang: {sample.get('piutang')}, "
                        f"umur: {sample.get('umur_hari')} hari", "INFO")

    def test_piutang_settings(self):
        """Test Pengingat Piutang settings."""
        self.log("\n=== Testing Piutang Reminder Settings ===", "INFO")
        
        # Get current settings
        success, settings = self.test("Get reminder settings", "GET", "/wa/reminder/settings", 200,
                                     token=self.admin_token)
        if success:
            self.log(f"  Enabled: {settings.get('enabled')}, "
                    f"Send hour: {settings.get('send_hour')}, "
                    f"Days: {settings.get('days')}", "INFO")
        
        # Update settings (valid)
        self.test("Update reminder settings (valid)", "PUT", "/wa/reminder/settings", 200,
                 token=self.admin_token,
                 data={
                     "enabled": False,  # Keep disabled for testing
                     "send_hour": 9,
                     "days": [1, 2, 3, 4, 5],
                     "min_nominal": 1000000.0,
                     "min_age_days": 14,
                     "cooldown_days": 3,
                     "skip_if_pending_transfer": True,
                     "cc_owner": False,
                     "exclude": [],
                     "template_name": "",
                     "template_lang": "id"
                 })
        
        # Test invalid send_hour
        self.test("Update reminder settings (invalid send_hour)", "PUT", "/wa/reminder/settings", 400,
                 token=self.admin_token,
                 data={
                     "enabled": False,
                     "send_hour": 25,  # Invalid
                     "days": [1, 2, 3],
                     "min_nominal": 1000000.0,
                     "min_age_days": 14,
                     "cooldown_days": 3
                 })
        
        # Test invalid days (empty)
        self.test("Update reminder settings (empty days)", "PUT", "/wa/reminder/settings", 400,
                 token=self.admin_token,
                 data={
                     "enabled": False,
                     "send_hour": 9,
                     "days": [],  # Invalid
                     "min_nominal": 1000000.0,
                     "min_age_days": 14,
                     "cooldown_days": 3
                 })
        
        # Test invalid cooldown
        self.test("Update reminder settings (invalid cooldown)", "PUT", "/wa/reminder/settings", 400,
                 token=self.admin_token,
                 data={
                     "enabled": False,
                     "send_hour": 9,
                     "days": [1, 2, 3],
                     "min_nominal": 1000000.0,
                     "min_age_days": 14,
                     "cooldown_days": 61  # > 60
                 })

    def test_piutang_preview_run(self):
        """Test Pengingat Piutang preview and run."""
        self.log("\n=== Testing Piutang Reminder Preview & Run ===", "INFO")
        
        # Get preview
        success, preview = self.test("Get reminder preview", "GET", "/wa/reminder/preview", 200,
                                    token=self.admin_token)
        if success:
            items = preview.get("items", [])
            self.log(f"  Preview: {len(items)} pengurus", "INFO")
            eligible = [i for i in items if i.get("eligible")]
            self.log(f"  Eligible for reminder: {len(eligible)}", "INFO")
        
        # Run reminder (manual, no force)
        success, run_result = self.test("Run reminder (manual)", "POST", "/wa/reminder/run", 200,
                                       token=self.admin_token,
                                       data={"force": False})
        if success:
            counts = run_result.get("counts", {})
            self.log(f"  Run result: {counts}", "INFO")
        
        # Get history
        success, history = self.test("Get reminder history", "GET", "/wa/reminder/history?limit=10", 200,
                                    token=self.admin_token)
        if success:
            self.log(f"  History: {len(history)} records", "INFO")

    def test_piutang_cron(self):
        """Test Pengingat Piutang cron endpoint."""
        self.log("\n=== Testing Piutang Reminder Cron ===", "INFO")
        
        # Test without auth (should fail)
        self.test("Cron piutang-reminder (no auth)", "POST", "/cron/piutang-reminder", 401)
        
        # Test with wrong bearer token
        self.test("Cron piutang-reminder (wrong token)", "POST", "/cron/piutang-reminder", 401,
                 headers={"Authorization": "Bearer wrong_token"})
        
        # Test with correct bearer token
        self.test("Cron piutang-reminder (correct token)", "POST", "/cron/piutang-reminder", 200,
                 headers={"Authorization": f"Bearer {WEBHOOK_CRON_SECRET}",
                         "X-Webhook-Id": f"test-{datetime.now().timestamp()}"})
        
        # Test duplicate webhook ID (should return duplicate status)
        webhook_id = f"test-duplicate-{datetime.now().timestamp()}"
        self.test("Cron piutang-reminder (first call)", "POST", "/cron/piutang-reminder", 200,
                 headers={"Authorization": f"Bearer {WEBHOOK_CRON_SECRET}",
                         "X-Webhook-Id": webhook_id})
        self.test("Cron piutang-reminder (duplicate)", "POST", "/cron/piutang-reminder", 200,
                 headers={"Authorization": f"Bearer {WEBHOOK_CRON_SECRET}",
                         "X-Webhook-Id": webhook_id})

    def test_weekly_settings(self):
        """Test Laporan Mingguan settings."""
        self.log("\n=== Testing Weekly Report Settings ===", "INFO")
        
        # Get current settings
        success, settings = self.test("Get weekly settings", "GET", "/wa/weekly/settings", 200,
                                     token=self.admin_token)
        if success:
            recipients = settings.get("recipients", [])
            self.log(f"  Enabled: {settings.get('enabled')}, Recipients: {len(recipients)}", "INFO")
        
        # Update settings (valid)
        self.test("Update weekly settings (valid)", "PUT", "/wa/weekly/settings", 200,
                 token=self.admin_token,
                 data={
                     "enabled": True,
                     "recipients": [
                         {"nama": "Pemilik", "phone": "6282343070023"}
                     ],
                     "template_name": "",
                     "template_lang": "id"
                 })
        
        # Test invalid phone
        self.test("Update weekly settings (invalid phone)", "PUT", "/wa/weekly/settings", 400,
                 token=self.admin_token,
                 data={
                     "enabled": True,
                     "recipients": [
                         {"nama": "Test", "phone": "123"}  # Too short
                     ],
                     "template_name": "",
                     "template_lang": "id"
                 })
        
        # Test empty recipients
        self.test("Update weekly settings (no recipients)", "PUT", "/wa/weekly/settings", 400,
                 token=self.admin_token,
                 data={
                     "enabled": True,
                     "recipients": [],
                     "template_name": "",
                     "template_lang": "id"
                 })

    def test_weekly_preview_run(self):
        """Test Laporan Mingguan preview and run."""
        self.log("\n=== Testing Weekly Report Preview & Run ===", "INFO")
        
        # Get preview (default: last week)
        success, preview = self.test("Get weekly preview (default)", "GET", "/wa/weekly/preview", 200,
                                    token=self.admin_token)
        if success:
            self.log(f"  Week: {preview.get('week_start')} to {preview.get('week_end')}", "INFO")
            self.log(f"  Total jam: {preview.get('total_jam')}, "
                    f"Total pemasukan: {preview.get('total_pemasukan')}", "INFO")
        
        # Get preview for specific week
        monday = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        success, preview = self.test("Get weekly preview (specific week)", "GET", 
                                    f"/wa/weekly/preview?week_start={monday}", 200,
                                    token=self.admin_token)
        
        # Run weekly report (manual)
        success, run_result = self.test("Run weekly report (manual)", "POST", "/wa/weekly/run", 200,
                                       token=self.admin_token,
                                       data={"force": False})
        if success:
            counts = run_result.get("counts", {})
            self.log(f"  Run result: {counts}", "INFO")
        
        # Get history
        success, history = self.test("Get weekly history", "GET", "/wa/weekly/history?limit=10", 200,
                                    token=self.admin_token)
        if success:
            self.log(f"  History: {len(history)} records", "INFO")

    def test_weekly_cron(self):
        """Test Laporan Mingguan cron endpoint."""
        self.log("\n=== Testing Weekly Report Cron ===", "INFO")
        
        # Test without auth
        self.test("Cron weekly-report (no auth)", "POST", "/cron/weekly-report", 401)
        
        # Test with correct bearer token
        self.test("Cron weekly-report (correct token)", "POST", "/cron/weekly-report", 200,
                 headers={"Authorization": f"Bearer {WEBHOOK_CRON_SECRET}",
                         "X-Webhook-Id": f"test-weekly-{datetime.now().timestamp()}"})

    def test_wa_simulation(self):
        """Test WhatsApp simulation (inbound messages)."""
        self.log("\n=== Testing WhatsApp Simulation ===", "INFO")
        
        # Test text message simulation (uses multipart form data)
        url = f"{BASE_URL}/wa/simulate/inbound"
        hdrs = {"Authorization": f"Bearer {self.admin_token}"}
        
        self.tests_run += 1
        self.log("Testing: Simulate inbound text", "INFO")
        try:
            r = requests.post(url, headers=hdrs, data={
                "phone": "628123456789",
                "name": "Test User",
                "text": "Test message",
                "message_id": f"sim.test.{datetime.now().timestamp()}"
            }, timeout=30)
            
            if r.status_code == 200:
                self.tests_passed += 1
                self.log(f"PASS - Simulate inbound text (status {r.status_code})", "PASS")
                result = r.json()
                self.log(f"  Simulation result: {result.get('status')}, type: {result.get('type')}", "INFO")
            else:
                self.tests_failed += 1
                self.log(f"FAIL - Simulate inbound text: Expected 200, got {r.status_code}", "FAIL")
        except Exception as e:
            self.tests_failed += 1
            self.log(f"FAIL - Simulate inbound text: {str(e)}", "FAIL")
        
        # Test invalid phone
        self.tests_run += 1
        self.log("Testing: Simulate inbound (invalid phone)", "INFO")
        try:
            r = requests.post(url, headers=hdrs, data={
                "phone": "123",  # Too short
                "name": "Test",
                "text": "Test"
            }, timeout=30)
            
            if r.status_code == 400:
                self.tests_passed += 1
                self.log(f"PASS - Simulate inbound (invalid phone) (status {r.status_code})", "PASS")
            else:
                self.tests_failed += 1
                self.log(f"FAIL - Simulate inbound (invalid phone): Expected 400, got {r.status_code}", "FAIL")
        except Exception as e:
            self.tests_failed += 1
            self.log(f"FAIL - Simulate inbound (invalid phone): {str(e)}", "FAIL")
        
        # Test empty text and no file
        self.tests_run += 1
        self.log("Testing: Simulate inbound (empty text, no file)", "INFO")
        try:
            r = requests.post(url, headers=hdrs, data={
                "phone": "628123456789",
                "name": "Test",
                "text": ""
            }, timeout=30)
            
            if r.status_code == 400:
                self.tests_passed += 1
                self.log(f"PASS - Simulate inbound (empty text, no file) (status {r.status_code})", "PASS")
            else:
                self.tests_failed += 1
                self.log(f"FAIL - Simulate inbound (empty text, no file): Expected 400, got {r.status_code}", "FAIL")
        except Exception as e:
            self.tests_failed += 1
            self.log(f"FAIL - Simulate inbound (empty text, no file): {str(e)}", "FAIL")

    def test_outbox(self):
        """Test outbox (simulated messages)."""
        self.log("\n=== Testing Outbox ===", "INFO")
        
        # Get outbox
        success, outbox = self.test("Get outbox", "GET", "/wa/outbox?limit=50", 200,
                                   token=self.admin_token)
        if success:
            items = outbox.get("items", [])
            counts = outbox.get("counts", {})
            self.log(f"  Outbox: {len(items)} items, counts: {counts}", "INFO")
            
            # Check for simulated items
            simulated = [i for i in items if i.get("status") == "simulated"]
            self.log(f"  Simulated messages: {len(simulated)}", "INFO")

    def test_backup(self):
        """Test backup functionality."""
        self.log("\n=== Testing Backup ===", "INFO")
        
        # Get backup info
        success, info = self.test("Get backup info", "GET", "/admin/backup/info", 200,
                                 token=self.admin_token)
        if success:
            collections = info.get("collections", {})
            self.log(f"  Collections: {len(collections)}", "INFO")
            self.log(f"  Excluded: {info.get('excluded')}", "INFO")
        
        # Test backup download endpoint (GET with stream to avoid downloading full file)
        self.log("Testing backup download endpoint...", "INFO")
        try:
            r = requests.get(f"{BASE_URL}/admin/backup?include_media=false",
                           headers={"Authorization": f"Bearer {self.admin_token}"},
                           stream=True, timeout=30)
            if r.status_code == 200:
                self.tests_passed += 1
                self.log("PASS - Backup download endpoint accessible", "PASS")
                # Close the stream without downloading
                r.close()
            else:
                self.tests_failed += 1
                self.log(f"FAIL - Backup download returned {r.status_code}", "FAIL")
        except Exception as e:
            self.tests_failed += 1
            self.log(f"FAIL - Backup download: {str(e)}", "FAIL")
        self.tests_run += 1

    def test_regression_auth(self):
        """Test regression: authentication endpoints."""
        self.log("\n=== Regression: Authentication ===", "INFO")
        
        # Test /auth/me
        self.test("Auth: Get current user", "GET", "/auth/me", 200, token=self.admin_token)
        
        # Note: We skip logout test here to keep the session valid for other regression tests

    def test_regression_units(self):
        """Test regression: Units CRUD."""
        self.log("\n=== Regression: Units ===", "INFO")
        
        # List units
        success, units = self.test("Units: List", "GET", "/units", 200, token=self.admin_token)
        if success:
            self.log(f"  Found {len(units)} units", "INFO")

    def test_regression_operations(self):
        """Test regression: Operations."""
        self.log("\n=== Regression: Operations ===", "INFO")
        
        # List operations
        success, ops = self.test("Operations: List", "GET", "/operations", 200, token=self.admin_token)
        if success:
            self.log(f"  Found {len(ops)} operations", "INFO")

    def test_regression_pengurus(self):
        """Test regression: Pengurus."""
        self.log("\n=== Regression: Pengurus ===", "INFO")
        
        # List pengurus
        success, pengurus = self.test("Pengurus: List", "GET", "/pengurus", 200, token=self.admin_token)
        if success:
            self.log(f"  Found {len(pengurus)} pengurus", "INFO")
        
        # List pengurus excavator registry
        success, registry = self.test("Pengurus Excavator: List", "GET", "/pengurus-excavator", 200,
                                     token=self.admin_token)
        if success:
            self.log(f"  Found {len(registry)} in registry", "INFO")

    def test_regression_wa_basic(self):
        """Test regression: Basic WA endpoints."""
        self.log("\n=== Regression: WhatsApp Basic ===", "INFO")
        
        # Get WA status
        self.test("WA: Get status", "GET", "/wa/status", 200, token=self.admin_token)
        
        # Get inbox
        self.test("WA: Get inbox", "GET", "/wa/inbox", 200, token=self.admin_token)
        
        # Get contacts
        self.test("WA: Get contacts", "GET", "/wa/contacts", 200, token=self.admin_token)
        
        # Get audit log
        self.test("WA: Get audit", "GET", "/wa/audit?limit=50", 200, token=self.admin_token)
        
        # Get connection status
        self.test("WA: Get connection", "GET", "/wa/connection", 200, token=self.admin_token)

    def test_regression_daily_summary(self):
        """Test regression: Daily summary."""
        self.log("\n=== Regression: Daily Summary ===", "INFO")
        
        # Get settings
        self.test("Daily Summary: Get settings", "GET", "/wa/summary/settings", 200,
                 token=self.admin_token)
        
        # Get preview
        today = datetime.now().strftime("%Y-%m-%d")
        self.test("Daily Summary: Get preview", "GET", f"/wa/summary/preview?tanggal={today}", 200,
                 token=self.admin_token)
        
        # Get history
        self.test("Daily Summary: Get history", "GET", "/wa/summary/history?limit=10", 200,
                 token=self.admin_token)

    def run_all_tests(self):
        """Run all tests."""
        self.log("\n" + "="*60, "INFO")
        self.log("TRIRARA TUNGGAL PUTRA - Backend API Testing", "INFO")
        self.log(f"Backend URL: {BACKEND_URL}", "INFO")
        self.log("="*60 + "\n", "INFO")
        
        # Authentication (required for all other tests)
        if not self.test_auth():
            self.log("\nAuthentication failed - stopping tests", "FAIL")
            return False
        
        # Security tests
        self.test_security()
        
        # HM Janggal tests
        self.test_hm_janggal()
        
        # Pengingat Piutang tests
        self.test_piutang_aging()
        self.test_piutang_settings()
        self.test_piutang_preview_run()
        self.test_piutang_cron()
        
        # Laporan Mingguan tests
        self.test_weekly_settings()
        self.test_weekly_preview_run()
        self.test_weekly_cron()
        
        # WhatsApp simulation tests
        self.test_wa_simulation()
        self.test_outbox()
        
        # Backup tests
        self.test_backup()
        
        # Regression tests
        self.test_regression_auth()
        self.test_regression_units()
        self.test_regression_operations()
        self.test_regression_pengurus()
        self.test_regression_wa_basic()
        self.test_regression_daily_summary()
        
        # Summary
        self.log("\n" + "="*60, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*60, "INFO")
        self.log(f"Total tests run: {self.tests_run}", "INFO")
        self.log(f"Passed: {self.tests_passed}", "PASS")
        self.log(f"Failed: {self.tests_failed}", "FAIL" if self.tests_failed > 0 else "INFO")
        self.log(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%", "INFO")
        self.log("="*60 + "\n", "INFO")
        
        return self.tests_failed == 0


def main():
    tester = APITester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
