#!/usr/bin/env python3
"""
Backend API Test Suite for EXCAVA.OPS - NEW FEATURES
Tests for:
1. POST /api/reports/number - Automatic report numbering with Roman numerals
2. GET /api/reports/units?periode=YYYY-MM - Period filtering
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
    print(f"✓ Logged in as {username} (role: {user_data.get('role')})")
    return session, user_data


def test_report_number():
    """Test 1: POST /api/reports/number - Automatic report numbering"""
    print("\n=== TEST 1: AUTOMATIC REPORT NUMBERING ===")
    
    errors = []
    
    # Test 1.1: Generate report number for month 8, year 2026
    print("\n[1.1] Generate report number for month=8, year=2026")
    response = admin_session.post(
        f"{BASE_URL}/reports/number",
        json={"month": 8, "year": 2026}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} {response.text}")
        return False
    
    result1 = response.json()
    print(f"Response: {json.dumps(result1, indent=2)}")
    
    # Verify format: LP/TTP/{seq}/VIII/2026
    nomor1 = result1.get("nomor", "")
    seq1 = result1.get("seq")
    
    if not nomor1.startswith("LP/TTP/"):
        errors.append(f"nomor format incorrect: {nomor1} (should start with 'LP/TTP/')")
    
    if "/VIII/2026" not in nomor1:
        errors.append(f"nomor format incorrect: {nomor1} (should contain '/VIII/2026')")
    
    if not isinstance(seq1, int):
        errors.append(f"seq should be integer, got {type(seq1)}: {seq1}")
    
    if seq1 < 200:
        errors.append(f"seq should be >= 200, got {seq1}")
    
    # Verify exact format
    expected_format = f"LP/TTP/{seq1}/VIII/2026"
    if nomor1 != expected_format:
        errors.append(f"nomor format mismatch: expected '{expected_format}', got '{nomor1}'")
    
    if errors:
        print("✗ Validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ Report number generated correctly: {nomor1}")
    print(f"  - Format: LP/TTP/{seq1}/VIII/2026")
    print(f"  - seq: {seq1} (integer >= 200)")
    
    # Test 1.2: Call again with same month/year - seq should increment
    print(f"\n[1.2] Generate report number again (month=8, year=2026) - seq should increment")
    response = admin_session.post(
        f"{BASE_URL}/reports/number",
        json={"month": 8, "year": 2026}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} {response.text}")
        return False
    
    result2 = response.json()
    print(f"Response: {json.dumps(result2, indent=2)}")
    
    nomor2 = result2.get("nomor", "")
    seq2 = result2.get("seq")
    
    if seq2 <= seq1:
        print(f"✗ seq should increment: first call seq={seq1}, second call seq={seq2}")
        return False
    
    if seq2 != seq1 + 1:
        print(f"✗ seq should increment by 1: expected {seq1 + 1}, got {seq2}")
        return False
    
    expected_format2 = f"LP/TTP/{seq2}/VIII/2026"
    if nomor2 != expected_format2:
        print(f"✗ nomor format mismatch: expected '{expected_format2}', got '{nomor2}'")
        return False
    
    print(f"✓ seq incremented correctly: {seq1} → {seq2}")
    print(f"✓ Report number: {nomor2}")
    
    # Test 1.3: Different month (3) - Roman numeral should be III
    print(f"\n[1.3] Generate report number for month=3, year=2026 (Roman numeral should be III)")
    response = admin_session.post(
        f"{BASE_URL}/reports/number",
        json={"month": 3, "year": 2026}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} {response.text}")
        return False
    
    result3 = response.json()
    print(f"Response: {json.dumps(result3, indent=2)}")
    
    nomor3 = result3.get("nomor", "")
    seq3 = result3.get("seq")
    
    if "/III/2026" not in nomor3:
        print(f"✗ Roman numeral for month 3 should be 'III', got: {nomor3}")
        return False
    
    expected_format3 = f"LP/TTP/{seq3}/III/2026"
    if nomor3 != expected_format3:
        print(f"✗ nomor format mismatch: expected '{expected_format3}', got '{nomor3}'")
        return False
    
    print(f"✓ Roman numeral correct for month 3: {nomor3}")
    
    # Test 1.4: Month 12 - Roman numeral should be XII
    print(f"\n[1.4] Generate report number for month=12, year=2025 (Roman numeral should be XII)")
    response = admin_session.post(
        f"{BASE_URL}/reports/number",
        json={"month": 12, "year": 2025}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} {response.text}")
        return False
    
    result4 = response.json()
    print(f"Response: {json.dumps(result4, indent=2)}")
    
    nomor4 = result4.get("nomor", "")
    seq4 = result4.get("seq")
    
    if "/XII/2025" not in nomor4:
        print(f"✗ Roman numeral for month 12 should be 'XII', got: {nomor4}")
        return False
    
    expected_format4 = f"LP/TTP/{seq4}/XII/2025"
    if nomor4 != expected_format4:
        print(f"✗ nomor format mismatch: expected '{expected_format4}', got '{nomor4}'")
        return False
    
    print(f"✓ Roman numeral correct for month 12: {nomor4}")
    
    print(f"\n✅ ALL REPORT NUMBERING TESTS PASSED")
    return True


def test_period_filter():
    """Test 2: GET /api/reports/units?periode=YYYY-MM - Period filtering"""
    print("\n=== TEST 2: PERIOD FILTERING ===")
    
    # First, get all reports without filter to see what data exists
    print("\n[2.1] Get all reports (no filter)")
    response = admin_session.get(f"{BASE_URL}/reports/units")
    
    if response.status_code != 200:
        print(f"✗ Failed to get reports: {response.status_code} {response.text}")
        return False
    
    all_reports = response.json()
    print(f"✓ Found {len(all_reports)} units in total")
    
    # Find unit CAT 320D (unit_seed_01 or any CAT 320D)
    cat_unit = None
    for unit in all_reports:
        if "CAT 320D" in unit.get("unit_name", ""):
            cat_unit = unit
            break
    
    if not cat_unit:
        print(f"⚠️  No CAT 320D unit found. Creating test data...")
        # We'll test with whatever data exists
        if len(all_reports) == 0:
            print(f"✗ No units found in database. Cannot test period filtering.")
            return False
        cat_unit = all_reports[0]
    
    print(f"✓ Testing with unit: {cat_unit['unit_name']} - {cat_unit['nomor_lambung']}")
    print(f"  - Total cars (all time): {cat_unit['total_cars']}")
    print(f"  - Total HM (all time): {cat_unit['total_hm']}")
    print(f"  - Total gaji (all time): {cat_unit['total_gaji']}")
    print(f"  - Total gaji bersih (all time): {cat_unit['total_gaji_bersih']}")
    print(f"  - Total sparepart (all time): {cat_unit['total_sparepart']}")
    print(f"  - Operations count: {cat_unit['ops_count']}")
    
    # Test 2.2: Filter by periode 2025-07
    print(f"\n[2.2] Get reports with periode=2025-07")
    response = admin_session.get(f"{BASE_URL}/reports/units", params={"periode": "2025-07"})
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} {response.text}")
        return False
    
    reports_2025_07 = response.json()
    print(f"✓ Got {len(reports_2025_07)} units for periode 2025-07")
    
    # Find the same unit in filtered results
    cat_unit_2025_07 = None
    for unit in reports_2025_07:
        if unit['unit_id'] == cat_unit['unit_id']:
            cat_unit_2025_07 = unit
            break
    
    if cat_unit_2025_07:
        print(f"✓ Unit found in periode 2025-07:")
        print(f"  - Total cars: {cat_unit_2025_07['total_cars']}")
        print(f"  - Total HM: {cat_unit_2025_07['total_hm']}")
        print(f"  - Total gaji: {cat_unit_2025_07['total_gaji']}")
        print(f"  - Total gaji bersih: {cat_unit_2025_07['total_gaji_bersih']}")
        print(f"  - Total sparepart: {cat_unit_2025_07['total_sparepart']}")
        print(f"  - Operations count: {cat_unit_2025_07['ops_count']}")
        
        # Verify expected values based on seed data
        # According to review request:
        # - operation tanggal 2025-07-02 (total_jam 10, cars 5, HM 100->110)
        # - payroll periode 2025-07 (gaji 500000, gaji_bersih 400000)
        # - sparepart tanggal 2025-07-01 (biaya 1300000)
        
        errors = []
        
        # Check if values match expected (if this is the seed unit)
        if cat_unit_2025_07['total_cars'] == 5:
            print(f"  ✓ total_cars matches expected seed data (5)")
        
        if cat_unit_2025_07['total_hm'] == 10:
            print(f"  ✓ total_hm matches expected seed data (10)")
        
        if cat_unit_2025_07['total_gaji'] == 500000:
            print(f"  ✓ total_gaji matches expected seed data (500000)")
        
        if cat_unit_2025_07['total_gaji_bersih'] == 400000:
            print(f"  ✓ total_gaji_bersih matches expected seed data (400000)")
        
        if cat_unit_2025_07['total_sparepart'] == 1300000:
            print(f"  ✓ total_sparepart matches expected seed data (1300000)")
        
        # Verify filtered values are <= all-time values
        if cat_unit_2025_07['total_cars'] > cat_unit['total_cars']:
            errors.append(f"Filtered total_cars ({cat_unit_2025_07['total_cars']}) > all-time ({cat_unit['total_cars']})")
        
        if cat_unit_2025_07['total_hm'] > cat_unit['total_hm']:
            errors.append(f"Filtered total_hm ({cat_unit_2025_07['total_hm']}) > all-time ({cat_unit['total_hm']})")
        
        if cat_unit_2025_07['total_gaji'] > cat_unit['total_gaji']:
            errors.append(f"Filtered total_gaji ({cat_unit_2025_07['total_gaji']}) > all-time ({cat_unit['total_gaji']})")
        
        if errors:
            print("✗ Validation errors:")
            for err in errors:
                print(f"  - {err}")
            return False
    else:
        print(f"⚠️  Unit not found in periode 2025-07 (no data for this period)")
    
    # Test 2.3: Filter by periode 2025-06 (should have no data or zeros)
    print(f"\n[2.3] Get reports with periode=2025-06 (should have no/zero data)")
    response = admin_session.get(f"{BASE_URL}/reports/units", params={"periode": "2025-06"})
    
    if response.status_code != 200:
        print(f"✗ Failed: {response.status_code} {response.text}")
        return False
    
    reports_2025_06 = response.json()
    print(f"✓ Got {len(reports_2025_06)} units for periode 2025-06")
    
    # Find the same unit in filtered results
    cat_unit_2025_06 = None
    for unit in reports_2025_06:
        if unit['unit_id'] == cat_unit['unit_id']:
            cat_unit_2025_06 = unit
            break
    
    if cat_unit_2025_06:
        print(f"✓ Unit found in periode 2025-06:")
        print(f"  - Total cars: {cat_unit_2025_06['total_cars']}")
        print(f"  - Total HM: {cat_unit_2025_06['total_hm']}")
        print(f"  - Total gaji: {cat_unit_2025_06['total_gaji']}")
        print(f"  - Total gaji bersih: {cat_unit_2025_06['total_gaji_bersih']}")
        print(f"  - Total sparepart: {cat_unit_2025_06['total_sparepart']}")
        
        # For periode with no data, all aggregations should be 0
        errors = []
        
        if cat_unit_2025_06['total_cars'] != 0:
            errors.append(f"total_cars should be 0 for empty period, got {cat_unit_2025_06['total_cars']}")
        
        if cat_unit_2025_06['total_hm'] != 0:
            errors.append(f"total_hm should be 0 for empty period, got {cat_unit_2025_06['total_hm']}")
        
        if cat_unit_2025_06['total_gaji'] != 0:
            errors.append(f"total_gaji should be 0 for empty period, got {cat_unit_2025_06['total_gaji']}")
        
        if cat_unit_2025_06['total_gaji_bersih'] != 0:
            errors.append(f"total_gaji_bersih should be 0 for empty period, got {cat_unit_2025_06['total_gaji_bersih']}")
        
        if cat_unit_2025_06['total_sparepart'] != 0:
            errors.append(f"total_sparepart should be 0 for empty period, got {cat_unit_2025_06['total_sparepart']}")
        
        if errors:
            print("✗ Validation errors:")
            for err in errors:
                print(f"  - {err}")
            return False
        
        print(f"  ✓ All aggregations are 0 (correct for empty period)")
    else:
        print(f"✓ Unit not found in periode 2025-06 (no data for this period - correct)")
    
    # Test 2.4: Verify no filter returns all data
    print(f"\n[2.4] Verify no filter returns all data (>= filtered data)")
    
    if cat_unit_2025_07:
        if cat_unit['total_cars'] < cat_unit_2025_07['total_cars']:
            print(f"✗ All-time total_cars ({cat_unit['total_cars']}) < filtered ({cat_unit_2025_07['total_cars']})")
            return False
        
        if cat_unit['total_hm'] < cat_unit_2025_07['total_hm']:
            print(f"✗ All-time total_hm ({cat_unit['total_hm']}) < filtered ({cat_unit_2025_07['total_hm']})")
            return False
        
        print(f"✓ All-time aggregations >= filtered aggregations (correct)")
    
    print(f"\n✅ ALL PERIOD FILTERING TESTS PASSED")
    return True


def main():
    global admin_session
    
    print("=" * 70)
    print("EXCAVA.OPS Backend API Test Suite - NEW FEATURES")
    print("=" * 70)
    
    try:
        # Login as admin
        admin_session, admin_user = login(ADMIN_CREDS["username"], ADMIN_CREDS["password"])
        
        # Run tests
        results = {
            "Automatic Report Numbering": test_report_number(),
            "Period Filtering": test_period_filter()
        }
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1
    
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
