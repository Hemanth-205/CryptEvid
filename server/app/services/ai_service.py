import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from bson import ObjectId
from app.core.config import settings
from app.models.risk import (
    RiskScoreResponse,
    AIAnalysisResponse,
    ForensicRecommendation,
    RecommendationsResponse
)

logger = logging.getLogger(__name__)

class ForensicAIService:
    """
    Forensic AI Intelligence Service.
    Generates structured threat narrative, pattern detection, and investigative hypotheses.
    Strictly separates cryptographically verified FACTS from AI INTERPRETATIONS.
    Gemini never modifies forensic data or overrides deterministic risk scores.
    Gracefully falls back to rule-based correlation when offline or unconfigured.
    """

    @classmethod
    async def generate_case_analysis(
        cls,
        db,
        case_id: str,
        risk_data: RiskScoreResponse
    ) -> AIAnalysisResponse:
        case_id_str = str(case_id)
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None

        # Fetch Case & Exhibits for structured context
        case = await db["cases"].find_one({"_id": case_oid if case_oid else case_id_str})
        case_num = case.get("case_number", "CASE") if case else "CASE"
        case_title = case.get("title", "Forensic Incident") if case else "Forensic Incident"

        ev_cursor = db["evidence"].find({"case_id": case_id_str})
        evidence_list = await ev_cursor.to_list(length=100)

        evt_cursor = db["forensic_events"].find({"case_id": case_id_str})
        events = await evt_cursor.to_list(length=100)

        # 1. Compile Verified Objective Forensic Facts
        facts: List[str] = [
            f"FACT: Case {case_num} contains {len(evidence_list)} registered digital forensic exhibit(s).",
            f"FACT: Total of {len(events)} timeline forensic event(s) recorded across the incident stream."
        ]

        tampered = [e for e in evidence_list if e.get("integrity_status") == "TAMPERED"]
        if tampered:
            facts.append(f"FACT: {len(tampered)} evidence exhibit(s) failed physical SHA-256 integrity verification.")
        else:
            facts.append(f"FACT: All {len(evidence_list)} evidence exhibit(s) currently match baseline SHA-256 digests.")

        critical_evts = [e for e in events if e.get("severity") == "CRITICAL"]
        if critical_evts:
            facts.append(f"FACT: {len(critical_evts)} critical severity event(s) recorded on case timeline.")

        attack_types = list({e.get("event_type") for e in events if e.get("event_type") in {"MALWARE_DETECTED", "PROCESS_EXECUTED", "USB_CONNECTED", "EVIDENCE_TAMPERED"}})
        if attack_types:
            facts.append(f"FACT: Identified attack-related technique indicators: {', '.join(attack_types)}.")

        # Backup integrity facts
        backup_records = await db["evidence_backups"].find({"case_id": case_id_str}).to_list(length=100)
        total_backups = len(backup_records)
        tampered_backups = [b for b in backup_records if b.get("status") in ("TAMPERED", "CORRUPT", "MISSING")]
        protected_backups = [b for b in backup_records if b.get("status") == "PROTECTED"]

        if total_backups > 0:
            facts.append(
                f"FACT: {total_backups} preserved original backup(s) registered. "
                f"{len(protected_backups)} PROTECTED, {len(tampered_backups)} with integrity issues."
            )
        if tampered_backups:
            facts.append(
                f"FACT: {len(tampered_backups)} backup(s) flagged TAMPERED/CORRUPT — working copy "
                f"SHA-256 diverged from sealed preserved original SHA-256."
            )

        # 2. Compile Interpretations and Hypotheses
        interpretations: List[str] = []
        patterns: List[str] = []
        considerations: List[str] = []

        if tampered:
            interpretations.append("AI INTERPRETATION: Physical evidence alteration detected. Storage media may have been compromised post-seizure or suffered silent hardware corruption.")
            patterns.append("Post-Collection Exhibit Tampering or Disk Modification")
            considerations.append("Immediate physical quarantine of affected forensic storage block is recommended.")

        # Backup-specific interpretations (AI must NOT modify backup records or hashes)
        if tampered_backups:
            interpretations.append(
                f"AI INTERPRETATION: {len(tampered_backups)} preserved original backup(s) confirm post-collection "
                f"evidence modification. The original sealed SHA-256 and backup copy remain available for "
                f"forensic comparison. Investigators should immediately compare the working copy against "
                f"the preserved original to determine the scope of modification."
            )
            patterns.append("Confirmed Post-Collection Evidence Tampering (Backup-Verified)")
            considerations.append(
                "Cross-reference the tampered evidence working copy against the preserved original backup. "
                "Determine if the modification was intentional, hardware failure, or malicious alteration."
            )

        if any(e.get("event_type") == "PROCESS_EXECUTED" for e in events):
            interpretations.append("AI INTERPRETATION: Unauthorized code execution detected on endpoint. High likelihood of adversary persistence or credential access.")
            patterns.append("Host-Based Memory Injection / Living-off-the-Land Attack")
            considerations.append("Correlate process command-line arguments against parent process IDs and Windows Event Log 4688.")

        if any(e.get("event_type") == "USB_CONNECTED" for e in events):
            interpretations.append("AI INTERPRETATION: Removable storage peripheral attached. Possible data exfiltration vector or external staging mechanism.")
            patterns.append("Removable Storage Insertion / Exfiltration")
            considerations.append("Query USBSTOR registry keys and volume serial numbers across the timeline window.")

        if not interpretations:
            interpretations.append("AI INTERPRETATION: Current findings are consistent with routine administrative or low-risk operational activities.")
            patterns.append("Standard Endpoint Activity")
            considerations.append("Maintain routine monitoring and ensure custody verification is scheduled periodically.")

        summary = f"Forensic analysis for {case_num} indicates a {risk_data.risk_level} risk posture ({risk_data.score}/100). " + (
            "Evidence tampering and threat activities require containment." if risk_data.score >= 50 else
            "Artifacts currently maintain cryptographic integrity without active high-severity breaches."
        )

        risk_explanation = risk_data.explanation

        # Check if Gemini API is configured
        gemini_key = settings.GEMINI_API_KEY
        if gemini_key and gemini_key.strip():
            try:
                prompt = (
                    f"You are a Senior Digital Forensics & Threat Intelligence Expert analyzing Case {case_num}: {case_title}.\n\n"
                    f"Verified Forensic Facts:\n" + "\n".join(f"- {f}" for f in facts) + "\n\n"
                    f"Deterministic Risk Posture: {risk_data.score}/100 ({risk_data.risk_level})\n"
                    f"Risk Analysis: {risk_explanation}\n\n"
                    f"Perform a comprehensive threat intelligence analysis. Return ONLY valid JSON matching this schema:\n"
                    f"{{\n"
                    f'  "summary": "concise, authoritative judicial forensic summary (2-3 sentences)",\n'
                    f'  "interpretations": ["expert hypothesis 1", "expert hypothesis 2"],\n'
                    f'  "attack_patterns": ["MITRE or threat tactic 1", "MITRE or threat tactic 2"],\n'
                    f'  "considerations": ["prioritized investigative consideration 1", "prioritized investigative consideration 2"]\n'
                    f"}}"
                )

                async with httpx.AsyncClient(timeout=25.0) as client:
                    for model_name in ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
                        try:
                            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                            resp = await client.post(
                                gemini_url,
                                json={
                                    "contents": [{"parts": [{"text": prompt}]}],
                                    "generationConfig": {"responseMimeType": "application/json"}
                                }
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                if text_output:
                                    parsed = json.loads(text_output)
                                    if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                                        parsed = parsed[0]
                                    if isinstance(parsed, dict):
                                        ai_sum = parsed.get("summary") or summary
                                        ai_interp = parsed.get("interpretations") or interpretations
                                        ai_pat = parsed.get("attack_patterns") or patterns
                                        ai_cons = parsed.get("considerations") or considerations

                                        clean_interps = [
                                            f"AI INTERPRETATION: {item}" if not str(item).startswith("AI INTERPRETATION:") else str(item)
                                            for item in (ai_interp if isinstance(ai_interp, list) else [str(ai_interp)])
                                        ]

                                        return AIAnalysisResponse(
                                            case_id=case_id_str,
                                            summary=ai_sum,
                                            risk_explanation=risk_explanation,
                                            facts=facts,
                                            ai_interpretations=clean_interps,
                                            detected_attack_patterns=ai_pat if isinstance(ai_pat, list) else [str(ai_pat)],
                                            investigation_considerations=ai_cons if isinstance(ai_cons, list) else [str(ai_cons)],
                                            ai_provider=f"Google Gemini Threat Intel ({model_name})",
                                            is_fallback=False,
                                            generated_at=datetime.now(timezone.utc)
                                        )
                        except Exception as model_err:
                            logger.warning(f"Error querying Gemini model {model_name}: {model_err}")
                            continue
            except Exception as e:
                logger.error(f"Gemini Threat Intelligence generation failed: {e}")

        # Offline / Rule-Based Intelligence
        return AIAnalysisResponse(
            case_id=case_id_str,
            summary=summary,
            risk_explanation=risk_explanation,
            facts=facts,
            ai_interpretations=interpretations,
            detected_attack_patterns=patterns,
            investigation_considerations=considerations,
            ai_provider="CRYPTEVID Forensic Rule-Based Engine (Offline Fallback)",
            is_fallback=True,
            generated_at=datetime.now(timezone.utc)
        )

class RecommendationService:
    """
    Forensic Recommendation Engine.
    Generates actionable, signal-derived investigative recommendations.
    Never modifies forensic data.
    """

    @classmethod
    async def generate_recommendations(
        cls,
        db,
        case_id: str,
        risk_data: RiskScoreResponse
    ) -> RecommendationsResponse:
        case_id_str = str(case_id)
        now = datetime.now(timezone.utc)
        recs: List[ForensicRecommendation] = []

        signal_types = {s.signal_type for s in risk_data.signals}

        # 1. Tampered Evidence Recommendation
        if "EVIDENCE_TAMPERED" in signal_types or "CUSTODY_INTEGRITY_FAILURE" in signal_types:
            recs.append(ForensicRecommendation(
                recommendation_id=str(uuid.uuid4())[:8],
                title="Quarantine Storage Volume & Secure Primary Image",
                description="Immediately lock physical write access to storage volumes hosting compromised evidence exhibits. Re-verify source disks using a certified hardware write-blocker.",
                reason="One or more evidence exhibits failed cryptographic SHA-256 verification against baseline.",
                severity="CRITICAL",
                source_signals=["EVIDENCE_TAMPERED", "CUSTODY_INTEGRITY_FAILURE"],
                action_category="EVIDENCE_PRESERVATION",
                created_at=now
            ))

        # 2. Critical Events / Attack Patterns
        if "CRITICAL_EVENTS" in signal_types or "SUSPICIOUS_ATTACK_PATTERNS" in signal_types:
            recs.append(ForensicRecommendation(
                recommendation_id=str(uuid.uuid4())[:8],
                title="Isolate Suspect Workstations & Extract Volatile Memory",
                description="Sever network connectivity to originating endpoints identified in critical timeline events. Acquire uncompressed RAM dumps prior to system reboot.",
                reason="Critical forensic timeline events indicate active adversary execution on endpoints.",
                severity="HIGH",
                source_signals=["CRITICAL_EVENTS", "SUSPICIOUS_ATTACK_PATTERNS"],
                action_category="INCIDENT_CONTAINMENT",
                created_at=now
            ))

        # 3. Evidence Concentration Hotspot
        if "EVIDENCE_CONCENTRATION_HOTSPOT" in signal_types:
            recs.append(ForensicRecommendation(
                recommendation_id=str(uuid.uuid4())[:8],
                title="Perform In-Depth Artifact Carving on Hotspot Exhibits",
                description="Execute deep file carving, string indexing, and metadata correlation on evidence exhibits linked to 3+ suspicious timeline events.",
                reason="High correlation of disparate forensic events centered on a single evidence artifact.",
                severity="MEDIUM",
                source_signals=["EVIDENCE_CONCENTRATION_HOTSPOT"],
                action_category="FORENSIC_ANALYSIS",
                created_at=now
            ))

        # 4. Standard Chain of Custody Baseline Recommendation
        recs.append(ForensicRecommendation(
            recommendation_id=str(uuid.uuid4())[:8],
            title="Maintain Continuous Cryptographic Chain of Custody Audits",
            description="Schedule recurring SHA-256 recalculations and ensure all evidence transfers and examinations are signed by authorized investigators.",
            reason="Ensures evidentiary integrity remains legally admissible in court proceedings.",
            severity="INFO",
            source_signals=["ROUTINE_GOVERNANCE"],
            action_category="AUDIT_COMPLIANCE",
            created_at=now
        ))

        return RecommendationsResponse(
            case_id=case_id_str,
            total_recommendations=len(recs),
            recommendations=recs
        )
