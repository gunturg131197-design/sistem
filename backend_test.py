#!/usr/bin/env python3
"""
Backend API Test Suite for EXCAVA.OPS
Tests sparepart multi-item, payroll per-jam, reports, and RBAC
"""
import requests
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://operator-hours-log-1.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"username": "admin", "password": "admin123"}
OPERATOR_CREDS = {"username": "budi", "password": "budi123"}

# Session storage
admin_session = None
operator_session = None
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
    print(f"✓ Logged in as {username} (role: {user_data.get('role')})")
    return session, user_data


def test_sparepart_multi_item():
    """Test 1: Sparepart multi-item with hm_service"""
    print("\n=== TEST 1: SPAREPART MULTI-ITEM ===")
    
    # First, create a unit as admin
    unit_payload = {
        "unit_name": "CAT 320D",
        "nomor_lambung": "EXC-001",
        "serial_number": "SN123456",
        "operator_id": test_data.get("operator_user_id", "user_op_seed01"),
        "operator_name": "Budi Operator"
    }
    
    response = admin_session.post(f"{BASE_URL}/units", json=unit_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create unit: {response.status_code} {response.text}")
        return False
    
    unit = response.json()
    test_data["unit_id"] = unit["id"]
    print(f"✓ Created unit: {unit['unit_name']} - {unit['nomor_lambung']} (ID: {unit['id']})")
    
    # Create sparepart with multi-item
    sparepart_payload = {
        "unit_id": test_data["unit_id"],
        "nomor_nota": "NOTA-001",
        "tanggal": "2025-07-01",
        "hm_service": 250,
        "items": [
            {
                "nama_sparepart": "Filter Oli",
                "qty": 2,
                "harga_satuan": 150000
            },
            {
                "nama_sparepart": "Bucket Teeth",
                "qty": 5,
                "harga_satuan": 200000
            }
        ]
    }
    
    response = admin_session.post(f"{BASE_URL}/spareparts", json=sparepart_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create sparepart: {response.status_code} {response.text}")
        return False
    
    sparepart = response.json()
    test_data["sparepart_id"] = sparepart["id"]
    
    # Verify calculations
    errors = []
    
    # Check items
    if len(sparepart.get("items", [])) != 2:
        errors.append(f"Expected 2 items, got {len(sparepart.get('items', []))}")
    
    # Check item 1 total
    item1 = sparepart["items"][0]
    expected_total1 = 2 * 150000  # 300000
    if item1.get("total") != expected_total1:
        errors.append(f"Item 1 total: expected {expected_total1}, got {item1.get('total')}")
    
    # Check item 2 total
    item2 = sparepart["items"][1]
    expected_total2 = 5 * 200000  # 1000000
    if item2.get("total") != expected_total2:
        errors.append(f"Item 2 total: expected {expected_total2}, got {item2.get('total')}")
    
    # Check total biaya
    expected_biaya = 300000 + 1000000  # 1300000
    if sparepart.get("biaya") != expected_biaya:
        errors.append(f"Total biaya: expected {expected_biaya}, got {sparepart.get('biaya')}")
    
    # Check hm_service
    if sparepart.get("hm_service") != 250:
        errors.append(f"HM service: expected 250, got {sparepart.get('hm_service')}")
    
    # Check nama_sparepart summary
    if "Filter Oli" not in sparepart.get("nama_sparepart", "") or "Bucket Teeth" not in sparepart.get("nama_sparepart", ""):
        errors.append(f"nama_sparepart summary missing item names: {sparepart.get('nama_sparepart')}")
    
    if errors:
        print("✗ Sparepart validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ Sparepart created with correct calculations:")
    print(f"  - Item 1: {item1['nama_sparepart']} x{item1['qty']} @ Rp{item1['harga_satuan']:,} = Rp{item1['total']:,}")
    print(f"  - Item 2: {item2['nama_sparepart']} x{item2['qty']} @ Rp{item2['harga_satuan']:,} = Rp{item2['total']:,}")
    print(f"  - Total biaya: Rp{sparepart['biaya']:,}")
    print(f"  - HM service: {sparepart['hm_service']}")
    
    # GET spareparts and verify items[] is returned
    response = admin_session.get(f"{BASE_URL}/spareparts")
    if response.status_code != 200:
        print(f"✗ Failed to get spareparts: {response.status_code}")
        return False
    
    spareparts = response.json()
    found = False
    for sp in spareparts:
        if sp["id"] == test_data["sparepart_id"]:
            found = True
            if not sp.get("items") or len(sp["items"]) != 2:
                print(f"✗ GET /spareparts did not return items[] array")
                return False
    
    if not found:
        print(f"✗ Created sparepart not found in GET /spareparts")
        return False
    
    print(f"✓ GET /spareparts returns items[] array correctly")
    return True


def test_payroll_per_jam():
    """Test 2: Payroll per-jam with hours endpoint"""
    print("\n=== TEST 2: PAYROLL PER-JAM ===")
    
    # Create operation as admin (10 hours)
    operation_payload = {
        "unit_id": test_data["unit_id"],
        "tanggal": "2025-07-02",
        "hour_meter_awal": 100,
        "hour_meter_akhir": 110,
        "jumlah_cars": 5,
        "pengurus": "Pak Tono"
    }
    
    response = admin_session.post(f"{BASE_URL}/operations", json=operation_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create operation (admin): {response.status_code} {response.text}")
        return False
    
    op1 = response.json()
    print(f"✓ Created operation as admin: {op1['total_jam']} jam (HM {op1['hour_meter_awal']}-{op1['hour_meter_akhir']})")
    
    # Create operation as budi (8 hours)
    operation_payload2 = {
        "unit_id": test_data["unit_id"],
        "tanggal": "2025-07-03",
        "hour_meter_awal": 110,
        "hour_meter_akhir": 118,
        "jumlah_cars": 3,
        "pengurus": "Pak Tono"
    }
    
    response = operator_session.post(f"{BASE_URL}/operations", json=operation_payload2)
    if response.status_code != 200:
        print(f"✗ Failed to create operation (budi): {response.status_code} {response.text}")
        return False
    
    op2 = response.json()
    print(f"✓ Created operation as budi: {op2['total_jam']} jam (HM {op2['hour_meter_awal']}-{op2['hour_meter_akhir']})")
    
    # GET /payroll/hours for budi on this unit
    operator_id = test_data.get("operator_user_id")
    response = admin_session.get(f"{BASE_URL}/payroll/hours", params={
        "operator_id": operator_id,
        "unit_id": test_data["unit_id"]
    })
    
    if response.status_code != 200:
        print(f"✗ Failed to get payroll hours: {response.status_code} {response.text}")
        return False
    
    hours_before = response.json()
    print(f"✓ Payroll hours before payment:")
    print(f"  - total_jam_kerja: {hours_before['total_jam_kerja']}")
    print(f"  - total_jam_dibayar: {hours_before['total_jam_dibayar']}")
    print(f"  - jam_belum_dibayar: {hours_before['jam_belum_dibayar']}")
    
    # Verify total_jam_kerja matches budi's operations (8.0 hours)
    expected_jam_kerja = 8.0  # Only budi's operation
    if hours_before["total_jam_kerja"] != expected_jam_kerja:
        print(f"✗ Expected total_jam_kerja={expected_jam_kerja}, got {hours_before['total_jam_kerja']}")
        return False
    
    if hours_before["total_jam_dibayar"] != 0:
        print(f"✗ Expected total_jam_dibayar=0, got {hours_before['total_jam_dibayar']}")
        return False
    
    if hours_before["jam_belum_dibayar"] != expected_jam_kerja:
        print(f"✗ Expected jam_belum_dibayar={expected_jam_kerja}, got {hours_before['jam_belum_dibayar']}")
        return False
    
    # Create payroll
    payroll_payload = {
        "operator_id": operator_id,
        "unit_id": test_data["unit_id"],
        "periode": "2025-07",
        "tarif_per_jam": 50000,
        "jam_dibayar": 8,
        "kasbon": 100000
    }
    
    response = admin_session.post(f"{BASE_URL}/payroll", json=payroll_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create payroll: {response.status_code} {response.text}")
        return False
    
    payroll = response.json()
    test_data["payroll_id"] = payroll["id"]
    
    # Verify payroll calculations
    errors = []
    
    expected_gaji = 8 * 50000  # 400000
    if payroll.get("gaji") != expected_gaji:
        errors.append(f"Gaji: expected {expected_gaji}, got {payroll.get('gaji')}")
    
    expected_gaji_bersih = 400000 - 100000  # 300000
    if payroll.get("gaji_bersih") != expected_gaji_bersih:
        errors.append(f"Gaji bersih: expected {expected_gaji_bersih}, got {payroll.get('gaji_bersih')}")
    
    if payroll.get("jam_kerja") != expected_jam_kerja:
        errors.append(f"Jam kerja snapshot: expected {expected_jam_kerja}, got {payroll.get('jam_kerja')}")
    
    if not payroll.get("unit_label"):
        errors.append("unit_label is empty")
    
    if errors:
        print("✗ Payroll validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ Payroll created with correct calculations:")
    print(f"  - Gaji: Rp{payroll['gaji']:,} (8 jam x Rp50,000)")
    print(f"  - Kasbon: Rp{payroll['kasbon']:,}")
    print(f"  - Gaji bersih: Rp{payroll['gaji_bersih']:,}")
    print(f"  - Jam kerja snapshot: {payroll['jam_kerja']}")
    print(f"  - Unit: {payroll['unit_label']}")
    
    # GET /payroll/hours again
    response = admin_session.get(f"{BASE_URL}/payroll/hours", params={
        "operator_id": operator_id,
        "unit_id": test_data["unit_id"]
    })
    
    if response.status_code != 200:
        print(f"✗ Failed to get payroll hours after payment: {response.status_code}")
        return False
    
    hours_after = response.json()
    print(f"✓ Payroll hours after payment:")
    print(f"  - total_jam_kerja: {hours_after['total_jam_kerja']}")
    print(f"  - total_jam_dibayar: {hours_after['total_jam_dibayar']}")
    print(f"  - jam_belum_dibayar: {hours_after['jam_belum_dibayar']}")
    
    # Verify hours updated correctly
    if hours_after["total_jam_dibayar"] != 8.0:
        print(f"✗ Expected total_jam_dibayar=8.0, got {hours_after['total_jam_dibayar']}")
        return False
    
    if hours_after["jam_belum_dibayar"] != 0.0:
        print(f"✗ Expected jam_belum_dibayar=0.0, got {hours_after['jam_belum_dibayar']}")
        return False
    
    print(f"✓ Hours tracking updated correctly after payment")
    return True


def test_reports():
    """Test 3: Reports per unit endpoint"""
    print("\n=== TEST 3: REPORTS PER UNIT ===")
    
    response = admin_session.get(f"{BASE_URL}/reports/units")
    if response.status_code != 200:
        print(f"✗ Failed to get reports: {response.status_code} {response.text}")
        return False
    
    reports = response.json()
    
    # Find our test unit
    unit_report = None
    for r in reports:
        if r["unit_id"] == test_data["unit_id"]:
            unit_report = r
            break
    
    if not unit_report:
        print(f"✗ Test unit not found in reports")
        return False
    
    print(f"✓ Found unit report: {unit_report['unit_label']}")
    
    # Verify aggregations
    errors = []
    
    # Total cars (5 + 3 = 8)
    expected_cars = 8
    if unit_report.get("total_cars") != expected_cars:
        errors.append(f"total_cars: expected {expected_cars}, got {unit_report.get('total_cars')}")
    
    # HM awal (min = 100)
    if unit_report.get("hm_awal") != 100:
        errors.append(f"hm_awal: expected 100, got {unit_report.get('hm_awal')}")
    
    # HM akhir (max = 118)
    if unit_report.get("hm_akhir") != 118:
        errors.append(f"hm_akhir: expected 118, got {unit_report.get('hm_akhir')}")
    
    # Total HM (10 + 8 = 18)
    expected_total_hm = 18.0
    if unit_report.get("total_hm") != expected_total_hm:
        errors.append(f"total_hm: expected {expected_total_hm}, got {unit_report.get('total_hm')}")
    
    # Total gaji (400000)
    expected_gaji = 400000
    if unit_report.get("total_gaji") != expected_gaji:
        errors.append(f"total_gaji: expected {expected_gaji}, got {unit_report.get('total_gaji')}")
    
    # Total gaji bersih (300000)
    expected_gaji_bersih = 300000
    if unit_report.get("total_gaji_bersih") != expected_gaji_bersih:
        errors.append(f"total_gaji_bersih: expected {expected_gaji_bersih}, got {unit_report.get('total_gaji_bersih')}")
    
    # Total sparepart (1300000)
    expected_sparepart = 1300000
    if unit_report.get("total_sparepart") != expected_sparepart:
        errors.append(f"total_sparepart: expected {expected_sparepart}, got {unit_report.get('total_sparepart')}")
    
    # Operators list
    if not unit_report.get("operators"):
        errors.append("operators list is empty")
    
    if errors:
        print("✗ Report validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ Report aggregations correct:")
    print(f"  - Total cars: {unit_report['total_cars']}")
    print(f"  - HM awal: {unit_report['hm_awal']}")
    print(f"  - HM akhir: {unit_report['hm_akhir']}")
    print(f"  - Total HM: {unit_report['total_hm']}")
    print(f"  - Total gaji: Rp{unit_report['total_gaji']:,}")
    print(f"  - Total gaji bersih: Rp{unit_report['total_gaji_bersih']:,}")
    print(f"  - Total sparepart: Rp{unit_report['total_sparepart']:,}")
    print(f"  - Operators: {', '.join(unit_report['operators'])}")
    
    return True


def test_rbac():
    """Test 4: RBAC - operator cannot access admin endpoints"""
    print("\n=== TEST 4: RBAC ===")
    
    errors = []
    
    # Test 1: Operator cannot POST spareparts
    sparepart_payload = {
        "unit_id": test_data["unit_id"],
        "nomor_nota": "NOTA-002",
        "tanggal": "2025-07-05",
        "items": [{"nama_sparepart": "Test", "qty": 1, "harga_satuan": 1000}]
    }
    
    response = operator_session.post(f"{BASE_URL}/spareparts", json=sparepart_payload)
    if response.status_code != 403:
        errors.append(f"POST /spareparts as operator: expected 403, got {response.status_code}")
    else:
        print(f"✓ Operator blocked from POST /spareparts (403)")
    
    # Test 2: Operator cannot POST payroll
    payroll_payload = {
        "operator_id": test_data.get("operator_user_id"),
        "unit_id": test_data["unit_id"],
        "periode": "2025-07",
        "tarif_per_jam": 50000,
        "jam_dibayar": 5,
        "kasbon": 0
    }
    
    response = operator_session.post(f"{BASE_URL}/payroll", json=payroll_payload)
    if response.status_code != 403:
        errors.append(f"POST /payroll as operator: expected 403, got {response.status_code}")
    else:
        print(f"✓ Operator blocked from POST /payroll (403)")
    
    # Test 3: Operator can only see their own units in reports
    response = operator_session.get(f"{BASE_URL}/reports/units")
    if response.status_code != 200:
        errors.append(f"GET /reports/units as operator failed: {response.status_code}")
    else:
        reports = response.json()
        # All units should belong to the operator
        for r in reports:
            if r.get("operator_utama") and r["operator_utama"] != "Budi Operator":
                # Check if operator worked on this unit
                if "Budi Operator" not in r.get("operators", []):
                    errors.append(f"Operator sees unit they don't own: {r['unit_label']}")
        
        if not errors:
            print(f"✓ Operator only sees their own units in reports ({len(reports)} units)")
    
    if errors:
        print("✗ RBAC validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    return True


def main():
    global admin_session, operator_session
    
    print("=" * 60)
    print("EXCAVA.OPS Backend API Test Suite")
    print("=" * 60)
    
    try:
        # Login as admin
        admin_session, admin_user = login(ADMIN_CREDS["username"], ADMIN_CREDS["password"])
        
        # Login as operator
        operator_session, operator_user = login(OPERATOR_CREDS["username"], OPERATOR_CREDS["password"])
        test_data["operator_user_id"] = operator_user["user_id"]
        
        # Run tests
        results = {
            "Sparepart Multi-Item": test_sparepart_multi_item(),
            "Payroll Per-Jam": test_payroll_per_jam(),
            "Reports Per Unit": test_reports(),
            "RBAC": test_rbac()
        }
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
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
