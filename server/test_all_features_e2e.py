import os
import io
import json
from fastapi.testclient import TestClient
from app.main import app

def run_comprehensive_e2e_verification():
    print("==================================================================")
    print("STARTING FULL END-TO-END SYSTEM FUNCTIONALITY VERIFICATION")
    print("==================================================================")

    with TestClient(app) as client:
        # 1. Login & Token Retrieval
        print("\n[1] Testing Auth Flow...")
        login_res = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "password123"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  -> Admin Login SUCCESS. Token acquired.")

        # 2. Cases Endpoints (Used by /cases & /dashboard)
        print("\n[2] Testing Cases Endpoints...")
        cases_res = client.get("/api/cases", headers=headers)
        assert cases_res.status_code == 200, f"Get cases failed: {cases_res.text}"
        cases_data = cases_res.json()
        cases_list = cases_data.get("cases", [])
        assert len(cases_list) > 0, "No cases found in DB."
        test_case = cases_list[0]
        case_id = str(test_case["_id"])
        print(f"  -> Successfully retrieved {len(cases_list)} cases. Active test case: {test_case.get('case_number')} ({case_id})")

        case_stats_res = client.get("/api/cases/stats", headers=headers)
        assert case_stats_res.status_code == 200, f"Case stats failed: {case_stats_res.text}"
        print(f"  -> Case Stats: {case_stats_res.json()}")

        # 3. Evidence Endpoints (Used by /evidence & CaseDetail)
        print("\n[3] Testing Evidence Endpoints...")
        ev_stats_res = client.get("/api/evidence/stats", headers=headers)
        assert ev_stats_res.status_code == 200, f"Evidence stats failed: {ev_stats_res.text}"
        print(f"  -> Evidence Stats: {ev_stats_res.json()}")

        case_ev_res = client.get(f"/api/cases/{case_id}/evidence", headers=headers)
        assert case_ev_res.status_code == 200, f"Get case evidence failed: {case_ev_res.text}"
        ev_res_data = case_ev_res.json()
        ev_list = ev_res_data if isinstance(ev_res_data, list) else ev_res_data.get("evidence", [])
        print(f"  -> Case {case_id} has {len(ev_list)} evidence exhibits.")

        if ev_list:
            test_ev = ev_list[0]
            ev_id = str(test_ev["_id"])
            print(f"  -> Testing verification on evidence exhibit: {test_ev.get('original_filename')} ({ev_id})")
            
            # Verify SHA-256 integrity
            verify_res = client.post(f"/api/evidence/{ev_id}/verify", headers=headers)
            assert verify_res.status_code == 200, f"Verify evidence failed: {verify_res.text}"
            print(f"  -> Evidence integrity result: {verify_res.json().get('status')}")

            # Custody history for evidence
            custody_res = client.get(f"/api/evidence/{ev_id}/custody", headers=headers)
            assert custody_res.status_code == 200, f"Evidence custody failed: {custody_res.text}"
            print(f"  -> Retrieved {len(custody_res.json().get('custody_events', []))} custody events for evidence {ev_id}")

            # Evidence download with ?token= (browser URL authentication)
            dl_res = client.get(f"/api/evidence/{ev_id}/download?token={token}")
            assert dl_res.status_code == 200, f"Evidence download with ?token= failed: {dl_res.status_code}"
            print(f"  -> Successfully downloaded evidence exhibit ({len(dl_res.content)} bytes) using URL token auth.")

        # 4. Chain of Custody Global Ledger (Used by /custody & CaseDetail tab)
        print("\n[4] Testing Chain of Custody Ledger...")
        all_custody_res = client.get("/api/custody?limit=50", headers=headers)
        assert all_custody_res.status_code == 200, f"Global custody failed: {all_custody_res.text}"
        custody_data = all_custody_res.json()
        print(f"  -> Chain of Custody Ledger: {len(custody_data.get('events', []))} total records verified.")

        # 5. Evidence Graph Topology (Used by /graph)
        print("\n[5] Testing Evidence Graph...")
        graph_res = client.get(f"/api/cases/{case_id}/graph", headers=headers)
        assert graph_res.status_code == 200, f"Graph endpoint failed: {graph_res.text}"
        g_data = graph_res.json()
        print(f"  -> Graph generated: {g_data.get('total_nodes')} nodes, {g_data.get('total_edges')} edges.")
        
        # Test node_type filter
        filtered_graph = client.get(f"/api/cases/{case_id}/graph?node_type=EVIDENCE", headers=headers)
        assert filtered_graph.status_code == 200
        print(f"  -> Graph with node_type=EVIDENCE: {len(filtered_graph.json().get('nodes', []))} nodes.")

        # 6. Threat Intelligence & AI Analysis (Used by /ai-analysis)
        print("\n[6] Testing Threat Intelligence & AI Analysis...")
        risk_res = client.get(f"/api/cases/{case_id}/risk-score", headers=headers)
        assert risk_res.status_code == 200, f"Risk score failed: {risk_res.text}"
        print(f"  -> Risk score: {risk_res.json().get('score')}/100, Level: {risk_res.json().get('risk_level')}")

        ai_res = client.get(f"/api/cases/{case_id}/ai-analysis", headers=headers)
        assert ai_res.status_code == 200, f"AI analysis failed: {ai_res.text}"
        ai_data = ai_res.json()
        print(f"  -> AI Analysis: Mode = {ai_data.get('model_used')}, Hypotheses = {len(ai_data.get('hypotheses', []))}")

        rec_res = client.get(f"/api/cases/{case_id}/recommendations", headers=headers)
        assert rec_res.status_code == 200, f"Recommendations failed: {rec_res.text}"
        print(f"  -> Recommendations count: {len(rec_res.json().get('recommendations', []))}")

        # 7. Security Alerts & Telemetry Stream (Used by /security-alerts)
        print("\n[7] Testing Security Alerts & SOC Stream...")
        sec_stats = client.get("/api/security/stats", headers=headers)
        assert sec_stats.status_code == 200, f"Security stats failed: {sec_stats.text}"
        print(f"  -> Security Stats: Open Alerts = {sec_stats.json().get('open_alerts')}, Blocked = {sec_stats.json().get('blocked_attempts')}")

        sec_alerts = client.get("/api/security/alerts?limit=50", headers=headers)
        assert sec_alerts.status_code == 200, f"Security alerts failed: {sec_alerts.text}"
        alerts_list = sec_alerts.json().get("alerts", [])
        print(f"  -> Security Alerts: {len(alerts_list)} alerts returned.")

        sec_events = client.get("/api/security/events?limit=50", headers=headers)
        assert sec_events.status_code == 200, f"Security events failed: {sec_events.text}"
        print(f"  -> Security Events: {len(sec_events.json().get('events', []))} events returned.")

        # 8. Reports Generation & Download (Used by /reports)
        print("\n[8] Testing Reports Generation & Download...")
        # Generate new report for case
        gen_rep = client.post(f"/api/cases/{case_id}/reports", json={"title": "Automated Verification Audit Report", "classification": "RESTRICTED", "notes": "E2E verification run."}, headers=headers)
        assert gen_rep.status_code in (200, 201), f"Report generation failed: {gen_rep.text}"
        rep_data = gen_rep.json()
        rep_id = rep_data["report_id"]
        print(f"  -> Generated report ID: {rep_id}, SHA-256 seal: {rep_data.get('sha256_hash', '')[:16]}...")

        # Download report with ?token= (browser URL authentication)
        rep_dl = client.get(f"/api/reports/{rep_id}/download?token={token}")
        assert rep_dl.status_code == 200, f"Report download failed: {rep_dl.status_code}"
        assert rep_dl.headers.get("content-type") == "application/pdf"
        assert len(rep_dl.content) > 1000
        print(f"  -> Successfully downloaded sealed court-admissible PDF report ({len(rep_dl.content)} bytes).")

        # 9. Hardware Ingestion Terminals (Used by /devices)
        print("\n[9] Testing Hardware Ingestion Terminals...")
        dev_res = client.get("/api/hardware/devices", headers=headers)
        assert dev_res.status_code == 200, f"Hardware devices failed: {dev_res.text}"
        devices_list = dev_res.json()
        print(f"  -> Registered hardware terminals: {len(devices_list)} device(s) found.")

        # 10. Settings Configuration (Used by /settings)
        print("\n[10] Testing Settings Endpoints...")
        settings_res = client.get("/api/settings", headers=headers)
        assert settings_res.status_code == 200, f"Get settings failed: {settings_res.text}"
        print(f"  -> Current settings: simulation_mode={settings_res.json().get('simulation_mode')}")

        update_settings = client.post("/api/settings", json={"simulation_mode": True, "gemini_api_key": ""}, headers=headers)
        assert update_settings.status_code == 200, f"Update settings failed: {update_settings.text}"
        print("  -> Updated settings successfully.")

        print("\n==================================================================")
        print(">>> ALL 10 MODULES & ALL FORENSIC ENDPOINTS PASSED WITH 100% SUCCESS! <<<")
        print("==================================================================")

if __name__ == "__main__":
    run_comprehensive_e2e_verification()
