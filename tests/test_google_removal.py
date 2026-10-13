"""Backend API testing for Google login removal feature.

Tests:
1. POST /api/auth/session must not exist (404/405)
2. Session tokens not starting with 'local_' are rejected on /api/auth/me (401)
3. POST /api/auth/login creates session_token starting with 'local_'
4. GET /api/users must NOT include password_hash
5. POST /api/users/manual creates users with optional username/password
6. PATCH /api/users/{id}/password without username for user lacking username -> 400
7. PATCH /api/users/{id}/password with duplicate username -> 400
8. PATCH /api/users/{id}/pin works
9. POST /users/verify-pin works
10. DELETE /api/users/{id} - can't delete self, can't delete last admin
11. Demote self -> 400, demote last admin -> 400
"""
import requests
import sys
import os
from datetime import datetime
from typing import Optional

# Get backend URL from frontend .env
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://admin-bonus-unit.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Credentials from test_credentials.md
ADMIN_USER = "admintest"
ADMIN_PASS = "admin123"


class GoogleRemovalTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.test_user_ids = []  # Track created test users for cleanup

    def log(self, msg: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {msg}")

    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             token: Optional[str] = None, data: Optional[dict] = None) -> tuple[bool, dict]:
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
                    self.log(f"  Response: {r.text[:300]}", "FAIL")
            
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
        try:
            r = requests.post(f"{BASE_URL}/auth/login", 
                            json={"username": username, "password": password},
                            timeout=30)
            if r.status_code == 200:
                token = r.cookies.get("session_token")
                if token:
                    self.log(f"Logged in successfully as {username}, token: {token[:20]}...", "PASS")
                    return token
                else:
                    self.log(f"Login succeeded but no session_token cookie found", "FAIL")
            else:
                self.log(f"Login failed with status {r.status_code}: {r.text[:200]}", "FAIL")
        except Exception as e:
            self.log(f"Login exception: {e}", "FAIL")
        return None

    def test_no_google_oauth_endpoint(self):
        """Test that POST /api/auth/session no longer exists."""
        self.log("\n=== Test: POST /api/auth/session removed ===", "INFO")
        
        # Try POST /api/auth/session (should be 404 or 405)
        success, _ = self.test(
            "POST /api/auth/session should not exist",
            "POST",
            "/auth/session",
            404,  # Expecting 404 Not Found
            data={"token": "fake_google_token"}
        )
        
        # Also accept 405 Method Not Allowed
        if not success:
            success2, _ = self.test(
                "POST /api/auth/session (405 also acceptable)",
                "POST",
                "/auth/session",
                405,
                data={"token": "fake_google_token"}
            )
            if success2:
                self.tests_passed += 1  # Adjust count
                self.tests_failed -= 1

    def test_local_token_requirement(self):
        """Test that session tokens must start with 'local_'."""
        self.log("\n=== Test: Session tokens must start with 'local_' ===", "INFO")
        
        # Try to use a fake non-local token
        fake_token = "google_abc123def456"
        success, resp = self.test(
            "GET /api/auth/me with non-local token (should fail)",
            "GET",
            "/auth/me",
            401,
            token=fake_token
        )
        
        if success and resp.get("detail") == "Invalid session":
            self.log("  Correct error message: 'Invalid session'", "PASS")

    def test_login_creates_local_token(self):
        """Test that POST /api/auth/login creates token starting with 'local_'."""
        self.log("\n=== Test: Login creates 'local_' token ===", "INFO")
        
        # Login as admin
        self.admin_token = self.login(ADMIN_USER, ADMIN_PASS)
        if not self.admin_token:
            self.log("Failed to login as admin - cannot continue", "FAIL")
            return False
        
        # Check token starts with 'local_'
        if self.admin_token.startswith("local_"):
            self.log(f"Token starts with 'local_': {self.admin_token[:20]}...", "PASS")
            self.tests_passed += 1
        else:
            self.log(f"Token does NOT start with 'local_': {self.admin_token[:20]}...", "FAIL")
            self.tests_failed += 1
        self.tests_run += 1
        
        return True

    def test_users_no_password_hash(self):
        """Test that GET /api/users does NOT include password_hash."""
        self.log("\n=== Test: GET /api/users excludes password_hash ===", "INFO")
        
        success, users = self.test(
            "GET /api/users",
            "GET",
            "/users",
            200,
            token=self.admin_token
        )
        
        if success and users:
            has_password_hash = any("password_hash" in u for u in users)
            if has_password_hash:
                self.log("FAIL - password_hash found in response", "FAIL")
                self.tests_failed += 1
            else:
                self.log("PASS - password_hash NOT in response", "PASS")
                self.tests_passed += 1
            self.tests_run += 1

    def test_create_manual_user(self):
        """Test POST /api/users/manual."""
        self.log("\n=== Test: Create manual users ===", "INFO")
        
        timestamp = int(datetime.now().timestamp())
        
        # Test 1: Create user WITH username/password
        success, user1 = self.test(
            "Create user WITH username/password",
            "POST",
            "/users/manual",
            200,
            token=self.admin_token,
            data={
                "name": f"Test User {timestamp}",
                "email": f"test{timestamp}@manual.local",
                "role": "operator",
                "pin": "1234",
                "username": f"testuser{timestamp}",
                "password": "test1234"
            }
        )
        if success:
            self.test_user_ids.append(user1.get("user_id"))
            self.log(f"  Created user: {user1.get('name')} (@{user1.get('username')})", "INFO")
        
        # Test 2: Create user WITHOUT username/password
        success, user2 = self.test(
            "Create user WITHOUT username/password",
            "POST",
            "/users/manual",
            200,
            token=self.admin_token,
            data={
                "name": f"No Login User {timestamp}",
                "role": "operator",
                "pin": "5678",
                "username": None,
                "password": None
            }
        )
        if success:
            self.test_user_ids.append(user2.get("user_id"))
            self.log(f"  Created user without login: {user2.get('name')}", "INFO")
            
            # Verify this user has no username
            if not user2.get("username"):
                self.log("  ✓ User has no username as expected", "PASS")
            else:
                self.log("  ✗ User has username when it shouldn't", "FAIL")
        
        # Test 3: Create user with password but no username (should fail)
        self.test(
            "Create user with password but no username (should fail)",
            "POST",
            "/users/manual",
            400,
            token=self.admin_token,
            data={
                "name": f"Invalid User {timestamp}",
                "role": "operator",
                "password": "test1234"
            }
        )
        
        # Test 4: Create user with duplicate username (should fail)
        self.test(
            "Create user with duplicate username (should fail)",
            "POST",
            "/users/manual",
            400,
            token=self.admin_token,
            data={
                "name": f"Duplicate User {timestamp}",
                "role": "operator",
                "username": f"testuser{timestamp}",  # Same as user1
                "password": "test1234"
            }
        )
        
        # Test 5: Create user with invalid PIN (should fail)
        self.test(
            "Create user with invalid PIN (should fail)",
            "POST",
            "/users/manual",
            400,
            token=self.admin_token,
            data={
                "name": f"Invalid PIN User {timestamp}",
                "role": "operator",
                "pin": "abc"  # Not numeric
            }
        )

    def test_password_update(self):
        """Test PATCH /api/users/{id}/password."""
        self.log("\n=== Test: Update user password ===", "INFO")
        
        timestamp = int(datetime.now().timestamp())
        
        # Create a user WITHOUT username
        success, user_no_username = self.test(
            "Create user without username for password test",
            "POST",
            "/users/manual",
            200,
            token=self.admin_token,
            data={
                "name": f"Password Test User {timestamp}",
                "role": "operator"
            }
        )
        
        if success:
            user_id = user_no_username.get("user_id")
            self.test_user_ids.append(user_id)
            
            # Test 1: Try to set password without username (should fail)
            self.test(
                "Set password without username (should fail)",
                "PATCH",
                f"/users/{user_id}/password",
                400,
                token=self.admin_token,
                data={"password": "newpass123"}
            )
            
            # Test 2: Set password WITH username (should succeed)
            success2, resp = self.test(
                "Set password with username (should succeed)",
                "PATCH",
                f"/users/{user_id}/password",
                200,
                token=self.admin_token,
                data={
                    "password": "newpass123",
                    "username": f"pwtest{timestamp}"
                }
            )
            
            if success2:
                self.log(f"  Username set to: {resp.get('username')}", "INFO")
                
                # Test 3: Try to set duplicate username (should fail)
                # Create another user first
                success3, user2 = self.test(
                    "Create second user for duplicate test",
                    "POST",
                    "/users/manual",
                    200,
                    token=self.admin_token,
                    data={
                        "name": f"Second User {timestamp}",
                        "role": "operator"
                    }
                )
                
                if success3:
                    user2_id = user2.get("user_id")
                    self.test_user_ids.append(user2_id)
                    
                    # Try to set same username
                    self.test(
                        "Set duplicate username (should fail)",
                        "PATCH",
                        f"/users/{user2_id}/password",
                        400,
                        token=self.admin_token,
                        data={
                            "password": "pass123",
                            "username": f"pwtest{timestamp}"  # Same as user1
                        }
                    )

    def test_pin_management(self):
        """Test PIN set/verify."""
        self.log("\n=== Test: PIN management ===", "INFO")
        
        timestamp = int(datetime.now().timestamp())
        
        # Create a user
        success, user = self.test(
            "Create user for PIN test",
            "POST",
            "/users/manual",
            200,
            token=self.admin_token,
            data={
                "name": f"PIN Test User {timestamp}",
                "role": "operator"
            }
        )
        
        if success:
            user_id = user.get("user_id")
            self.test_user_ids.append(user_id)
            
            # Test 1: Set PIN
            success2, _ = self.test(
                "Set PIN",
                "PATCH",
                f"/users/{user_id}/pin",
                200,
                token=self.admin_token,
                data={"pin": "9876"}
            )
            
            if success2:
                # Test 2: Verify correct PIN
                success3, resp = self.test(
                    "Verify correct PIN",
                    "POST",
                    "/users/verify-pin",
                    200,
                    token=self.admin_token,
                    data={
                        "user_id": user_id,
                        "pin": "9876"
                    }
                )
                
                if success3 and resp.get("ok"):
                    self.log("  ✓ PIN verified successfully", "PASS")
                else:
                    self.log("  ✗ PIN verification failed", "FAIL")
                
                # Test 3: Verify wrong PIN
                success4, resp2 = self.test(
                    "Verify wrong PIN",
                    "POST",
                    "/users/verify-pin",
                    200,
                    token=self.admin_token,
                    data={
                        "user_id": user_id,
                        "pin": "0000"
                    }
                )
                
                if success4 and not resp2.get("ok"):
                    self.log("  ✓ Wrong PIN correctly rejected", "PASS")
                else:
                    self.log("  ✗ Wrong PIN was accepted", "FAIL")
                
                # Test 4: Clear PIN
                self.test(
                    "Clear PIN",
                    "PATCH",
                    f"/users/{user_id}/pin",
                    200,
                    token=self.admin_token,
                    data={"pin": None}
                )

    def test_delete_restrictions(self):
        """Test DELETE user restrictions."""
        self.log("\n=== Test: Delete user restrictions ===", "INFO")
        
        timestamp = int(datetime.now().timestamp())
        
        # Test 1: Try to delete self (should fail)
        # First get current user info
        success, me = self.test(
            "Get current user",
            "GET",
            "/auth/me",
            200,
            token=self.admin_token
        )
        
        if success:
            my_user_id = me.get("user_id")
            self.test(
                "Delete self (should fail)",
                "DELETE",
                f"/users/{my_user_id}",
                400,
                token=self.admin_token
            )
        
        # Test 2: Create and delete a regular user (should succeed)
        success2, user = self.test(
            "Create user for deletion test",
            "POST",
            "/users/manual",
            200,
            token=self.admin_token,
            data={
                "name": f"Delete Test User {timestamp}",
                "role": "operator"
            }
        )
        
        if success2:
            user_id = user.get("user_id")
            self.test(
                "Delete regular user (should succeed)",
                "DELETE",
                f"/users/{user_id}",
                200,
                token=self.admin_token
            )
        
        # Test 3: Try to delete last admin (should fail)
        # First, count admins
        success3, users = self.test(
            "Get all users to count admins",
            "GET",
            "/users",
            200,
            token=self.admin_token
        )
        
        if success3:
            admins = [u for u in users if u.get("role") == "admin"]
            self.log(f"  Found {len(admins)} admin(s)", "INFO")
            
            if len(admins) == 1:
                # Only one admin, try to delete (should fail)
                admin_id = admins[0].get("user_id")
                self.test(
                    "Delete last admin (should fail)",
                    "DELETE",
                    f"/users/{admin_id}",
                    400,
                    token=self.admin_token
                )
            else:
                self.log("  Multiple admins exist, skipping last admin deletion test", "WARN")

    def test_role_change_restrictions(self):
        """Test role change restrictions."""
        self.log("\n=== Test: Role change restrictions ===", "INFO")
        
        # Get current user
        success, me = self.test(
            "Get current user for role test",
            "GET",
            "/auth/me",
            200,
            token=self.admin_token
        )
        
        if success and me.get("role") == "admin":
            my_user_id = me.get("user_id")
            
            # Test 1: Try to demote self (should fail)
            self.test(
                "Demote self to operator (should fail)",
                "PATCH",
                f"/users/{my_user_id}/role",
                400,
                token=self.admin_token,
                data={"role": "operator"}
            )
            
            # Test 2: Count admins and try to demote last admin
            success2, users = self.test(
                "Get all users to test last admin demotion",
                "GET",
                "/users",
                200,
                token=self.admin_token
            )
            
            if success2:
                admins = [u for u in users if u.get("role") == "admin"]
                if len(admins) == 1:
                    self.test(
                        "Demote last admin (should fail)",
                        "PATCH",
                        f"/users/{admins[0].get('user_id')}/role",
                        400,
                        token=self.admin_token,
                        data={"role": "operator"}
                    )
                else:
                    self.log("  Multiple admins exist, skipping last admin demotion test", "WARN")

    def cleanup(self):
        """Clean up test users."""
        self.log("\n=== Cleanup: Removing test users ===", "INFO")
        for user_id in self.test_user_ids:
            try:
                r = requests.delete(
                    f"{BASE_URL}/users/{user_id}",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=30
                )
                if r.status_code == 200:
                    self.log(f"  Deleted test user: {user_id}", "INFO")
                elif r.status_code == 400:
                    self.log(f"  Could not delete {user_id} (might be self or last admin)", "WARN")
            except Exception as e:
                self.log(f"  Error deleting {user_id}: {e}", "WARN")

    def run_all_tests(self):
        """Run all tests."""
        self.log("\n" + "="*70, "INFO")
        self.log("GOOGLE LOGIN REMOVAL - Backend API Testing", "INFO")
        self.log(f"Backend URL: {BACKEND_URL}", "INFO")
        self.log("="*70 + "\n", "INFO")
        
        # Test 1: No Google OAuth endpoint
        self.test_no_google_oauth_endpoint()
        
        # Test 2: Local token requirement
        self.test_local_token_requirement()
        
        # Test 3: Login creates local token
        if not self.test_login_creates_local_token():
            self.log("\nLogin failed - stopping tests", "FAIL")
            return False
        
        # Test 4: Users endpoint excludes password_hash
        self.test_users_no_password_hash()
        
        # Test 5: Create manual users
        self.test_create_manual_user()
        
        # Test 6: Password updates
        self.test_password_update()
        
        # Test 7: PIN management
        self.test_pin_management()
        
        # Test 8: Delete restrictions
        self.test_delete_restrictions()
        
        # Test 9: Role change restrictions
        self.test_role_change_restrictions()
        
        # Cleanup
        self.cleanup()
        
        # Summary
        self.log("\n" + "="*70, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*70, "INFO")
        self.log(f"Total tests run: {self.tests_run}", "INFO")
        self.log(f"Passed: {self.tests_passed}", "PASS")
        self.log(f"Failed: {self.tests_failed}", "FAIL" if self.tests_failed > 0 else "INFO")
        self.log(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%", "INFO")
        self.log("="*70 + "\n", "INFO")
        
        return self.tests_failed == 0


def main():
    tester = GoogleRemovalTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
