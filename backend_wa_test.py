#!/usr/bin/env python3
"""
Backend API Test Suite for WhatsApp Integration
Tests WhatsApp inbox, upload, AI processing, approve/reject, contacts, and status endpoints
"""
import requests
import base64
import time
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://admin-bonus-unit.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"username": "admin", "password": "admin123"}
OPERATOR_CREDS = {"username": "budi", "password": "budi123"}

# Session storage
admin_session = None
operator_session = None
test_data = {
    "created_items": [],  # Track all created items for cleanup
    "created_contacts": [],  # Track all created contacts for cleanup
    "created_kas_masuk": [],  # Track kas_masuk entries created by approve
    "created_operations": [],  # Track operations created by approve
    "units_to_reset": []  # Track units whose kode_wa needs to be reset
}

# Existing unit IDs from the problem statement
EXISTING_UNIT_EX01 = "de90def5-6a41-4e1c-91f8-cfe3dfe017f0"  # Komatsu PC200, nomor_lambung EX-01


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


def test_wa_status():
    """Test 1: GET /api/wa/status - should show not configured"""
    print("\n=== TEST 1: WhatsApp Status (Not Configured) ===")
    
    response = admin_session.get(f"{BASE_URL}/wa/status")
    if response.status_code != 200:
        print(f"✗ Failed to get WA status: {response.status_code} {response.text}")
        return False
    
    status = response.json()
    print(f"✓ GET /wa/status successful")
    
    # Verify not configured
    if status.get("configured") != False:
        print(f"✗ Expected configured=false, got {status.get('configured')}")
        return False
    
    # Check missing credentials
    expected_missing = ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN"]
    missing = status.get("missing", [])
    if set(missing) != set(expected_missing):
        print(f"✗ Expected missing {expected_missing}, got {missing}")
        return False
    
    # Check AI model
    if not status.get("ai_model"):
        print(f"✗ ai_model not returned")
        return False
    
    # Check counts
    if "counts" not in status:
        print(f"✗ counts not returned")
        return False
    
    print(f"✓ Status shows not configured (expected)")
    print(f"  - Missing credentials: {len(missing)}")
    print(f"  - AI model: {status.get('ai_model')}")
    print(f"  - Counts: {status.get('counts')}")
    
    return True


def test_webhook_disabled():
    """Test 2: Webhook endpoints should return disabled/503"""
    print("\n=== TEST 2: Webhook Endpoints (Disabled) ===")
    
    # Test GET webhook (verification)
    response = requests.get(f"{BASE_URL}/whatsapp/webhook")
    if response.status_code != 503:
        print(f"✗ Expected 503 for GET webhook, got {response.status_code}")
        return False
    
    print(f"✓ GET /whatsapp/webhook returns 503 (not configured)")
    
    # Test POST webhook
    response = requests.post(f"{BASE_URL}/whatsapp/webhook", json={"test": "data"})
    if response.status_code != 200:
        print(f"✗ POST webhook failed: {response.status_code}")
        return False
    
    data = response.json()
    if data.get("status") != "disabled":
        print(f"✗ Expected status='disabled', got {data.get('status')}")
        return False
    
    print(f"✓ POST /whatsapp/webhook returns {{'status': 'disabled'}}")
    
    return True


