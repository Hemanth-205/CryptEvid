import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.repositories.diary import DiaryRepository
from app.models.diary import DiaryEntryCreate, DiaryEntryAmend
from app.services.report_service import ForensicReportService

async def main():
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    db = get_database()
    diary_repo = DiaryRepository(db)

    test_case_id = f"test_pdf_case_{int(datetime.now().timestamp())}"
    case_oid = ObjectId()
    print(f"Creating test case: {test_case_id} (OID: {case_oid})")
    
    case_doc = {
        "_id": case_oid,
        "case_number": "CASE-REPORT-BNSS-01",
        "title": "Corporate Intranet Exfiltration & Tampering Investigation",
        "case_type": "DATA_BREACH",
        "priority": "CRITICAL",
        "status": "IN_PROGRESS",
        "created_by": "inv_007",
        "created_by_name": "Senior Investigator Rajesh Nair",
        "assigned_investigator": "inv_007",
        "assigned_investigator_name": "Senior Investigator Rajesh Nair",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "notes": []
    }
    await db["cases"].insert_one(case_doc)

    investigator_user = {
        "_id": "inv_007",
        "name": "Senior Investigator Rajesh Nair",
        "email": "nair@cryptevid.internal",
        "role": "investigator"
    }

    try:
        # Create 2 diary entries
        p1 = DiaryEntryCreate(
            investigation_date="2026-10-18",
            time_info_received="08:45",
            start_time="09:00",
            closing_time="18:30",
            places_visited=["Regional Cyber Forensic Center", "Server Hosting Facility A-1"],
            activities_performed="Collected initial bit-stream image of SQL database mirror and analyzed web server access logs for anomalous POST requests.",
            findings="Discovered automated script injecting payload via authenticated session token. Isolated impacted subnet.",
            related_evidence_ids=["ev_mirror_01", "ev_traffic_02"],
            witness_references="Network Operations Lead confirmed anomalous egress flow starting 02:15 UTC.",
            next_steps="Perform deep packet inspection on pcap artifact and reverse engineer payload."
        )
        e1 = await diary_repo.create_entry(str(case_oid), investigator_user, p1)
        print(f"Created Diary Entry 1: Code={e1['entry_code']}")

        # Amend entry 1 to test amendment display in PDF
        amend_p = DiaryEntryAmend(
            reason="Corrected exact IP subnet notation and appended secondary network switch serial.",
            findings="Discovered automated script injecting payload via authenticated session token on subnet 10.14.0.0/16. Isolated impacted switch SW-CORE-02.",
            next_steps="Coordinate with digital evidence vault for cold storage archival."
        )
        await diary_repo.amend_entry(e1["_id"], str(case_oid), investigator_user, amend_p)
        print(f"Amended Diary Entry 1 with amendment record.")

        p2 = DiaryEntryCreate(
            investigation_date="2026-10-19",
            time_info_received="09:00",
            start_time="09:15",
            closing_time="17:00",
            places_visited=["Forensic Lab 3", "Branch Banking Hub"],
            activities_performed="Extracted firmware dumps from suspected gateway routers and completed volatility memory image analysis.",
            findings="Verified that baseline cryptographic hashes on gateway firmware remain intact; attack vector confirmed as application-layer token hijack.",
            related_evidence_ids=["ev_fw_03"],
            witness_references="Security architect testimony recorded regarding API key rotation schedule.",
            next_steps="Draft final forensic conclusion and recommendations."
        )
        e2 = await diary_repo.create_entry(str(case_oid), investigator_user, p2)
        print(f"Created Diary Entry 2: Code={e2['entry_code']}")

        # Now generate report PDF
        print("\n--- Generating Forensic PDF Report with Section 15 Diary ---")
        report_res = await ForensicReportService.generate_case_report(
            db=db,
            case_id=str(case_oid),
            user=investigator_user,
            title="Official Forensic Examination Report with BNSS Section 192 Investigation Diary"
        )
        print(f"Report Generated Successfully!")
        print(f"Report ID: {report_res.report_id}")
        print(f"Version: {report_res.version}")
        print(f"File Size: {report_res.file_size} bytes")
        print(f"SHA-256: {report_res.sha256_hash}")

        # Check generated PDF file on disk
        doc = await db["forensic_reports"].find_one({"_id": ObjectId(report_res.report_id)})
        assert doc is not None, "Report record must exist in DB"
        assert os.path.exists(doc["file_path"]), f"PDF file must exist at {doc['file_path']}"
        file_size = os.path.getsize(doc["file_path"])
        assert file_size > 10000, f"PDF file size ({file_size}) must be substantial"

        print(f"\n[SUCCESS] PDF generated and verified successfully at {doc['file_path']}!")

    finally:
        print("\nCleaning up test artifacts...")
        await db["cases"].delete_many({"_id": case_oid})
        await db["investigation_diary"].delete_many({"case_id": str(case_oid)})
        await db["forensic_reports"].delete_many({"case_id": str(case_oid)})
        await db["audit_logs"].delete_many({"case_id": str(case_oid)})
        await close_mongo_connection()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
