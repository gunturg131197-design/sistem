#!/usr/bin/env python3
"""Unit test untuk resolve_db_url: memastikan tidak pernah crash dengan env salah format."""
import sys
import os

# Tambahkan backend ke path agar bisa import mariadb_store
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mariadb_store import resolve_db_url

def test_db_host_contains_full_url():
    """DB_HOST berisi URL lengkap mysql://user:pass@host:3306/db → dipakai sebagai MARIADB_URL"""
    print("\n=== Test 1: DB_HOST berisi URL lengkap ===")
    env = {
        'DB_HOST': 'mysql://u:p@h:3306/db',
        'DB_USERNAME': 'ignored',
        'DB_PASSWORD': 'ignored'
    }
    url, warnings, error = resolve_db_url(env)
    print(f"URL: {url}")
    print(f"Warnings: {warnings}")
    print(f"Error: {error}")
    
    assert 'mysql+asyncmy://u:p@h:3306/db' in url, f"URL harus mengandung kredensial dari DB_HOST, got: {url}"
    assert any('DB_HOST berisi URL lengkap' in w for w in warnings), f"Harus ada warning tentang DB_HOST berisi URL, got: {warnings}"
    assert error is None, f"Tidak boleh ada error, got: {error}"
    print("✅ PASS: DB_HOST dengan URL lengkap diproses dengan benar")

def test_db_host_with_port():
    """DB_HOST berisi host:port → dipisah menjadi host dan port"""
    print("\n=== Test 2: DB_HOST berisi host:port ===")
    env = {
        'DB_HOST': 'h:3307',
        'DB_USERNAME': 'user',
        'DB_PASSWORD': 'x',
        'DB_DATABASE': 'db'
    }
    url, warnings, error = resolve_db_url(env)
    print(f"URL: {url}")
    print(f"Warnings: {warnings}")
    print(f"Error: {error}")
    
    assert ':3307' in url, f"Port 3307 harus ada di URL, got: {url}"
    assert any('host:port' in w for w in warnings), f"Harus ada warning tentang host:port, got: {warnings}"
    assert error is None, f"Tidak boleh ada error, got: {error}"
    print("✅ PASS: DB_HOST dengan host:port diproses dengan benar")

def test_db_port_not_number():
    """DB_PORT bukan angka → default 3306 + warning"""
    print("\n=== Test 3: DB_PORT bukan angka ===")
    env = {
        'DB_HOST': 'h',
        'DB_PORT': 'GANTI',
        'DB_USERNAME': 'user',
        'DB_PASSWORD': 'pass',
        'DB_DATABASE': 'db'
    }
    url, warnings, error = resolve_db_url(env)
    print(f"URL: {url}")
    print(f"Warnings: {warnings}")
    print(f"Error: {error}")
    
    assert ':3306' in url, f"Port harus default ke 3306, got: {url}"
    assert any('bukan angka' in w and '3306' in w for w in warnings), f"Harus ada warning tentang port bukan angka, got: {warnings}"
    assert error is None, f"Tidak boleh ada error untuk port salah, got: {error}"
    print("✅ PASS: DB_PORT bukan angka ditangani dengan default 3306")

def test_mariadb_url_invalid():
    """MARIADB_URL tidak valid → URL cadangan + error (tanpa password di pesan)"""
    print("\n=== Test 4: MARIADB_URL tidak valid ===")
    env = {
        'MARIADB_URL': 'mysql://user:rahasia99@host:33x6/db'  # port 33x6 tidak valid
    }
    url, warnings, error = resolve_db_url(env)
    print(f"URL: {url}")
    print(f"Warnings: {warnings}")
    print(f"Error: {error}")
    
    assert 'belum-dikonfigurasi' in url and '127.0.0.1' in url, f"Harus pakai URL cadangan, got: {url}"
    assert error is not None, f"Harus ada error untuk URL tidak valid"
    assert 'Konfigurasi database tidak valid' in error, f"Error harus jelas, got: {error}"
    assert 'rahasia99' not in error, f"Password tidak boleh muncul di error, got: {error}"
    print("✅ PASS: MARIADB_URL tidak valid menghasilkan URL cadangan + error tanpa password")

def test_empty_env():
    """Env kosong → default 127.0.0.1 tanpa error"""
    print("\n=== Test 5: Env kosong ===")
    env = {}
    url, warnings, error = resolve_db_url(env)
    print(f"URL: {url}")
    print(f"Warnings: {warnings}")
    print(f"Error: {error}")
    
    assert '127.0.0.1' in url, f"Harus default ke 127.0.0.1, got: {url}"
    assert error is None, f"Env kosong tidak boleh error, got: {error}"
    print("✅ PASS: Env kosong menghasilkan URL default tanpa error")

def test_database_url_backward_compat():
    """DATABASE_URL (legacy) tetap berfungsi"""
    print("\n=== Test 6: DATABASE_URL backward compatibility ===")
    env = {
        'DATABASE_URL': 'mysql://olduser:oldpass@oldhost:3306/olddb'
    }
    url, warnings, error = resolve_db_url(env)
    print(f"URL: {url}")
    print(f"Warnings: {warnings}")
    print(f"Error: {error}")
    
    assert 'olduser' in url and 'oldhost' in url, f"DATABASE_URL harus dipakai, got: {url}"
    assert error is None, f"DATABASE_URL valid tidak boleh error, got: {error}"
    print("✅ PASS: DATABASE_URL (legacy) masih berfungsi")

def test_build_url_from_env_backward_compat():
    """build_url_from_env (fungsi lama) tetap berfungsi tanpa regresi"""
    print("\n=== Test 7: build_url_from_env backward compatibility ===")
    from mariadb_store import build_url_from_env
    env = {
        'DB_HOST': 'testhost',
        'DB_PORT': '3307',
        'DB_USERNAME': 'testuser',
        'DB_PASSWORD': 'testpass',
        'DB_DATABASE': 'testdb'
    }
    url = build_url_from_env(env)
    print(f"URL: {url}")
    
    assert 'testuser' in url and 'testhost' in url and '3307' in url, f"build_url_from_env harus berfungsi, got: {url}"
    print("✅ PASS: build_url_from_env (fungsi lama) tidak regresi")

if __name__ == '__main__':
    print("=" * 70)
    print("UNIT TEST: resolve_db_url")
    print("=" * 70)
    
    try:
        test_db_host_contains_full_url()
        test_db_host_with_port()
        test_db_port_not_number()
        test_mariadb_url_invalid()
        test_empty_env()
        test_database_url_backward_compat()
        test_build_url_from_env_backward_compat()
        
        print("\n" + "=" * 70)
        print("✅ SEMUA TEST UNIT BERHASIL (7/7)")
        print("=" * 70)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST GAGAL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