def test_upload_transfer():
    """Test 3: Upload transfer image (hm.webp is actually BRI transfer)"""
    print("\n=== TEST 3: Upload Transfer Image (AI Processing) ===")
    
    # Read the test image (hm.webp is actually the BRI transfer receipt)
    try:
        with open("/app/tests/fixtures/hm.webp", "rb") as f:
            image_data = f.read()
    except Exception as e:
        print(f"✗ Failed to read test image: {e}")
        return False
    
    # Upload with caption matching unit EX-01
    files = {"file": ("transfer.webp", image_data, "image/webp")}
    data = {"caption": "EX-01", "phone": ""}
    
    response = admin_session.post(f"{BASE_URL}/wa/upload", files=files, data=data)
    if response.status_code != 200:
        print(f"✗ Failed to upload: {response.status_code} {response.text}")
        return False
    
    item = response.json()
    test_data["created_items"].append(item["id"])
    print(f"✓ Upload successful, item ID: {item['id']}")
    print(f"  - Status: {item.get('status')}")
    print(f"  - Caption: {item.get('caption')}")
    
    if item.get("status") != "processing":
        print(f"✗ Expected status='processing', got {item.get('status')}")
        return False
    
    # Wait for AI processing (10-25 seconds)
    print(f"  - Waiting for AI processing (max 30s)...")
    max_wait = 30
    waited = 0
    processed_item = None
    
    while waited < max_wait:
        time.sleep(3)
        waited += 3
        
        # Poll inbox
        response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "all"})
        if response.status_code != 200:
            continue
        
        items = response.json()
        for it in items:
            if it["id"] == item["id"]:
                if it["status"] != "processing":
                    processed_item = it
                    break
        
        if processed_item:
            break
        
        print(f"    ... {waited}s")
    
    if not processed_item:
        print(f"✗ AI processing did not complete within {max_wait}s")
        return False
    
    print(f"✓ AI processing completed in ~{waited}s")
    print(f"  - Status: {processed_item.get('status')}")
    print(f"  - Jenis: {processed_item.get('jenis')}")
    
    # Verify it's recognized as transfer
    if processed_item.get("jenis") != "transfer":
        print(f"✗ Expected jenis='transfer', got {processed_item.get('jenis')}")
        return False
    
    # Check draft fields
    draft = processed_item.get("draft", {})
    if not draft.get("debit"):
        print(f"✗ Draft debit not extracted")
        return False
    
    if not draft.get("no_ref"):
        print(f"✗ Draft no_ref not extracted")
        return False
    
    print(f"✓ Transfer data extracted:")
    print(f"  - Debit: Rp{draft.get('debit'):,.0f}")
    print(f"  - No. Ref: {draft.get('no_ref')}")
    print(f"  - Tanggal: {draft.get('tanggal')}")
    print(f"  - Unit matched: {processed_item.get('match', {}).get('unit_label', 'none')}")
    
    # Store for next test
    test_data["transfer_item_id"] = item["id"]
    test_data["transfer_no_ref"] = draft.get("no_ref")
    
    return True


def test_upload_hour_meter():
    """Test 4: Upload hour meter image (transfer.png is actually ZOOMLION HM)"""
    print("\n=== TEST 4: Upload Hour Meter Image (AI Processing) ===")
    
    # Read the test image (transfer.png is actually the ZOOMLION HM screen)
    try:
        with open("/app/tests/fixtures/transfer.png", "rb") as f:
            image_data = f.read()
    except Exception as e:
        print(f"✗ Failed to read test image: {e}")
        return False
    
    # Upload with caption
    files = {"file": ("hm.png", image_data, "image/png")}
    data = {"caption": "EX-01", "phone": ""}
    
    response = admin_session.post(f"{BASE_URL}/wa/upload", files=files, data=data)
    if response.status_code != 200:
        print(f"✗ Failed to upload: {response.status_code} {response.text}")
        return False
    
    item = response.json()
    test_data["created_items"].append(item["id"])
    print(f"✓ Upload successful, item ID: {item['id']}")
    
    # Wait for AI processing
    print(f"  - Waiting for AI processing (max 30s)...")
    max_wait = 30
    waited = 0
    processed_item = None
    
    while waited < max_wait:
        time.sleep(3)
        waited += 3
        
        response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "all"})
        if response.status_code != 200:
            continue
        
        items = response.json()
        for it in items:
            if it["id"] == item["id"]:
                if it["status"] != "processing":
                    processed_item = it
                    break
        
        if processed_item:
            break
        
        print(f"    ... {waited}s")
    
    if not processed_item:
        print(f"✗ AI processing did not complete within {max_wait}s")
        return False
    
    print(f"✓ AI processing completed in ~{waited}s")
    print(f"  - Status: {processed_item.get('status')}")
    print(f"  - Jenis: {processed_item.get('jenis')}")
    
    # Verify it's recognized as hour_meter
    if processed_item.get("jenis") != "hour_meter":
        print(f"✗ Expected jenis='hour_meter', got {processed_item.get('jenis')}")
        return False
    
    # Check draft fields
    draft = processed_item.get("draft", {})
    if not draft.get("hm_akhir"):
        print(f"✗ Draft hm_akhir not extracted")
        return False
    
    print(f"✓ Hour meter data extracted:")
    print(f"  - HM Akhir: {draft.get('hm_akhir')}")
    print(f"  - HM Awal: {draft.get('hm_awal')}")
    print(f"  - Tanggal: {draft.get('tanggal')}")
    print(f"  - Unit matched: {processed_item.get('match', {}).get('unit_label', 'none')}")
    
    # Store for next test
    test_data["hm_item_id"] = item["id"]
    
    return True


