# CRYPTEVID — USB Hardware-to-Software Integration Audit

**Date:** October 21, 2026  
**Auditor:** Senior Full-Stack & Embedded Software Engineer  
**Scope:** ESP32 USB Serial Communication, FastAPI Event Ingestion, MongoDB Audit Persistence, React Dashboard Telemetry, and Platform Security Integrity.

---

## 1. Executive Summary

This audit assesses the implementation of the USB serial communication bridge and backend/frontend telemetry integrations for the CRYPTEVID Forensic Intelligence Platform. The system enables real-time physical authentication event forwarding from an ESP32 forensic ingestion terminal (MFRC522 RFID reader, R307 fingerprint sensor, OLED, LEDs, buzzer) over a USB cable to a local FastAPI backend and React dashboard without compromising role-based access control, bypassing authentication, or modifying hardware wiring.

---

## 2. Modified and Created Files

| File | Type | Description |
|---|---|---|
| `hardware_serial_bridge.py` | Created | Standalone Python USB serial bridge module. Reads newline-terminated protocol packets, validates syntax, debounces duplicate events, handles COM port disconnection/reconnection, and forwards authenticated payloads to FastAPI. |
| `esp32_serial_bridge.py` | Updated | Compatibility wrapper delegating execution to `hardware_serial_bridge.py`. |
| `server/app/models/hardware.py` | Created | Pydantic validation schemas for `HardwareSerialEventPayload`, `HardwareBridgeHeartbeatPayload`, and `HardwareBridgeStatusResponse`. |
| `server/app/repositories/hardware.py` | Created | Repository managing MongoDB interactions for `hardware_events` and `hardware_bridge_state`. |
| `server/app/routers/hardware.py` | Created | FastAPI route handler implementing `/api/hardware/events`, `/api/hardware/bridge-heartbeat`, `/api/hardware/bridge-status`, and `/api/hardware/events`. Enforces `X-Bridge-Key` local bridge authentication. |
| `server/app/core/config.py` | Updated | Added `HARDWARE_BRIDGE_SECRET`, `ESP32_COM_PORT`, and `ESP32_BAUD_RATE` configurations with permissive extra configuration allowance. |
| `server/.env` | Updated | Configured default bridge secrets and serial port constants. |
| `server/requirements.txt` | Updated | Added `pyserial==3.5` and `requests>=2.31.0`. |
| `server/app/main.py` | Updated | Mounted hardware router under `/api` and root prefixes. |
| `client/src/services/api.ts` | Updated | Added `hardwareApi` with endpoints for bridge status and event queries, along with TypeScript interfaces `HardwareEvent` and `HardwareBridgeStatus`. |
| `client/src/components/HardwareTelemetryCard.tsx` | Created | High-fidelity React component displaying real-time hardware connection status (Connected / Disconnected / Error), most recent event spotlight, mapped investigator info, verification badge, and recent events ledger. |
| `client/src/App.tsx` | Updated | Integrated `HardwareTelemetryCard` into both `DashboardView` (`/dashboard`) and `DevicesView` (`/devices`). |
| `server/test_hardware_integration.py` | Created | Comprehensive automated test suite with 15 unit and integration tests covering protocol parsing, bridge security, UID mapping, duplicate protection, and audit logs. |
| `HARDWARE_INTEGRATION_SETUP.md` | Created | Step-by-step operations, COM port discovery, execution instructions, and troubleshooting guide. |
| `HARDWARE_SOFTWARE_INTEGRATION_AUDIT.md` | Created | This architectural audit document. |

---

## 3. Key Architectural Findings & Security Safeguards

1. **Separation of Hardware Telemetry from Web Session Auth**:
   - The hardware emits `CRYPTEVID|1|GRANTED|UID=...|REASON=AUTH_SUCCESS`.
   - Ingesting a `GRANTED` event records the hardware telemetry and validates the user record in MongoDB, but **does not** automatically create a website JWT session or bypass user authentication tokens.
2. **Identity Verification & Unknown UID Protection**:
   - Only UIDs that match an active user in the database (e.g. `admin@forensics.gov` with UID `10 5B 96 5C`, or `investigator@forensics.gov` with UID `C0 A3 CF 54`) are mapped to an investigator.
   - Any unknown UID is marked `is_identity_verified=False` with `mapped_investigator=None`. Unknown cards are **never** arbitrarily assigned to active investigators.
3. **Bridge Authentication (`X-Bridge-Key`)**:
   - The `/api/hardware/events` endpoint rejects all requests lacking the `X-Bridge-Key` header with `403 Forbidden`, preventing unauthorized clients from injecting synthetic hardware events.
4. **Resilient Serial Port Management**:
   - If COM5 is unplugged, the bridge does not crash; it logs structured warnings, notifies FastAPI with `status="Disconnected"`, and polls with exponential backoff.
   - A filesystem lock (`.hardware_bridge.lock`) prevents multiple processes from contending for the same physical COM port.
