#!/usr/bin/env python3
"""Test admin system status endpoint dan regression test preview backend."""
import requests
import sys

BASE_URL = "http://localhost:8001"

def test_admin_system_status():
    """Test GET /api/admin/system-status dengan login admin"""
    print("="*70)
    print("TEST: Admin System Status & Regression Preview")
    print("="*70)
    
    # Login sebagai admin
    print("\n1. Login sebagai admintest...")
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admintest",
        "password": "admin123"
    })
    
    if resp.status_code != 200:
        print(f"❌ Login gagal: {resp.status_code}")
        print(resp.text)
        return False
    
    session_token = resp.cookies.get('session_token')
    if not session_token:
        print("❌ Tidak dapat session_token dari login")
        return False
    
    print(f"✅ Login berhasil, session_token: {session_token[:20]}...")
    
    # Test /api/health
    print("\n2. Test /api/health...")
    resp = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Response: {data}")
    
    assert resp.status_code == 200, f"/api/health harus 200, got {resp.status_code}"
    assert data.get('status') == 'ok', f"status harus 'ok', got {data.get('status')}"
    print("✅ /api/health: OK")
    
    # Test /api/health/live
    print("\n3. Test /api/health/live...")
    resp = requests.get(f"{BASE_URL}/api/health/live")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Response: {data}")
    
    assert resp.status_code == 200, f"/api/health/live harus 200, got {resp.status_code}"
    assert 'version' in data, "Harus ada field 'version'"
    print("✅ /api/health/live: OK")
    
    # Test /api/admin/system-status
    print("\n4. Test /api/admin/system-status...")
    resp = requests.get(f"{BASE_URL}/api/admin/system-status", cookies={'session_token': session_token})
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ /api/admin/system-status gagal: {resp.status_code}")
        print(resp.text)
        return False
    
    data = resp.json()
    print(f"Response keys: {list(data.keys())}")
    print(f"Database: {data.get('database')}")
    print(f"Startup: {data.get('startup')}")
    print(f"Runtime: {data.get('runtime')}")
    
    # Validasi struktur response
    assert 'database' in data, "Harus ada field 'database'"
    assert 'startup' in data, "Harus ada field 'startup'"
    assert 'runtime' in data, "Harus ada field 'runtime'"
    assert 'version' in data, "Harus ada field 'version'"
    
    db = data['database']
    assert 'config_warnings' in db, "database harus punya field 'config_warnings'"
    assert isinstance(db['config_warnings'], list), "config_warnings harus list"
    assert db.get('ok') is True, f"database.ok harus true di preview, got {db.get('ok')}"
    
    print(f"✅ /api/admin/system-status: OK")
    print(f"   - config_warnings: {db['config_warnings']} (kosong di preview = OK)")
    print(f"   - database.ok: {db.get('ok')}")
    
    # Test beberapa endpoint lain untuk regression
    print("\n5. Regression test endpoints...")
    
    endpoints = [
        "/api/units",
        "/api/operations",
        "/api/admin/backup/info"
    ]
    
    for endpoint in endpoints:
        resp = requests.get(f"{BASE_URL}{endpoint}", cookies={'session_token': session_token})
        print(f"   {endpoint}: {resp.status_code}")
        assert resp.status_code == 200, f"{endpoint} harus 200, got {resp.status_code}"
    
    print("✅ Regression test: semua endpoint OK")
    
    print("\n" + "="*70)
    print("✅ PASS: Admin System Status & Regression Preview")
    print("="*70)
    return True

if __name__ == '__main__':
    try:
        success = test_admin_system_status()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