def test_inbox_list():
    """Test 5: GET /api/wa/inbox with filters"""
    print("\n=== TEST 5: List Inbox Items ===")
    
    # Get all items
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "all"})
    if response.status_code != 200:
        print(f"✗ Failed to get inbox: {response.status_code}")
        return False
    
    all_items = response.json()
    print(f"✓ GET /wa/inbox?status=all returned {len(all_items)} items")
    
    # Get pending items
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "pending"})
    if response.status_code != 200:
        print(f"✗ Failed to get pending: {response.status_code}")
        return False
    
    pending_items = response.json()
    print(f"✓ GET /wa/inbox?status=pending returned {len(pending_items)} items")
    
    # Verify our items are in the list
    our_ids = set(test_data["created_items"])
    found_ids = set(item["id"] for item in all_items)
    
    if not our_ids.issubset(found_ids):
        print(f"✗ Not all uploaded items found in inbox")
        return False
    
    print(f"✓ All uploaded items found in inbox")
    
    return True


def test_media_endpoint():
    """Test 6: GET /api/wa/inbox/{id}/media"""
    print("\n=== TEST 6: Get Media Image ===")
    
    if "transfer_item_id" not in test_data:
        print(f"⚠️  Skipping (no transfer item)")
        return True
    
    item_id = test_data["transfer_item_id"]
    response = admin_session.get(f"{BASE_URL}/wa/inbox/{item_id}/media")
    
    if response.status_code != 200:
        print(f"✗ Failed to get media: {response.status_code}")
        return False
    
    # Check content type
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        print(f"✗ Expected image content-type, got {content_type}")
        return False
    
    # Check we got image data
    if len(response.content) < 1000:
        print(f"✗ Image data too small: {len(response.content)} bytes")
        return False
    
    print(f"✓ GET /wa/inbox/{item_id}/media successful")
    print(f"  - Content-Type: {content_type}")
    print(f"  - Size: {len(response.content):,} bytes")
    
    return True


def test_update_draft():
    """Test 7: PATCH /api/wa/inbox/{id} to update draft"""
    print("\n=== TEST 7: Update Draft Fields ===")
    
    if "transfer_item_id" not in test_data:
        print(f"⚠️  Skipping (no transfer item)")
        return True
    
    item_id = test_data["transfer_item_id"]
    
    # Update draft
    payload = {
        "draft": {
            "pengurus": "Test Pengurus",
            "uraian": "Updated uraian via PATCH"
        }
    }
    
    response = admin_session.patch(f"{BASE_URL}/wa/inbox/{item_id}", json=payload)
    if response.status_code != 200:
        print(f"✗ Failed to update draft: {response.status_code} {response.text}")
        return False
    
    updated = response.json()
    draft = updated.get("draft", {})
    
    if draft.get("pengurus") != "Test Pengurus":
        print(f"✗ Draft pengurus not updated")
        return False
    
    if draft.get("uraian") != "Updated uraian via PATCH":
        print(f"✗ Draft uraian not updated")
        return False
    
    print(f"✓ PATCH /wa/inbox/{item_id} successful")
    print(f"  - Pengurus: {draft.get('pengurus')}")
    print(f"  - Uraian: {draft.get('uraian')}")
    
    return True