5. **No Synthetic Connection State**:
   - The dashboard does not show "Connected" merely because FastAPI is running. It checks for fresh bridge heartbeats (sent every 5s; threshold 12s) and serial port availability.

---

## 4. Test Results Summary

The integration test suite (`server/test_hardware_integration.py`) was executed against the active MongoDB instance and ASGI application transport:

```text
test_bridge_authentication_required                      [PASS]
test_bridge_heartbeat_and_status                         [PASS]
test_duplicate_event_handling                            [PASS]
test_ingest_admin_granted_event                          [PASS]
test_ingest_denied_event_with_registered_uid             [PASS]
test_ingest_investigator_granted_event                   [PASS]
test_ingest_unknown_uid_never_maps_to_arbitrary_user     [PASS]
test_mongodb_audit_log_created                           [PASS]
test_preservation_of_jwt_authentication                  [PASS]
test_boot_messages_and_noise_ignored                     [PASS]
test_bridge_deduplication                                [PASS]
test_malformed_protocol_messages_rejected                [PASS]
test_valid_denied_message                                [PASS]
test_valid_granted_message                               [PASS]
test_varied_uids_and_reasons                             [PASS]

----------------------------------------------------------------------
Ran 15 tests in 0.691s - ALL PASSED (OK)
```

Frontend production build check:
```text
$ tsc -b && vite build
✓ built in 2.63s (Zero compilation or TypeScript errors)
```

---

## 5. Requirement Verification Matrix

| Requirement | Description | Status | Verification Notes |
|---|---|---|---|
| **R1. USB Serial Bridge** | Python module `hardware_serial_bridge.py` reading newline protocol from COM port (default COM5, 115200 baud). | **PASS** | Implemented with PySerial, configurable env vars, singleton lockfile, and auto-reconnect. |
| **R2. Protocol Parsing** | Strict parsing of `CRYPTEVID\|1\|STATUS\|UID=...\|REASON=...` with GRANTED/DENIED support. | **PASS** | Regex validator enforces field boundaries; ignores boot noise and rejects malformed fields. |
| **R3. Duplicate Suppression** | Debounce rapid repeated sensor reads within a sliding window. | **PASS** | Suppresses duplicate status/UID events within 2.0s; backend deduplicates event IDs. |
| **R4. Bridge Authentication** | Authenticate bridge requests to FastAPI backend. | **PASS** | Validates `X-Bridge-Key` matching `HARDWARE_BRIDGE_SECRET`; 403 on invalid or missing key. |
| **R5. Event Ingestion Route** | Dedicated `POST /api/hardware/events` validating incoming payload. | **PASS** | Validates Pydantic schema, stores in `hardware_events`, logs to `audit_logs`. |
| **R6. Identity Mapping** | Map RFID UIDs to registered investigators without arbitrary mapping. | **PASS** | Verified with Admin (`10 5B 96 5C`) and Analyst (`C0 A3 CF 54`). Unknown UIDs remain unverified with `mapped_investigator=None`. |
| **R7. Auth Integrity** | Preserve existing JWT login and role-based access control. | **PASS** | Hardware events do not grant arbitrary web sessions or alter token authorization paths. |
| **R8. MongoDB Audit Log** | Ingest events into tamper-evident forensic `audit_logs`. | **PASS** | Recorded via `AuditRepository` with UTC timestamp, device ID `ESP32_USB`, and full detail string. |
| **R9. React Dashboard Display** | Telemetry panel showing connection status, latest event, mapped investigator, and event table. | **PASS** | `HardwareTelemetryCard.tsx` created, styled, and mounted in `/dashboard` and `/devices`. |
| **R10. Real Connection Status** | Do not show "Connected" simply because FastAPI is online. | **PASS** | Evaluates bridge heartbeat freshness (<12s) and serial port status. Shows DISCONNECTED when bridge is inactive. |
| **R11. Automated Tests** | Unit and integration tests covering protocol, auth, persistence, and error states. | **PASS** | 15 tests executed and passing with 100% success rate. |
| **R12. Physical Hardware E2E** | Live scan with physical ESP32 plugged into USB port. | **NOT TESTED** | Simulated and automated software-to-serial communication path verified; physical scan requires physical ESP32 USB cable connected to the host. |

---

## 6. Known Limitations & Recommendations

1. **Physical Cable Attachment**:
   - The COM port on Windows currently lists `COM3` and `COM4` (Bluetooth links). When the physical ESP32 cable is inserted into the PC, it will register as `COM5` (or another port number, easily configured via `$env:ESP32_COM_PORT`).
2. **Serial Port Exclusivity**:
   - On Windows, only one application can hold a COM port open at a time. The Arduino IDE Serial Monitor must be closed before starting `hardware_serial_bridge.py`.
