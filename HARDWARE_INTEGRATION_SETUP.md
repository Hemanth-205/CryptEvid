# CRYPTEVID — USB Hardware-to-Software Integration Setup Guide

This guide details the end-to-end setup, execution, and troubleshooting procedures for connecting the physical ESP32 forensic hardware terminal (MFRC522 RFID reader, R307 optical fingerprint scanner, OLED, LEDs, buzzer) over USB Serial on Windows to the CRYPTEVID full-stack platform.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────┐
│     ESP32 Hardware Terminal    │
│  (RFID MFRC522 + R307 Optical)  │
└────────────────┬────────────────┘
                 │ USB Cable (COM5 @ 115200 baud)
                 ▼
┌─────────────────────────────────┐
│   hardware_serial_bridge.py     │
│  - Non-blocking PySerial reader │
│  - Protocol sanity validation   │
│  - Debounce / deduplication     │
│  - Auto-reconnect & heartbeats  │
└────────────────┬────────────────┘
                 │ HTTP POST /api/hardware/events
                 │ Header: X-Bridge-Key: <SECRET>
                 ▼
┌─────────────────────────────────┐
│        FastAPI Backend          │
│         (Port 8000)             │
│  - Validates bridge auth key    │
│  - Normalizes RFID UID          │
│  - Resolves investigator in DB  │
│  - Distinguishes report vs verif│
│  - Dispatches WebSocket updates │
└───────┬─────────────────┬───────┘
        │                 │
        ▼                 ▼
┌──────────────┐   ┌───────────────────────────┐
│ MongoDB      │   │ React Dashboard (Vite)    │
│ - hardware_  │   │ - Live COM status badge   │
│   events     │   │ - Granted/Denied metrics  │
│ - audit_logs │   │ - Mapped investigator ID  │
└──────────────┘   │ - Real-time event feed    │
                   └───────────────────────────┘
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

> **Security Note**: A hardware `GRANTED` event is a telemetry report and **does not** automatically create an active browser session or bypass JWT role-based access controls. Identity verification is checked against registered records in MongoDB.

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

## 5. Identifying Your Windows COM Port

To verify which COM port your ESP32 is plugged into:

### Method A: Python PySerial Tool (Recommended)
```powershell
python -m serial.tools.list_ports
```
*Output will show detected USB UART bridges (e.g. `CP210x`, `CH340`, or `COM5`).*

### Method B: Windows PowerShell
```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.Class -eq "Ports" } | Select-Object FriendlyName, InstanceId
```

### Method C: Device Manager
1. Press `Win + X` and select **Device Manager**.
2. Expand **Ports (COM & LPT)**.
3. Locate **Silicon Labs CP210x USB to UART Bridge** or **USB-SERIAL CH340** (e.g., `COM5`).

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
You can configure the bridge through terminal environment variables without editing code:
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
*(Or ensure your MongoDB service or cloud URI is reachable).*

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
*The bridge will output structured logs showing connection to COM5 and background heartbeat dispatch.*

### Terminal 4: React Frontend Client
```powershell
cd c:\Users\Hari\Downloads\CRYPTEVID\client
corepack pnpm dev
```
*Access dashboard in browser at: `http://localhost:5173`*

---

## 8. Verifying Event Ingestion & Persistence

1. **Dashboard Verification**:
   - Open `http://localhost:5173/dashboard` or `http://localhost:5173/devices`.
   - The top status pill will display **`CONNECTED (COM5)`** with a pulsing green indicator.
2. **Scan RFID / Verify Fingerprint**:
   - Tap an authorized RFID card (`10 5B 96 5C` or `C0 A3 CF 54`) on the MFRC522 sensor.
   - The ESP32 sends `CRYPTEVID|1|GRANTED|UID=10 5B 96 5C|REASON=AUTH_SUCCESS`.
   - The bridge forwards the event to `http://127.0.0.1:8000/api/hardware/events`.
3. **Verify FastAPI & MongoDB Log**:
   - Query the REST API directly:
     ```powershell
     curl http://127.0.0.1:8000/api/hardware/events
     ```
   - The record appears in `hardware_events` and the forensic tamper-evident chain of custody in `audit_logs`:
     ```json
     {
       "action": "hardware_auth_granted",
       "device_id": "ESP32_USB",
       "details": "ESP32 USB Event: GRANTED | UID=10 5B 96 5C | Reason=AUTH_SUCCESS | Identity Verified=True | Notes=Identity verified: Chief Investigator (Admin) (admin@forensics.gov)"
     }
     ```

---

## 9. Troubleshooting & Diagnostics

| Problem | Root Cause | Solution |
|---|---|---|
| **Port COM5 not found** | USB cable disconnected or ESP32 assigned a different COM number. | Check Device Manager for actual port (e.g. `COM4`). Run `$env:ESP32_COM_PORT="COM4"; python hardware_serial_bridge.py`. |
| **PermissionError: Access is denied** | Another program (Arduino IDE Serial Monitor, PuTTY, or another bridge) is holding the COM port. | Close Arduino IDE Serial Monitor or terminate conflicting process before launching the bridge. |
| **HTTP 403 Forbidden** | `X-Bridge-Key` mismatch between bridge and backend. | Verify that `HARDWARE_BRIDGE_SECRET` in `server/.env` matches the secret used by `hardware_serial_bridge.py`. |
| **Dashboard shows DISCONNECTED** | Bridge is not running or has not sent a heartbeat in >12s. | Launch `hardware_serial_bridge.py`. The dashboard will automatically switch to `CONNECTED` on the next polling cycle (within 3s). |
| **Identity shows UNVERIFIED** | The scanned RFID card is not registered in the database. | The event is safely recorded, but unmapped. Register the RFID UID in MongoDB for the intended investigator using the user profile settings. |