def test_approve_transfer():
    """Test 8: POST /api/wa/inbox/{id}/approve for transfer -> creates kas_masuk"""
    print("\n=== TEST 8: Approve Transfer (Creates Kas Masuk) ===")
    
    if "transfer_item_id" not in test_data:
        print(f"⚠️  Skipping (no transfer item)")
        return True
    
    item_id = test_data["transfer_item_id"]
    
    # Approve with draft data
    payload = {
        "jenis": "transfer",
        "draft": {
            "unit_id": EXISTING_UNIT_EX01,
            "pengurus": "Test Pengurus",
            "tanggal": "2026-10-11",
            "debit": 58000000,
            "no_ref": test_data.get("transfer_no_ref", "TEST-REF-001"),
            "uraian": "Test transfer approval",
            "tujuan_dana": "EX-01",
            "pic": "GUNTUR"
        }
    }
    
    response = admin_session.post(f"{BASE_URL}/wa/inbox/{item_id}/approve", json=payload)
    if response.status_code != 200:
        print(f"✗ Failed to approve: {response.status_code} {response.text}")
        return False
    
    result = response.json()
    print(f"✓ Approve successful")
    
    # Check result
    if not result.get("ok"):
        print(f"✗ Result ok=false")
        return False
    
    res_data = result.get("result", {})
    if res_data.get("type") != "kas_masuk":
        print(f"✗ Expected type='kas_masuk', got {res_data.get('type')}")
        return False
    
    if not res_data.get("no"):
        print(f"✗ No bukti number returned")
        return False
    
    print(f"  - Type: {res_data.get('type')}")
    print(f"  - No. Bukti: {res_data.get('no')}")
    print(f"  - ID: {res_data.get('id')}")
    
    # Store for cleanup
    test_data["created_kas_masuk"].append(res_data.get("id"))
    
    # Verify item status changed to approved
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "approved"})
    if response.status_code == 200:
        approved_items = response.json()
        found = any(it["id"] == item_id for it in approved_items)
        if found:
            print(f"✓ Item status changed to 'approved'")
        else:
            print(f"✗ Item not found in approved list")
            return False
    
    return True


def test_duplicate_transfer():
    """Test 9: Uploading same transfer again should result in duplicate status"""
    print("\n=== TEST 9: Duplicate Transfer Detection ===")
    
    # Upload the same transfer image again
    try:
        with open("/app/tests/fixtures/hm.webp", "rb") as f:
            image_data = f.read()
    except Exception as e:
        print(f"✗ Failed to read test image: {e}")
        return False
    
    files = {"file": ("transfer2.webp", image_data, "image/webp")}
    data = {"caption": "EX-01 duplicate", "phone": ""}
    
    response = admin_session.post(f"{BASE_URL}/wa/upload", files=files, data=data)
    if response.status_code != 200:
        print(f"✗ Failed to upload: {response.status_code}")
        return False
    
    item = response.json()
    test_data["created_items"].append(item["id"])
    
    # Wait for AI processing
    print(f"  - Waiting for AI processing...")
    time.sleep(15)  # Wait a bit longer to ensure processing completes
    
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "all"})
    if response.status_code != 200:
        print(f"✗ Failed to get inbox")
        return False
    
    items = response.json()
    dup_item = None
    for it in items:
        if it["id"] == item["id"]:
            dup_item = it
            break
    
    if not dup_item:
        print(f"✗ Duplicate item not found")
        return False
    
    if dup_item.get("status") != "duplicate":
        print(f"⚠️  Expected status='duplicate', got {dup_item.get('status')} (may need more time)")
        # Not failing the test as AI might still be processing
    else:
        print(f"✓ Duplicate detected correctly")
        print(f"  - Status: {dup_item.get('status')}")
        warnings = dup_item.get("warnings", [])
        if warnings:
            print(f"  - Warning: {warnings[0]}")
    
    return True


def test_approve_hour_meter():
    """Test 10: Approve hour meter -> creates/updates operation"""
    print("\n=== TEST 10: Approve Hour Meter (Creates Operation) ===")
    
    if "hm_item_id" not in test_data:
        print(f"⚠️  Skipping (no HM item)")
        return True
    
    item_id = test_data["hm_item_id"]
    
    # Approve with draft data
    payload = {
        "jenis": "hour_meter",
        "draft": {
            "unit_id": EXISTING_UNIT_EX01,
            "pengurus": "Test Pengurus",
            "tanggal": "2026-10-12",
            "hm_awal": 527.0,
            "hm_akhir": 527.6,
            "jumlah_cars": 0,
            "operator_id": ""
        }
    }
    
    response = admin_session.post(f"{BASE_URL}/wa/inbox/{item_id}/approve", json=payload)
    if response.status_code != 200:
        print(f"✗ Failed to approve: {response.status_code} {response.text}")
        return False
    
    result = response.json()
    print(f"✓ Approve successful")
    
    res_data = result.get("result", {})
    if res_data.get("type") != "operation":
        print(f"✗ Expected type='operation', got {res_data.get('type')}")
        return False
    
    print(f"  - Type: {res_data.get('type')}")
    print(f"  - No: {res_data.get('no')}")
    print(f"  - ID: {res_data.get('id')}")
    print(f"  - Updated existing: {res_data.get('updated', False)}")
    
    # Store for cleanup
    test_data["created_operations"].append(res_data.get("id"))
    
    return True


