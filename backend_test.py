#!/usr/bin/env python3
"""Backend API testing for WhatsApp Cloud API integration."""
import requests
import sys
import json
from datetime import datetime

BASE_URL = "https://theme-logo-studio.preview.emergentagent.com"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.operator_token = None

    def log(self, msg, color=Colors.BLUE):
        print(f"{color}{msg}{Colors.END}")

    def test(self, name, method, endpoint, expected_status, data=None, headers=None, params=None, check_fn=None):
        """Run a single API test."""
        url = f"{BASE_URL}{endpoint}"
        self.tests_run += 1
        
        print(f"\n{Colors.BLUE}🔍 Test {self.tests_run}: {name}{Colors.END}")
        
        try:
            h = headers or {}
            if method == 'GET':
                response = self.session.get(url, headers=h, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=h, params=params)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=h)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data, headers=h)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=h)
            else:
                raise ValueError(f"Unsupported method: {method}")

            status_ok = response.status_code == expected_status
            check_ok = True
            check_msg = ""
            
            if check_fn and status_ok:
                try:
                    body = response.json() if response.content else {}
                    check_ok, check_msg = check_fn(body)
                except Exception as e:
                    check_ok = False
                    check_msg = f"Check function error: {str(e)}"

            success = status_ok and check_ok
            
            if success:
                self.tests_passed += 1
                print(f"{Colors.GREEN}✅ PASSED - Status: {response.status_code}{Colors.END}")
                if check_msg:
                    print(f"   {check_msg}")
            else:
                self.tests_failed += 1
                print(f"{Colors.RED}❌ FAILED{Colors.END}")
                if not status_ok:
                    print(f"   Expected status {expected_status}, got {response.status_code}")
                if not check_ok:
                    print(f"   {check_msg}")
                try:
                    print(f"   Response: {response.text[:300]}")
                except:
                    pass

            return success, response

        except Exception as e:
            self.tests_failed += 1
            print(f"{Colors.RED}❌ FAILED - Error: {str(e)}{Colors.END}")
            return False, None

    def login(self, username, password):
        """Login and store session cookie."""
        success, response = self.test(
            f"Login as {username}",
            "POST",
            "/api/auth/login",
            200,
            data={"username": username, "password": password}
        )
        return success

    def test_wa_connection(self):
        """Test GET /api/wa/connection endpoint."""
        def check(body):
            if body.get("level") != "not_configured":
                return False, f"Expected level 'not_configured', got '{body.get('level')}'"
            if not body.get("missing"):
                return False, "Expected 'missing' list to be non-empty"
            # Check that no secrets are exposed
            body_str = json.dumps(body)
            if "EAA" in body_str or "token" in body_str.lower():
                return False, "Response may contain token values"
            return True, f"Level: {body.get('level')}, Missing: {len(body.get('missing', []))} items"
        
        return self.test(
            "GET /api/wa/connection (not configured)",
            "GET",
            "/api/wa/connection",
            200,
            check_fn=check
        )

    def test_wa_status(self):
        """Test GET /api/wa/status endpoint."""
        def check(body):
            if body.get("configured") != False:
                return False, "Expected configured=false"
            conn = body.get("connection", {})
            if conn.get("level") != "not_configured":
                return False, f"Expected connection level 'not_configured', got '{conn.get('level')}'"
            return True, f"Configured: {body.get('configured')}, Connection: {conn.get('level')}"
        
        return self.test(
            "GET /api/wa/status (not configured)",
            "GET",
            "/api/wa/status",
            200,
            check_fn=check
        )

    def test_wa_cloud_check_unconfigured(self):
        """Test POST /api/wa/cloud/check when not configured."""
        def check(body):
            if "Kredensial WhatsApp belum lengkap" not in body.get("detail", ""):
                return False, f"Expected error message about missing credentials, got: {body.get('detail')}"
            return True, "Correctly returns 400 when not configured"
        
        return self.test(
            "POST /api/wa/cloud/check (not configured)",
            "POST",
            "/api/wa/cloud/check",
            400,
            check_fn=check
        )

    def test_wa_cloud_send_test_unconfigured(self):
        """Test POST /api/wa/cloud/send-test when not configured."""
        def check(body):
            if "Kredensial WhatsApp belum lengkap" not in body.get("detail", ""):
                return False, f"Expected error message about missing credentials"
            return True, "Correctly returns 400 when not configured"
        
        return self.test(
            "POST /api/wa/cloud/send-test (not configured)",
            "POST",
            "/api/wa/cloud/send-test",
            400,
            data={"to": "628123456789", "mode": "text", "text": "Test"},
            check_fn=check
        )

    def test_wa_cloud_register_unconfigured(self):
        """Test POST /api/wa/cloud/register when not configured."""
        def check(body):
            if "Kredensial WhatsApp belum lengkap" not in body.get("detail", ""):
                return False, "Expected error message about missing credentials"
            return True, "Correctly returns 400 when not configured"
        
        return self.test(
            "POST /api/wa/cloud/register (not configured)",
            "POST",
            "/api/wa/cloud/register",
            400,
            data={"pin": "123456"},
            check_fn=check
        )

    def test_wa_cloud_register_invalid_pin(self):
        """Test POST /api/wa/cloud/register with invalid PIN."""
        def check(body):
            if "PIN harus 6 digit angka" not in body.get("detail", ""):
                return False, "Expected error about 6-digit PIN"
            return True, "Correctly validates PIN format"
        
        # Test with non-6-digit PIN
        self.test(
            "POST /api/wa/cloud/register (invalid PIN - 5 digits)",
            "POST",
            "/api/wa/cloud/register",
            400,
            data={"pin": "12345"},
            check_fn=check
        )
        
        # Test with non-numeric PIN
        return self.test(
            "POST /api/wa/cloud/register (invalid PIN - non-numeric)",
            "POST",
            "/api/wa/cloud/register",
            400,
            data={"pin": "12345a"},
            check_fn=check
        )

    def test_wa_cloud_subscribe_unconfigured(self):
        """Test POST /api/wa/cloud/subscribe when not configured."""
        def check(body):
            if "Kredensial WhatsApp belum lengkap" not in body.get("detail", ""):
                return False, "Expected error message about missing credentials"
            return True, "Correctly returns 400 when not configured"
        
        return self.test(
            "POST /api/wa/cloud/subscribe (not configured)",
            "POST",
            "/api/wa/cloud/subscribe",
            400,
            check_fn=check
        )

    def test_wa_outbox(self):
        """Test GET /api/wa/outbox endpoint."""
        def check(body):
            if "items" not in body or "counts" not in body:
                return False, "Expected 'items' and 'counts' in response"
            if not isinstance(body["items"], list):
                return False, "'items' should be a list"
            if not isinstance(body["counts"], dict):
                return False, "'counts' should be a dict"
            # Check for token leakage in outbox items
            body_str = json.dumps(body)
            if "EAA" in body_str:
                return False, "Outbox response may contain token values"
            return True, f"Items: {len(body['items'])}, Counts: {body['counts']}"
        
        return self.test(
            "GET /api/wa/outbox",
            "GET",
            "/api/wa/outbox",
            200,
            check_fn=check
        )

    def test_wa_outbox_retry_invalid(self):
        """Test POST /api/wa/outbox/{id}/retry with invalid ID."""
        def check(body):
            # Should return error for non-existent or non-failed message
            return True, f"Response: {body.get('detail', body)}"
        
        return self.test(
            "POST /api/wa/outbox/{id}/retry (invalid ID)",
            "POST",
            "/api/wa/outbox/nonexistent-id/retry",
            400,
            check_fn=check
        )

    def test_cron_wa_outbox_retry_no_auth(self):
        """Test POST /api/cron/wa-outbox-retry without auth."""
        return self.test(
            "POST /api/cron/wa-outbox-retry (no auth)",
            "POST",
            "/api/cron/wa-outbox-retry",
            401
        )

    def test_cron_wa_outbox_retry_wrong_auth(self):
        """Test POST /api/cron/wa-outbox-retry with wrong auth."""
        return self.test(
            "POST /api/cron/wa-outbox-retry (wrong auth)",
            "POST",
            "/api/cron/wa-outbox-retry",
            401,
            headers={"Authorization": "Bearer wrong-secret"}
        )

    def test_cron_wa_outbox_retry_valid(self):
        """Test POST /api/cron/wa-outbox-retry with valid auth."""
        # Read the secret from .env
        try:
            with open("/app/backend/.env") as f:
                for line in f:
                    if line.startswith("WEBHOOK_CRON_SECRET="):
                        secret = line.split("=", 1)[1].strip()
                        break
        except:
            print(f"{Colors.YELLOW}⚠️  Could not read WEBHOOK_CRON_SECRET from .env{Colors.END}")
            return False, None
        
        def check(body):
            if body.get("status") not in ("accepted", "duplicate"):
                return False, f"Expected status 'accepted' or 'duplicate', got '{body.get('status')}'"
            return True, f"Status: {body.get('status')}"
        
        return self.test(
            "POST /api/cron/wa-outbox-retry (valid auth)",
            "POST",
            "/api/cron/wa-outbox-retry",
            200,
            headers={"Authorization": f"Bearer {secret}"},
            data={},
            check_fn=check
        )

    def test_cron_wa_outbox_retry_duplicate(self):
        """Test POST /api/cron/wa-outbox-retry with same X-Webhook-Id."""
        try:
            with open("/app/backend/.env") as f:
                for line in f:
                    if line.startswith("WEBHOOK_CRON_SECRET="):
                        secret = line.split("=", 1)[1].strip()
                        break
        except:
            return False, None
        
        webhook_id = f"test-{int(datetime.now().timestamp())}"
        
        # First call
        self.test(
            "POST /api/cron/wa-outbox-retry (first call)",
            "POST",
            "/api/cron/wa-outbox-retry",
            200,
            headers={"Authorization": f"Bearer {secret}", "X-Webhook-Id": webhook_id},
            data={}
        )
        
        # Second call with same webhook_id should return duplicate
        def check(body):
            if body.get("status") != "duplicate":
                return False, f"Expected status 'duplicate', got '{body.get('status')}'"
            return True, "Correctly detects duplicate webhook ID"
        
        return self.test(
            "POST /api/cron/wa-outbox-retry (duplicate webhook ID)",
            "POST",
            "/api/cron/wa-outbox-retry",
            200,
            headers={"Authorization": f"Bearer {secret}", "X-Webhook-Id": webhook_id},
            data={},
            check_fn=check
        )

    def test_cron_wa_outbox_retry_invalid_body(self):
        """Test POST /api/cron/wa-outbox-retry with invalid JSON body."""
        try:
            with open("/app/backend/.env") as f:
                for line in f:
                    if line.startswith("WEBHOOK_CRON_SECRET="):
                        secret = line.split("=", 1)[1].strip()
                        break
        except:
            return False, None
        
        # Send non-object JSON (array instead of object)
        import requests
        url = f"{BASE_URL}/api/cron/wa-outbox-retry"
        response = requests.post(url, json=["not", "an", "object"], headers={"Authorization": f"Bearer {secret}"})
        
        self.tests_run += 1
        if response.status_code == 400:
            self.tests_passed += 1
            print(f"\n{Colors.BLUE}🔍 Test {self.tests_run}: POST /api/cron/wa-outbox-retry (invalid body){Colors.END}")
            print(f"{Colors.GREEN}✅ PASSED - Status: {response.status_code}{Colors.END}")
            return True, response
        else:
            self.tests_failed += 1
            print(f"\n{Colors.BLUE}🔍 Test {self.tests_run}: POST /api/cron/wa-outbox-retry (invalid body){Colors.END}")
            print(f"{Colors.RED}❌ FAILED - Expected 400, got {response.status_code}{Colors.END}")
            return False, response

    def test_wa_summary_preview(self):
        """Test GET /api/wa/summary/preview."""
        def check(body):
            if "tanggal" not in body or "items" not in body:
                return False, "Expected 'tanggal' and 'items' in response"
            if not isinstance(body["items"], list):
                return False, "'items' should be a list"
            return True, f"Tanggal: {body.get('tanggal')}, Items: {len(body['items'])}"
        
        return self.test(
            "GET /api/wa/summary/preview",
            "GET",
            "/api/wa/summary/preview",
            200,
            check_fn=check
        )

    def test_wa_summary_run(self):
        """Test POST /api/wa/summary/run."""
        def check(body):
            if "run_id" not in body or "counts" not in body:
                return False, "Expected 'run_id' and 'counts' in response"
            counts = body.get("counts", {})
            # In preview mode (not configured), should have 'preview' or 'skipped' counts
            if not any(k in counts for k in ["preview", "skipped", "sent"]):
                return False, "Expected counts to have 'preview', 'skipped', or 'sent'"
            return True, f"Run ID: {body.get('run_id')}, Counts: {counts}"
        
        return self.test(
            "POST /api/wa/summary/run",
            "POST",
            "/api/wa/summary/run",
            200,
            data={},
            check_fn=check
        )

    def test_operator_access(self):
        """Test that operator (budi) cannot access admin endpoints."""
        # Logout admin
        self.session = requests.Session()
        
        # Login as operator
        if not self.login("budi", "budi123"):
            print(f"{Colors.YELLOW}⚠️  Could not login as operator{Colors.END}")
            return False, None
        
        # Try to access admin endpoint
        def check(body):
            # Should return 403 Forbidden
            return True, "Operator correctly denied access"
        
        return self.test(
            "GET /api/wa/connection (as operator - should fail)",
            "GET",
            "/api/wa/connection",
            403,
            check_fn=check
        )

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access endpoints."""
        # Logout
        self.session = requests.Session()
        
        return self.test(
            "GET /api/wa/connection (unauthenticated)",
            "GET",
            "/api/wa/connection",
            401
        )

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print(f"{Colors.BLUE}📊 TEST SUMMARY{Colors.END}")
        print(f"{'='*60}")
        print(f"Total tests run: {self.tests_run}")
        print(f"{Colors.GREEN}✅ Passed: {self.tests_passed}{Colors.END}")
        print(f"{Colors.RED}❌ Failed: {self.tests_failed}{Colors.END}")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}🎉 All tests passed!{Colors.END}")
            return 0
        else:
            print(f"\n{Colors.RED}⚠️  Some tests failed{Colors.END}")
            return 1

def main():
    tester = APITester()
    
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}WhatsApp Cloud API Integration - Backend Tests{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"Base URL: {BASE_URL}")
    print(f"Testing preview mode (WhatsApp not configured)")
    
    # Login as admin
    if not tester.login("admin", "admin123"):
        print(f"{Colors.RED}❌ Failed to login as admin. Cannot continue.{Colors.END}")
        return 1
    
    # Test connection endpoints
    tester.test_wa_connection()
    tester.test_wa_status()
    
    # Test cloud API endpoints (should fail when not configured)
    tester.test_wa_cloud_check_unconfigured()
    tester.test_wa_cloud_send_test_unconfigured()
    tester.test_wa_cloud_register_unconfigured()
    tester.test_wa_cloud_register_invalid_pin()
    tester.test_wa_cloud_subscribe_unconfigured()
    
    # Test outbox endpoints
    tester.test_wa_outbox()
    tester.test_wa_outbox_retry_invalid()
    
    # Test cron endpoint
    tester.test_cron_wa_outbox_retry_no_auth()
    tester.test_cron_wa_outbox_retry_wrong_auth()
    tester.test_cron_wa_outbox_retry_valid()
    tester.test_cron_wa_outbox_retry_duplicate()
    tester.test_cron_wa_outbox_retry_invalid_body()
    
    # Test daily summary endpoints
    tester.test_wa_summary_preview()
    tester.test_wa_summary_run()
    
    # Test access control
    tester.test_operator_access()
    tester.test_unauthenticated_access()
    
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
