# CRYPTEVID — USB Hardware-to-Software Integration Setup Guide

This guide details the end-to-end setup, execution, and troubleshooting procedures for connecting the physical ESP32 forensic hardware terminal (MFRC522 RFID reader, R307 optical fingerprint scanner, OLED, LEDs, buzzer) over USB Serial on Windows to the CRYPTEVID full-stack platform.

---

## 1. System Architecture: Mandatory Two-Stage Authentication

CRYPTEVID enforces strict zero-trust **Two-Stage Authentication**:

1. **Stage 1 (Hardware Authentication)**:
   - User authenticates physically via the ESP32 (RFID scan + R307 biometric verification).
   - ESP32 emits `CRYPTEVID|1|GRANTED|UID=10 5B 96 5C|REASON=AUTH_SUCCESS`.
   - `hardware_serial_bridge.py` forwards the scan to FastAPI `/api/hardware/events`.
   - Backend verifies the UID and fingerprint against registered investigator credentials in MongoDB.
   - Upon verification, the backend issues a cryptographically secure, 5-minute single-use challenge ticket (`hardware_ticket_id`).
   - **Crucial Security Rule**: Hardware verification alone **NEVER** issues a full JWT session token or unlocks the dashboard directly.
2. **Stage 2 (Software Login)**:
   - User provides their registered User ID (email) and master passphrase.
   - Backend atomically validates:
     1. Ticket is present, VALID, unexpired (< 5 minutes), and not previously used.
     2. Email matches the identity bound to the hardware ticket.
     3. Passphrase matches the hash in MongoDB.
   - Ticket is atomically consumed to eliminate replay attacks.
   - Backend issues the full JWT token and redirects to `/dashboard`.

```
┌─────────────────────────────────┐
│     ESP32 Hardware Terminal    │
│  (RFID MFRC522 + R307 Optical)  │
└────────────────┬────────────────┘
                 │ USB Cable (COM5 / Auto-detected @ 115200 baud)
                 ▼
┌─────────────────────────────────┐
│   hardware_serial_bridge.py     │
│  - Smart port auto-detection    │
│  - Ignores Bluetooth links      │
│  - Protocol sanity validation   │
│  - Debounce / deduplication     │
│  - Singleton lock (PID guard)   │
└────────────────┬────────────────┘
                 │ HTTP POST /api/hardware/events (X-Bridge-Key)
                 ▼
┌─────────────────────────────────┐
│   FastAPI Backend (Stage 1)     │
│  - Issues 5-min challenge ticket│
│  - Broadcasts Stage 1 ticket    │
└───────┬─────────────────┬───────┘
        │                 │
        ▼                 ▼
┌──────────────┐   ┌───────────────────────────┐
│ MongoDB      │   │ React Terminal (Stage 2)  │
│ - hardware_  │   │ - Stage 1 Verified Banner │
│   tickets    │   │ - 5-min Countdown Timer   │
│ - audit_logs │   │ - User ID + Passphrase    │
│ - users      │   │ - Atomic Ticket Consume   │
└──────────────┘   └───────────────────────────┘
```

---

## 2. Hardware Protocol Specification

The ESP32 sketch emits newline-terminated serial records matching this exact protocol:

```text
CRYPTEVID|1|GRANTED|UID=10 5B 96 5C|REASON=AUTH_SUCCESS
CRYPTEVID|1|DENIED|UID=10 5B 96 5C|REASON=AUTH_FAILED
```

- **Prefix**: `CRYPTEVID` (magic packet header)
- **Version**: `1`
- **Reported Status**: `GRANTED` or `DENIED`
- **Card Identifier**: `UID=<hex_bytes_with_or_without_spaces>`
- **Hardware Reason**: `REASON=<status_reason>` (e.g. `AUTH_SUCCESS`, `AUTH_FAILED`, `TIMEOUT`, `UNKNOWN_CARD`)

> **Security Note**: A hardware `GRANTED` event is a Stage 1 verification report and produces a single-use challenge ticket. It **never** issues a JWT directly.

---

## 3. Registered Hardware Identifiers

| Role | Investigator Name | Email | Registered RFID UID | Fingerprint ID |
|---|---|---|---|---|
| **Admin** | Chief Investigator (Admin) | `admin@forensics.gov` | `10 5B 96 5C` (`105B965C`) | `6` |
| **Investigator** | Forensic Analyst | `investigator@forensics.gov` | `C0 A3 CF 54` (`C0A3CF54`) | `2` |
| **Read-Only** | Court Auditor (Read-Only) | `viewer@forensics.gov` | `C3 D4 E5 F6` (`C3D4E5F6`) | `20` |

*Any unmapped or unregistered UID reported by the ESP32 is safely logged as unverified and is **never** assigned to an arbitrary investigator.*

---

## 4. Prerequisites & Python Dependencies

Ensure Python 3.11+ is installed. In the server directory or global Python environment:

```bash
# In c:\Users\Hari\Downloads\CRYPTEVID\server
.\venv\Scripts\pip install pyserial requests uvicorn fastapi motor pydantic
```

---

## 5. Identifying Your Windows COM Port & Auto-Detection