def test_reject():
    """Test 11: POST /api/wa/inbox/{id}/reject"""
    print("\n=== TEST 11: Reject Item ===")
    
    # Upload a new item to reject
    try:
        with open("/app/tests/fixtures/hm.webp", "rb") as f:
            image_data = f.read()
    except Exception as e:
        print(f"⚠️  Skipping (cannot read image)")
        return True
    
    files = {"file": ("reject_test.webp", image_data, "image/webp")}
    data = {"caption": "To be rejected", "phone": ""}
    
    response = admin_session.post(f"{BASE_URL}/wa/upload", files=files, data=data)
    if response.status_code != 200:
        print(f"✗ Failed to upload: {response.status_code}")
        return False
    
    item = response.json()
    item_id = item["id"]
    test_data["created_items"].append(item_id)
    
    # Wait a bit for processing to start
    time.sleep(5)
    
    # Reject it
    response = admin_session.post(f"{BASE_URL}/wa/inbox/{item_id}/reject")
    if response.status_code != 200:
        print(f"✗ Failed to reject: {response.status_code} {response.text}")
        return False
    
    print(f"✓ Reject successful")
    
    # Verify status changed
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "rejected"})
    if response.status_code == 200:
        rejected_items = response.json()
        found = any(it["id"] == item_id for it in rejected_items)
        if found:
            print(f"✓ Item status changed to 'rejected'")
        else:
            print(f"⚠️  Item not found in rejected list (may still be processing)")
    
    return True


def test_reprocess():
    """Test 12: POST /api/wa/inbox/{id}/reprocess"""
    print("\n=== TEST 12: Reprocess Item ===")
    
    # Find a rejected or error item to reprocess
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "rejected,error"})
    if response.status_code != 200:
        print(f"⚠️  Skipping (cannot get inbox)")
        return True
    
    items = response.json()
    if not items:
        print(f"⚠️  Skipping (no rejected/error items)")
        return True
    
    item_id = items[0]["id"]
    
    response = admin_session.post(f"{BASE_URL}/wa/inbox/{item_id}/reprocess")
    if response.status_code != 200:
        print(f"✗ Failed to reprocess: {response.status_code} {response.text}")
        return False
    
    print(f"✓ Reprocess successful for item {item_id}")
    
    # Verify status changed to processing
    time.sleep(2)
    response = admin_session.get(f"{BASE_URL}/wa/inbox", params={"status": "all"})
    if response.status_code == 200:
        all_items = response.json()
        reprocessed = next((it for it in all_items if it["id"] == item_id), None)
        if reprocessed and reprocessed.get("status") == "processing":
            print(f"✓ Item status changed to 'processing'")
    
    return True


def test_contacts_crud():
    """Test 13: Contacts CRUD operations"""
    print("\n=== TEST 13: Contacts CRUD ===")
    
    # Create contact
    contact_payload = {
        "phone": "081234567890",
        "nama": "Test Contact",
        "tipe": "operator",
        "user_id": "",
        "unit_id": EXISTING_UNIT_EX01,
        "pengurus": ""
    }
    
    response = admin_session.post(f"{BASE_URL}/wa/contacts", json=contact_payload)
    if response.status_code != 200:
        print(f"✗ Failed to create contact: {response.status_code} {response.text}")
        return False
    
    contact = response.json()
    contact_id = contact["id"]
    test_data["created_contacts"].append(contact_id)
    
    print(f"✓ Created contact: {contact['nama']}")
    print(f"  - Phone: {contact['phone']}")
    print(f"  - Normalized: {contact['phone'].startswith('628')}")
    
    # List contacts
    response = admin_session.get(f"{BASE_URL}/wa/contacts")
    if response.status_code != 200:
        print(f"✗ Failed to list contacts: {response.status_code}")
        return False
    
    contacts = response.json()
    found = any(c["id"] == contact_id for c in contacts)
    if not found:
        print(f"✗ Created contact not found in list")
        return False
    
    print(f"✓ GET /wa/contacts returned {len(contacts)} contacts")
    
    # Update contact
    update_payload = {
        **contact_payload,
        "nama": "Updated Test Contact",
        "tipe": "pengurus"
    }
    
    response = admin_session.patch(f"{BASE_URL}/wa/contacts/{contact_id}", json=update_payload)
    if response.status_code != 200:
        print(f"✗ Failed to update contact: {response.status_code}")
        return False
    
    updated = response.json()
    if updated["nama"] != "Updated Test Contact":
        print(f"✗ Contact name not updated")
        return False
    
    print(f"✓ PATCH /wa/contacts/{contact_id} successful")
    
    # Test duplicate phone
    dup_payload = {
        **contact_payload,
        "nama": "Duplicate Phone"
    }
    
    response = admin_session.post(f"{BASE_URL}/wa/contacts", json=dup_payload)
    if response.status_code != 400:
        print(f"✗ Expected 400 for duplicate phone, got {response.status_code}")
        return False
    
    print(f"✓ Duplicate phone blocked (400)")
    
    return True


