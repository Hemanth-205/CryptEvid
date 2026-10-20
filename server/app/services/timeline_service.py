from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any, List, Optional, Tuple
from app.repositories.base import BaseRepository

class TimelineService:
    """
    Forensic Timeline Engine.
    Correlates disparate data sources (Forensic Events, Evidence Chain of Custody,
    System Audit Logs, and File Metadata) into an immutable, unified chronological event stream.
    Applies deterministic deduplication to guarantee zero duplicate synthesized events.
    """

    @classmethod
    async def build_case_timeline(
        cls,
        db,
        case_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        source_type: Optional[str] = None,
        evidence_id: Optional[str] = None,
        search: Optional[str] = None,
        order: str = "asc",
        limit: int = 300,
        skip: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        events: List[Dict[str, Any]] = []
        seen_dedup_keys = set()

        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None
        case_id_str = str(case_id)

        # 1. Fetch Manual & Stored Forensic Events
        stored_cursor = db["forensic_events"].find({"case_id": case_id_str})
        stored_docs = await stored_cursor.to_list(length=1000)
        for doc in stored_docs:
            s = BaseRepository.serialize_doc(doc)
            s["event_id"] = s["_id"]
            dedup_key = f"MANUAL:{s['_id']}"
            if dedup_key not in seen_dedup_keys:
                seen_dedup_keys.add(dedup_key)
                events.append(s)

        # 2. Fetch Evidence Artifacts for this case to hydrate filenames and synthesize custody/metadata events
        ev_cursor = db["evidence"].find({"case_id": case_id_str})
        evidence_items = await ev_cursor.to_list(length=500)
        evidence_map = {str(e["_id"]): e for e in evidence_items}

        # 3. Synthesize Timeline Events from Chain of Custody
        evidence_ids = list(evidence_map.keys())
        if evidence_ids:
            custody_cursor = db["chain_of_custody"].find({"evidence_id": {"$in": evidence_ids}})
            custody_docs = await custody_cursor.to_list(length=1000)

            for c in custody_docs:
                c_id = str(c["_id"])
                dedup_key = f"CUSTODY:{c_id}"
                if dedup_key in seen_dedup_keys:
                    continue
                seen_dedup_keys.add(dedup_key)

                action = c.get("action", "")
                ev_id = c.get("evidence_id")
                ev_meta = evidence_map.get(ev_id, {})
                ev_name = ev_meta.get("original_filename", "Evidence Artifact")

                # Map custody action to timeline attributes
                if action == "EVIDENCE_UPLOADED":
                    t_type = "EVIDENCE_UPLOADED"
                    sev = "INFO"
                    title = f"Evidence Artifact Ingested: {ev_name}"
                elif action == "EVIDENCE_VERIFIED":
                    t_type = "EVIDENCE_VERIFIED"
                    sev = "INFO"
                    title = f"Cryptographic Integrity Verified: {ev_name}"
                elif action == "EVIDENCE_INTEGRITY_FAILURE":
                    t_type = "EVIDENCE_TAMPERED"
                    sev = "CRITICAL"
                    title = f"CRITICAL: Integrity Tamper Detected on {ev_name}"
                elif action == "EVIDENCE_VIEWED":
                    t_type = "FILE_ACCESSED"
                    sev = "INFO"
                    title = f"Evidence Examined: {ev_name}"
                elif action == "EVIDENCE_DOWNLOADED":
                    t_type = "FILE_ACCESSED"
                    sev = "LOW"
                    title = f"Evidence Downloaded for Examination: {ev_name}"
                else:
                    t_type = "CASE_EVENT"
                    sev = "INFO"
                    title = f"Custody Event: {action} ({ev_name})"

                ts = c.get("timestamp")
                events.append({
                    "_id": f"custody_{c_id}",
                    "event_id": f"custody_{c_id}",
                    "case_id": case_id_str,
                    "evidence_id": ev_id,
                    "evidence_filename": ev_name,
                    "event_type": t_type,
                    "event_time": ts,
                    "event_time_end": None,
                    "time_precision": "EXACT",
                    "time_start": ts,
                    "time_end": ts,
                    "title": title,
                    "description": c.get("details", ""),
                    "source": "Digital Chain of Custody Ledger",
                    "source_type": "AUDIT_LOG",
                    "source_reference": c_id,
                    "actor_id": c.get("actor_id"),
                    "actor_name": c.get("actor_name"),
                    "device_id": c.get("device_id", "CRYPTEVID_TERMINAL"),
                    "location": None,
                    "latitude": None,
                    "longitude": None,
                    "confidence": "HIGH",
                    "severity": sev,
                    "tags": ["CUSTODY", action],
                    "metadata": {"event_hash": c.get("event_hash"), "previous_hash": c.get("previous_hash")},
                    "is_system_generated": True,
                    "created_at": ts
                })

        # 4. Synthesize Timeline Events from Case Audit Logs
        audit_query = {"$or": [{"case_id": case_id_str}]}
        if case_oid:
            audit_query["$or"].append({"case_id": case_oid})

        audit_cursor = db["audit_logs"].find(audit_query).limit(500)
        audit_docs = await audit_cursor.to_list(length=500)

        for a in audit_docs:
            a_id = str(a["_id"])
            dedup_key = f"AUDIT:{a_id}"
            if dedup_key in seen_dedup_keys:
                continue
            seen_dedup_keys.add(dedup_key)

            action = a.get("action", "")
            # Skip if already synthesized via custody
            if action.startswith("EVIDENCE_"):
                continue

            ts = a.get("timestamp")
            events.append({
                "_id": f"audit_{a_id}",
                "event_id": f"audit_{a_id}",
                "case_id": case_id_str,
                "evidence_id": str(a.get("evidence_id")) if a.get("evidence_id") else None,
                "evidence_filename": None,
                "event_type": "CASE_EVENT",
                "event_time": ts,
                "event_time_end": None,
                "time_precision": "EXACT",
                "time_start": ts,
                "time_end": ts,
                "title": f"Case Governance Action: {action}",
                "description": a.get("details", ""),
                "source": "Platform Security Audit Trail",
                "source_type": "SYSTEM",
                "source_reference": a_id,
                "actor_id": str(a.get("user_id")) if a.get("user_id") else None,
                "actor_name": "System Audit Engine",
                "device_id": a.get("device_id", "SECURITY_GATEWAY"),
                "location": None,
                "latitude": None,
                "longitude": None,
                "confidence": "HIGH",
                "severity": "INFO",
                "tags": ["AUDIT", action],
                "metadata": {"ip_address": a.get("ip_address")},
                "is_system_generated": True,
                "created_at": ts
            })

        # 5. Synthesize Timeline Events from Extracted Metadata (EXIF GPS & Captured Timestamps)
        meta_cursor = db["evidence_metadata"].find({"case_id": case_id_str})
        meta_docs = await meta_cursor.to_list(length=500)

        for m in meta_docs:
            m_id = str(m["_id"])
            dedup_key = f"METADATA_GPS:{m_id}"
            if dedup_key in seen_dedup_keys:
                continue
            seen_dedup_keys.add(dedup_key)

            lat = m.get("latitude")
            lon = m.get("longitude")
            attrs = m.get("extracted_attributes") or {}
            exif_time_str = attrs.get("datetime_original") or attrs.get("creation_date")

            if lat is not None or exif_time_str:
                ev_id = m.get("evidence_id")
                ev_name = m.get("original_filename", "Evidence File")
                ts = m.get("collection_timestamp")

                # Parse exif timestamp if present
                parsed_time = ts
                precision = "APPROXIMATE"
                if exif_time_str:
                    try:
                        # Common EXIF date formats: 'YYYY:MM:DD HH:MM:SS'
                        clean_time = exif_time_str.replace(":", "-", 2)
                        parsed_time = datetime.fromisoformat(clean_time)
                        precision = "EXACT"
                    except Exception:
                        pass

                events.append({
                    "_id": f"meta_{m_id}",
                    "event_id": f"meta_{m_id}",
                    "case_id": case_id_str,
                    "evidence_id": ev_id,
                    "evidence_filename": ev_name,
                    "event_type": "FILE_CREATED" if exif_time_str else "EVIDENCE_COLLECTED",
                    "event_time": parsed_time,
                    "event_time_end": None,
                    "time_precision": precision,
                    "time_start": parsed_time,
                    "time_end": parsed_time,
                    "title": f"Metadata Timestamp Capture: {ev_name}",
                    "description": f"Extracted camera/file header temporal capture for {ev_name}." + (f" GPS: {lat}, {lon}" if lat else ""),
                    "source": "Forensic Metadata Parsing Engine",
                    "source_type": "EVIDENCE_METADATA",
                    "source_reference": m_id,
                    "actor_id": None,
                    "actor_name": m.get("collector", "Forensic Collector"),
                    "device_id": m.get("source_device", "EXIF_CAMERA"),
                    "location": f"Coordinates: {lat}, {lon}" if lat else None,
                    "latitude": lat,
                    "longitude": lon,
                    "confidence": "HIGH" if lat else "MEDIUM",
                    "severity": "INFO",
                    "tags": ["METADATA", "EXIF", "TEMPORAL"],
                    "metadata": attrs,
                    "is_system_generated": True,
                    "created_at": ts or datetime.now(timezone.utc)
                })

        # 6. Synthesize Timeline Events from Unauthorized Security Events
        sec_query = {"$or": [{"case_id": case_id_str}]}
        if evidence_ids:
            sec_query["$or"].append({"evidence_id": {"$in": evidence_ids}})

        sec_cursor = db["security_events"].find(sec_query).limit(500)
        sec_docs = await sec_cursor.to_list(length=500)
        for s in sec_docs:
            s_id = str(s["_id"])
            dedup_key = f"SEC_EVENT:{s_id}"
            if dedup_key in seen_dedup_keys:
                continue
            seen_dedup_keys.add(dedup_key)

            ts = s.get("timestamp")
            target = s.get("target_resource", {})
            auth_ctx = s.get("auth_context", {})
            actor_name = auth_ctx.get("email") or "Unauthenticated Actor"
            action = target.get("action", "UNAUTHORIZED_ACCESS")
            ev_id = s.get("evidence_id")
            ev_meta = evidence_map.get(ev_id, {}) if ev_id else {}
            ev_name = ev_meta.get("original_filename")

            events.append({
                "_id": f"sec_{s_id}",
                "event_id": f"sec_{s_id}",
                "case_id": case_id_str,
                "evidence_id": ev_id,
                "evidence_filename": ev_name,
                "event_type": "SECURITY_ALERT",
                "event_time": ts,
                "event_time_end": None,
                "time_precision": "EXACT",
                "time_start": ts,
                "time_end": ts,
                "title": f"Security Violation: {s.get('event_type')} ({action})",
                "description": f"{s.get('failure_reason', 'Access blocked')}. Source IP: {s.get('ip_address')} ({s.get('ip_source')}). Target: {target.get('path')}",
                "source": "Forensic Security Tracking Engine",
                "source_type": "SECURITY_EVENT",
                "source_reference": s_id,
                "actor_id": auth_ctx.get("user_id"),
                "actor_name": actor_name,
                "device_id": s.get("device_info", {}).get("client_type", "UNKNOWN_CLIENT"),
                "location": None,
                "latitude": None,
                "longitude": None,
                "confidence": "HIGH",
                "severity": s.get("severity", "HIGH"),
                "tags": ["SECURITY", s.get("event_type", "UNAUTHORIZED"), s.get("result", "BLOCKED")],
                "metadata": {
                    "ip_address": s.get("ip_address"),
                    "ip_source": s.get("ip_source"),
                    "result": s.get("result", "BLOCKED"),
                    "security_event_id": s.get("event_id")
                },
                "is_system_generated": True,
                "created_at": ts
            })

        # 7. Apply Server-Side Filters
        filtered: List[Dict[str, Any]] = []
        for e in events:
            # Date Range Filter (checks event_time or created_at)
            t = e.get("event_time") or e.get("created_at")
            if start_time and t and t < start_time:
                continue
            if end_time and t and t > end_time:
                continue

            # Event Type Filter
            if event_type and event_type.strip():
                if e.get("event_type", "").upper() != event_type.strip().upper():
                    continue

            # Severity Filter
            if severity and severity.strip():
                if e.get("severity", "").upper() != severity.strip().upper():
                    continue

            # Source Type Filter
            if source_type and source_type.strip():
                if e.get("source_type", "").upper() != source_type.strip().upper():
                    continue

            # Evidence Filter
            if evidence_id and evidence_id.strip():
                if str(e.get("evidence_id")) != evidence_id.strip():
                    continue

            # Search Query (Title, Description, Tags)
            if search and search.strip():
                term = search.strip().lower()
                title_match = term in (e.get("title") or "").lower()
                desc_match = term in (e.get("description") or "").lower()
                tags_match = any(term in str(tag).lower() for tag in e.get("tags", []))
                if not (title_match or desc_match or tags_match):
                    continue

            filtered.append(e)

        # 7. Chronological Sorting
        def get_sort_key(item):
            val = item.get("event_time") or item.get("created_at")
            if val is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except Exception:
                    return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            return datetime.min.replace(tzinfo=timezone.utc)

        reverse = (order.lower() == "desc")
        filtered.sort(key=get_sort_key, reverse=reverse)

        total_count = len(filtered)
        paginated = filtered[skip : skip + limit]

        # Hydrate evidence filenames if missing
        for item in paginated:
            if item.get("evidence_id") and not item.get("evidence_filename"):
                item["evidence_filename"] = evidence_map.get(str(item["evidence_id"]), {}).get("original_filename")

        return paginated, total_count

    @classmethod
    async def get_timeline_stats(cls, db, case_id: str) -> Dict[str, Any]:
        """Calculate summary metrics for a case timeline."""
        events, total = await cls.build_case_timeline(db, case_id=case_id, limit=2000)

        stats = {
            "total_events": total,
            "critical_events": 0,
            "high_events": 0,
            "medium_events": 0,
            "low_events": 0,
            "info_events": 0,
            "system_events": 0,
            "manual_events": 0,
            "first_event_time": None,
            "last_event_time": None,
            "event_types": {}
        }

        times = []
        for e in events:
            sev = (e.get("severity") or "INFO").upper()
            if sev == "CRITICAL":
                stats["critical_events"] += 1
            elif sev == "HIGH":
                stats["high_events"] += 1
            elif sev == "MEDIUM":
                stats["medium_events"] += 1
            elif sev == "LOW":
                stats["low_events"] += 1
            else:
                stats["info_events"] += 1

            if e.get("is_system_generated"):
                stats["system_events"] += 1
            else:
                stats["manual_events"] += 1

            t_type = e.get("event_type", "OTHER")
            stats["event_types"][t_type] = stats["event_types"].get(t_type, 0) + 1

            t = e.get("event_time") or e.get("created_at")
            if isinstance(t, datetime):
                times.append(t)

        if times:
            times.sort()
            stats["first_event_time"] = times[0]
            stats["last_event_time"] = times[-1]

        return stats
