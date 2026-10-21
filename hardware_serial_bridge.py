#!/usr/bin/env python3
"""
CRYPTEVID — USB Hardware-to-Software Serial Bridge
=================================================
Connects an ESP32 forensic ingestion node (MFRC522 RFID reader, R307 fingerprint
sensor, OLED, LEDs, buzzer) connected via USB Serial to the CRYPTEVID FastAPI backend.

Protocol format parsed:
    CRYPTEVID|1|GRANTED|UID=<RFID_UID>|REASON=<REASON_CODE>
    CRYPTEVID|1|DENIED|UID=<RFID_UID>|REASON=<REASON_CODE>

Environment Variables:
    ESP32_COM_PORT: Serial COM port (default: COM5)
    ESP32_BAUD_RATE: Baud rate (default: 115200)
    FASTAPI_URL: Backend base URL (default: http://127.0.0.1:8000)
    HARDWARE_BRIDGE_SECRET: Bridge authentication key (default: cryptevid_usb_bridge_secret_dev)
    DEVICE_ID: Hardware identifier (default: ESP32_USB)
    HEARTBEAT_INTERVAL: Seconds between heartbeats (default: 5.0)
    DEDUP_WINDOW_SECONDS: Duplicate suppression window in seconds (default: 2.0)
    RECONNECT_INTERVAL: Seconds between reconnection attempts (default: 3.0)
"""

import os
import sys
import time
import json
import re
import uuid
import signal
import logging
import threading
from typing import Optional, Dict, Any, Tuple
import urllib.request
import urllib.error

# Setup Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [BRIDGE] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("hardware_serial_bridge")

# Configuration via Environment Variables
COM_PORT = os.getenv("ESP32_COM_PORT", "COM5")
BAUD_RATE = int(os.getenv("ESP32_BAUD_RATE", "115200"))
BRIDGE_SECRET = os.getenv("HARDWARE_BRIDGE_SECRET", "cryptevid_usb_bridge_secret_dev")
DEVICE_ID = os.getenv("DEVICE_ID", "ESP32_USB")
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "5.0"))
DEDUP_WINDOW_SECONDS = float(os.getenv("DEDUP_WINDOW_SECONDS", "2.0"))
RECONNECT_INTERVAL = float(os.getenv("RECONNECT_INTERVAL", "3.0"))

