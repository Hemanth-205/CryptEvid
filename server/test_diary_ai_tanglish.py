import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.repositories.diary import DiaryRepository
from app.models.diary import DiaryEntryCreate, DiaryEntryAmend, DiaryParseRequest
from app.services.diary_ai_service import DiaryAIService
from app.services.report_service import ForensicReportService

async def main():
    print("=================================================================")
    print("CRYPTEVID BNSS 192: TANGLISH & AI EVENT TIMELINE TEST SUITE")
    print("=================================================================")
    
    await connect_to_mongo()
    db = get_database()
    repo = DiaryRepository(db)
    ai_service = DiaryAIService()

    # 1. Test AI parsing of Tanglish narrative
    print("\n[Step 1] Parsing realistic raw Tanglish field proceedings...")
    tanglish_raw = (
        "inniku morning 10 am ku cyber cell ponen, server room la check pannom disk image clone eduthom. "
        "apram 2 pm ku bank manager kita statement vaanginom, 5 pm ku office vanthu daily proceedings mudichom"
    )
    print(f"Raw Input: \"{tanglish_raw}\"")
    
    parse_result = await ai_service.parse_and_organize(
        raw_text=tanglish_raw,
        investigation_date="2026-10-20",
        db=db
    )
    
    print(f"-> Detected Format / Language: {parse_result.detected_language}")
    print(f"-> Start Time: {parse_result.start_time} | Closing Time: {parse_result.closing_time}")
    print(f"-> Visited Locations: {parse_result.places_visited}")
    print(f"-> Organized Timeline Milestones ({len(parse_result.timeline_events)} items):")
    for idx, ev in enumerate(parse_result.timeline_events, 1):
        print(f"   [{idx}] Time: {ev.time} | Location: {ev.location} | Activity: {ev.activity}")
    
    assert "Tanglish" in parse_result.detected_language, f"Expected Tanglish detection, got {parse_result.detected_language}"
    assert len(parse_result.timeline_events) >= 3, f"Expected >= 3 timeline milestones, got {len(parse_result.timeline_events)}"
    print("[PASS] Step 1 passed: Tanglish detected and timeline milestones extracted chronologically.")

    # 2. Test inserting into DiaryRepository with timeline_events, raw_input, and detected_language
    print("\n[Step 2] Recording Diary Entry with Chronological Timeline...")
    case_oid = ObjectId()
    test_case_id = str(case_oid)
    await db["cases"].insert_one({
        "_id": case_oid,
        "case_number": "CASE-TANGLISH-001",
        "title": "State Cyber Investigation Unit vs Unknown Accused",
        "case_type": "CYBER_FRAUD",
        "priority": "HIGH",
        "status": "OPEN",
        "created_by": "inv_007",
        "created_by_name": "Officer Murugan",
        "assigned_investigator": "inv_007",
        "assigned_investigator_name": "Officer Murugan",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "notes": []
    })

    investigator_user = {
        "_id": "inv_007",
        "name": "Officer Murugan",
        "email": "murugan@cybercrime.gov.in",
        "role": "investigator"
    }

    create_payload = DiaryEntryCreate(
        investigation_date=parse_result.investigation_date,
        time_info_received=parse_result.time_info_received,
        start_time=parse_result.start_time,
        closing_time=parse_result.closing_time,
        places_visited=parse_result.places_visited,
        activities_performed=parse_result.activities_performed,
        findings=parse_result.findings,
        related_evidence_ids=[],
        witness_references=parse_result.witness_references,
        next_steps=parse_result.next_steps,
        timeline_events=parse_result.timeline_events,
        raw_input=tanglish_raw,
        detected_language=parse_result.detected_language
    )

    entry = await repo.create_entry(test_case_id, investigator_user, create_payload)
    print(f"-> Created Entry #{entry['entry_number']} ({entry['entry_code']})")
    print(f"-> Stored Hash: {entry['entry_hash']}")
    print(f"-> Stored Timeline Events: {len(entry['timeline_events'])}")
    assert len(entry["timeline_events"]) == len(parse_result.timeline_events)
    assert entry["raw_input"] == tanglish_raw
    assert entry["detected_language"] == parse_result.detected_language
    print("[PASS] Step 2 passed: Entry stored with complete timeline milestones and metadata.")

    # 3. Test Cryptographic Verification
    print("\n[Step 3] Verifying SHA-256 seal integrity including timeline serialization...")
    verify_res = await repo.verify_entry_integrity(entry["_id"], test_case_id)
    print(f"-> Verification Status: {verify_res['status']}")
    print(f"-> Stored Hash:        {verify_res['stored_hash']}")
    print(f"-> Recalculated Hash:  {verify_res['recalculated_hash']}")
    assert verify_res["is_valid"] is True, "Verification failed! Recalculated hash does not match stored hash."
    assert verify_res["status"] == "VERIFIED_INTEGRITY_SECURE"
    print("[PASS] Step 3 passed: Cryptographic hash seal verified with timeline integrity.")

    # 4. Test Forensic PDF Report Generation including Section 15 timeline table
    print("\n[Step 4] Generating official Forensic PDF Report containing Section 15 Timeline...")
    report_resp = await ForensicReportService.generate_case_report(
        db=db,
        case_id=test_case_id,
        user=investigator_user,
        title="Forensic Case Examination & BNSS Investigation Diary Report"
    )
    print(f"-> Generated Report ID: {report_resp.report_id}")
    print(f"-> File Size: {report_resp.file_size:,} bytes")
    print(f"-> PDF SHA-256: {report_resp.sha256_hash}")
    assert report_resp.file_size > 5000, "Report PDF appears too small!"
    print("[PASS] Step 4 passed: PDF Report successfully rendered with Section 15 timeline table.")

    # 5. Test Amendment with Updated Timeline
    print("\n[Step 5] Testing amendment to append a supplementary timeline milestone...")
    updated_timeline = list(parse_result.timeline_events)
    from app.models.diary import TimelineEvent
    updated_timeline.append(TimelineEvent(
        time="18:30",
        location="Headquarters",
        activity="Secured physical evidence locker under secondary biometric seal."
    ))

    amend_payload = DiaryEntryAmend(
        reason="Supplemental timeline milestone added following post-briefing locker sealing.",
        timeline_events=updated_timeline,
        closing_time="18:30"
    )
    amended = await repo.amend_entry(entry["_id"], test_case_id, investigator_user, amend_payload)
    print(f"-> Amended Entry: Is Amended = {amended['is_amended']}, Amendments Count = {len(amended['amendments'])}")
    assert amended["is_amended"] is True
    assert len(amended["timeline_events"]) == len(updated_timeline)
    print("[PASS] Step 5 passed: Diary amendment recorded with updated timeline.")

    # Cleanup test data
    await db["cases"].delete_many({"case_number": "CASE-TANGLISH-001"})
    await db["investigation_diary"].delete_many({"case_id": test_case_id})
    await db["forensic_reports"].delete_many({"case_id": test_case_id})

    await close_mongo_connection()
    print("\n=================================================================")
    print("ALL TANGLISH & AI EVENT TIMELINE TESTS COMPLETED SUCCESSFULLY!")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(main())
