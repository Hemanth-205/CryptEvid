from bson import ObjectId
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.models.risk import RiskLevel, RiskSignal, RiskScoreResponse, GlobalRiskStats

class RiskScoringService:
    """
    Deterministic, Explainable Forensic Risk Scoring Engine.
    Evaluates real forensic evidence, custody audits, and timeline events
    to calculate a mathematical risk score between 0 and 100 with distinct risk signals.
    """

    @classmethod
    async def calculate_case_risk(cls, db, case_id: str) -> RiskScoreResponse:
        case_id_str = str(case_id)
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None

        # Fetch Case
        case = await db["cases"].find_one({"_id": case_oid if case_oid else case_id_str})
        if not case:
            return RiskScoreResponse(
                case_id=case_id_str,
                score=0,
                risk_level=RiskLevel.LOW,
                signals=[],
                explanation="Case record not found.",
                calculated_at=datetime.now(timezone.utc)
            )

        signals: List[RiskSignal] = []
        raw_score = 0

        # 0. Evaluate Backup-Confirmed Evidence Integrity Failures (highest priority)
        # This fires when a tamper was confirmed against the preserved original
        tampered_backups = await db["evidence_backups"].find(
            {"case_id": case_id_str, "status": {"$in": ["TAMPERED", "CORRUPT", "MISSING"]}}
        ).to_list(length=500)

        if tampered_backups:
            tb_count = len(tampered_backups)
            tb_impact = min(75, 45 + (tb_count - 1) * 15)  # 45 base, +15 per additional
            raw_score += tb_impact
            signals.append(RiskSignal(
                signal_type="EVIDENCE_INTEGRITY_FAILURE",
                count=tb_count,
                impact_score=tb_impact,
                reason=(
                    f"{tb_count} preserved original backup(s) confirmed evidence tampering or "
                    f"backup corruption. Working copy SHA-256 diverged from sealed original."
                ),
                associated_ids=[str(b.get("evidence_id")) for b in tampered_backups]
            ))

        # 1. Evaluate Tampered Evidence
        ev_cursor = db["evidence"].find({"case_id": case_id_str})
        evidence_list = await ev_cursor.to_list(length=500)
        tampered_ev = [e for e in evidence_list if e.get("integrity_status") == "TAMPERED"]

        if tampered_ev:
            tamper_count = len(tampered_ev)
            # 40 pts for first, 20 for second (cap 60)
            tamper_impact = min(60, 40 + (tamper_count - 1) * 20)
            raw_score += tamper_impact
            signals.append(RiskSignal(
                signal_type="EVIDENCE_TAMPERED",
                count=tamper_count,
                impact_score=tamper_impact,
                reason=f"{tamper_count} evidence exhibit(s) failed cryptographic SHA-256 integrity verification.",
                associated_ids=[str(e["_id"]) for e in tampered_ev]
            ))

        # 2. Evaluate Forensic Events Severity
        evt_cursor = db["forensic_events"].find({"case_id": case_id_str})
        events = await evt_cursor.to_list(length=1000)

        critical_events = [e for e in events if e.get("severity") == "CRITICAL"]
        if critical_events:
            crit_count = len(critical_events)
            crit_impact = min(50, crit_count * 25)
            raw_score += crit_impact
            signals.append(RiskSignal(
                signal_type="CRITICAL_EVENTS",
                count=crit_count,
                impact_score=crit_impact,
                reason=f"{crit_count} critical severity forensic event(s) recorded on case timeline.",
                associated_ids=[str(e["_id"]) for e in critical_events]
            ))

        high_events = [e for e in events if e.get("severity") == "HIGH"]
        if high_events:
            high_count = len(high_events)
            high_impact = min(30, high_count * 10)
            raw_score += high_impact
            signals.append(RiskSignal(
                signal_type="HIGH_SEVERITY_EVENTS",
                count=high_count,
                impact_score=high_impact,
                reason=f"{high_count} high-severity forensic event(s) recorded.",
                associated_ids=[str(e["_id"]) for e in high_events]
            ))

        # 3. Evaluate Suspicious Attack Event Types
        suspicious_types = {"MALWARE_DETECTED", "EVIDENCE_TAMPERED", "PROCESS_EXECUTED", "FILE_DELETED"}
        suspicious_events = [e for e in events if e.get("event_type") in suspicious_types]
        if suspicious_events:
            susp_impact = 15
            raw_score += susp_impact
            signals.append(RiskSignal(
                signal_type="SUSPICIOUS_ATTACK_PATTERNS",
                count=len(suspicious_events),
                impact_score=susp_impact,
                reason="Timeline exhibits known adversary execution or tampering patterns.",
                associated_ids=[str(e["_id"]) for e in suspicious_events[:5]]
            ))

        # 4. Evaluate Chain of Custody Failures
        ev_ids = [str(e["_id"]) for e in evidence_list]
        if ev_ids:
            cust_failures = await db["chain_of_custody"].count_documents({
                "evidence_id": {"$in": ev_ids},
                "action": "EVIDENCE_INTEGRITY_FAILURE"
            })
            if cust_failures > 0:
                cust_impact = 20
                raw_score += cust_impact
                signals.append(RiskSignal(
                    signal_type="CUSTODY_INTEGRITY_FAILURE",
                    count=cust_failures,
                    impact_score=cust_impact,
                    reason=f"{cust_failures} cryptographic chain of custody tampering breach event(s) logged.",
                    associated_ids=[]
                ))

        # 5. Evaluate Evidence Concentration Hotspots
        ev_event_counts: Dict[str, int] = {}
        for e in events:
            ev_ref = e.get("evidence_id")
            if ev_ref:
                ev_event_counts[ev_ref] = ev_event_counts.get(ev_ref, 0) + 1

        hotspots = [ev_ref for ev_ref, cnt in ev_event_counts.items() if cnt >= 3]
        if hotspots:
            hotspot_impact = 10
            raw_score += hotspot_impact
            signals.append(RiskSignal(
                signal_type="EVIDENCE_CONCENTRATION_HOTSPOT",
                count=len(hotspots),
                impact_score=hotspot_impact,
                reason=f"{len(hotspots)} exhibit(s) have a high concentration (>=3) of forensic incident events.",
                associated_ids=hotspots
            ))

        # 6. Evaluate Unauthorized Access and Modification Attempts
        sec_query = {"$or": [{"case_id": case_id_str}]}
        if ev_ids:
            sec_query["$or"].append({"evidence_id": {"$in": ev_ids}})

        sec_events = await db["security_events"].find(sec_query).to_list(length=500)
        if sec_events:
            access_attempts = [s for s in sec_events if s.get("target_resource", {}).get("action") not in ("MODIFY", "DELETE", "UPDATE", "TAMPER")]
            mod_attempts = [s for s in sec_events if s.get("target_resource", {}).get("action") in ("MODIFY", "DELETE", "UPDATE", "TAMPER")]

            if access_attempts:
                acc_count = len(access_attempts)
                acc_impact = min(15, acc_count * 5)
                raw_score += acc_impact
                signals.append(RiskSignal(
                    signal_type="UNAUTHORIZED_ACCESS_ATTEMPTS",
                    count=acc_count,
                    impact_score=acc_impact,
                    reason=f"{acc_count} unauthorized access attempt(s) intercepted and blocked on case resources.",
                    associated_ids=[s.get("event_id") for s in access_attempts[:5]]
                ))

            if mod_attempts:
                mod_count = len(mod_attempts)
                mod_impact = min(25, mod_count * 15)
                raw_score += mod_impact
                signals.append(RiskSignal(
                    signal_type="UNAUTHORIZED_MODIFICATION_ATTEMPTS",
                    count=mod_count,
                    impact_score=mod_impact,
                    reason=f"{mod_count} unauthorized modification/tampering attempt(s) blocked on protected case data.",
                    associated_ids=[s.get("event_id") for s in mod_attempts[:5]]
                ))

        # Clamp Score between 0 and 100
        final_score = max(0, min(100, raw_score))

        # Determine Risk Level
        if final_score >= 75:
            level = RiskLevel.CRITICAL
        elif final_score >= 50:
            level = RiskLevel.HIGH
        elif final_score >= 25:
            level = RiskLevel.MODERATE
        else:
            level = RiskLevel.LOW

        # Generate Explainable Summary
        if not signals:
            explanation = "Normal baseline risk. No evidence tampering or critical timeline threats detected."
        else:
            top_reasons = [s.reason for s in signals[:2]]
            explanation = f"Case exhibits {level} risk profile ({final_score}/100). " + " ".join(top_reasons)

        return RiskScoreResponse(
            case_id=case_id_str,
            score=final_score,
            risk_level=level,
            signals=signals,
            explanation=explanation,
            calculated_at=datetime.now(timezone.utc)
        )

    @classmethod
    async def get_global_risk_stats(cls, db, allowed_case_ids: Optional[List[str]] = None) -> GlobalRiskStats:
        """Calculate global risk aggregates across all registered cases (optionally filtered by allowed_case_ids)."""
        query: Dict[str, Any] = {}
        if allowed_case_ids is not None:
            from bson import ObjectId
            oids = [ObjectId(cid) for cid in allowed_case_ids if ObjectId.is_valid(cid)]
            query = {"$or": [{"_id": {"$in": oids}}, {"_id": {"$in": allowed_case_ids}}]}

        cases_cursor = db["cases"].find(query)
        cases = await cases_cursor.to_list(length=500)

        total_cases = len(cases)
        if total_cases == 0:
            return GlobalRiskStats(
                average_risk_score=0.0,
                critical_risk_cases=0,
                high_risk_cases=0,
                moderate_risk_cases=0,
                low_risk_cases=0,
                total_assessed_cases=0
            )

        total_score = 0
        crit_count = 0
        high_count = 0
        mod_count = 0
        low_count = 0

        for c in cases:
            risk = await cls.calculate_case_risk(db, str(c["_id"]))
            total_score += risk.score
            if risk.risk_level == RiskLevel.CRITICAL:
                crit_count += 1
            elif risk.risk_level == RiskLevel.HIGH:
                high_count += 1
            elif risk.risk_level == RiskLevel.MODERATE:
                mod_count += 1
            else:
                low_count += 1

        avg = round(total_score / total_cases, 1)

        return GlobalRiskStats(
            average_risk_score=avg,
            critical_risk_cases=crit_count,
            high_risk_cases=high_count,
            moderate_risk_cases=mod_count,
            low_risk_cases=low_count,
            total_assessed_cases=total_cases
        )
