import urllib.request
import json
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def request_json(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def main():
    print("1. Authenticating as admin@forensics.gov...")
    status, auth_data = request_json(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"email": "admin@forensics.gov", "password": "password123"}
    )
    assert status == 200, f"Login failed: {auth_data}"
    token = auth_data["access_token"]
    print("Login successful. Token obtained.")

    print("\n2. Getting active cases...")
    status, cases_data = request_json(f"{BASE_URL}/api/cases", token=token)
    assert status == 200, f"Cases failed: {cases_data}"
    cases = cases_data["cases"] if isinstance(cases_data, dict) and "cases" in cases_data else cases_data
    assert len(cases) > 0, "At least one case should exist"
    case = cases[0]
    case_id = case["_id"]
    print(f"Target Case: {case['case_number']} (ID: {case_id})")

    print("\n3. Creating Digital Investigation Diary entry (BNSS Section 192)...")
    diary_payload = {
        "investigation_date": "2026-10-19",
        "time_info_received": "09:30",
        "start_time": "10:00",
        "closing_time": "18:00",
        "places_visited": ["State Cyber Cell", "Main Server Facility"],
        "activities_performed": "Conducted live forensic triaging and memory extraction on database node. Preserved bit-stream snapshot.",
        "findings": "Identified anomalous cron execution triggering outbound connection to external IP. Cryptographic exhibit baselines registered.",
        "related_evidence_ids": [],
        "witness_references": "Witness statement of system administrator recorded under official protocol.",
        "next_steps": "Subject disk image to timeline analysis and correlation with gateway packet capture."
    }
    status, entry_res = request_json(f"{BASE_URL}/api/cases/{case_id}/diary", method="POST", data=diary_payload, token=token)
    assert status == 201, f"Create diary entry failed: {entry_res}"
    entry_id = entry_res["_id"]
    entry_code = entry_res["entry_code"]
    entry_hash = entry_res["entry_hash"]
    print(f"Created Diary Entry: {entry_code} (ID: {entry_id})")
    print(f"SHA-256 Hash Seal: {entry_hash}")
    assert len(entry_hash) == 64, "SHA-256 digest must be 64 hex characters"

    print("\n4. Verifying cryptographic integrity of diary entry...")
    status, verify_res = request_json(f"{BASE_URL}/api/cases/{case_id}/diary/{entry_id}/verify", token=token)
    assert status == 200, f"Verify failed: {verify_res}"
    print(f"Verification Result: status={verify_res['status']}, is_valid={verify_res['is_valid']}, chain_matches={verify_res['previous_hash_matches']}")
    assert verify_res["is_valid"] is True

    print("\n5. Testing amendment protocol with mandatory reason...")
    amend_payload = {
        "reason": "Corrected primary server room location designation and supplemented follow-up steps.",
        "places_visited": ["State Cyber Cell", "Main Server Facility (Vault Rack 04)"],
        "next_steps": "Subject disk image to timeline analysis and correlate with pcap exhibit."
    }
    status, amend_res = request_json(f"{BASE_URL}/api/cases/{case_id}/diary/{entry_id}/amend", method="POST", data=amend_payload, token=token)
    assert status == 200, f"Amend failed: {amend_res}"
    print(f"Amendment Applied: is_amended={amend_res['is_amended']}, amendment_count={len(amend_res['amendments'])}")
    assert amend_res["is_amended"] is True
    assert len(amend_res["amendments"]) == 1
    assert amend_res["entry_hash"] == entry_hash, "Original baseline hash must remain permanent"

    print("\n6. Testing immutability constraint: DELETE must return 405...")
    status, del_res = request_json(f"{BASE_URL}/api/cases/{case_id}/diary/{entry_id}", method="DELETE", token=token)
    print(f"Delete Response Code: {status}")
    print(f"Delete Detail: {del_res.get('detail')}")
    assert status == 405, f"Expected 405 Method Not Allowed, got {status}"

    print("\n7. Listing diary entries for case with date filters...")
    status, list_res = request_json(f"{BASE_URL}/api/cases/{case_id}/diary?start_date=2026-10-19&end_date=2026-10-19", token=token)
    assert status == 200, f"List failed: {list_res}"
    print(f"List Result: total={list_res['total']}, entries_returned={len(list_res['entries'])}")
    assert list_res["total"] >= 1
    assert "BNSS SECTION 192 STATUTORY NOTICE" in list_res["legal_disclaimer"]

    print("\n[ALL LIVE E2E API TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    main()
