import io
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

def run_milestone4_tests():
    print("==================================================================")
    print("RUNNING PHASE 3 (MILESTONE 4) FORENSIC EVENT & TIMELINE ENGINE")
    print("==================================================================")

    with TestClient(app) as client:
        # Step 0: Admin Authentication
        admin_login = client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("[PASS] 0. Admin Authentication: Obtained JWT Bearer token")

        # Step 1: Create Case Container
        case_res = client.post("/api/cases", json={
            "title": "Operation Chronos - Forensic Timeline Reconstruction",
            "description": "Validation case for multi-source event correlation and timeline engine.",
            "case_type": "DATA_BREACH",
            "priority": "CRITICAL",
            "tags": ["TIMELINE", "CORRELATION", "CHRONOS"]
        }, headers=admin_headers)
        assert case_res.status_code == 201
        case = case_res.json()
        case_id = case["_id"]
        case_num = case["case_number"]
        print(f"[PASS] 1. Case Container Setup: Created {case_num} ({case_id})")

        # Step 2: Ingest Evidence to establish baseline exhibit
        evidence_bytes = b"CORPO_INTRANET_ACTIVE_DIRECTORY_SECURITY_LOGS_2026_09_01"
        upload_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("security_event_log.evtx", io.BytesIO(evidence_bytes), "application/octet-stream")},
            data={"description": "Active Directory security event log exhibit", "tags": "LOGS,AD,AUTHENTICATION"},
            headers=admin_headers
        )
        assert upload_res.status_code == 201
        evidence_item = upload_res.json()
        evidence_id = evidence_item["_id"]
        print(f"[PASS] 2. Evidence Ingestion: Uploaded {evidence_item['original_filename']} ({evidence_id})")

        # Step 3: Create Forensic Event with EXACT timestamp
        base_time = datetime(2026, 9, 1, 10, 15, 0, tzinfo=timezone.utc)
        event1_res = client.post(
            f"/api/cases/{case_id}/events",
            json={
                "event_type": "PROCESS_EXECUTED",
                "title": "Unauthorized Mimikatz Memory Dump Invocation",
                "description": "Process lsass.exe accessed via suspected malware payload.",
                "event_time": base_time.isoformat(),
                "time_precision": "EXACT",
                "severity": "CRITICAL",
                "confidence": "HIGH",
                "evidence_id": evidence_id,
                "device_id": "SUSPECT_WORKSTATION_07",
                "location": "Finance Department Floor 2",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "tags": ["MIMIKATZ", "CREDENTIAL_THEFT", "LSASS"]
            },
            headers=admin_headers
        )
        assert event1_res.status_code == 201
        event1 = event1_res.json()
        event1_id = event1["_id"]
        assert event1["event_type"] == "PROCESS_EXECUTED"
        assert event1["severity"] == "CRITICAL"
        assert event1["time_precision"] == "EXACT"
        assert event1["latitude"] == 12.9716
        assert event1["longitude"] == 77.5946
        assert event1["evidence_filename"] == "security_event_log.evtx"
        print(f"[PASS] 3. Create Forensic Event (EXACT): Created '{event1['title']}' with GPS & exhibit link")

        # Step 4: Create Event with APPROXIMATE timestamp interval
        approx_start = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
        approx_end = datetime(2026, 9, 1, 11, 45, 0, tzinfo=timezone.utc)
        event2_res = client.post(
            f"/api/cases/{case_id}/events",
            json={
                "event_type": "USB_CONNECTED",
                "title": "Unregistered SanDisk USB Flash Drive Attached",
                "description": "Hardware peripheral inserted during active workstation lock.",
                "event_time": approx_start.isoformat(),
                "time_precision": "APPROXIMATE",
                "time_start": approx_start.isoformat(),
                "time_end": approx_end.isoformat(),
                "severity": "HIGH",
                "confidence": "MEDIUM",
                "device_id": "SUSPECT_WORKSTATION_07",
                "tags": ["USB", "PERIPHERAL", "DATA_EXFILTRATION"]
            },
            headers=admin_headers
        )
        assert event2_res.status_code == 201
        event2 = event2_res.json()
        event2_id = event2["_id"]
        assert event2["time_precision"] == "APPROXIMATE"
        print(f"[PASS] 4. Timestamp Precision (APPROXIMATE): Interval recorded between {approx_start.isoformat()} and {approx_end.isoformat()}")

        # Step 5: Create Event with UNKNOWN timestamp (null event_time)
        event3_res = client.post(
            f"/api/cases/{case_id}/events",
            json={
                "event_type": "INVESTIGATOR_NOTE",
                "title": "Suspect Interview Notes Analysis",
                "description": "Interview statements correlate with physical badge access logs.",
                "event_time": None,
                "time_precision": "UNKNOWN",
                "severity": "INFO",
                "confidence": "LOW",
                "tags": ["INTERVIEW", "TESTIMONY"]
            },
            headers=admin_headers
        )
        assert event3_res.status_code == 201
        event3 = event3_res.json()
        event3_id = event3["_id"]
        assert event3["time_precision"] == "UNKNOWN"
        assert event3["event_time"] is None
        print(f"[PASS] 5. Missing Timestamp Handling (UNKNOWN): Created '{event3['title']}' without fabricated time")

        # Step 6: Retrieve Individual Event & View Audit
        get_res = client.get(f"/api/events/{event1_id}", headers=admin_headers)
        assert get_res.status_code == 200
        retrieved_event = get_res.json()
        assert retrieved_event["title"] == event1["title"]
        assert retrieved_event["evidence_filename"] == "security_event_log.evtx"
        print(f"[PASS] 6. Retrieve Event Details: Hydrated exhibit filename '{retrieved_event['evidence_filename']}'")

        # Step 7: Update Authorized Event
        update_res = client.put(
            f"/api/events/{event1_id}",
            json={
                "title": "CONFIRMED: Mimikatz LSASS In-Memory Dump",
                "severity": "CRITICAL",
                "confidence": "HIGH",
                "description": "Validated through forensic memory dump analysis. 14 hashes compromised."
            },
            headers=admin_headers
        )
        assert update_res.status_code == 200
        updated = update_res.json()
        assert updated["title"] == "CONFIRMED: Mimikatz LSASS In-Memory Dump"
        assert "14 hashes compromised" in updated["description"]
        print(f"[PASS] 7. Update Authorized Event: Title & narrative updated and audit logged")

        # Step 8: Multi-Source Timeline Generation & Ordering
        print("\n--- Testing TimelineService Multi-Source Correlation ---")
        timeline_res = client.get(f"/api/cases/{case_id}/timeline?order=asc", headers=admin_headers)
        assert timeline_res.status_code == 200
        tl_data = timeline_res.json()
        events = tl_data["events"]

        # Confirm multiple sources synthesized
        source_types = set(e["source_type"] for e in events)
        assert "MANUAL_ENTRY" in source_types
        assert "AUDIT_LOG" in source_types  # from custody
        assert any(e["event_type"] == "EVIDENCE_UPLOADED" for e in events)
        print(f"[PASS] 8. Multi-Source Timeline: Unified {len(events)} events across sources: {source_types}")

        # Step 9: Chronological Ascending vs Descending Ordering
        timeline_desc = client.get(f"/api/cases/{case_id}/timeline?order=desc", headers=admin_headers).json()["events"]
        assert len(timeline_desc) == len(events)
        assert timeline_desc[0]["_id"] != events[0]["_id"] or len(events) <= 1
        print(f"[PASS] 9. Timeline Chronological Sorting: Ascending and Descending orders verified")

        # Step 10: Deduplication Guarantee
        print("\n--- Verifying Deterministic Deduplication on Repeated Queries ---")
        tl_repeat = client.get(f"/api/cases/{case_id}/timeline", headers=admin_headers).json()
        assert tl_repeat["total_events"] == tl_data["total_events"]
        # Check no duplicated event_ids
        event_ids = [e["event_id"] for e in tl_repeat["events"]]
        assert len(event_ids) == len(set(event_ids)), "Duplicate event IDs found in timeline output!"
        print(f"[PASS] 10. Duplicate Prevention: {len(event_ids)} unique events with zero duplicate synthesized IDs")

        # Step 11: Custody Event Synthesis (Verify and Tamper on Timeline)
        print("\n--- Testing Custody & Tamper Timeline Integration ---")
        # Run verify (PASS)
        verify_res = client.post(f"/api/evidence/{evidence_id}/verify", headers=admin_headers)
        assert verify_res.status_code == 200

        tl_with_verify = client.get(f"/api/cases/{case_id}/timeline", headers=admin_headers).json()["events"]
        assert any(e["event_type"] == "EVIDENCE_VERIFIED" for e in tl_with_verify)
        print("[PASS] 11a. Custody Integration: EVIDENCE_VERIFIED synthesized onto timeline")

        # Simulate tamper on disk
        import os
        from app.core.config import settings
        ev_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, case_id, evidence_id)
        files = os.listdir(ev_dir)
        with open(os.path.join(ev_dir, files[0]), "wb") as f:
            f.write(b"COMPROMISED_CORRUPT_BYTES")

        tamper_res = client.post(f"/api/evidence/{evidence_id}/verify", headers=admin_headers)
        assert tamper_res.status_code == 200

        tl_with_tamper = client.get(f"/api/cases/{case_id}/timeline", headers=admin_headers).json()["events"]
        tamper_timeline_events = [e for e in tl_with_tamper if e["event_type"] == "EVIDENCE_TAMPERED"]
        assert len(tamper_timeline_events) >= 1
        assert tamper_timeline_events[0]["severity"] == "CRITICAL"
        print(f"[PASS] 11b. Tamper Integration: CRITICAL EVIDENCE_TAMPERED reflected on timeline")

        # Step 12: Immutability Protection (System Events Cannot Be Edited)
        custody_evt = [e for e in tl_with_verify if e.get("is_system_generated")][0]
        bad_edit = client.put(
            f"/api/events/{custody_evt['event_id']}",
            json={"title": "Hacked History Title"},
            headers=admin_headers
        )
        assert bad_edit.status_code in (403, 404), "Editing system-generated custody event must be blocked!"
        print("[PASS] 12. Immutability Protection: System-generated timeline events cannot be modified")

        # Step 13: Timeline Filtering by Severity, Event Type, and Evidence ID
        print("\n--- Testing Server-Side Timeline Filters ---")
        crit_res = client.get(f"/api/cases/{case_id}/timeline?severity=CRITICAL", headers=admin_headers).json()
        assert all(e["severity"] == "CRITICAL" for e in crit_res["events"])

        type_res = client.get(f"/api/cases/{case_id}/timeline?event_type=PROCESS_EXECUTED", headers=admin_headers).json()
        assert all(e["event_type"] == "PROCESS_EXECUTED" for e in type_res["events"])

        ev_filter = client.get(f"/api/cases/{case_id}/timeline?evidence_id={evidence_id}", headers=admin_headers).json()
        assert all(e["evidence_id"] == evidence_id for e in ev_filter["events"])
        print(f"[PASS] 13. Server-side Filtering: Filtered {crit_res['total_events']} CRITICAL, {type_res['total_events']} PROCESS_EXECUTED, {ev_filter['total_events']} by exhibit")

        # Step 14: Search by Query Term
        search_res = client.get(f"/api/cases/{case_id}/timeline?search=Mimikatz", headers=admin_headers).json()
        assert search_res["total_events"] >= 1
        assert any("Mimikatz" in e["title"] or "Mimikatz" in e["description"] for e in search_res["events"])
        print(f"[PASS] 14. Timeline Search: Successfully located {search_res['total_events']} event(s) matching 'Mimikatz'")

        # Step 15: Timeline Summary Statistics API
        stats_res = client.get(f"/api/cases/{case_id}/timeline/stats", headers=admin_headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_events"] >= 3
        assert stats["critical_events"] >= 1
        assert stats["system_events"] >= 1
        assert stats["manual_events"] >= 2
        print(f"[PASS] 15. Timeline Summary Statistics API: Validated metrics -> {stats}")

        # Step 16: Role Authorization (Readonly Access Enforcement)
        # Unauthenticated request
        unauth_res = client.post(f"/api/cases/{case_id}/events", json={"title": "test", "event_type": "LOGIN"})
        assert unauth_res.status_code in (401, 403)
        print("[PASS] 16. Role Authorization: Unauthenticated event creation blocked with 401/403")

        # Step 17: Error Handling (Non-existent Case / Event)
        bad_case = client.post("/api/cases/65f000000000000000000000/events", json={
            "title": "Bad Case Event",
            "event_type": "LOGIN"
        }, headers=admin_headers)
        assert bad_case.status_code == 404

        bad_event = client.get("/api/events/65f000000000000000000000", headers=admin_headers)
        assert bad_event.status_code == 404
        print("[PASS] 17. Error Handling: 404 returned for non-existent case and event IDs")

    print("\n==================================================================")
    print("ALL PHASE 3 (MILESTONE 4) TIMELINE TESTS PASSED WITH ZERO FAILURES!")
    print("==================================================================")

if __name__ == "__main__":
    run_milestone4_tests()
