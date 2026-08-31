#!/usr/bin/env python3
"""
Backend API Test Suite for EXCAVA.OPS - ARSIP NOMOR LAPORAN
Tests report numbering archive feature
"""
import requests
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://operator-hours-log-1.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"username": "admin", "password": "admin123"}

# Session storage
admin_session = None
test_data = {}


def login(username: str, password: str) -> requests.Session:
    """Login and return session with cookie"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code != 200:
        raise Exception(f"Login failed for {username}: {response.status_code} {response.text}")
    
    user_data = response.json()
    print(f"✓ Logged in as {username} (role: {user_data.get('role')}, name: {user_data.get('name')})")
    return session, user_data


def test_issue_report_numbers():
    """Test 1: POST /api/reports/number with jenis, unit_label, periode_label"""
    print("\n=== TEST 1: ISSUE REPORT NUMBERS ===")
    
    issued_numbers = []
    
    # (a) Issue number for jenis "unit"
    print("\n1a. Issue report number - jenis 'unit'")
    payload_a = {
        "month": 8,
        "year": 2026,
        "jenis": "unit",
        "unit_label": "CAT 320D - TTP-01",
        "periode_label": "Agustus 2026"
    }
    response = admin_session.post(f"{BASE_URL}/reports/number", json=payload_a)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
        return False
    
    data_a = response.json()
    if "nomor" not in data_a or "id" not in data_a:
        print(f"   ❌ FAILED: Response missing 'nomor' or 'id' field")
        return False
    
    # Verify format LP/TTP/{seq}/VIII/2026
    nomor_a = data_a["nomor"]
    if not nomor_a.startswith("LP/TTP/") or "/VIII/2026" not in nomor_a:
        print(f"   ❌ FAILED: Nomor format incorrect. Expected LP/TTP/{{seq}}/VIII/2026, got {nomor_a}")
        return False
    
    print(f"   ✓ Nomor issued: {nomor_a}")
    print(f"   ✓ ID: {data_a['id']}")
    print(f"   ✓ Seq: {data_a.get('seq')}")
    issued_numbers.append(data_a)
    
    # (b) Issue number for jenis "semua"
    print("\n1b. Issue report number - jenis 'semua'")
    payload_b = {
        "month": 8,
        "year": 2026,
        "jenis": "semua",
        "periode_label": "Semua Periode"
    }
    response = admin_session.post(f"{BASE_URL}/reports/number", json=payload_b)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
        return False
    
    data_b = response.json()
    if "nomor" not in data_b or "id" not in data_b:
        print(f"   ❌ FAILED: Response missing 'nomor' or 'id' field")
        return False
    
    print(f"   ✓ Nomor issued: {data_b['nomor']}")
    print(f"   ✓ ID: {data_b['id']}")
    print(f"   ✓ Seq: {data_b.get('seq')}")
    issued_numbers.append(data_b)
    
    # (c) Issue number for jenis "unit" with different month
    print("\n1c. Issue report number - jenis 'unit' (September)")
    payload_c = {
        "month": 9,
        "year": 2026,
        "jenis": "unit",
        "unit_label": "CAT 320D - TTP-01",
        "periode_label": "September 2026"
    }
    response = admin_session.post(f"{BASE_URL}/reports/number", json=payload_c)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
        return False
    
    data_c = response.json()
    if "nomor" not in data_c or "id" not in data_c:
        print(f"   ❌ FAILED: Response missing 'nomor' or 'id' field")
        return False
    
    # Verify format LP/TTP/{seq}/IX/2026 (September = IX)
    nomor_c = data_c["nomor"]
    if not nomor_c.startswith("LP/TTP/") or "/IX/2026" not in nomor_c:
        print(f"   ❌ FAILED: Nomor format incorrect. Expected LP/TTP/{{seq}}/IX/2026, got {nomor_c}")
        return False
    
    print(f"   ✓ Nomor issued: {nomor_c}")
    print(f"   ✓ ID: {data_c['id']}")
    print(f"   ✓ Seq: {data_c.get('seq')}")
    issued_numbers.append(data_c)
    
    # Store for next test
    test_data["issued_numbers"] = issued_numbers
    
    print("\n✅ TEST 1 PASSED: All 3 report numbers issued successfully")
    return True


def test_archive_list():
    """Test 2: GET /api/reports/archive - verify list, sorting, fields"""
    print("\n=== TEST 2: ARCHIVE LIST ===")
    
    response = admin_session.get(f"{BASE_URL}/reports/archive")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        return False
    
    archive_list = response.json()
    print(f"✓ Response is array with {len(archive_list)} entries")
    
    # Verify contains at least 3 newly issued entries
    issued_numbers = test_data.get("issued_numbers", [])
    issued_ids = {item["id"] for item in issued_numbers}
    
    found_count = 0
    for entry in archive_list:
        if entry.get("id") in issued_ids:
            found_count += 1
    
    if found_count < 3:
        print(f"❌ FAILED: Expected at least 3 newly issued entries, found {found_count}")
        return False
    
    print(f"✓ Contains {found_count} newly issued entries")
    
    # Verify sorting by seq DESCENDING (newest/largest seq on top)
    if len(archive_list) >= 2:
        seqs = [entry.get("seq", 0) for entry in archive_list]
        is_descending = all(seqs[i] >= seqs[i+1] for i in range(len(seqs)-1))
        
        if not is_descending:
            print(f"❌ FAILED: Archive not sorted by seq DESCENDING")
            print(f"   Seq order: {seqs[:10]}")
            return False
        
        print(f"✓ Sorted by seq DESCENDING (newest first)")
        print(f"   Top 5 seq values: {seqs[:5]}")
    
    # Verify each item has required fields
    print("\nVerifying fields in archive entries:")
    required_fields = ["nomor", "seq", "jenis", "unit_label", "periode_label", "issued_by", "created_at"]
    
    for i, entry in enumerate(archive_list[:5]):  # Check first 5 entries
        print(f"\n  Entry {i+1}:")
        print(f"    nomor: {entry.get('nomor')}")
        print(f"    seq: {entry.get('seq')}")
        print(f"    jenis: {entry.get('jenis')}")
        print(f"    unit_label: {entry.get('unit_label')}")
        print(f"    periode_label: {entry.get('periode_label')}")
        print(f"    issued_by: {entry.get('issued_by')}")
        print(f"    created_at: {entry.get('created_at')}")
        
        missing_fields = [field for field in required_fields if field not in entry]
        if missing_fields:
            print(f"    ❌ FAILED: Missing fields: {missing_fields}")
            return False
    
    print("\n✓ All entries have required fields")
    
    # Verify issued_by = "Admin Test" (nama user admin)
    admin_name = test_data.get("admin_name", "")
    print(f"\nVerifying issued_by field (expected: '{admin_name}'):")
    
    for entry in archive_list[:3]:
        issued_by = entry.get("issued_by", "")
        if entry.get("id") in issued_ids:
            print(f"  Entry {entry.get('nomor')}: issued_by = '{issued_by}'")
            if issued_by != admin_name:
                print(f"    ⚠️  WARNING: Expected '{admin_name}', got '{issued_by}'")
    
    # Verify jenis "unit" has unit_label filled
    print("\nVerifying unit_label for jenis 'unit':")
    for entry in archive_list[:5]:
        if entry.get("jenis") == "unit":
            unit_label = entry.get("unit_label", "")
            if not unit_label:
                print(f"  ❌ FAILED: Entry {entry.get('nomor')} has jenis='unit' but empty unit_label")
                return False
            print(f"  ✓ Entry {entry.get('nomor')}: unit_label = '{unit_label}'")
    
    print("\n✅ TEST 2 PASSED: Archive list verified successfully")
    return True


def test_archive_auth():
    """Test 3: GET /api/reports/archive without auth - must return 401"""
    print("\n=== TEST 3: ARCHIVE AUTH ===")
    
    # Create new session without login
    no_auth_session = requests.Session()
    response = no_auth_session.get(f"{BASE_URL}/reports/archive")
    
    print(f"Status: {response.status_code}")
    
    if response.status_code != 401:
        print(f"❌ FAILED: Expected 401 Unauthorized, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print("✓ Correctly returned 401 Unauthorized")
    print("\n✅ TEST 3 PASSED: Auth protection working")
    return True


def main():
    """Run all tests"""
    global admin_session
    
    print("=" * 80)
    print("BACKEND TEST SUITE - ARSIP NOMOR LAPORAN")
    print("=" * 80)
    
    try:
        # Login as admin
        print("\n--- LOGIN ---")
        admin_session, admin_user = login(ADMIN_CREDS["username"], ADMIN_CREDS["password"])
        test_data["admin_name"] = admin_user.get("name", "")
        
        # Run tests
        results = []
        
        results.append(("Issue Report Numbers", test_issue_report_numbers()))
        results.append(("Archive List", test_archive_list()))
        results.append(("Archive Auth", test_archive_auth()))
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{status}: {test_name}")
        
        total = len(results)
        passed = sum(1 for _, p in results if p)
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
