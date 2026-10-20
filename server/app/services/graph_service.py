from bson import ObjectId
from typing import Dict, Any, List, Optional, Set
from app.models.graph import GraphNodeType, GraphEdgeType, GraphNode, GraphEdge, EvidenceGraphResponse

class GraphService:
    """
    Constructs real, non-fabricated topological entity-relationship graphs
    connecting Cases, Evidence Artifacts, Forensic Events, Custody Milestones,
    Originating Devices, Investigators, and Physical Locations.
    """

    @classmethod
    async def build_case_graph(
        cls,
        db,
        case_id: str,
        node_type_filter: Optional[str] = None,
        severity_filter: Optional[str] = None
    ) -> EvidenceGraphResponse:
        case_id_str = str(case_id)
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None

        # 1. Fetch Case
        case = await db["cases"].find_one({"_id": case_oid if case_oid else case_id_str})
        if not case:
            return EvidenceGraphResponse(case_id=case_id_str, total_nodes=0, total_edges=0, nodes=[], edges=[])

        case_num = case.get("case_number", "CASE")
        case_title = case.get("title", "Forensic Investigation")

        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}

        # Center: Case Node
        case_node_id = f"case_{case_id_str}"
        nodes[case_node_id] = GraphNode(
            id=case_node_id,
            node_type=GraphNodeType.CASE,
            label=f"{case_num}: {case_title}",
            case_id=case_id_str,
            source_id=case_id_str,
            severity=case.get("priority", "INFO"),
            metadata={"status": case.get("status"), "case_type": case.get("case_type")}
        )

        # 2. Fetch Evidence Artifacts
        ev_cursor = db["evidence"].find({"case_id": case_id_str})
        evidence_list = await ev_cursor.to_list(length=500)
        evidence_ids = []

        for ev in evidence_list:
            ev_id = str(ev["_id"])
            evidence_ids.append(ev_id)
            ev_node_id = f"ev_{ev_id}"
            ev_filename = ev.get("original_filename", "Artifact")
            integrity = ev.get("integrity_status", "VERIFIED")
            ev_sev = "CRITICAL" if integrity == "TAMPERED" else "INFO"

            nodes[ev_node_id] = GraphNode(
                id=ev_node_id,
                node_type=GraphNodeType.EVIDENCE,
                label=ev_filename,
                case_id=case_id_str,
                source_id=ev_id,
                severity=ev_sev,
                metadata={
                    "file_size": ev.get("file_size"),
                    "sha256_hash": ev.get("sha256_hash"),
                    "integrity_status": integrity,
                    "mime_type": ev.get("mime_type")
                }
            )

            # Edge: CASE -> EVIDENCE
            edge_id = f"e_case_{ev_id}"
            edges[edge_id] = GraphEdge(
                id=edge_id,
                source=case_node_id,
                target=ev_node_id,
                edge_type=GraphEdgeType.CONTAINS,
                label="CONTAINS"
            )

            # Evidence Device
            dev_name = ev.get("source_device")
            if dev_name:
                dev_node_id = f"dev_{dev_name.replace(' ', '_').lower()}"
                if dev_node_id not in nodes:
                    nodes[dev_node_id] = GraphNode(
                        id=dev_node_id,
                        node_type=GraphNodeType.DEVICE,
                        label=f"Terminal: {dev_name}",
                        case_id=case_id_str,
                        source_id=dev_name,
                        severity="INFO"
                    )
                edges[f"e_ev_dev_{ev_id}"] = GraphEdge(
                    id=f"e_ev_dev_{ev_id}",
                    source=ev_node_id,
                    target=dev_node_id,
                    edge_type=GraphEdgeType.COLLECTED_FROM,
                    label="COLLECTED_FROM"
                )

            # Evidence Investigator / Collector
            collector = ev.get("collector_name")
            if collector:
                inv_node_id = f"inv_{collector.replace(' ', '_').lower()}"
                if inv_node_id not in nodes:
                    nodes[inv_node_id] = GraphNode(
                        id=inv_node_id,
                        node_type=GraphNodeType.INVESTIGATOR,
                        label=f"Operator: {collector}",
                        case_id=case_id_str,
                        source_id=collector,
                        severity="INFO"
                    )
                edges[f"e_ev_inv_{ev_id}"] = GraphEdge(
                    id=f"e_ev_inv_{ev_id}",
                    source=ev_node_id,
                    target=inv_node_id,
                    edge_type=GraphEdgeType.HANDLED_BY,
                    label="HANDLED_BY"
                )

        # 3. Fetch Forensic Events
        evt_cursor = db["forensic_events"].find({"case_id": case_id_str})
        forensic_events = await evt_cursor.to_list(length=500)

        for evt in forensic_events:
            evt_id = str(evt["_id"])
            evt_node_id = f"evt_{evt_id}"
            evt_sev = evt.get("severity", "INFO")
            evt_type = evt.get("event_type", "EVENT")
            evt_title = evt.get("title", evt_type)

            nodes[evt_node_id] = GraphNode(
                id=evt_node_id,
                node_type=GraphNodeType.EVENT,
                label=f"[{evt_type}] {evt_title}",
                case_id=case_id_str,
                source_id=evt_id,
                severity=evt_sev,
                metadata={
                    "event_type": evt_type,
                    "confidence": evt.get("confidence"),
                    "time_precision": evt.get("time_precision"),
                    "event_time": evt.get("event_time")
                }
            )

            # Relationship: EVIDENCE -> EVENT or CASE -> EVENT
            ev_ref = evt.get("evidence_id")
            if ev_ref and f"ev_{ev_ref}" in nodes:
                edges[f"e_ev_evt_{evt_id}"] = GraphEdge(
                    id=f"e_ev_evt_{evt_id}",
                    source=f"ev_{ev_ref}",
                    target=evt_node_id,
                    edge_type=GraphEdgeType.GENERATED_EVENT,
                    label="GENERATED_EVENT"
                )
            else:
                edges[f"e_case_evt_{evt_id}"] = GraphEdge(
                    id=f"e_case_evt_{evt_id}",
                    source=case_node_id,
                    target=evt_node_id,
                    edge_type=GraphEdgeType.CONTAINS,
                    label="HAS_EVENT"
                )

            # Event Device
            evt_dev = evt.get("device_id")
            if evt_dev and evt_dev != "INVESTIGATOR_WORKSTATION":
                dev_node_id = f"dev_{evt_dev.replace(' ', '_').lower()}"
                if dev_node_id not in nodes:
                    nodes[dev_node_id] = GraphNode(
                        id=dev_node_id,
                        node_type=GraphNodeType.DEVICE,
                        label=f"Device: {evt_dev}",
                        case_id=case_id_str,
                        source_id=evt_dev,
                        severity=evt_sev
                    )
                edges[f"e_evt_dev_{evt_id}"] = GraphEdge(
                    id=f"e_evt_dev_{evt_id}",
                    source=evt_node_id,
                    target=dev_node_id,
                    edge_type=GraphEdgeType.OCCURRED_ON,
                    label="OCCURRED_ON"
                )

            # Event Location
            evt_loc = evt.get("location")
            lat = evt.get("latitude")
            lon = evt.get("longitude")
            if evt_loc or lat is not None:
                loc_label = evt_loc or f"GPS: {lat}, {lon}"
                loc_node_id = f"loc_{loc_label.replace(' ', '_').lower()[:30]}"
                if loc_node_id not in nodes:
                    nodes[loc_node_id] = GraphNode(
                        id=loc_node_id,
                        node_type=GraphNodeType.LOCATION,
                        label=loc_label,
                        case_id=case_id_str,
                        source_id=loc_label,
                        severity="INFO",
                        metadata={"latitude": lat, "longitude": lon}
                    )
                edges[f"e_evt_loc_{evt_id}"] = GraphEdge(
                    id=f"e_evt_loc_{evt_id}",
                    source=evt_node_id,
                    target=loc_node_id,
                    edge_type=GraphEdgeType.LOCATED_AT,
                    label="LOCATED_AT"
                )

        # 4. Fetch Chain of Custody Events
        if evidence_ids:
            custody_cursor = db["chain_of_custody"].find({"evidence_id": {"$in": evidence_ids}})
            custody_list = await custody_cursor.to_list(length=500)

            for cust in custody_list:
                cust_id = str(cust["_id"])
                cust_node_id = f"cust_{cust_id}"
                action = cust.get("action", "CUSTODY")
                sev = "CRITICAL" if action == "EVIDENCE_INTEGRITY_FAILURE" else "INFO"
                ev_id = cust.get("evidence_id")

                nodes[cust_node_id] = GraphNode(
                    id=cust_node_id,
                    node_type=GraphNodeType.CUSTODY,
                    label=f"Custody: {action}",
                    case_id=case_id_str,
                    source_id=cust_id,
                    severity=sev,
                    metadata={"action": action, "timestamp": cust.get("timestamp")}
                )

                if ev_id and f"ev_{ev_id}" in nodes:
                    edges[f"e_ev_cust_{cust_id}"] = GraphEdge(
                        id=f"e_ev_cust_{cust_id}",
                        source=f"ev_{ev_id}",
                        target=cust_node_id,
                        edge_type=GraphEdgeType.HAS_CUSTODY_EVENT,
                        label="HAS_CUSTODY_EVENT"
                    )

        # 5. Fetch Security Violations & Unauthorized Access Attempts
        sec_query = {"$or": [{"case_id": case_id_str}]}
        if evidence_ids:
            sec_query["$or"].append({"evidence_id": {"$in": evidence_ids}})

        sec_cursor = db["security_events"].find(sec_query).limit(500)
        security_events = await sec_cursor.to_list(length=500)

        for s in security_events:
            ip_addr = s.get("ip_address") or "unknown_ip"
            auth_ctx = s.get("auth_context") or {}
            actor_label = auth_ctx.get("email") or f"Suspect IP ({ip_addr})"
            target_ev = s.get("evidence_id")

            # Actor Node
            actor_node_id = f"suspect_{ip_addr.replace('.', '_').replace(':', '_')}"
            if actor_node_id not in nodes:
                nodes[actor_node_id] = GraphNode(
                    id=actor_node_id,
                    node_type=GraphNodeType.ACTOR,
                    label=f"Suspect: {actor_label}",
                    case_id=case_id_str,
                    source_id=ip_addr,
                    severity="HIGH",
                    metadata={
                        "ip_address": ip_addr,
                        "ip_source": s.get("ip_source"),
                        "device_type": s.get("device_info", {}).get("client_type")
                    }
                )

            # ATTEMPTED_ACCESS Edge
            if target_ev and f"ev_{target_ev}" in nodes:
                edge_id = f"e_att_{actor_node_id}_ev_{target_ev}"
                edges[edge_id] = GraphEdge(
                    id=edge_id,
                    source=actor_node_id,
                    target=f"ev_{target_ev}",
                    edge_type=GraphEdgeType.ATTEMPTED_ACCESS,
                    label="ATTEMPTED_ACCESS",
                    metadata={"result": s.get("result", "BLOCKED"), "reason": s.get("failure_reason")}
                )
            else:
                edge_id = f"e_att_{actor_node_id}_case_{case_id_str}"
                edges[edge_id] = GraphEdge(
                    id=edge_id,
                    source=actor_node_id,
                    target=case_node_id,
                    edge_type=GraphEdgeType.ATTEMPTED_ACCESS,
                    label="ATTEMPTED_ACCESS",
                    metadata={"result": s.get("result", "BLOCKED"), "reason": s.get("failure_reason")}
                )

            # TAMPER_DETECTED edge for tamper events
            if s.get("event_type") == "TAMPER_DETECTED" and target_ev and f"ev_{target_ev}" in nodes:
                login_id = s.get("login_id") or "UNKNOWN USER"
                tamper_actor_id = f"tamper_actor_{login_id.replace(' ', '_').lower()}"
                if tamper_actor_id not in nodes:
                    nodes[tamper_actor_id] = GraphNode(
                        id=tamper_actor_id,
                        node_type=GraphNodeType.ACTOR,
                        label=f"Actor: {login_id}",
                        case_id=case_id_str,
                        source_id=login_id,
                        severity="CRITICAL",
                        metadata={
                            "ip_address": ip_addr,
                            "original_sha256": s.get("original_sha256"),
                            "current_sha256": s.get("current_sha256")
                        }
                    )
                tamper_edge_id = f"e_tamper_{tamper_actor_id}_ev_{target_ev}"
                if tamper_edge_id not in edges:
                    edges[tamper_edge_id] = GraphEdge(
                        id=tamper_edge_id,
                        source=tamper_actor_id,
                        target=f"ev_{target_ev}",
                        edge_type=GraphEdgeType.TAMPER_DETECTED,
                        label="TAMPER_DETECTED",
                        metadata={
                            "original_sha256": s.get("original_sha256"),
                            "current_sha256": s.get("current_sha256"),
                            "backup_id": s.get("backup_id")
                        }
                    )

        # 5b. Fetch Preserved Original Backup Records and add BACKUP nodes
        if evidence_ids:
            backup_cursor = db["evidence_backups"].find({"evidence_id": {"$in": evidence_ids}})
            backup_docs = await backup_cursor.to_list(length=500)

            for bk in backup_docs:
                bk_id = bk.get("backup_id", str(bk["_id"]))
                ev_id = bk.get("evidence_id")
                bk_node_id = f"backup_{bk_id}"
                bk_status = bk.get("status", "PROTECTED")
                bk_sev = "CRITICAL" if bk_status == "TAMPERED" else "INFO"

                # BACKUP Node — only shows logical reference, never physical path
                nodes[bk_node_id] = GraphNode(
                    id=bk_node_id,
                    node_type=GraphNodeType.BACKUP,
                    label=f"Preserved Original: {bk.get('storage_reference', bk_id)}",
                    case_id=case_id_str,
                    source_id=bk_id,
                    severity=bk_sev,
                    metadata={
                        "backup_id": bk_id,
                        "storage_reference": bk.get("storage_reference"),
                        "original_sha256": bk.get("original_sha256"),
                        "backup_sha256": bk.get("backup_sha256"),
                        "status": bk_status,
                        "version": bk.get("version", 1)
                    }
                )

                # HAS_BACKUP Edge: EVIDENCE → BACKUP
                if ev_id and f"ev_{ev_id}" in nodes:
                    edges[f"e_ev_backup_{bk_id}"] = GraphEdge(
                        id=f"e_ev_backup_{bk_id}",
                        source=f"ev_{ev_id}",
                        target=bk_node_id,
                        edge_type=GraphEdgeType.HAS_BACKUP,
                        label="HAS_PRESERVED_ORIGINAL"
                    )

        # 6. Apply Filtering if specified
        final_nodes = list(nodes.values())
        final_edges = list(edges.values())

        if node_type_filter and node_type_filter != "ALL":
            try:
                target_type = GraphNodeType(node_type_filter.upper())
                final_nodes = [n for n in final_nodes if n.node_type == target_type]
                valid_ids = {n.id for n in final_nodes}
                final_edges = [e for e in final_edges if e.source in valid_ids and e.target in valid_ids]
            except Exception:
                pass


        if severity_filter and severity_filter != "ALL":
            # Filter nodes by severity (keep CASE node for topology anchor)
            final_nodes = [n for n in final_nodes if n.node_type == GraphNodeType.CASE or n.severity == severity_filter]
            valid_ids = {n.id for n in final_nodes}
            final_edges = [e for e in final_edges if e.source in valid_ids and e.target in valid_ids]

        return EvidenceGraphResponse(
            case_id=case_id_str,
            total_nodes=len(final_nodes),
            total_edges=len(final_edges),
            nodes=final_nodes,
            edges=final_edges
        )
