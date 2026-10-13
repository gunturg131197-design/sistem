#!/usr/bin/env python3
"""Test safe mode: server.py gagal import dengan secret di env, harus tetap hidup dan sanitize secret."""
import os
import sys
import time
import subprocess
import requests
from pathlib import Path
import tempfile
import shutil

def test_safe_mode_with_secret():
    """Test: server.py crash dengan secret di env → safe mode aktif, secret disembunyikan"""
    print("="*70)
    print("TEST: Safe Mode dengan Secret Sanitization")
    print("="*70)
    
    # Setup
    tmpdir = tempfile.mkdtemp(prefix="test_safe_")
    backend_src = Path(__file__).parent.parent / "backend"
    backend_dst = Path(tmpdir) / "backend"
    
    print(f"Menyalin backend ke {tmpdir}...")
    shutil.copytree(backend_src, backend_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    
    # Hapus .env
    env_file = backend_dst / ".env"
    if env_file.exists():
        env_file.unlink()
    
    # Inject error di server.py (baris pertama)
    server_file = backend_dst / "server.py"
    original_content = server_file.read_text()
    
    # Tambahkan import os dan raise error dengan password di baris pertama
    modified_content = (
        "import os\n"
        "raise RuntimeError('gagal ' + os.environ.get('DB_PASSWORD', 'nopass'))\n"
        + original_content
    )
    server_file.write_text(modified_content)
    
    # Setup env dengan secret
    secret_password = "RahasiaSekali123"
    port = 8795
    
    test_env = os.environ.copy()
    test_env['PORT'] = str(port)
    test_env['EXTRA_PORTS'] = ''
    test_env['PYTHONPATH'] = str(backend_dst)
    test_env['DB_PASSWORD'] = secret_password
    test_env['MARIADB_URL'] = f'mysql+asyncmy://user:{secret_password}@127.0.0.1:3306/db'
    
    print(f"\nMenjalankan run.py dengan DB_PASSWORD={secret_password}...")
    proc = subprocess.Popen(
        [sys.executable, str(backend_dst / "run.py")],
        env=test_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=backend_dst
    )
    
    try:
        # Tunggu server start
        print("Menunggu server start...")
        time.sleep(3)
        
        # Cek proses masih hidup
        if proc.poll() is not None:
            stdout, _ = proc.communicate()
            print(f"❌ GAGAL: Proses keluar dengan code {proc.returncode}")
            print(f"Output:\n{stdout}")
            raise AssertionError("Proses keluar, seharusnya tetap hidup dalam safe mode")
        
        print("✅ Proses tetap hidup")
        
        # Test /api/health/live harus 200 dengan safe_mode: true
        print("\nTesting /api/health/live...")
        resp = requests.get(f"http://127.0.0.1:{port}/api/health/live", timeout=5)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        assert resp.status_code == 200, f"/api/health/live harus 200, got {resp.status_code}"
        assert data.get('safe_mode') is True, f"safe_mode harus true, got {data}"
        assert 'error' in data, "Harus ada field 'error'"
        
        # Secret tidak boleh muncul di response
        resp_text = resp.text
        assert secret_password not in resp_text, f"Secret '{secret_password}' tidak boleh muncul di /api/health/live response"
        assert '***' in resp_text or 'gagal' in resp_text, "Error harus ada tapi secret disembunyikan"
        print("✅ /api/health/live: 200, safe_mode: true, secret tersembunyi")
        
        # Test /api/health harus 503 dengan detail error (tanpa secret)
        print("\nTesting /api/health...")
        resp = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=5)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        assert resp.status_code == 503, f"/api/health harus 503, got {resp.status_code}"
        assert data.get('safe_mode') is True, "safe_mode harus true"
        assert 'detail' in data, "Harus ada field 'detail'"
        
        resp_text = resp.text
        assert secret_password not in resp_text, f"Secret '{secret_password}' tidak boleh muncul di /api/health response"
        print("✅ /api/health: 503, safe_mode: true, secret tersembunyi")
        
        # Test path lain (/) harus 503 text
        print("\nTesting / (root path)...")
        resp = requests.get(f"http://127.0.0.1:{port}/", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
        print(f"Response (first 200 chars): {resp.text[:200]}")
        
        assert resp.status_code == 503, f"/ harus 503, got {resp.status_code}"
        assert 'text/plain' in resp.headers.get('content-type', ''), "Content-Type harus text/plain"
        assert secret_password not in resp.text, f"Secret tidak boleh muncul di / response"
        print("✅ /: 503 text/plain, secret tersembunyi")
        
        # Cek stdout/stderr tidak memuat secret
        print("\nMemeriksa log stdout/stderr...")
        output_lines = []
        import select
        while True:
            ready, _, _ = select.select([proc.stdout], [], [], 0.1)
            if ready:
                line = proc.stdout.readline()
                if line:
                    output_lines.append(line)
            else:
                break
        
        output = ''.join(output_lines)
        print(f"Log output (first 500 chars):\n{output[:500]}")
        
        # Secret harus disembunyikan di log juga (yang penting secret tidak muncul)
        assert secret_password not in output, f"Secret '{secret_password}' tidak boleh muncul di log stdout/stderr"
        print("✅ Log tidak memuat secret (yang penting secret tersembunyi)")
        
        # Tunggu 10 detik lagi, pastikan tetap hidup
        print("\nMenunggu 10 detik untuk memastikan proses stabil...")
        time.sleep(10)
        
        if proc.poll() is not None:
            raise AssertionError("Proses keluar setelah 10 detik, seharusnya tetap hidup")
        
        # Test lagi
        resp = requests.get(f"http://127.0.0.1:{port}/api/health/live", timeout=5)
        assert resp.status_code == 200, "/api/health/live harus tetap 200"
        
        print("\n" + "="*70)
        print("✅ PASS: Safe Mode dengan Secret Sanitization")
        print("="*70)
        print("Summary:")
        print("  - Proses tetap hidup walau server.py crash")
        print("  - /api/health/live: 200 dengan safe_mode: true")
        print("  - /api/health: 503 dengan error detail")
        print("  - Secret tidak muncul di response API")
        print("  - Secret tidak muncul di log stdout/stderr")
        print("  - Proses stabil >10 detik")
        
        return True
        
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

if __name__ == '__main__':
    try:
        success = test_safe_mode_with_secret()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST GAGAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