`hardware_serial_bridge.py` includes **intelligent automatic port detection**:
- Scans all serial ports on the host.
- Automatically ignores Windows virtual Bluetooth links (`BTHENUM`).
- Matches known ESP32 USB UART chipsets:
  - Silicon Labs CP210x (`VID 0x10C4`)
  - WCH CH340 / CH341 (`VID 0x1A86`)
  - Espressif Native USB (`VID 0x303A`)
  - FTDI FT232 (`VID 0x0403`)
- Falls back to configured `ESP32_COM_PORT` (default: `COM5`).

To view detected serial ports manually:
```powershell
.\server\venv\Scripts\python.exe -m serial.tools.list_ports
```

---

## 6. Environment Configuration

### Backend Environment (`server/.env`)
```ini
PROJECT_NAME="Secure Forensic IoT Platform"
MONGODB_URL="mongodb://localhost:27017"
DATABASE_NAME="macro"
JWT_SECRET_KEY="supersecretkey_change_in_production_for_forensic_platform"
HOST="127.0.0.1"
PORT=8000

# Hardware USB Serial Bridge Settings
HARDWARE_BRIDGE_SECRET="cryptevid_usb_bridge_secret_dev"
ESP32_COM_PORT="COM5"
ESP32_BAUD_RATE=115200
```

### Bridge Execution Environment (Optional overrides)
```powershell
$env:ESP32_COM_PORT="COM5"
$env:ESP32_BAUD_RATE="115200"
$env:FASTAPI_URL="http://127.0.0.1:8000"
$env:HARDWARE_BRIDGE_SECRET="cryptevid_usb_bridge_secret_dev"
```

---

## 7. Startup Instructions

Run each of the following components in separate PowerShell terminal windows:

### Terminal 1: MongoDB Daemon (if local)
Ensure MongoDB is running on port `27017`:
```powershell
mongod --dbpath "C:\data\db"
```

### Terminal 2: FastAPI Backend Server
```powershell
cd c:\Users\Hari\Downloads\CRYPTEVID\server
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health check URL: `http://127.0.0.1:8000/health`*

### Terminal 3: USB Serial Hardware Bridge
```powershell
cd c:\Users\Hari\Downloads\CRYPTEVID
.\server\venv\Scripts\python.exe hardware_serial_bridge.py
```
*The bridge will auto-detect your ESP32, filter out Bluetooth links, and begin background telemetry dispatch.*

### Terminal 4: React Frontend Client
```powershell
cd c:\Users\Hari\Downloads\CRYPTEVID\client
npm run dev
```
*Access terminal in browser at: `http://localhost:5173`*

---

## 8. Verifying Two-Stage Ingestion & Automated Tests

To run the complete automated test suite verifying all Two-Stage Authentication, anti-replay, and ticket validation guarantees:

```powershell
cd c:\Users\Hari\Downloads\CRYPTEVID\server
.\venv\Scripts\python.exe test_two_stage_auth.py
.\venv\Scripts\python.exe test_hardware_integration.py
```

### Manual Two-Stage Authentication Flow:
1. Open `http://localhost:5173/login`.
2. Notice the two-stage indicator: **Stage 1 (Hardware Auth)** is active, **Stage 2 (Software Login)** is locked.
3. Tap authorized RFID card (`10 5B 96 5C`) and place finger on R307 sensor (or click "Simulate Hardware Verification").
4. Stage 1 succeeds:
   - Green banner appears: "Stage 1 Verified: Chief Investigator (admin@forensics.gov)".
   - 5-Minute countdown timer starts.
   - Stage 2 unlocks.
5. Enter passphrase (`password123`) and click "Complete Software Login & Enter Workstation".
6. Ticket is atomically consumed and you are redirected into the workstation dashboard (`/dashboard`).
7. Single-click logout: Clicking "Logout" in the navbar immediately terminates your session and revokes the hardware ticket.

---

## 9. Troubleshooting & Diagnostics

| Problem | Root Cause | Solution |
|---|---|---|
| **Port COM5 not found** | USB cable disconnected or ESP32 assigned a different COM number. | `hardware_serial_bridge.py` will automatically auto-detect CP210x/CH340/Espressif ports. If using custom port, set `$env:ESP32_COM_PORT="COM6"`. |
| **PermissionError: Access is denied** | Another program (Arduino IDE Serial Monitor, PuTTY, or browser Web Serial) is holding the COM port. | Close Arduino IDE Serial Monitor or terminate conflicting process before launching the bridge. |
| **HTTP 403 Forbidden** | `X-Bridge-Key` mismatch between bridge and backend. | Verify that `HARDWARE_BRIDGE_SECRET` in `server/.env` matches the secret used by `hardware_serial_bridge.py`. |
| **Two clicks required for Logout** | Stale hardware session polling re-authenticated user before token deletion. | Resolved: `logout()` now atomically invalidates tickets on server and applies anti-bounce guard. |
| **Hardware Ticket Expired** | More than 5 minutes elapsed between physical scan and software password entry. | Re-authenticate on the ESP32 hardware terminal or click "Rescan Hardware". |
