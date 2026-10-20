"""
CRYPTEVID ESP32 USB Serial Bridge
---------------------------------
Forwards USB Serial data from a physically wired ESP32 to the deployed cloud platform.
Works with any deployed backend (default: https://cryptevid-final.onrender.com).

Usage:
    pip install pyserial requests
    python esp32_serial_bridge.py
"""

import sys
import time
import json
import re
import threading
import urllib.request
import urllib.error

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("[ERROR] 'pyserial' is not installed.")
    print("Please install it by running: pip install pyserial")
    sys.exit(1)

BACKEND_URL = "https://cryptevid-final.onrender.com"
DEVICE_ID = "ESP32_WIFI"
MAC_ADDR = "DA:51:53:00:95:7C"
BAUD_RATE = 115200

def post_json(endpoint, data):
    url = f"{BACKEND_URL.rstrip('/')}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return None, str(e)

def heartbeat_worker(stop_event):
    while not stop_event.is_set():
        code, resp = post_json("/api/hardware/heartbeat", {
            "device": DEVICE_ID,
            "macAddress": MAC_ADDR,
            "firmwareVersion": "v1.0.4-forensic-usb"
        })
        if code in (200, 201):
            print(f"[HEARTBEAT] Node status: ONLINE on dashboard ({BACKEND_URL})")
        else:
            print(f"[HEARTBEAT] Warning: {code} - {resp}")
        stop_event.wait(15.0)

def find_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None
    for p in ports:
        desc = (p.description or "").lower()
        if "cp210" in desc or "ch340" in desc or "ch910" in desc or "usb" in desc or "uart" in desc:
            return p.device
    return ports[0].device

def main():
    print("=" * 65)
    print("  CRYPTEVID — Physical ESP32 USB Hardware Bridge")
    print("=" * 65)
    print(f"Target Backend: {BACKEND_URL}")
    print(f"Device Node:    {DEVICE_ID}")
    
    port_name = find_esp32_port()
    if not port_name:
        print("[!] No USB COM ports detected. Please plug in your ESP32 cable.")
        return

    print(f"[*] Detected ESP32 on port: {port_name} at {BAUD_RATE} baud.")
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"[!] Could not open port {port_name}: {e}")
        return

    print(f"[✓] Connected to {port_name}! Starting background heartbeat monitor...")
    stop_event = threading.Event()
    t = threading.Thread(target=heartbeat_worker, args=(stop_event,), daemon=True)
    t.start()

    print("\n[*] Ready for scans. Tap an RFID card or place a finger on the sensor...\n")

    try:
        while True:
            raw_line = ser.readline()
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            print(f"[ESP32 Serial]: {line}")

            # Check for RFID UID (e.g. "10 5B 96 5C" or "105B965C" or "C0 A3 CF 54")
            hex_match = re.search(r'(?:UID:?\s*)?([0-9a-fA-F]{2}[\s:-]?[0-9a-fA-F]{2}[\s:-]?[0-9a-fA-F]{2}[\s:-]?[0-9a-fA-F]{2})', line)
            if hex_match:
                rfid_clean = re.sub(r'[\s:-]', '', hex_match.group(1)).upper()
                if rfid_clean in ("105B965C", "C0A3CF54"):
                    print(f"\n[★] Valid RFID Scanned: {rfid_clean} -> Sending to cloud platform...")
                    code, resp = post_json("/api/hardware/authenticate", {
                        "deviceId": DEVICE_ID,
                        "rfid": rfid_clean,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    })
                    print(f"[*] Cloud Response [{code}]: {resp}\n")

            # Check for Fingerprint ID (e.g. "Fingerprint ID: 1", "Found ID #1", "FID: 2")
            fp_match = re.search(r'(?:fingerprint|id|fid|found id #?)\s*[:#]?\s*([12])\b', line, re.IGNORECASE)
            if fp_match:
                fp_id = int(fp_match.group(1))
                print(f"\n[★] Valid Fingerprint Verified: ID #{fp_id} -> Sending to cloud platform...")
                code, resp = post_json("/api/hardware/authenticate", {
                    "deviceId": DEVICE_ID,
                    "fingerprintId": fp_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
                print(f"[*] Cloud Response [{code}]: {resp}\n")

    except KeyboardInterrupt:
        print("\n[*] Stopping serial bridge...")
    finally:
        stop_event.set()
        ser.close()
        print("[*] Bridge closed.")

if __name__ == "__main__":
    main()