def resolve_fastapi_url() -> str:
    """Automatically resolve target backend: explicit ENV -> local 8000 -> cloud Render."""
    explicit = os.getenv("FASTAPI_URL")
    if explicit:
        return explicit.rstrip("/")

    # Check if local FastAPI server is running
    local_url = "http://127.0.0.1:8000"
    try:
        req = urllib.request.Request(f"{local_url}/health", headers={"User-Agent": "CRYPTEVID-Bridge"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.getcode() == 200:
                return local_url
    except Exception:
        pass

    # Default to production cloud deployment
    return "https://cryptevid-final.onrender.com"

FASTAPI_URL = resolve_fastapi_url()

LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".hardware_bridge.lock")

# Protocol Regex
# Exact match for: CRYPTEVID|1|STATUS|UID=...|REASON=...
PROTOCOL_REGEX = re.compile(
    r"^CRYPTEVID\|(\d+)\|(GRANTED|DENIED)\|UID=([^|\r\n]+)\|REASON=([^|\r\n]+)$"
)

def parse_serial_message(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse and validate a raw newline-terminated serial message from the ESP32.
    Returns parsed dictionary if valid, or None if malformed or boot noise.
    """
    if not line:
        return None

    stripped = line.strip()
    if not stripped:
        return None

    match = PROTOCOL_REGEX.match(stripped)
    if not match:
        # Boot messages, initialization text, or malformed noise
        if stripped.startswith("CRYPTEVID"):
            logger.warning(f"Malformed protocol packet discarded: '{stripped}'")
        else:
            logger.debug(f"Ignored non-protocol serial message: '{stripped}'")
        return None

    ver_str, status, uid, reason = match.groups()
    try:
        protocol_version = int(ver_str)
        if not (1 <= protocol_version <= 10):
            logger.warning(f"Discarding message with unsupported protocol version ({protocol_version})")
            return None
    except ValueError:
        return None

    # Length and character sanity validation
    uid_clean = uid.strip()
    reason_clean = reason.strip()

    if not (1 <= len(uid_clean) <= 64):
        logger.warning(f"Discarding message with invalid UID length ({len(uid_clean)}): '{uid_clean}'")
        return None

    if not (1 <= len(reason_clean) <= 128):
        logger.warning(f"Discarding message with invalid Reason length ({len(reason_clean)}): '{reason_clean}'")
        return None

    return {
        "event_id": str(uuid.uuid4()),
        "protocol_version": protocol_version,
        "status": status,
        "uid": uid_clean,
        "reason": reason_clean,
        "device_id": DEVICE_ID,
        "raw_message": stripped,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

class HardwareSerialBridge:
    def __init__(self):
        self.running = True
        self.serial_port: Optional[Any] = None
        self.connected = False
        self.active_port = COM_PORT
        self.error_message: Optional[str] = None
        self.last_seen_event: Optional[Tuple[str, str, str]] = None
        self.last_seen_time: float = 0.0
        self.lock = threading.Lock()
        self.heartbeat_thread: Optional[threading.Thread] = None

    def acquire_singleton_lock(self) -> bool:
        """Prevent multiple processes from opening the same serial port simultaneously."""
        try:
            if os.path.exists(LOCK_FILE):
                try:
                    with open(LOCK_FILE, "r") as f:
                        old_pid = int(f.read().strip())
                    # Check if process is still alive
                    if sys.platform == "win32":
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        SYNCHRONIZE = 0x00100000
                        process = kernel32.OpenProcess(SYNCHRONIZE, False, old_pid)
                        if process != 0:
                            kernel32.CloseHandle(process)
                            logger.error(f"Another instance of hardware_serial_bridge is running (PID: {old_pid}). Exiting.")
                            return False
                    else:
                        os.kill(old_pid, 0)
                        logger.error(f"Another instance of hardware_serial_bridge is running (PID: {old_pid}). Exiting.")
                        return False
                except (ValueError, OSError):
                    pass # Stale lock file

            with open(LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            logger.warning(f"Could not write singleton lockfile: {e}")
            return True

    def release_singleton_lock(self):
        """Release the pid lockfile on shutdown."""
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass

    def find_esp32_port(self) -> Optional[Tuple[str, str]]:
        """
        Scan and auto-detect ESP32 serial communication ports.
        1. Filters out Bluetooth serial ports (BTHENUM).
        2. Detects Silicon Labs CP210x (VID 0x10C4), WCH CH340 (VID 0x1A86),
           Espressif Native USB (VID 0x303A), and FTDI (VID 0x0403).
        3. Falls back to user-configured COM_PORT if present.
        Returns: Tuple of (port_device, description) or None.
        """
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return None

        # Filter out Bluetooth virtual ports
        valid_ports = []
        for p in ports:
            hwid = (p.hwid or "").upper()
            desc = (p.description or "").upper()
            if "BTHENUM" in hwid or "BLUETOOTH" in desc:
                continue
            valid_ports.append(p)

        if not valid_ports:
            return None

        # Check for configured port first if it's available and not Bluetooth
        for p in valid_ports:
            if p.device.upper() == COM_PORT.upper():
                return p.device, p.description

        # Known ESP32 USB-to-UART Bridge Vendor IDs
        ESP_VIDS = {
            0x10C4: "Silicon Labs CP210x (ESP32)",
            0x1A86: "WCH CH340 (ESP32)",
            0x303A: "Espressif Native USB (ESP32-S2/S3/C3)",
            0x0403: "FTDI FT232 (ESP32)",
            0x067B: "Prolific PL2303"
        }

        # Check VID matches
        for p in valid_ports:
            if p.vid in ESP_VIDS:
                return p.device, f"{ESP_VIDS[p.vid]} ({p.device})"

        # Check description patterns
        patterns = ["CP210", "CH340", "CH341", "ESPRESSIF", "UART", "USB SERIAL", "USB-SERIAL"]
        for p in valid_ports:
            desc_upper = (p.description or "").upper()
            if any(k in desc_upper for k in patterns):
                return p.device, p.description

        # Return first non-Bluetooth USB serial candidate
        candidate = valid_ports[0]
        return candidate.device, candidate.description

    def send_http_request(self, endpoint: str, data: Dict[str, Any]) -> Tuple[Optional[int], Optional[Dict[str, Any]], str]:
        """Send an authenticated HTTP POST to FastAPI backend."""
        url = f"{FASTAPI_URL}{endpoint}"
        body_bytes = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Bridge-Key": BRIDGE_SECRET,
                "User-Agent": "CRYPTEVID-Hardware-Bridge/1.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                code = resp.getcode()
                raw_body = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(raw_body)
                except Exception:
                    parsed = None
                return code, parsed, raw_body
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return e.code, None, err_body
        except Exception as e:
            return None, None, str(e)

    def heartbeat_worker(self):
        """Periodically broadcast bridge health and connection telemetry to FastAPI."""
        logger.info(f"Bridge heartbeat worker started (Interval: {HEARTBEAT_INTERVAL}s)")
        while self.running:
            with self.lock:
                status_str = "Connected" if self.connected else ("Error" if self.error_message else "Disconnected")
                err_msg = self.error_message if not self.connected else None
                current_port = self.active_port

            code, _, err = self.send_http_request("/api/hardware/bridge-heartbeat", {
                "port": current_port,
                "status": status_str,
                "baud_rate": BAUD_RATE,
                "device_id": DEVICE_ID,
                "error_message": err_msg
            })
            if code not in (200, 201):
                logger.debug(f"Heartbeat dispatch warning [{code}]: {err}")
            
            # Sleep in small increments for quick responsive shutdown
            slept = 0.0
            while self.running and slept < HEARTBEAT_INTERVAL:
                time.sleep(0.5)
                slept += 0.5

    def is_duplicate(self, status: str, uid: str, reason: str) -> bool:
        """Sliding window debounce check to suppress hardware sensor flutter."""
        now = time.time()
        event_tuple = (status, uid, reason)
        if self.last_seen_event == event_tuple:
            if (now - self.last_seen_time) < DEDUP_WINDOW_SECONDS:
                return True
        self.last_seen_event = event_tuple
        self.last_seen_time = now
        return False

    def forward_event(self, event: Dict[str, Any]):
        """Forward a validated hardware event to the FastAPI backend."""
        status = event["status"]
        uid = event["uid"]
        reason = event["reason"]

        if self.is_duplicate(status, uid, reason):
            logger.debug(f"Suppressed duplicate event within {DEDUP_WINDOW_SECONDS}s: UID={uid} Status={status}")
            return

        logger.info(f"Forwarding {status} event: UID='{uid}' Reason='{reason}' -> FastAPI")
        code, parsed, raw = self.send_http_request("/api/hardware/events", event)

        if code in (200, 201):
            verified = parsed.get("is_identity_verified", False) if parsed else False
            inv = parsed.get("mapped_investigator") if parsed else None
            inv_name = inv.get("name") if inv else "Unknown / Unmapped"
            ticket_id = parsed.get("ticket_id") if parsed else None
            logger.info(f"[✓ SUCCESS] Backend Accepted: Verified={verified} | Investigator={inv_name} | Stage1 Ticket={ticket_id}")
        elif code == 403:
            logger.error("[!] Authentication Rejected: Bridge secret mismatch (Check HARDWARE_BRIDGE_SECRET)")
        elif code is None:
            logger.error(f"[!] Network Error: Unable to reach FastAPI at {FASTAPI_URL}: {raw}")
        else:
            logger.warning(f"[!] Server returned HTTP {code}: {raw}")

    def run(self):
        """Main lifecycle loop with auto-detection, auto-reconnection and exception resilience."""
        if not self.acquire_singleton_lock():
            return

        logger.info("=" * 65)
        logger.info("  CRYPTEVID — Physical ESP32 USB Hardware Bridge (Two-Stage)")
        logger.info("=" * 65)
        logger.info(f"Preferred Port:   {COM_PORT}")
        logger.info(f"Baud Rate:        {BAUD_RATE}")
        logger.info(f"Target FastAPI:   {FASTAPI_URL}")
        logger.info(f"Ingestion Device: {DEVICE_ID}")

        # Try importing pyserial
        try:
            import serial
            import serial.tools.list_ports
        except ImportError:
            logger.error("The 'pyserial' library is required. Install with: pip install pyserial")
            self.release_singleton_lock()
            return

        # Start telemetry heartbeat worker
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()

        while self.running:
            # 1. Auto-detect or verify COM port (filtering out Bluetooth virtual links)
            detected = self.find_esp32_port()
            if not detected:
                with self.lock:
                    self.connected = False
                    self.error_message = "No ESP32 USB UART device found. Connect USB cable to PC."
                logger.warning(f"No ESP32 device detected (Bluetooth ports ignored). Retrying in {RECONNECT_INTERVAL}s...")
                time.sleep(RECONNECT_INTERVAL)
                continue

            target_port, port_desc = detected
            with self.lock:
                self.active_port = target_port

            if target_port != COM_PORT:
                logger.info(f"[AUTO-DETECT] ESP32 found on {target_port} ({port_desc})")

            # 2. Attempt to open serial connection
            logger.info(f"Opening serial port {target_port} at {BAUD_RATE} baud...")
            try:
                self.serial_port = serial.Serial(
                    port=target_port,
                    baudrate=BAUD_RATE,
                    timeout=1.0,
                    write_timeout=1.0
                )
                # Flush initial buffer noise
                self.serial_port.reset_input_buffer()
                with self.lock:
                    self.connected = True
                    self.error_message = None
                logger.info(f"[✓ CONNECTED] Successfully bound to {target_port}. Ready for RFID / Fingerprint scans.")
            except serial.SerialException as se:
                with self.lock:
                    self.connected = False
                    err_str = str(se)
                    if "PermissionError" in err_str or "Access is denied" in err_str:
                        self.error_message = f"Port {target_port} is busy or opened by another application (e.g. Arduino IDE or browser)."
                    else:
                        self.error_message = f"Failed to open port {target_port}: {err_str}"
                logger.error(f"{self.error_message}. Retrying in {RECONNECT_INTERVAL}s...")
                time.sleep(RECONNECT_INTERVAL)
                continue
            except Exception as e:
                with self.lock:
                    self.connected = False
                    self.error_message = f"Unexpected serial error on {target_port}: {e}"
                logger.error(f"{self.error_message}. Retrying in {RECONNECT_INTERVAL}s...")
                time.sleep(RECONNECT_INTERVAL)
                continue

            # 3. Read stream loop
            try:
                while self.running and self.serial_port and self.serial_port.is_open:
                    try:
                        raw_bytes = self.serial_port.readline()
                    except serial.SerialException as se:
                        logger.warning(f"Serial read exception on {target_port}: {se}")
                        break

                    if not raw_bytes:
                        continue

                    try:
                        line = raw_bytes.decode("utf-8", errors="replace").strip()
                    except Exception:
                        continue

                    if not line:
                        continue

                    # Parse message
                    parsed_event = parse_serial_message(line)
                    if parsed_event:
                        self.forward_event(parsed_event)

            except Exception as loop_err:
                logger.error(f"Unexpected error in serial read loop: {loop_err}")
            finally:
                with self.lock:
                    self.connected = False
                if self.serial_port:
                    try:
                        self.serial_port.close()
                    except Exception:
                        pass
                    self.serial_port = None
                logger.warning(f"Disconnected from {target_port}. Reconnecting...")
                if self.running:
                    time.sleep(RECONNECT_INTERVAL)

        # Clean shutdown
        self.release_singleton_lock()
        logger.info("Bridge cleanly terminated.")

    def stop(self):
        """Signal bridge to shut down cleanly."""
        logger.info("Received termination signal. Shutting down...")
        self.running = False
        with self.lock:
            self.connected = False
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass

def main():
    bridge = HardwareSerialBridge()

    def signal_handler(sig, frame):
        bridge.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.stop()

if __name__ == "__main__":
    main()
