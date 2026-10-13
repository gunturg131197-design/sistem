#!/usr/bin/env python3
"""
Test suite untuk normalisasi URL MariaDB di build_url_from_env().
Bug fix: mysql:// dari Coolify dinormalisasi ke mysql+asyncmy:// + charset=utf8mb4.
"""
import sys
import os
import subprocess
import time
import signal
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from mariadb_store import build_url_from_env


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add(self, name, passed, expected, actual, note=""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "note": note
        })
        if passed:
            self.passed += 1
            print(f"✅ PASS: {name}")
            if note:
                print(f"   Note: {note}")
        else:
            self.failed += 1
            print(f"❌ FAIL: {name}")
            print(f"   Expected: {expected}")
            print(f"   Actual:   {actual}")
            if note:
                print(f"   Note: {note}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"Test Summary: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"Failed tests:")
            for t in self.tests:
                if not t["passed"]:
                    print(f"  - {t['name']}")
        print(f"{'='*70}\n")
        return self.failed == 0


def test_unit_basic_coolify_url():
    """Test 1: URL Coolify mysql:// dengan password special char → mysql+asyncmy:// + charset"""
    print("\n" + "="*70)
    print("TEST 1: Basic Coolify URL normalization")
    print("="*70)
    
    results = TestResults()
    
    # Test case dari review request
    env = {"MARIADB_URL": "mysql://mariadb:p%40ss@k8s0wc4g:3306/default"}
    result = build_url_from_env(env)
    expected = "mysql+asyncmy://mariadb:p%40ss@k8s0wc4g:3306/default?charset=utf8mb4"
    results.add(
        "Coolify mysql:// URL with encoded password",
        result == expected,
        expected,
        result,
        "Password p%40ss (p@ss encoded) should be preserved"
    )
    
    return results


