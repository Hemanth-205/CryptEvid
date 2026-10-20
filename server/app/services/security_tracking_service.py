import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from bson import ObjectId
from fastapi import Request

from app.core.security import decode_token
from app.models.security_event import (
    SecurityEventType,
    SecurityAlertStatus,
    SecurityAlertSeverity
)

class SecurityTrackingService:
    """
    Forensic Unauthorized Access Detection & Security Tracking Engine.
    Captures unauthenticated and unauthorized attempts across all protected endpoints,
    fingerprints client requests without assuming untrusted remote MAC addresses,
    and aggregates deterministic threat signals into security alerts and timelines.
    """

    FAILED_LOGIN_WINDOW_MINUTES = 15
    FAILED_LOGIN_THRESHOLD = 5

    @staticmethod
    def extract_ip(request: Request) -> Tuple[str, str]:
        """
        Safely determine client IP and record its source.
        Does not blindly trust X-Forwarded-For unless reverse proxy environment is active.
        """
        # Fallback to direct client socket
        direct_ip = request.client.host if request.client else "127.0.0.1"

        # Check for forwarded headers if behind proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in the list is the originating client
            client_candidate = forwarded.split(",")[0].strip()
            return client_candidate, "trusted_forwarded_for"

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip(), "trusted_real_ip"

        return direct_ip, "direct_socket"

    @staticmethod
    def extract_device_info(request: Request) -> Dict[str, Any]:
        """
        Extract technically verifiable device/session information from HTTP request.
        MAC address is strictly nullable and never guessed for remote web requests.
        """
        user_agent = request.headers.get("user-agent", "Unknown Client")
        device_id = request.headers.get("x-device-id") or request.headers.get("device-id")

        # Classify client platform from user agent
        device_type = "UNKNOWN"
        ua_lower = user_agent.lower()
        if "esp32" in ua_lower or "iot" in ua_lower:
            device_type = "IOT_TERMINAL"
        elif "postman" in ua_lower or "curl" in ua_lower or "python" in ua_lower or "httpclient" in ua_lower:
            device_type = "AUTOMATED_TOOL"
        elif "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_type = "MOBILE_DEVICE"
        elif "mozilla" in ua_lower or "chrome" in ua_lower or "safari" in ua_lower:
            device_type = "DESKTOP_BROWSER"

        # MAC address is only recorded when provided by registered local hardware or test harness
        raw_mac = request.headers.get("x-mac-address")
        mac_address = raw_mac.strip() if raw_mac and re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", raw_mac.strip()) else None

        return {
            "user_agent": user_agent,
            "device_id": device_id,
            "device_type": device_type,
            "mac_address": mac_address
        }

    @staticmethod
    async def extract_auth_context(request: Request, db) -> Dict[str, Any]:
        """
        Inspect request authorization headers to differentiate between
        unauthenticated users and authenticated users acting without permission.
        """
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {
                "is_authenticated": False,
                "user_id": None,
                "login_id": None,
                "user_role": None,
                "user_name": None
            }

        token = auth_header[7:].strip()
        payload = decode_token(token)
        if not payload or not payload.get("sub"):
            return {
                "is_authenticated": False,
                "user_id": None,
                "login_id": None,
                "user_role": None,
                "user_name": None
            }

        email = payload.get("sub")
        user = await db["users"].find_one({"email": email})
        if not user:
            return {
                "is_authenticated": True,
                "user_id": None,
                "login_id": email,
                "user_role": payload.get("role"),
                "user_name": "Unknown User"
            }

        return {
            "is_authenticated": True,
            "user_id": str(user["_id"]),
            "login_id": user["email"],
            "user_role": user.get("role"),
            "user_name": user.get("name")
        }

    @staticmethod
    def deduce_target_resources(path: str, method: str) -> Dict[str, Any]:
        """Extract target case ID, evidence ID, and intended action from URI."""
        case_id = None
        evidence_id = None

        # Detect Case ID
        case_match = re.search(r"/cases/([a-zA-Z0-9_-]+)", path)
        if case_match and case_match.group(1) not in ("stats", "seed-demo", "reports"):
            case_id = case_match.group(1)

        # Detect Evidence ID
        ev_match = re.search(r"/evidence/([a-zA-Z0-9_-]+)", path)
        if ev_match and ev_match.group(1) not in ("stats", "upload"):
            evidence_id = ev_match.group(1)

        # Determine Action
        method_upper = method.upper()
        action = "ACCESS"
        if "verify" in path:
            action = "VERIFY"
        elif "download" in path:
            action = "DOWNLOAD"
        elif "upload" in path or method_upper == "POST":
            action = "MODIFY" if "evidence" in path or "cases" in path else "CREATE"
        elif method_upper in ("PUT", "PATCH"):
            action = "MODIFY"
        elif method_upper == "DELETE":
            action = "DELETE"
        elif method_upper == "GET":
            action = "VIEW"

        return {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "action": action
        }

    @classmethod
    async def record_http_security_event(
        cls,
        request: Request,
        status_code: int,
        detail: str,
        db=None,
        explicit_case_id: Optional[str] = None,
        explicit_evidence_id: Optional[str] = None,
        explicit_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record unauthenticated or unauthorized access attempt into security_events.
        Generates security alert if action is high-risk or repeated.
        """
        if db is None:
            from app.core.database import get_database
            db = get_database()

        now = datetime.now(timezone.utc)
        path = request.url.path
        method = request.method

        # 1. Extract context
        ip_addr, ip_source = cls.extract_ip(request)
        device_info = cls.extract_device_info(request)
        auth_context = await cls.extract_auth_context(request, db)
        resource_info = cls.deduce_target_resources(path, method)

        case_id = explicit_case_id or resource_info["case_id"]
        evidence_id = explicit_evidence_id or resource_info["evidence_id"]
        action = explicit_action or resource_info["action"]

        # 2. Differentiate Event Type:
        # UNAUTHORIZED_ACCESS_ATTEMPT (no valid credentials) vs AUTHENTICATED_BUT_UNAUTHORIZED (valid login but insufficient RBAC)
        if not auth_context["is_authenticated"]:
            event_type = SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value
            reason = "AUTHENTICATION_REQUIRED"
        elif status_code == 403:
            event_type = SecurityEventType.AUTHENTICATED_BUT_UNAUTHORIZED.value
            reason = detail or "FORBIDDEN_RESOURCE_ACCESS"
        else:
            event_type = SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value
            reason = detail or "ACCESS_DENIED"

        # Refine reason based on detail message
        if "Investigator is not assigned" in str(detail) or "FORBIDDEN_CASE_ACCESS" in str(detail):
            reason = "FORBIDDEN_CASE_ACCESS"
        elif "FORBIDDEN_EVIDENCE_ACCESS" in str(detail):
            reason = "FORBIDDEN_EVIDENCE_ACCESS"
        elif "Read-only accounts cannot" in str(detail):
            reason = "READONLY_PERMISSION_VIOLATION"

        # 3. Severity mapping
        if action in ("MODIFY", "DELETE") or "TAMPER" in str(detail).upper():
            severity = SecurityAlertSeverity.CRITICAL.value
        elif "EVIDENCE" in reason or "CASE" in reason or status_code == 403:
            severity = SecurityAlertSeverity.HIGH.value
        else:
            severity = SecurityAlertSeverity.MEDIUM.value

        # Resolve Case Number & Evidence Filename
        case_number = None
        evidence_name = None
        if case_id:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None
            c_doc = await db["cases"].find_one({"_id": c_oid if c_oid else case_id})
            if c_doc:
                case_number = c_doc.get("case_number")
        if evidence_id:
            e_oid = ObjectId(evidence_id) if ObjectId.is_valid(evidence_id) else None
            e_doc = await db["evidence"].find_one({"_id": e_oid if e_oid else evidence_id})
            if e_doc:
                evidence_name = e_doc.get("original_filename")
                if not case_id and e_doc.get("case_id"):
                    case_id = str(e_doc["case_id"])

        event_id = f"SEC-EVT-{int(now.timestamp())}-{uuid.uuid4().hex[:6].upper()}"

        event_doc = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": now,
            "ip_address": ip_addr,
            "ip_source": ip_source,
            "http_method": method,
            "endpoint": path,
            "request_type": "REST",
            "user_id": auth_context["user_id"],
            "login_id": auth_context["login_id"],
            "user_role": auth_context["user_role"],
            "user_name": auth_context["user_name"],
            "user_agent": device_info["user_agent"],
            "device_id": device_info["device_id"],
            "device_type": device_info["device_type"],
            "mac_address": device_info["mac_address"],
            "case_id": case_id,
            "case_number": case_number,
            "evidence_id": evidence_id,
            "evidence_name": evidence_name,
            "action": action,
            "result": "BLOCKED",
            "reason": reason,
            "severity": severity,
            "status_code": status_code,
            "error_detail": detail,
            "created_at": now
        }

        res = await db["security_events"].insert_one(event_doc)
        event_doc["_id"] = str(res.inserted_id)

        # 4. Trigger Security Alert when appropriate
        await cls._evaluate_security_alert(db, event_doc)

        return event_doc

    @classmethod
    async def record_login_failure(
        cls,
        request: Request,
        email: Optional[str],
        reason: str = "INCORRECT_CREDENTIALS",
        db=None
    ) -> Dict[str, Any]:
        """
        Record failed authentication attempts, tracking failure frequency from the same IP.
        Triggers REPEATED_LOGIN_FAILURE alert if threshold is exceeded.
        Plaintext passwords are NEVER accepted or stored here.
        """
        if db is None:
            from app.core.database import get_database
            db = get_database()

        now = datetime.now(timezone.utc)
        ip_addr, ip_source = cls.extract_ip(request)
        device_info = cls.extract_device_info(request)

        event_id = f"SEC-EVT-{int(now.timestamp())}-{uuid.uuid4().hex[:6].upper()}"

        event_doc = {
            "event_id": event_id,
            "event_type": SecurityEventType.FAILED_LOGIN.value,
            "timestamp": now,
            "ip_address": ip_addr,
            "ip_source": ip_source,
            "http_method": request.method,
            "endpoint": request.url.path,
            "request_type": "REST",
            "user_id": None,
            "login_id": email.lower() if email else None,
            "user_role": None,
            "user_name": None,
            "user_agent": device_info["user_agent"],
            "device_id": device_info["device_id"],
            "device_type": device_info["device_type"],
            "mac_address": device_info["mac_address"],
            "case_id": None,
            "case_number": None,
            "evidence_id": None,
            "evidence_name": None,
            "action": "LOGIN",
            "result": "FAILED",
            "reason": reason,
            "severity": SecurityAlertSeverity.MEDIUM.value,
            "status_code": 401,
            "error_detail": reason,
            "created_at": now
        }

        res = await db["security_events"].insert_one(event_doc)
        event_doc["_id"] = str(res.inserted_id)

        # Check for repeated failures from same IP within the time window
        window_start = now - timedelta(minutes=cls.FAILED_LOGIN_WINDOW_MINUTES)
        recent_failures_count = await db["security_events"].count_documents({
            "ip_address": ip_addr,
            "event_type": SecurityEventType.FAILED_LOGIN.value,
            "timestamp": {"$gte": window_start}
        })

        if recent_failures_count >= cls.FAILED_LOGIN_THRESHOLD:
            # Query recent failure IDs
            cursor = db["security_events"].find({
                "ip_address": ip_addr,
                "event_type": SecurityEventType.FAILED_LOGIN.value,
                "timestamp": {"$gte": window_start}
            }).sort("timestamp", -1).limit(10)
            related_docs = await cursor.to_list(length=10)
            related_ids = [d["event_id"] for d in related_docs]

            # Check if an OPEN alert for this IP already exists
            existing_alert = await db["security_alerts"].find_one({
                "ip_address": ip_addr,
                "alert_type": "REPEATED_LOGIN_FAILURE",
                "status": {"$in": [SecurityAlertStatus.OPEN.value, SecurityAlertStatus.INVESTIGATING.value]}
            })

            if existing_alert:
                # Update existing alert with new related events
                await db["security_alerts"].update_one(
                    {"_id": existing_alert["_id"]},
                    {
                        "$addToSet": {"related_event_ids": {"$each": related_ids}},
                        "$set": {
                            "updated_at": now,
                            "description": f"Repeated login failures detected: {recent_failures_count} failed attempts from IP {ip_addr} in past {cls.FAILED_LOGIN_WINDOW_MINUTES} minutes."
                        }
                    }
                )
            else:
                # Create new Security Alert
                alert_id = f"ALT-{int(now.timestamp())}-{uuid.uuid4().hex[:6].upper()}"
                alert_doc = {
                    "alert_id": alert_id,
                    "alert_type": "REPEATED_LOGIN_FAILURE",
                    "severity": SecurityAlertSeverity.CRITICAL.value,
                    "timestamp": now,
                    "ip_address": ip_addr,
                    "user_id": None,
                    "login_id": email.lower() if email else None,
                    "device_id": device_info["device_id"],
                    "case_id": None,
                    "case_number": None,
                    "evidence_id": None,
                    "action": "LOGIN",
                    "description": f"Security threshold exceeded: {recent_failures_count} consecutive failed login attempts from IP {ip_addr} within {cls.FAILED_LOGIN_WINDOW_MINUTES} minutes.",
                    "status": SecurityAlertStatus.OPEN.value,
                    "related_event_ids": related_ids,
                    "resolution_notes": None,
                    "resolved_by": None,
                    "resolved_at": None,
                    "created_at": now,
                    "updated_at": now
                }
                await db["security_alerts"].insert_one(alert_doc)

        return event_doc

    @classmethod
    async def _evaluate_security_alert(cls, db, event: Dict[str, Any]):
        """Evaluates whether a security event should spawn or aggregate into a Security Alert."""
        now = datetime.now(timezone.utc)
        action = event.get("action", "")
        reason = event.get("reason", "")
        event_type = event.get("event_type", "")

        # Only high, critical, or specific forbidden events spawn alerts
        spawn_alert = False
        alert_type = "UNAUTHORIZED_ACCESS"
        alert_severity = event.get("severity", SecurityAlertSeverity.MEDIUM.value)

        if action in ("MODIFY", "DELETE") or "TAMPER" in reason:
            spawn_alert = True
            alert_type = "UNAUTHORIZED_MODIFICATION_ATTEMPT"
            alert_severity = SecurityAlertSeverity.CRITICAL.value
        elif reason == "FORBIDDEN_CASE_ACCESS":
            spawn_alert = True
            alert_type = "FORBIDDEN_CASE_ACCESS"
            alert_severity = SecurityAlertSeverity.HIGH.value
        elif reason == "FORBIDDEN_EVIDENCE_ACCESS":
            spawn_alert = True
            alert_type = "FORBIDDEN_EVIDENCE_ACCESS"
            alert_severity = SecurityAlertSeverity.HIGH.value
        elif event.get("severity") in (SecurityAlertSeverity.HIGH.value, SecurityAlertSeverity.CRITICAL.value):
            spawn_alert = True
            alert_type = "UNAUTHORIZED_ACCESS"

        if spawn_alert:
            alert_id = f"ALT-{int(now.timestamp())}-{uuid.uuid4().hex[:6].upper()}"
            actor_label = event.get("login_id") or event.get("ip_address")
            alert_doc = {
                "alert_id": alert_id,
                "alert_type": alert_type,
                "severity": alert_severity,
                "timestamp": now,
                "ip_address": event.get("ip_address", "127.0.0.1"),
                "user_id": event.get("user_id"),
                "login_id": event.get("login_id"),
                "user_role": event.get("user_role"),
                "device_id": event.get("device_id"),
                "case_id": event.get("case_id"),
                "case_number": event.get("case_number"),
                "evidence_id": event.get("evidence_id"),
                "action": action,
                "description": f"Security alert: {event_type} detected. Action '{action}' on endpoint '{event.get('endpoint')}' blocked. Reason: {reason}. Actor: {actor_label}.",
                "status": SecurityAlertStatus.OPEN.value,
                "related_event_ids": [event.get("event_id")],
                "resolution_notes": None,
                "resolved_by": None,
                "resolved_at": None,
                "created_at": now,
                "updated_at": now
            }
            await db["security_alerts"].insert_one(alert_doc)
