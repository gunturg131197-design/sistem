#!/usr/bin/env python3
"""Integration test untuk run.py: proses harus tetap hidup dengan env salah format."""
import os
import sys
import time
import signal
import subprocess
import requests
from pathlib import Path

# Port untuk testing (harus bebas, tidak bentrok dengan 3000/8001)
TEST_PORTS = list(range(8791, 8800))
used_ports = []

def get_free_port():
    """Ambil port bebas dari pool"""
    for p in TEST_PORTS:
        if p not in used_ports:
            used_ports.append(p)
            return p
    raise RuntimeError("Tidak ada port bebas untuk testing")

def test_malformed_env(test_name, env_vars, expected_health_status=200, expected_health_contains=None):
    """Test run.py dengan env tertentu, pastikan proses tetap hidup dan /api/health/live 200"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    
    port = get_free_port()
    print(f"Port: {port}")
    print(f"Env vars: {env_vars}")
    
    # Salin backend ke dir sementara
    import tempfile
    import shutil
    tmpdir = tempfile.mkdtemp(prefix="test_run_")
    backend_src = Path(__file__).parent.parent / "backend"
    backend_dst = Path(tmpdir) / "backend"
    
    print(f"Menyalin backend ke {tmpdir}...")
    shutil.copytree(backend_src, backend_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    
    # Hapus .env agar tidak mengganggu
    env_file = backend_dst / ".env"
    if env_file.exists():
        env_file.unlink()
    
    # Setup env untuk subprocess
    test_env = os.environ.copy()
    test_env['PORT'] = str(port)
    test_env['EXTRA_PORTS'] = ''  # Kosongkan agar hanya listen di satu port
    test_env['PYTHONPATH'] = str(backend_dst)
    
    # Tambahkan env vars test
    for k, v in env_vars.items():
        test_env[k] = v
    
    # Jalankan run.py
    print(f"Menjalankan run.py...")
    proc = subprocess.Popen(
        [sys.executable, str(backend_dst / "run.py")],
        env=test_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=backend_dst
    )
    
    try:
        # Tunggu proses start (max 15 detik)
        print("Menunggu server start...")
        start_time = time.time()
        server_ready = False
        
        while time.time() - start_time < 15:
            if proc.poll() is not None:
                # Proses mati - GAGAL
                stdout, _ = proc.communicate()
                print(f"❌ GAGAL: Proses keluar dengan code {proc.returncode}")
                print(f"Output:\n{stdout}")
                raise AssertionError(f"Proses keluar (exit code {proc.returncode}), seharusnya tetap hidup")
            
            try:
                resp = requests.get(f"http://127.0.0.1:{port}/api/health/live", timeout=1)
                if resp.status_code == 200:
                    server_ready = True
                    print(f"✅ Server ready setelah {time.time() - start_time:.1f} detik")
                    break
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(0.5)
        
        if not server_ready:
            raise AssertionError("Server tidak ready setelah 15 detik")
        
        # Test /api/health/live harus 200
        print("\nTesting /api/health/live...")
        resp = requests.get(f"http://127.0.0.1:{port}/api/health/live", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        
        assert resp.status_code == 200, f"/api/health/live harus 200, got {resp.status_code}"
        data = resp.json()
        assert 'status' in data, "Response harus punya field 'status'"
        
        # Test /api/health
        print("\nTesting /api/health...")
        resp = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        
        assert resp.status_code == expected_health_status, f"/api/health harus {expected_health_status}, got {resp.status_code}"
        
        if expected_health_contains:
            resp_text = resp.text
            for text in expected_health_contains:
                assert text in resp_text, f"Response harus mengandung '{text}', got: {resp_text}"
        
        # Pastikan proses masih hidup setelah 12 detik
        print("\nMenunggu 12 detik untuk memastikan proses stabil...")
        time.sleep(12)
        
        if proc.poll() is not None:
            stdout, _ = proc.communicate()
            print(f"❌ GAGAL: Proses keluar setelah 12 detik dengan code {proc.returncode}")
            print(f"Output:\n{stdout}")
            raise AssertionError(f"Proses keluar setelah 12 detik, seharusnya tetap hidup")
        
        # Test lagi /api/health/live
        resp = requests.get(f"http://127.0.0.1:{port}/api/health/live", timeout=5)
        assert resp.status_code == 200, f"/api/health/live harus tetap 200 setelah 12 detik"
        
        print(f"\n✅ PASS: {test_name}")
        print(f"   - Proses tetap hidup >12 detik")
        print(f"   - /api/health/live: 200")
        print(f"   - /api/health: {expected_health_status}")
        
    finally:
        # Cleanup
        print("\nMembersihkan...")
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        
        shutil.rmtree(tmpdir, ignore_errors=True)
        used_ports.remove(port)

def main():
    print("="*70)
    print("INTEGRATION TEST: run.py dengan env salah format")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: DB_PORT bukan angka
    tests_total += 1
    try:
        test_malformed_env(
            "DB_PORT bukan angka",
            {
                'DB_HOST': '127.0.0.1',
                'DB_PORT': 'GANTI',
                'DB_USERNAME': 'trirara',
                'DB_PASSWORD': 'trirara_dev',
                'DB_DATABASE': 'trirara'
            },
            expected_health_status=200,
            expected_health_contains=['config_warnings']
        )
        tests_passed += 1
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
    
    # Test 2: DB_HOST berisi URL lengkap
    tests_total += 1
    try:
        test_malformed_env(
            "DB_HOST berisi URL lengkap",
            {
                'DB_HOST': 'mysql://trirara:trirara_dev@127.0.0.1:3306/trirara',
                'DB_USERNAME': 'ignored',
                'DB_PASSWORD': 'ignored'
            },
            expected_health_status=200,
            expected_health_contains=['config_warnings']
        )
        tests_passed += 1
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
    
    # Test 3: DB_HOST berisi host:port
    tests_total += 1
    try:
        test_malformed_env(
            "DB_HOST berisi host:port",
            {
                'DB_HOST': '127.0.0.1:3306',
                'DB_USERNAME': 'trirara',
                'DB_PASSWORD': 'trirara_dev',
                'DB_DATABASE': 'trirara'
            },
            expected_health_status=200,
            expected_health_contains=['config_warnings']
        )
        tests_passed += 1
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
    
    # Test 4: MARIADB_URL rusak (port tidak valid)
    tests_total += 1
    try:
        test_malformed_env(
            "MARIADB_URL rusak (port tidak valid)",
            {
                'MARIADB_URL': 'mysql://user:rahasia99@host:33x6/db'
            },
            expected_health_status=503,
            expected_health_contains=['Konfigurasi database tidak valid']
        )
        tests_passed += 1
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
    
    # Test 5: PORT bukan angka (harus listen di 8000 atau log warning)
    tests_total += 1
    try:
        # Untuk test ini, kita cek log saja karena port akan default ke 8000
        print(f"\n{'='*70}")
        print(f"TEST: PORT bukan angka")
        print(f"{'='*70}")
        
        import tempfile
        import shutil
        tmpdir = tempfile.mkdtemp(prefix="test_run_")
        backend_src = Path(__file__).parent.parent / "backend"
        backend_dst = Path(tmpdir) / "backend"
        shutil.copytree(backend_src, backend_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        
        env_file = backend_dst / ".env"
        if env_file.exists():
            env_file.unlink()
        
        test_env = os.environ.copy()
        test_env['PORT'] = 'abc'  # Bukan angka
        test_env['EXTRA_PORTS'] = ''
        test_env['PYTHONPATH'] = str(backend_dst)
        test_env['MARIADB_URL'] = 'mysql+asyncmy://trirara:trirara_dev@127.0.0.1:3306/trirara?charset=utf8mb4'
        
        proc = subprocess.Popen(
            [sys.executable, str(backend_dst / "run.py")],
            env=test_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=backend_dst
        )
        
        try:
            time.sleep(3)
            output_lines = []
            
            # Baca output
            import select
            while True:
                ready, _, _ = select.select([proc.stdout], [], [], 0.1)
                if ready:
                    line = proc.stdout.readline()
                    if line:
                        output_lines.append(line)
                        print(line.rstrip())
                else:
                    break
            
            output = ''.join(output_lines)
            
            # Cek log harus ada warning tentang PORT bukan angka
            assert 'bukan angka' in output and '8000' in output, f"Log harus ada warning PORT bukan angka, got: {output}"
            
            print(f"\n✅ PASS: PORT bukan angka")
            tests_passed += 1
            
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            shutil.rmtree(tmpdir, ignore_errors=True)
            
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
    
    # Summary
    print("\n" + "="*70)
    print(f"HASIL: {tests_passed}/{tests_total} test berhasil")
    print("="*70)
    
    if tests_passed == tests_total:
        print("✅ SEMUA TEST INTEGRATION BERHASIL")
        return 0
    else:
        print(f"❌ {tests_total - tests_passed} test gagal")
        return 1

if __name__ == '__main__':
    sys.exit(main())
