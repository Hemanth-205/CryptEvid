#!/usr/bin/env python3
"""
CRYPTEVID ESP32 USB Serial Bridge Compatibility Wrapper
--------------------------------------------------------
Delegates execution to the production 'hardware_serial_bridge.py' module.
"""

from hardware_serial_bridge import main

if __name__ == "__main__":
    main()