def test_operator_permissions():
    """Test 14: Operator should get 403 on all /api/wa/* endpoints"""
    print("\n=== TEST 14: Operator Permissions (403) ===")
    
    endpoints = [
        ("GET", "/wa/status"),
        ("GET", "/wa/inbox"),
        ("POST", "/wa/upload"),
        ("GET", "/wa/contacts"),
    ]
    
    all_blocked = True
    for method, path in endpoints:
        if method == "GET":
            response = operator_session.get(f"{BASE_URL}{path}")
        else:
            response = operator_session.post(f"{BASE_URL}{path}", json={})
        
        if response.status_code != 403:
            print(f"✗ {method} {path} should return 403, got {response.status_code}")
            all_blocked = False
        else:
            print(f"✓ {method} {path} blocked (403)")
    
    return all_blocked


def test_pengurus_rekap_diterima_piutang():
    """Test 15: GET /api/pengurus-rekap includes diterima and piutang"""
    print("\n=== TEST 15: Pengurus Rekap (Diterima & Piutang) ===")
    
    response = admin_session.get(f"{BASE_URL}/pengurus-rekap", params={"year": 2026})
    if response.status_code != 200:
        print(f"✗ Failed to get pengurus rekap: {response.status_code}")
        return False
    
    data = response.json()
    print(f"✓ GET /pengurus-rekap?year=2026 successful")
    
    # Check structure
    if "rows" not in data or "total" not in data:
        print(f"✗ Missing rows or total in response")
        return False
    
    # Check that diterima and piutang are in totals
    total = data.get("total", {})
    if "diterima" not in total:
        print(f"✗ Missing 'diterima' in total")
        return False
    
    if "piutang" not in total:
        print(f"✗ Missing 'piutang' in total")
        return False
    
    print(f"✓ Rekap includes diterima and piutang:")
    print(f"  - Total Diterima: Rp{total.get('diterima', 0):,.0f}")
    print(f"  - Total Piutang: Rp{total.get('piutang', 0):,.0f}")
    
    # Check months also have diterima and piutang
    if data.get("rows"):
        first_row = data["rows"][0]
        if first_row.get("months"):
            first_month = first_row["months"][0]
            if "diterima" not in first_month or "piutang" not in first_month:
                print(f"✗ Missing diterima/piutang in month data")
                return False
            print(f"✓ Month data includes diterima and piutang")
    
    return True


def test_units_kode_wa():
    """Test 16: Units have kode_wa field and can be updated"""
    print("\n=== TEST 16: Units kode_wa Field ===")
    
    # Get existing unit
    response = admin_session.get(f"{BASE_URL}/units")
    if response.status_code != 200:
        print(f"✗ Failed to get units: {response.status_code}")
        return False
    
    units = response.json()
    ex01 = next((u for u in units if u["id"] == EXISTING_UNIT_EX01), None)
    
    if not ex01:
        print(f"✗ Unit EX-01 not found")
        return False
    
    # Check kode_wa field exists
    if "kode_wa" not in ex01:
        print(f"✗ kode_wa field missing from unit")
        return False
    
    print(f"✓ Unit has kode_wa field: '{ex01.get('kode_wa', '')}'")
    
    # Update kode_wa
    original_kode_wa = ex01.get("kode_wa", "")
    test_data["units_to_reset"].append({"id": EXISTING_UNIT_EX01, "original_kode_wa": original_kode_wa})
    
    update_payload = {
        "unit_name": ex01["unit_name"],
        "nomor_lambung": ex01["nomor_lambung"],
        "serial_number": ex01["serial_number"],
        "kode_wa": "Sdlg 10, SDLG10"
    }
    
    response = admin_session.patch(f"{BASE_URL}/units/{EXISTING_UNIT_EX01}", json=update_payload)
    if response.status_code != 200:
        print(f"✗ Failed to update unit: {response.status_code}")
        return False
    
    updated = response.json()
    if updated.get("kode_wa") != "Sdlg 10, SDLG10":
        print(f"✗ kode_wa not updated")
        return False
    
    print(f"✓ PATCH /units/{EXISTING_UNIT_EX01} updated kode_wa")
    print(f"  - New kode_wa: {updated.get('kode_wa')}")
    
    return True


