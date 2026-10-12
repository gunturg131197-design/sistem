#!/usr/bin/env python3
"""
Backend API Test Suite for TRIRARA TUNGGAL PUTRA Hour Meter System
Tests new Hour Meter fields, operations PATCH, reports extras, and all integrations
"""
import requests
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://theme-logo-studio.preview.emergentagent.com/api"

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


def test_units_new_fields():
    """Test 1: Units API with new Hour Meter fields"""
    print("\n=== TEST 1: UNITS WITH NEW HOUR METER FIELDS ===")
    
    # Create unit with all new fields
    unit_payload = {
        "unit_name": "TEST_Komatsu PC200",
        "nomor_lambung": "TEST-EX-01",
        "serial_number": "TEST-SN-12345",
        "operator_id": test_data.get("operator_user_id"),
        "operator_name": "Budi Operator",
        "pengurus": "Pak Tono",
        "merek_type": "Komatsu PC200-8",
        "pemilik_alat": "CV. Trirara Tunggal Putra",
        "nama_proyek": "Normalisasi Sungai Ciliwung",
        "lokasi_proyek": "Jakarta Timur",
        "pengawas_lapangan": "Ir. Bambang Sutrisno"
    }
    
    response = admin_session.post(f"{BASE_URL}/units", json=unit_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create unit: {response.status_code} {response.text}")
        return False
    
    unit = response.json()
    test_data["unit_id"] = unit["id"]
    print(f"✓ Created unit: {unit['unit_name']} - {unit['nomor_lambung']}")
    
    # Verify all new fields are returned
    errors = []
    expected_fields = ["merek_type", "pemilik_alat", "nama_proyek", "lokasi_proyek", "pengawas_lapangan"]
    for field in expected_fields:
        if field not in unit:
            errors.append(f"Missing field: {field}")
        elif unit[field] != unit_payload[field]:
            errors.append(f"{field}: expected '{unit_payload[field]}', got '{unit[field]}'")
    
    if errors:
        print("✗ Unit field validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ All new fields present and correct:")
    print(f"  - Merek/Type: {unit['merek_type']}")
    print(f"  - Pemilik Alat: {unit['pemilik_alat']}")
    print(f"  - Nama Proyek: {unit['nama_proyek']}")
    print(f"  - Lokasi Proyek: {unit['lokasi_proyek']}")
    print(f"  - Pengawas Lapangan: {unit['pengawas_lapangan']}")
    
    # Test PATCH unit
    patch_payload = {
        **unit_payload,
        "nama_proyek": "Pembangunan Jalan Tol",
        "lokasi_proyek": "Bekasi"
    }
    
    response = admin_session.patch(f"{BASE_URL}/units/{unit['id']}", json=patch_payload)
    if response.status_code != 200:
        print(f"✗ Failed to patch unit: {response.status_code} {response.text}")
        return False
    
    updated_unit = response.json()
    if updated_unit["nama_proyek"] != "Pembangunan Jalan Tol":
        print(f"✗ PATCH unit failed: nama_proyek not updated")
        return False
    
    print(f"✓ PATCH unit successful: nama_proyek updated to '{updated_unit['nama_proyek']}'")
    
    # GET units and verify fields are returned
    response = admin_session.get(f"{BASE_URL}/units")
    if response.status_code != 200:
        print(f"✗ Failed to get units: {response.status_code}")
        return False
    
    units = response.json()
    found = False
    for u in units:
        if u["id"] == test_data["unit_id"]:
            found = True
            if not all(field in u for field in expected_fields):
                print(f"✗ GET /units missing new fields")
                return False
    
    if not found:
        print(f"✗ Created unit not found in GET /units")
        return False
    
    print(f"✓ GET /units returns all new fields correctly")
    return True


def test_operations_new_fields():
    """Test 2: Operations API with new Hour Meter fields"""
    print("\n=== TEST 2: OPERATIONS WITH NEW HOUR METER FIELDS ===")
    
    # Create operation with all new fields
    kondisi_alat = {
        "mesin": {"status": "baik", "keterangan": "Mesin normal"},
        "sistem_hidrolik": {"status": "baik", "keterangan": ""},
        "ban_track": {"status": "tidak", "keterangan": "Track aus, perlu ganti"},
        "lampu": {"status": "baik", "keterangan": ""},
        "rem": {"status": "baik", "keterangan": ""},
        "kelistrikan": {"status": "tidak", "keterangan": "Aki lemah"}
    }
    
    operation_payload = {
        "unit_id": test_data["unit_id"],
        "tanggal": "2026-02-15",
        "hour_meter_awal": 100.5,
        "hour_meter_akhir": 108.5,
        "jumlah_cars": 12,
        "pengurus": "Pak Tono",
        "keterangan": "Galian saluran, hujan 1 jam",
        "downtime_jam": 1.5,
        "solar_liter": 45.0,
        "catatan_operator": "Track mulai aus, perlu pengecekan. Aki lemah, minta ganti.",
        "kondisi_alat": kondisi_alat
    }
    
    response = operator_session.post(f"{BASE_URL}/operations", json=operation_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create operation: {response.status_code} {response.text}")
        return False
    
    op = response.json()
    test_data["operation_id"] = op["id"]
    print(f"✓ Created operation: {op['tanggal']} - {op['total_jam']} jam")
    
    # Verify all new fields
    errors = []
    
    if op.get("keterangan") != operation_payload["keterangan"]:
        errors.append(f"keterangan mismatch")
    
    if op.get("downtime_jam") != operation_payload["downtime_jam"]:
        errors.append(f"downtime_jam: expected {operation_payload['downtime_jam']}, got {op.get('downtime_jam')}")
    
    if op.get("solar_liter") != operation_payload["solar_liter"]:
        errors.append(f"solar_liter: expected {operation_payload['solar_liter']}, got {op.get('solar_liter')}")
    
    if op.get("catatan_operator") != operation_payload["catatan_operator"]:
        errors.append(f"catatan_operator mismatch")
    
    if not op.get("kondisi_alat"):
        errors.append("kondisi_alat missing")
    else:
        # Check kondisi_alat structure
        ka = op["kondisi_alat"]
        if ka.get("mesin", {}).get("status") != "baik":
            errors.append("kondisi_alat.mesin.status incorrect")
        if ka.get("ban_track", {}).get("status") != "tidak":
            errors.append("kondisi_alat.ban_track.status incorrect")
        if "Track aus" not in ka.get("ban_track", {}).get("keterangan", ""):
            errors.append("kondisi_alat.ban_track.keterangan missing")
    
    if op.get("total_jam") != 8.0:
        errors.append(f"total_jam: expected 8.0, got {op.get('total_jam')}")
    
    if errors:
        print("✗ Operation field validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ All new operation fields present and correct:")
    print(f"  - Keterangan: {op['keterangan']}")
    print(f"  - Downtime: {op['downtime_jam']} jam")
    print(f"  - Solar: {op['solar_liter']} liter")
    print(f"  - Catatan Operator: {op['catatan_operator'][:50]}...")
    print(f"  - Kondisi Alat: {len(op['kondisi_alat'])} items checked")
    print(f"  - Total Jam: {op['total_jam']} (auto-calculated)")
    
    return True


def test_operations_patch():
    """Test 3: PATCH operations (operator can patch own ops)"""
    print("\n=== TEST 3: PATCH OPERATIONS ===")
    
    # Operator patches their own operation
    patch_payload = {
        "unit_id": test_data["unit_id"],
        "tanggal": "2026-02-15",
        "hour_meter_awal": 100.5,
        "hour_meter_akhir": 110.0,  # Changed from 108.5
        "jumlah_cars": 15,  # Changed from 12
        "pengurus": "Pak Tono",
        "keterangan": "Galian saluran, hujan 2 jam",  # Changed
        "downtime_jam": 2.0,  # Changed from 1.5
        "solar_liter": 50.0,  # Changed from 45.0
        "catatan_operator": "Track aus, sudah diganti. Aki baru dipasang.",  # Changed
        "kondisi_alat": {
            "mesin": {"status": "baik", "keterangan": ""},
            "sistem_hidrolik": {"status": "baik", "keterangan": ""},
            "ban_track": {"status": "baik", "keterangan": "Track baru"},
            "lampu": {"status": "baik", "keterangan": ""},
            "rem": {"status": "baik", "keterangan": ""},
            "kelistrikan": {"status": "baik", "keterangan": "Aki baru"}
        }
    }
    
    response = operator_session.patch(f"{BASE_URL}/operations/{test_data['operation_id']}", json=patch_payload)
    if response.status_code != 200:
        print(f"✗ Failed to patch operation: {response.status_code} {response.text}")
        return False
    
    updated_op = response.json()
    
    # Verify updates
    errors = []
    
    if updated_op.get("hour_meter_akhir") != 110.0:
        errors.append(f"hour_meter_akhir not updated")
    
    if updated_op.get("jumlah_cars") != 15:
        errors.append(f"jumlah_cars not updated")
    
    if updated_op.get("downtime_jam") != 2.0:
        errors.append(f"downtime_jam not updated")
    
    if updated_op.get("solar_liter") != 50.0:
        errors.append(f"solar_liter not updated")
    
    # Check total_jam recalculated
    expected_total = 110.0 - 100.5  # 9.5
    if updated_op.get("total_jam") != expected_total:
        errors.append(f"total_jam not recalculated: expected {expected_total}, got {updated_op.get('total_jam')}")
    
    # Check kondisi_alat updated
    if updated_op.get("kondisi_alat", {}).get("ban_track", {}).get("status") != "baik":
        errors.append("kondisi_alat.ban_track not updated")
    
    if errors:
        print("✗ PATCH operation validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ PATCH operation successful:")
    print(f"  - HM Akhir: 108.5 → 110.0")
    print(f"  - Cars: 12 → 15")
    print(f"  - Downtime: 1.5 → 2.0 jam")
    print(f"  - Solar: 45.0 → 50.0 liter")
    print(f"  - Total Jam recalculated: {updated_op['total_jam']} jam")
    print(f"  - Kondisi ban_track: tidak → baik")
    
    # Test admin can also patch
    admin_patch = {
        **patch_payload,
        "keterangan": "Admin edit: Galian selesai"
    }
    
    response = admin_session.patch(f"{BASE_URL}/operations/{test_data['operation_id']}", json=admin_patch)
    if response.status_code != 200:
        print(f"✗ Admin failed to patch operation: {response.status_code}")
        return False
    
    print(f"✓ Admin can also PATCH operations")
    
    return True


def test_reports_extras():
    """Test 4: Reports extras API (admin only)"""
    print("\n=== TEST 4: REPORTS EXTRAS (ADMIN ONLY) ===")
    
    # GET extras (should return defaults)
    response = admin_session.get(f"{BASE_URL}/reports/extras", params={
        "unit_id": test_data["unit_id"],
        "periode": "2026-02"
    })
    
    if response.status_code != 200:
        print(f"✗ Failed to get extras: {response.status_code} {response.text}")
        return False
    
    extras = response.json()
    print(f"✓ GET /reports/extras successful (defaults)")
    
    # PUT extras (admin only)
    extras_payload = {
        "unit_id": test_data["unit_id"],
        "periode": "2026-02",
        "pengembalian_jam": 500000,
        "lain_lain": 250000,
        "keterangan_tambahan": "Hujan 2 hari, unit standby menunggu material"
    }
    
    response = admin_session.put(f"{BASE_URL}/reports/extras", json=extras_payload)
    if response.status_code != 200:
        print(f"✗ Failed to put extras: {response.status_code} {response.text}")
        return False
    
    saved_extras = response.json()
    print(f"✓ PUT /reports/extras successful")
    
    # Verify saved data
    errors = []
    
    if saved_extras.get("pengembalian_jam") != 500000:
        errors.append(f"pengembalian_jam not saved")
    
    if saved_extras.get("lain_lain") != 250000:
        errors.append(f"lain_lain not saved")
    
    if saved_extras.get("keterangan_tambahan") != extras_payload["keterangan_tambahan"]:
        errors.append(f"keterangan_tambahan not saved")
    
    if errors:
        print("✗ Extras validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ Extras saved correctly:")
    print(f"  - Pengembalian Jam: Rp{saved_extras['pengembalian_jam']:,}")
    print(f"  - Lain-lain: Rp{saved_extras['lain_lain']:,}")
    print(f"  - Keterangan: {saved_extras['keterangan_tambahan'][:50]}...")
    
    # Test operator cannot PUT extras
    response = operator_session.put(f"{BASE_URL}/reports/extras", json=extras_payload)
    if response.status_code != 403:
        print(f"✗ Operator should be blocked from PUT /reports/extras, got {response.status_code}")
        return False
    
    print(f"✓ Operator blocked from PUT /reports/extras (403)")
    
    return True


def test_reports_units():
    """Test 5: Reports units API with all new fields"""
    print("\n=== TEST 5: REPORTS UNITS WITH NEW FIELDS ===")
    
    # GET reports for periode
    response = admin_session.get(f"{BASE_URL}/reports/units", params={"periode": "2026-02"})
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
    
    # Verify all new fields are present
    errors = []
    
    # Unit fields
    expected_unit_fields = ["merek_type", "pemilik_alat", "nama_proyek", "lokasi_proyek", "pengawas_lapangan"]
    for field in expected_unit_fields:
        if field not in unit_report:
            errors.append(f"Missing unit field: {field}")
    
    # Aggregated operation fields
    if "total_downtime" not in unit_report:
        errors.append("Missing total_downtime")
    elif unit_report["total_downtime"] != 2.0:
        errors.append(f"total_downtime: expected 2.0, got {unit_report['total_downtime']}")
    
    if "total_solar" not in unit_report:
        errors.append("Missing total_solar")
    elif unit_report["total_solar"] != 50.0:
        errors.append(f"total_solar: expected 50.0, got {unit_report['total_solar']}")
    
    if "hari_operasional" not in unit_report:
        errors.append("Missing hari_operasional")
    elif unit_report["hari_operasional"] != 1:
        errors.append(f"hari_operasional: expected 1, got {unit_report['hari_operasional']}")
    
    if "kondisi_alat" not in unit_report:
        errors.append("Missing kondisi_alat")
    else:
        # Check kondisi_alat structure (latest from operations)
        ka = unit_report["kondisi_alat"]
        if "mesin" not in ka or "ban_track" not in ka:
            errors.append("kondisi_alat missing items")
    
    if "catatan_operator" not in unit_report:
        errors.append("Missing catatan_operator")
    elif not isinstance(unit_report["catatan_operator"], list):
        errors.append("catatan_operator should be a list")
    
    # Extras fields
    if "pengembalian_jam" not in unit_report:
        errors.append("Missing pengembalian_jam")
    elif unit_report["pengembalian_jam"] != 500000:
        errors.append(f"pengembalian_jam: expected 500000, got {unit_report['pengembalian_jam']}")
    
    if "lain_lain" not in unit_report:
        errors.append("Missing lain_lain")
    elif unit_report["lain_lain"] != 250000:
        errors.append(f"lain_lain: expected 250000, got {unit_report['lain_lain']}")
    
    if "keterangan_tambahan" not in unit_report:
        errors.append("Missing keterangan_tambahan")
    
    if errors:
        print("✗ Report validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"✓ All new report fields present and correct:")
    print(f"  - Merek/Type: {unit_report['merek_type']}")
    print(f"  - Nama Proyek: {unit_report['nama_proyek']}")
    print(f"  - Lokasi Proyek: {unit_report['lokasi_proyek']}")
    print(f"  - Pengawas Lapangan: {unit_report['pengawas_lapangan']}")
    print(f"  - Total Downtime: {unit_report['total_downtime']} jam")
    print(f"  - Total Solar: {unit_report['total_solar']} liter")
    print(f"  - Hari Operasional: {unit_report['hari_operasional']} hari")
    print(f"  - Kondisi Alat: {len(unit_report['kondisi_alat'])} items")
    print(f"  - Catatan Operator: {len(unit_report['catatan_operator'])} entries")
    print(f"  - Pengembalian Jam: Rp{unit_report['pengembalian_jam']:,}")
    print(f"  - Lain-lain: Rp{unit_report['lain_lain']:,}")
    print(f"  - Keterangan Tambahan: {unit_report['keterangan_tambahan'][:50]}...")
    
    return True


def cleanup():
    """Cleanup test data"""
    print("\n=== CLEANUP TEST DATA ===")
    
    try:
        # Delete operation
        if "operation_id" in test_data:
            response = admin_session.delete(f"{BASE_URL}/operations/{test_data['operation_id']}")
            if response.status_code == 200:
                print(f"✓ Deleted test operation")
        
        # Delete unit
        if "unit_id" in test_data:
            response = admin_session.delete(f"{BASE_URL}/units/{test_data['unit_id']}")
            if response.status_code == 200:
                print(f"✓ Deleted test unit")
        
        print(f"✓ Cleanup complete")
        return True
    except Exception as e:
        print(f"⚠️  Cleanup error (non-critical): {e}")
        return True


def main():
    global admin_session, operator_session
    
    print("=" * 70)
    print("TRIRARA TUNGGAL PUTRA - Hour Meter Backend API Test Suite")
    print("=" * 70)
    
    try:
        # Login as admin
        admin_session, admin_user = login(ADMIN_CREDS["username"], ADMIN_CREDS["password"])
        
        # Login as operator
        operator_session, operator_user = login(OPERATOR_CREDS["username"], OPERATOR_CREDS["password"])
        test_data["operator_user_id"] = operator_user["user_id"]
        
        # Run tests
        results = {
            "Units with New Fields": test_units_new_fields(),
            "Operations with New Fields": test_operations_new_fields(),
            "PATCH Operations": test_operations_patch(),
            "Reports Extras (Admin Only)": test_reports_extras(),
            "Reports Units with All Fields": test_reports_units()
        }
        
        # Cleanup
        cleanup()
        
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
            print("\n🎉 All backend tests passed!")
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
