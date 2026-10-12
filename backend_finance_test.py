#!/usr/bin/env python3
"""
Backend Finance Module Test Suite - Phase 2
Tests all /api/finance/* endpoints, auto-numbering, auto-creation from sparepart/payroll,
and reports/units new fields
"""
import requests
import json
import sys
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://theme-logo-studio.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"username": "admin", "password": "admin123"}
OPERATOR_CREDS = {"username": "budi", "password": "budi123"}

# Test data storage
test_data = {}
tests_passed = 0
tests_failed = 0


def print_test(name: str):
    """Print test header"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print('='*70)


def pass_test(msg: str):
    """Mark test as passed"""
    global tests_passed
    tests_passed += 1
    print(f"✓ PASS: {msg}")


def fail_test(msg: str):
    """Mark test as failed"""
    global tests_failed
    tests_failed += 1
    print(f"✗ FAIL: {msg}")


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


def test_auth_finance_admin_only():
    """Test 1: Finance endpoints require admin role"""
    print_test("Finance endpoints require admin (operator gets 403)")
    
    operator_session, _ = login(OPERATOR_CREDS["username"], OPERATOR_CREDS["password"])
    
    endpoints = [
        "/finance/kas-masuk",
        "/finance/kas-keluar",
        "/finance/invoices",
        "/finance/surat-masuk",
        "/finance/surat-keluar",
        "/finance/summary"
    ]
    
    all_403 = True
    for endpoint in endpoints:
        response = operator_session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 403:
            pass_test(f"Operator blocked from {endpoint} (403)")
        else:
            fail_test(f"Operator should get 403 on {endpoint}, got {response.status_code}")
            all_403 = False
    
    return all_403


def test_kas_masuk_crud(admin_session):
    """Test 2: Kas Masuk CRUD with auto-numbering KM-TTP-xxx"""
    print_test("Kas Masuk CRUD with auto-numbering")
    
    # Create kas masuk
    payload = {
        "tanggal": "2026-01-15",
        "uraian": "TEST Pembayaran dari Client A",
        "tujuan_dana": "Operasional",
        "debit": 5000000,
        "pic": "Pak Budi"
    }
    
    response = admin_session.post(f"{BASE_URL}/finance/kas-masuk", json=payload)
    if response.status_code != 200:
        fail_test(f"Failed to create kas masuk: {response.status_code} {response.text}")
        return False
    
    km = response.json()
    test_data["kas_masuk_id"] = km["id"]
    
    # Check auto-numbering
    if "no_bukti" not in km:
        fail_test("no_bukti not returned")
        return False
    
    if not km["no_bukti"].startswith("KM-TTP-"):
        fail_test(f"no_bukti should start with KM-TTP-, got {km['no_bukti']}")
        return False
    
    pass_test(f"Created kas masuk with auto number: {km['no_bukti']}")
    
    # Test PATCH
    patch_payload = {**payload, "uraian": "TEST UPDATED Pembayaran dari Client A"}
    response = admin_session.patch(f"{BASE_URL}/finance/kas-masuk/{km['id']}", json=patch_payload)
    if response.status_code != 200:
        fail_test(f"Failed to patch kas masuk: {response.status_code}")
        return False
    
    updated = response.json()
    if updated["uraian"] != patch_payload["uraian"]:
        fail_test(f"PATCH failed: uraian not updated")
        return False
    
    pass_test("PATCH kas masuk successful")
    
    # Test DELETE
    response = admin_session.delete(f"{BASE_URL}/finance/kas-masuk/{km['id']}")
    if response.status_code != 200:
        fail_test(f"Failed to delete kas masuk: {response.status_code}")
        return False
    
    pass_test("DELETE kas masuk successful")
    return True


def test_kas_keluar_jenis_numbering(admin_session):
    """Test 3: Kas Keluar with jenis BK/KK auto-numbering"""
    print_test("Kas Keluar jenis BK/KK auto-numbering")
    
    # Create BK (Belanja Barang)
    bk_payload = {
        "tanggal": "2026-01-16",
        "uraian": "TEST Pembelian oli mesin",
        "penerima": "Toko Sparepart",
        "jenis": "BK",
        "kredit": 500000,
        "keterangan": "Oli SAE 40"
    }
    
    response = admin_session.post(f"{BASE_URL}/finance/kas-keluar", json=bk_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create BK: {response.status_code} {response.text}")
        return False
    
    bk = response.json()
    test_data["kas_keluar_bk_id"] = bk["id"]
    
    if not bk["no_bukti"].startswith("BK-TTP-"):
        fail_test(f"BK should have BK-TTP- prefix, got {bk['no_bukti']}")
        return False
    
    pass_test(f"Created BK with auto number: {bk['no_bukti']}")
    
    # Create KK (Gaji/Kasbon)
    kk_payload = {
        "tanggal": "2026-01-17",
        "uraian": "TEST Kasbon operator",
        "penerima": "Pak Joko",
        "jenis": "KK",
        "kredit": 1000000,
        "keterangan": "Kasbon bulan Januari"
    }
    
    response = admin_session.post(f"{BASE_URL}/finance/kas-keluar", json=kk_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create KK: {response.status_code} {response.text}")
        return False
    
    kk = response.json()
    test_data["kas_keluar_kk_id"] = kk["id"]
    
    if not kk["no_bukti"].startswith("KK-TTP-"):
        fail_test(f"KK should have KK-TTP- prefix, got {kk['no_bukti']}")
        return False
    
    pass_test(f"Created KK with auto number: {kk['no_bukti']}")
    
    # Test PATCH manual entry
    patch_payload = {**kk_payload, "uraian": "TEST UPDATED Kasbon operator"}
    response = admin_session.patch(f"{BASE_URL}/finance/kas-keluar/{kk['id']}", json=patch_payload)
    if response.status_code != 200:
        fail_test(f"Failed to patch KK: {response.status_code}")
        return False
    
    pass_test("PATCH manual kas keluar successful")
    
    # Clean up
    admin_session.delete(f"{BASE_URL}/finance/kas-keluar/{bk['id']}")
    admin_session.delete(f"{BASE_URL}/finance/kas-keluar/{kk['id']}")
    
    return True


def test_auto_kas_from_sparepart(admin_session):
    """Test 4: Sparepart auto-creates BK kas keluar"""
    print_test("Sparepart auto-creates BK kas keluar")
    
    # First, create a unit
    unit_payload = {
        "unit_name": "TEST_CAT320",
        "nomor_lambung": "TEST-FIN-01",
        "serial_number": "TEST-SN-001"
    }
    response = admin_session.post(f"{BASE_URL}/units", json=unit_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create unit: {response.status_code}")
        return False
    
    unit = response.json()
    test_data["test_unit_id"] = unit["id"]
    pass_test(f"Created test unit: {unit['unit_name']}")
    
    # Create sparepart
    sp_payload = {
        "unit_id": unit["id"],
        "nomor_nota": "TEST-NOTA-001",
        "tanggal": "2026-01-18",
        "items": [
            {"nama_sparepart": "Filter Oli", "qty": 2, "harga_satuan": 150000, "total": 300000},
            {"nama_sparepart": "Seal Kit", "qty": 1, "harga_satuan": 500000, "total": 500000}
        ]
    }
    
    response = admin_session.post(f"{BASE_URL}/spareparts", json=sp_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create sparepart: {response.status_code} {response.text}")
        return False
    
    sp = response.json()
    test_data["test_sparepart_id"] = sp["id"]
    pass_test(f"Created sparepart nota: {sp['nomor_nota']}, biaya: {sp['biaya']}")
    
    # Check if BK kas keluar was auto-created
    response = admin_session.get(f"{BASE_URL}/finance/kas-keluar")
    if response.status_code != 200:
        fail_test(f"Failed to get kas keluar: {response.status_code}")
        return False
    
    kas_keluar_list = response.json()
    auto_bk = [k for k in kas_keluar_list if k.get("source") == "sparepart" and k.get("source_id") == sp["id"]]
    
    if not auto_bk:
        fail_test("Auto BK from sparepart not found")
        return False
    
    bk = auto_bk[0]
    if not bk["no_bukti"].startswith("BK-TTP-"):
        fail_test(f"Auto BK should have BK-TTP- prefix, got {bk['no_bukti']}")
        return False
    
    if bk["kredit"] != sp["biaya"]:
        fail_test(f"Auto BK kredit should match sparepart biaya: {bk['kredit']} != {sp['biaya']}")
        return False
    
    pass_test(f"Auto BK created from sparepart: {bk['no_bukti']}, kredit: {bk['kredit']}")
    test_data["auto_bk_id"] = bk["id"]
    
    # Test that auto BK cannot be edited
    patch_payload = {"tanggal": "2026-01-19", "uraian": "Try to edit", "penerima": "", "jenis": "BK", "kredit": 999999, "keterangan": ""}
    response = admin_session.patch(f"{BASE_URL}/finance/kas-keluar/{bk['id']}", json=patch_payload)
    if response.status_code == 400:
        pass_test("Auto BK correctly blocked from PATCH (400)")
    else:
        fail_test(f"Auto BK should return 400 on PATCH, got {response.status_code}")
    
    # Test that auto BK cannot be deleted directly
    response = admin_session.delete(f"{BASE_URL}/finance/kas-keluar/{bk['id']}")
    if response.status_code == 400:
        pass_test("Auto BK correctly blocked from DELETE (400)")
    else:
        fail_test(f"Auto BK should return 400 on DELETE, got {response.status_code}")
    
    # Delete sparepart should remove auto BK
    response = admin_session.delete(f"{BASE_URL}/spareparts/{sp['id']}")
    if response.status_code != 200:
        fail_test(f"Failed to delete sparepart: {response.status_code}")
        return False
    
    pass_test("Deleted sparepart")
    
    # Check if auto BK was removed
    response = admin_session.get(f"{BASE_URL}/finance/kas-keluar")
    kas_keluar_list = response.json()
    auto_bk_after = [k for k in kas_keluar_list if k.get("id") == bk["id"]]
    
    if auto_bk_after:
        fail_test("Auto BK should be removed when sparepart is deleted")
        return False
    
    pass_test("Auto BK removed when sparepart deleted")
    
    # Clean up unit
    admin_session.delete(f"{BASE_URL}/units/{unit['id']}")
    
    return True


def test_auto_kas_from_payroll(admin_session):
    """Test 5: Payroll auto-creates KK kas keluar (gaji + kasbon)"""
    print_test("Payroll auto-creates KK kas keluar")
    
    # Get operator user
    response = admin_session.get(f"{BASE_URL}/users")
    if response.status_code != 200:
        fail_test(f"Failed to get users: {response.status_code}")
        return False
    
    users = response.json()
    operator = next((u for u in users if u.get("role") == "operator"), None)
    if not operator:
        fail_test("No operator user found")
        return False
    
    # Create unit for payroll test
    unit_payload = {"unit_name": "TEST_CAT320_PAYROLL", "nomor_lambung": "TEST-FIN-02", "serial_number": "TEST-SN-002"}
    response = admin_session.post(f"{BASE_URL}/units", json=unit_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create unit: {response.status_code}")
        return False
    unit = response.json()
    test_data["test_payroll_unit_id"] = unit["id"]
    pass_test(f"Created test unit for payroll: {unit['unit_name']}")
    
    # Create payroll with kasbon
    payroll_payload = {
        "operator_id": operator["user_id"],
        "unit_id": test_data["test_payroll_unit_id"],
        "periode": "2026-01",
        "tarif_per_jam": 50000,
        "jam_dibayar": 100,
        "kasbon": 1500000
    }
    
    response = admin_session.post(f"{BASE_URL}/payroll", json=payroll_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create payroll: {response.status_code} {response.text}")
        return False
    
    payroll = response.json()
    test_data["test_payroll_id"] = payroll["id"]
    pass_test(f"Created payroll: gaji={payroll['gaji']}, kasbon={payroll['kasbon']}, gaji_bersih={payroll['gaji_bersih']}")
    
    # Check if KK kas keluar was auto-created (should be 2: kasbon + gaji_bersih)
    response = admin_session.get(f"{BASE_URL}/finance/kas-keluar")
    if response.status_code != 200:
        fail_test(f"Failed to get kas keluar: {response.status_code}")
        return False
    
    kas_keluar_list = response.json()
    auto_kk = [k for k in kas_keluar_list if k.get("source") == "payroll" and k.get("source_id") == payroll["id"]]
    
    if not auto_kk:
        fail_test("Auto KK from payroll not found")
        return False
    
    # Should have 2 entries: kasbon + gaji_bersih
    expected_count = 2 if payroll["kasbon"] > 0 else 1
    if len(auto_kk) != expected_count:
        fail_test(f"Expected {expected_count} auto KK entries, got {len(auto_kk)}")
        return False
    
    pass_test(f"Auto KK created from payroll: {len(auto_kk)} entries")
    
    # Verify amounts
    total_kredit = sum(k["kredit"] for k in auto_kk)
    expected_total = payroll["kasbon"] + payroll["gaji_bersih"]
    if abs(total_kredit - expected_total) > 0.01:
        fail_test(f"Auto KK total kredit mismatch: {total_kredit} != {expected_total}")
        return False
    
    pass_test(f"Auto KK amounts correct: kasbon + gaji_bersih = {total_kredit}")
    
    # Test that auto KK cannot be edited
    response = admin_session.patch(f"{BASE_URL}/finance/kas-keluar/{auto_kk[0]['id']}", json={"tanggal": "2026-01-20", "uraian": "Try", "penerima": "", "jenis": "KK", "kredit": 999, "keterangan": ""})
    if response.status_code == 400:
        pass_test("Auto KK correctly blocked from PATCH (400)")
    else:
        fail_test(f"Auto KK should return 400 on PATCH, got {response.status_code}")
    
    # Delete payroll should remove auto KK
    response = admin_session.delete(f"{BASE_URL}/payroll/{payroll['id']}")
    if response.status_code != 200:
        fail_test(f"Failed to delete payroll: {response.status_code}")
        return False
    
    pass_test("Deleted payroll")
    
    # Check if auto KK was removed
    response = admin_session.get(f"{BASE_URL}/finance/kas-keluar")
    kas_keluar_list = response.json()
    auto_kk_after = [k for k in kas_keluar_list if k.get("source") == "payroll" and k.get("source_id") == payroll["id"]]
    
    if auto_kk_after:
        fail_test("Auto KK should be removed when payroll is deleted")
        return False
    
    pass_test("Auto KK removed when payroll deleted")
    
    return True


def test_surat_keluar_numbering(admin_session):
    """Test 6: Surat Keluar auto-numbering SP/TTP/{seq}/{ROMAN}/{YEAR}"""
    print_test("Surat Keluar auto-numbering SP/TTP/xxx/ROMAN/YEAR")
    
    # Create surat keluar
    sk_payload = {
        "tanggal_surat": "2026-01-20",
        "tujuan_surat": "TEST PT. ABC Indonesia",
        "perihal": "TEST Penawaran Harga Sewa Excavator",
        "pengirim": "Direktur",
        "keterangan": "Test surat"
    }
    
    response = admin_session.post(f"{BASE_URL}/finance/surat-keluar", json=sk_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create surat keluar: {response.status_code} {response.text}")
        return False
    
    sk = response.json()
    test_data["surat_keluar_id"] = sk["id"]
    
    # Check format: SP/TTP/{seq}/I/2026 (January = I)
    if not sk["nomor_surat"].startswith("SP/TTP/"):
        fail_test(f"nomor_surat should start with SP/TTP/, got {sk['nomor_surat']}")
        return False
    
    parts = sk["nomor_surat"].split("/")
    if len(parts) != 5:
        fail_test(f"nomor_surat should have 5 parts, got {len(parts)}: {sk['nomor_surat']}")
        return False
    
    if parts[-2] != "I":  # January
        fail_test(f"Month should be I (January), got {parts[-2]}")
        return False
    
    if parts[-1] != "2026":
        fail_test(f"Year should be 2026, got {parts[-1]}")
        return False
    
    pass_test(f"Created surat keluar with correct format: {sk['nomor_surat']}")
    
    # Test PATCH with new date (should update roman month/year but keep seq)
    seq_num = parts[2]
    patch_payload = {**sk_payload, "tanggal_surat": "2026-03-15"}  # March = III
    response = admin_session.patch(f"{BASE_URL}/finance/surat-keluar/{sk['id']}", json=patch_payload)
    if response.status_code != 200:
        fail_test(f"Failed to patch surat keluar: {response.status_code}")
        return False
    
    updated_sk = response.json()
    updated_parts = updated_sk["nomor_surat"].split("/")
    
    if updated_parts[2] != seq_num:
        fail_test(f"Seq should remain {seq_num}, got {updated_parts[2]}")
        return False
    
    if updated_parts[-2] != "III":  # March
        fail_test(f"Month should be III (March), got {updated_parts[-2]}")
        return False
    
    pass_test(f"PATCH updated roman month/year, kept seq: {updated_sk['nomor_surat']}")
    
    # Clean up
    admin_session.delete(f"{BASE_URL}/finance/surat-keluar/{sk['id']}")
    
    return True


def test_invoice_numbering(admin_session):
    """Test 7: Invoice auto-numbering INV/TTP/{seq}/{ROMAN}/{YEAR}"""
    print_test("Invoice auto-numbering INV/TTP/xxx/ROMAN/YEAR")
    
    # Create invoice
    inv_payload = {
        "tanggal": "2026-02-10",
        "nama_client": "TEST PT. XYZ Construction",
        "deskripsi": "TEST Sewa excavator CAT 320D - Februari 2026",
        "jumlah": 50000000,
        "status": "Belum Dibayar"
    }
    
    response = admin_session.post(f"{BASE_URL}/finance/invoices", json=inv_payload)
    if response.status_code != 200:
        fail_test(f"Failed to create invoice: {response.status_code} {response.text}")
        return False
    
    inv = response.json()
    test_data["invoice_id"] = inv["id"]
    
    # Check format: INV/TTP/{seq}/II/2026 (February = II)
    if not inv["no_invoice"].startswith("INV/TTP/"):
        fail_test(f"no_invoice should start with INV/TTP/, got {inv['no_invoice']}")
        return False
    
    parts = inv["no_invoice"].split("/")
    if len(parts) != 5:
        fail_test(f"no_invoice should have 5 parts, got {len(parts)}: {inv['no_invoice']}")
        return False
    
    if parts[-2] != "II":  # February
        fail_test(f"Month should be II (February), got {parts[-2]}")
        return False
    
    if parts[-1] != "2026":
        fail_test(f"Year should be 2026, got {parts[-1]}")
        return False
    
    pass_test(f"Created invoice with correct format: {inv['no_invoice']}")
    
    # Test PATCH with new date
    seq_num = parts[2]
    patch_payload = {**inv_payload, "tanggal": "2026-04-20"}  # April = IV
    response = admin_session.patch(f"{BASE_URL}/finance/invoices/{inv['id']}", json=patch_payload)
    if response.status_code != 200:
        fail_test(f"Failed to patch invoice: {response.status_code}")
        return False
    
    updated_inv = response.json()
    updated_parts = updated_inv["no_invoice"].split("/")
    
    if updated_parts[2] != seq_num:
        fail_test(f"Seq should remain {seq_num}, got {updated_parts[2]}")
        return False
    
    if updated_parts[-2] != "IV":  # April
        fail_test(f"Month should be IV (April), got {updated_parts[-2]}")
        return False
    
    pass_test(f"PATCH updated roman month/year, kept seq: {updated_inv['no_invoice']}")
    
    # Clean up
    admin_session.delete(f"{BASE_URL}/finance/invoices/{inv['id']}")
    
    return True


def test_finance_summary(admin_session):
    """Test 8: GET /api/finance/summary returns correct structure"""
    print_test("Finance summary endpoint")
    
    response = admin_session.get(f"{BASE_URL}/finance/summary", params={"year": 2026})
    if response.status_code != 200:
        fail_test(f"Failed to get summary: {response.status_code}")
        return False
    
    summary = response.json()
    
    # Check required fields
    required_fields = [
        "year", "total_kas_masuk", "total_kas_keluar", "saldo_akhir",
        "saldo_awal_tahun", "keluar_bk", "keluar_kk", "invoice_outstanding",
        "invoice_count", "months"
    ]
    
    missing = [f for f in required_fields if f not in summary]
    if missing:
        fail_test(f"Missing fields in summary: {missing}")
        return False
    
    pass_test("Summary has all required fields")
    
    # Check months array
    if not isinstance(summary["months"], list):
        fail_test("months should be a list")
        return False
    
    if len(summary["months"]) != 12:
        fail_test(f"months should have 12 entries, got {len(summary['months'])}")
        return False
    
    # Check month structure
    month = summary["months"][0]
    month_fields = ["bulan", "periode", "total_masuk", "total_keluar", "selisih", "saldo"]
    missing_month = [f for f in month_fields if f not in month]
    if missing_month:
        fail_test(f"Missing fields in month: {missing_month}")
        return False
    
    pass_test(f"Summary structure correct: {len(summary['months'])} months, keluar_bk={summary['keluar_bk']}, keluar_kk={summary['keluar_kk']}")
    
    return True


def test_reports_units_new_fields(admin_session):
    """Test 9: GET /api/reports/units returns new fields"""
    print_test("Reports units endpoint with new fields")
    
    response = admin_session.get(f"{BASE_URL}/reports/units")
    if response.status_code != 200:
        fail_test(f"Failed to get reports: {response.status_code}")
        return False
    
    reports = response.json()
    
    if not reports:
        pass_test("No units in reports (empty DB is OK)")
        return True
    
    # Check first report has new fields
    report = reports[0]
    new_fields = [
        "tgl_hm_awal", "tgl_hm_akhir", "tgl_perpanjang_cars",
        "status", "lokasi_proyek", "serial_number"
    ]
    
    missing = [f for f in new_fields if f not in report]
    if missing:
        fail_test(f"Missing fields in report: {missing}")
        return False
    
    pass_test(f"Reports have all new fields: {', '.join(new_fields)}")
    
    return True


def cleanup_test_data(admin_session):
    """Clean up all test data"""
    print_test("Cleanup test data")
    
    # Delete test unit if exists
    if "test_unit_id" in test_data:
        admin_session.delete(f"{BASE_URL}/units/{test_data['test_unit_id']}")
        pass_test("Cleaned up test unit")
    
    # Delete payroll test unit if exists
    if "test_payroll_unit_id" in test_data:
        admin_session.delete(f"{BASE_URL}/units/{test_data['test_payroll_unit_id']}")
        pass_test("Cleaned up payroll test unit")
    
    pass_test("Cleanup complete")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("BACKEND FINANCE MODULE TEST SUITE - PHASE 2")
    print("="*70)
    
    try:
        # Login as admin
        admin_session, admin_user = login(ADMIN_CREDS["username"], ADMIN_CREDS["password"])
        
        # Run tests
        test_auth_finance_admin_only()
        test_kas_masuk_crud(admin_session)
        test_kas_keluar_jenis_numbering(admin_session)
        test_auto_kas_from_sparepart(admin_session)
        test_auto_kas_from_payroll(admin_session)
        test_surat_keluar_numbering(admin_session)
        test_invoice_numbering(admin_session)
        test_finance_summary(admin_session)
        test_reports_units_new_fields(admin_session)
        
        # Cleanup
        cleanup_test_data(admin_session)
        
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✓ Passed: {tests_passed}")
    print(f"✗ Failed: {tests_failed}")
    print(f"Total: {tests_passed + tests_failed}")
    print("="*70)
    
    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