def test_unit_various_schemes():
    """Test 2: Berbagai skema URL → semua ke mysql+asyncmy://"""
    print("\n" + "="*70)
    print("TEST 2: Various URL schemes normalization")
    print("="*70)
    
    results = TestResults()
    
    test_cases = [
        {
            "name": "mariadb:// scheme",
            "env": {"MARIADB_URL": "mariadb://u:p@h/db"},
            "expected": "mysql+asyncmy://u:p@h/db?charset=utf8mb4"
        },
        {
            "name": "mysql+pymysql:// scheme",
            "env": {"MARIADB_URL": "mysql+pymysql://u:p@h:3306/db"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        },
        {
            "name": "mysql+mysqldb:// scheme",
            "env": {"MARIADB_URL": "mysql+mysqldb://u:p@h:3306/db"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        },
        {
            "name": "mysql+aiomysql:// scheme",
            "env": {"MARIADB_URL": "mysql+aiomysql://u:p@h:3306/db"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        },
        {
            "name": "mariadb+asyncmy:// scheme",
            "env": {"MARIADB_URL": "mariadb+asyncmy://u:p@h:3306/db"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        },
        {
            "name": "Already mysql+asyncmy:// with charset (no double charset)",
            "env": {"MARIADB_URL": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        },
        {
            "name": "URL with other query params (ssl=false)",
            "env": {"MARIADB_URL": "mysql://u:p@h:3306/db?ssl=false"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?ssl=false&charset=utf8mb4"
        },
        {
            "name": "URL wrapped in double quotes",
            "env": {"MARIADB_URL": '"mysql://u:p@h:3306/db"'},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        },
        {
            "name": "URL wrapped in single quotes",
            "env": {"MARIADB_URL": "'mysql://u:p@h:3306/db'"},
            "expected": "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
        }
    ]
    
    for tc in test_cases:
        result = build_url_from_env(tc["env"])
        results.add(
            tc["name"],
            result == tc["expected"],
            tc["expected"],
            result
        )
    
    return results


def test_unit_priority_and_fallback():
    """Test 3: Prioritas URL dan fallback ke DB_* / MARIADB_*"""
    print("\n" + "="*70)
    print("TEST 3: URL priority and fallback to DB_* / MARIADB_*")
    print("="*70)
    
    results = TestResults()
    
    # Test DATABASE_URL dipakai bila MARIADB_URL kosong
    env = {"DATABASE_URL": "mysql://u:p@h:3306/db"}
    result = build_url_from_env(env)
    expected = "mysql+asyncmy://u:p@h:3306/db?charset=utf8mb4"
    results.add(
        "DATABASE_URL used when MARIADB_URL empty",
        result == expected,
        expected,
        result
    )
    
    # Test postgres:// diabaikan, jatuh ke DB_*
    env = {
        "DATABASE_URL": "postgres://u:p@h:5432/db",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_DATABASE": "trirara",
        "DB_USERNAME": "trirara",
        "DB_PASSWORD": "trirara_dev"
    }
    result = build_url_from_env(env)
    expected = "mysql+asyncmy://trirara:trirara_dev@127.0.0.1:3306/trirara?charset=utf8mb4"
    results.add(
        "postgres:// ignored, falls back to DB_*",
        result == expected,
        expected,
        result
    )
    
    # Test mongodb:// diabaikan, jatuh ke DB_*
    env = {
        "DATABASE_URL": "mongodb://u:p@h:27017/db",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_DATABASE": "trirara",
        "DB_USERNAME": "trirara",
        "DB_PASSWORD": "trirara_dev"
    }
    result = build_url_from_env(env)
    expected = "mysql+asyncmy://trirara:trirara_dev@127.0.0.1:3306/trirara?charset=utf8mb4"
    results.add(
        "mongodb:// ignored, falls back to DB_*",
        result == expected,
        expected,
        result
    )
    
    # Test DB_* dengan password karakter khusus (a@b#c) di-quote benar
    env = {
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_DATABASE": "trirara",
        "DB_USERNAME": "user",
        "DB_PASSWORD": "a@b#c"
    }
    result = build_url_from_env(env)
    # quote_plus should encode @ as %40 and # as %23
    expected_contains = ["mysql+asyncmy://", "127.0.0.1:3306/trirara", "charset=utf8mb4"]
    passed = all(part in result for part in expected_contains) and "a%40b%23c" in result
    results.add(
        "DB_* with special chars in password (a@b#c) quoted correctly",
        passed,
        "URL with encoded password (a%40b%23c)",
        result
    )
    
    # Test default tanpa env → trirara@127.0.0.1:3306/trirara
    env = {}
    result = build_url_from_env(env)
    expected = "mysql+asyncmy://trirara:@127.0.0.1:3306/trirara?charset=utf8mb4"
    results.add(
        "Default without env vars",
        result == expected,
        expected,
        result,
        "Should use default trirara@127.0.0.1:3306/trirara"
    )
    
    return results


def test_integration_correct_url():
    """Test 4: Integrasi - jalankan backend di port 8791 dengan MARIADB_URL"""
    print("\n" + "="*70)
    print("TEST 4: Integration - backend with correct MARIADB_URL")
    print("="*70)
    
    results = TestResults()
    
    # Prepare environment
    env = os.environ.copy()
    env["PORT"] = "8791"
    env["EXTRA_PORTS"] = ""
    env["MARIADB_URL"] = "mysql://trirara:trirara_dev@127.0.0.1:3306/trirara"
    
    # Remove .env to ensure only env vars are used
    backend_dir = Path(__file__).parent
    
    print("Starting backend on port 8791...")
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=str(backend_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for startup
    max_wait = 30
    started = False
    for i in range(max_wait):
        try:
            import requests
            resp = requests.get("http://127.0.0.1:8791/api/health/live", timeout=2)
            if resp.status_code == 200:
                started = True
                print(f"Backend started after {i+1} seconds")
                break
        except:
            pass
        time.sleep(1)
    
    if not started:
        proc.terminate()
        proc.wait(timeout=5)
        results.add(
            "Backend startup on port 8791",
            False,
            "Backend should start within 30 seconds",
            "Backend failed to start",
            "Check logs for errors"
        )
        return results
    
    # Wait a bit more for DB connection
    time.sleep(3)
    
    try:
        import requests
        
        # Test /api/health
        resp = requests.get("http://127.0.0.1:8791/api/health", timeout=5)
        health_data = resp.json()
        
        results.add(
            "/api/health returns 200",
            resp.status_code == 200,
            "200",
            str(resp.status_code)
        )
        
        results.add(
            "/api/health status is 'ok'",
            health_data.get("status") == "ok",
            "ok",
            health_data.get("status", "N/A")
        )
        
        results.add(
            "/api/health target is trirara@127.0.0.1:3306/trirara",
            health_data.get("target") == "trirara@127.0.0.1:3306/trirara",
            "trirara@127.0.0.1:3306/trirara",
            health_data.get("target", "N/A")
        )
        
        results.add(
            "/api/health startup_ready is true",
            health_data.get("startup_ready") == True,
            "true",
            str(health_data.get("startup_ready", "N/A"))
        )
        
        # Test login
        login_resp = requests.post(
            "http://127.0.0.1:8791/api/auth/login",
            json={"username": "admintest", "password": "admin123"},
            timeout=5
        )
        
        results.add(
            "Login admintest/admin123 returns 200",
            login_resp.status_code == 200,
            "200",
            str(login_resp.status_code)
        )
        
        if login_resp.status_code == 200:
            login_data = login_resp.json()
            results.add(
                "Login returns user data with role",
                "role" in login_data and "user_id" in login_data,
                "user data with role and user_id",
                f"role={login_data.get('role')}, user_id={login_data.get('user_id')}"
            )
    
    except Exception as e:
        results.add(
            "Integration test execution",
            False,
            "All API calls should succeed",
            f"Exception: {type(e).__name__}: {e}"
        )
    
    finally:
        # Cleanup
        print("Stopping backend on port 8791...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    
    return results


def test_integration_wrong_password():
    """Test 5: Integrasi - password salah → 503 tanpa bocor password"""
    print("\n" + "="*70)
    print("TEST 5: Integration - wrong password returns 503 without leaking")
    print("="*70)
    
    results = TestResults()
    
    # Prepare environment with wrong password
    env = os.environ.copy()
    env["PORT"] = "8792"
    env["EXTRA_PORTS"] = ""
    env["MARIADB_URL"] = "mysql://trirara:wrong_password@127.0.0.1:3306/trirara"
    
    backend_dir = Path(__file__).parent
    
    print("Starting backend on port 8792 with wrong password...")
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=str(backend_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for startup
    max_wait = 15
    started = False
    for i in range(max_wait):
        try:
            import requests
            resp = requests.get("http://127.0.0.1:8792/api/health/live", timeout=2)
            if resp.status_code == 200:
                started = True
                print(f"Backend started after {i+1} seconds")
                break
        except:
            pass
        time.sleep(1)
    
    if not started:
        proc.terminate()
        proc.wait(timeout=5)
        results.add(
            "Backend startup on port 8792",
            False,
            "Backend should start within 15 seconds",
            "Backend failed to start"
        )
        return results
    
    # Wait a bit for DB connection attempts
    time.sleep(3)
    
    try:
        import requests
        
        # Test /api/health/live should still return 200
        resp_live = requests.get("http://127.0.0.1:8792/api/health/live", timeout=5)
        results.add(
            "/api/health/live returns 200 even with DB error",
            resp_live.status_code == 200,
            "200",
            str(resp_live.status_code)
        )
        
        # Test /api/health should return 503
        resp_health = requests.get("http://127.0.0.1:8792/api/health", timeout=5)
        results.add(
            "/api/health returns 503 with wrong password",
            resp_health.status_code == 503,
            "503",
            str(resp_health.status_code)
        )
        
        if resp_health.status_code == 503:
            health_data = resp_health.json()
            detail = health_data.get("detail", "")
            
            # Check for "Access denied" message
            results.add(
                "/api/health detail contains 'Access denied'",
                "Access denied" in detail or "access denied" in detail.lower(),
                "Detail with 'Access denied'",
                detail[:100]
            )
            
            # Check password is NOT leaked
            password_leaked = "wrong_password" in detail or "wrong_password" in str(health_data)
            results.add(
                "/api/health does NOT leak password",
                not password_leaked,
                "Password should not appear in response",
                "Password found in response" if password_leaked else "Password not found (good)"
            )
    
    except Exception as e:
        results.add(
            "Integration test with wrong password",
            False,
            "API calls should complete",
            f"Exception: {type(e).__name__}: {e}"
        )
    
    finally:
        # Cleanup
        print("Stopping backend on port 8792...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    
    return results


def test_regression_preview_backend():
    """Test 6: Regresi - backend preview (port 8001) masih berfungsi"""
    print("\n" + "="*70)
    print("TEST 6: Regression - preview backend on port 8001")
    print("="*70)
    
    results = TestResults()
    
    try:
        import requests
        
        # Get backend URL from frontend env
        backend_url = "https://admin-bonus-unit.preview.emergentagent.com"
        
        # Test /api/health
        resp = requests.get(f"{backend_url}/api/health", timeout=10)
        results.add(
            "Preview /api/health returns 200",
            resp.status_code == 200,
            "200",
            str(resp.status_code)
        )
        
        # Test login
        login_resp = requests.post(
            f"{backend_url}/api/auth/login",
            json={"username": "admintest", "password": "admin123"},
            timeout=10
        )
        results.add(
            "Preview login admintest/admin123 returns 200",
            login_resp.status_code == 200,
            "200",
            str(login_resp.status_code)
        )
        
        if login_resp.status_code == 200:
            token = login_resp.cookies.get("session_token")
            if not token:
                # Try to get from response
                login_data = login_resp.json()
                # For testing, we'll use the session from cookies or create a new request
            
            headers = {}
            if login_resp.cookies.get("session_token"):
                headers["Cookie"] = f"session_token={login_resp.cookies.get('session_token')}"
            
            # Test /api/units
            units_resp = requests.get(
                f"{backend_url}/api/units",
                headers=headers,
                cookies=login_resp.cookies,
                timeout=10
            )
            results.add(
                "Preview /api/units returns 200",
                units_resp.status_code == 200,
                "200",
                str(units_resp.status_code)
            )
            
            # Test /api/operations
            ops_resp = requests.get(
                f"{backend_url}/api/operations",
                headers=headers,
                cookies=login_resp.cookies,
                timeout=10
            )
            results.add(
                "Preview /api/operations returns 200",
                ops_resp.status_code == 200,
                "200",
                str(ops_resp.status_code)
            )
            
            # Test /api/bonus-admin (bonus module)
            bonus_resp = requests.get(
                f"{backend_url}/api/bonus-admin",
                headers=headers,
                cookies=login_resp.cookies,
                timeout=10
            )
            results.add(
                "Preview /api/bonus-admin returns 200",
                bonus_resp.status_code == 200,
                "200",
                str(bonus_resp.status_code)
            )
    
    except Exception as e:
        results.add(
            "Regression test execution",
            False,
            "All API calls should succeed",
            f"Exception: {type(e).__name__}: {e}"
        )
    
    return results


def main():
    print("\n" + "="*70)
    print("MariaDB URL Normalization Test Suite")
    print("Testing build_url_from_env() fix for Coolify deployment")
    print("="*70)
    
    all_results = []
    
    # Run all tests
    all_results.append(test_unit_basic_coolify_url())
    all_results.append(test_unit_various_schemes())
    all_results.append(test_unit_priority_and_fallback())
    all_results.append(test_integration_correct_url())
    all_results.append(test_integration_wrong_password())
    all_results.append(test_regression_preview_backend())
    
    # Aggregate results
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed
    
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {total_passed} ✅")
    print(f"Failed: {total_failed} ❌")
    print(f"Success rate: {(total_passed/total_tests*100):.1f}%")
    print("="*70)
    
    if total_failed > 0:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