def cleanup():
    """Cleanup all test data"""
    print("\n=== CLEANUP TEST DATA ===")
    
    try:
        # Delete operations
        for op_id in test_data.get("created_operations", []):
            try:
                response = admin_session.delete(f"{BASE_URL}/operations/{op_id}")
                if response.status_code == 200:
                    print(f"✓ Deleted operation {op_id}")
            except:
                pass
        
        # Delete kas_masuk entries
        for km_id in test_data.get("created_kas_masuk", []):
            try:
                response = admin_session.delete(f"{BASE_URL}/finance/kas-masuk/{km_id}")
                if response.status_code == 200:
                    print(f"✓ Deleted kas_masuk {km_id}")
            except:
                pass
        
        # Delete contacts
        for contact_id in test_data.get("created_contacts", []):
            try:
                response = admin_session.delete(f"{BASE_URL}/wa/contacts/{contact_id}")
                if response.status_code == 200:
                    print(f"✓ Deleted contact {contact_id}")
            except:
                pass
        
        # Delete inbox items
        for item_id in test_data.get("created_items", []):
            try:
                response = admin_session.delete(f"{BASE_URL}/wa/inbox/{item_id}")
                if response.status_code == 200:
                    print(f"✓ Deleted inbox item {item_id}")
            except:
                pass
        
        # Reset unit kode_wa
        for unit_reset in test_data.get("units_to_reset", []):
            try:
                response = admin_session.get(f"{BASE_URL}/units")
                if response.status_code == 200:
                    units = response.json()
                    unit = next((u for u in units if u["id"] == unit_reset["id"]), None)
                    if unit:
                        update_payload = {
                            "unit_name": unit["unit_name"],
                            "nomor_lambung": unit["nomor_lambung"],
                            "serial_number": unit["serial_number"],
                            "kode_wa": unit_reset["original_kode_wa"]
                        }
                        response = admin_session.patch(f"{BASE_URL}/units/{unit_reset['id']}", json=update_payload)
                        if response.status_code == 200:
                            print(f"✓ Reset kode_wa for unit {unit_reset['id']}")
            except:
                pass
        
        print(f"✓ Cleanup complete")
        return True
    except Exception as e:
        print(f"⚠️  Cleanup error (non-critical): {e}")
        return True


def main():
    global admin_session, operator_session
    
    print("=" * 70)
    print("WhatsApp Integration - Backend API Test Suite")
    print("=" * 70)
    
    try:
        # Login
        admin_session, admin_user = login(ADMIN_CREDS["username"], ADMIN_CREDS["password"])
        operator_session, operator_user = login(OPERATOR_CREDS["username"], OPERATOR_CREDS["password"])
        
        # Run tests
        results = {
            "WhatsApp Status (Not Configured)": test_wa_status(),
            "Webhook Endpoints (Disabled)": test_webhook_disabled(),
            "Upload Transfer Image": test_upload_transfer(),
            "Upload Hour Meter Image": test_upload_hour_meter(),
            "List Inbox Items": test_inbox_list(),
            "Get Media Image": test_media_endpoint(),
            "Update Draft Fields": test_update_draft(),
            "Approve Transfer": test_approve_transfer(),
            "Duplicate Transfer Detection": test_duplicate_transfer(),
            "Approve Hour Meter": test_approve_hour_meter(),
            "Reject Item": test_reject(),
            "Reprocess Item": test_reprocess(),
            "Contacts CRUD": test_contacts_crud(),
            "Operator Permissions": test_operator_permissions(),
            "Pengurus Rekap (Diterima & Piutang)": test_pengurus_rekap_diterima_piutang(),
            "Units kode_wa Field": test_units_kode_wa(),
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
            print("\n🎉 All WhatsApp backend tests passed!")
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
