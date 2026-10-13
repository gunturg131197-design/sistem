"""Test scripts/cron_call.py for Coolify Scheduled Tasks.

Tests:
1. Valid job with correct secret -> 200
2. Invalid secret -> 401
3. Invalid job name -> exit 2 with usage message
"""
import subprocess
import os


def _cron_secret():
    """Baca WEBHOOK_CRON_SECRET dari env atau /app/backend/.env (tidak di-hardcode)."""
    import os as _os
    v = _os.environ.get("WEBHOOK_CRON_SECRET")
    if v:
        return v
    try:
        for line in open("/app/backend/.env"):
            if line.startswith("WEBHOOK_CRON_SECRET="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
    print(f"{prefix} {msg}")

def test_cron_call():
    log("\n=== Testing scripts/cron_call.py ===", "INFO")
    
    # Get env vars
    webhook_secret = _cron_secret()
    port = "8001"  # Supervisor backend port
    
    # Test 1: Valid job with correct secret
    log("\nTest 1: wa-outbox-retry with correct secret", "INFO")
    env = os.environ.copy()
    env["WEBHOOK_CRON_SECRET"] = webhook_secret
    env["PORT"] = port
    
    result = subprocess.run(
        ["python", "scripts/cron_call.py", "wa-outbox-retry"],
        cwd="/app/backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        log(f"✅ Exit code 0 (success)", "PASS")
        if "200" in result.stdout or "accepted" in result.stdout.lower():
            log(f"✅ Output indicates success: {result.stdout[:100]}", "PASS")
        else:
            log(f"⚠️  Output: {result.stdout[:200]}", "WARN")
    else:
        log(f"❌ Exit code {result.returncode}", "FAIL")
        log(f"  Output: {result.stdout[:200]}", "FAIL")
        log(f"  Error: {result.stderr[:200]}", "FAIL")
    
    # Test 2: Invalid secret
    log("\nTest 2: wa-outbox-retry with wrong secret", "INFO")
    env["WEBHOOK_CRON_SECRET"] = "wrong_secret"
    
    result = subprocess.run(
        ["python", "scripts/cron_call.py", "wa-outbox-retry"],
        cwd="/app/backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 1:
        log(f"✅ Exit code 1 (auth error expected)", "PASS")
        if "401" in result.stdout or "unauthorized" in result.stdout.lower():
            log(f"✅ Output indicates 401: {result.stdout[:100]}", "PASS")
        else:
            log(f"⚠️  Output: {result.stdout[:200]}", "WARN")
    else:
        log(f"❌ Exit code {result.returncode} (expected 1)", "FAIL")
        log(f"  Output: {result.stdout[:200]}", "FAIL")
    
    # Test 3: Invalid job name
    log("\nTest 3: Invalid job name", "INFO")
    env["WEBHOOK_CRON_SECRET"] = webhook_secret
    
    result = subprocess.run(
        ["python", "scripts/cron_call.py", "invalid-job"],
        cwd="/app/backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 2:
        log(f"✅ Exit code 2 (usage error expected)", "PASS")
        if "Pemakaian" in result.stdout or "usage" in result.stdout.lower():
            log(f"✅ Output shows usage message", "PASS")
        else:
            log(f"⚠️  Output: {result.stdout[:200]}", "WARN")
    else:
        log(f"❌ Exit code {result.returncode} (expected 2)", "FAIL")
        log(f"  Output: {result.stdout[:200]}", "FAIL")
    
    # Test 4: No secret set
    log("\nTest 4: No WEBHOOK_CRON_SECRET set", "INFO")
    env_no_secret = os.environ.copy()
    if "WEBHOOK_CRON_SECRET" in env_no_secret:
        del env_no_secret["WEBHOOK_CRON_SECRET"]
    env_no_secret["PORT"] = port
    
    result = subprocess.run(
        ["python", "scripts/cron_call.py", "wa-outbox-retry"],
        cwd="/app/backend",
        env=env_no_secret,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 1:
        log(f"✅ Exit code 1 (error expected)", "PASS")
        if "belum di-set" in result.stdout or "not set" in result.stdout.lower():
            log(f"✅ Output indicates missing secret: {result.stdout[:100]}", "PASS")
        else:
            log(f"⚠️  Output: {result.stdout[:200]}", "WARN")
    else:
        log(f"❌ Exit code {result.returncode} (expected 1)", "FAIL")

def main():
    log("\n" + "="*70, "INFO")
    log("scripts/cron_call.py Tests", "INFO")
    log("="*70 + "\n", "INFO")
    
    try:
        test_cron_call()
        
        log("\n" + "="*70, "INFO")
        log("All cron_call.py tests completed", "INFO")
        log("="*70 + "\n", "INFO")
        
    except Exception as e:
        log(f"\n❌ Test suite failed: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
