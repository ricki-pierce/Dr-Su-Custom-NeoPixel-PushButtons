"""
=====================================
Force Plate Trigger Test — Spacebar
=====================================
Press SPACEBAR to send a TTL pulse to the AMTI force plate via USB2TTL8.
Press ESC to quit.

SETUP:
- USB2TTL8 connected to laptop via USB
- RCA center wire on USB2TTL8 pin 2 (D0)
- RCA ground wire on USB2TTL8 pin 18 (GND)
- RCA plug into AMTI force plate sync input
- NetForce open and recording, trigger set to External Source / Rising Edge

INSTALL DEPENDENCIES:
    pip install pyserial keyboard
"""

import serial
import serial.tools.list_ports
import time
import keyboard  # For spacebar detection

# =====================================================
#  CONFIGURATION — change COM port to match your system
# =====================================================
COM_PORT = "COM4"   # <<< Change this to your USB2TTL8 COM port
BAUD_RATE = 115200
PULSE_DURATION = 0.01  # 10ms pulse — long enough for NetForce to catch it

# =====================================================
#  HOW TO FIND YOUR COM PORT:
#  - Open Device Manager on Windows
#  - Look under "Ports (COM & LPT)"
#  - Find the USB2TTL8 / USB Serial Device
#  - Note the COM number (e.g. COM4, COM5) and set it above
# =====================================================

def find_usb2ttl8():
    """Lists all available COM ports to help identify the USB2TTL8."""
    ports = serial.tools.list_ports.comports()
    print("\nAvailable COM ports:")
    for p in ports:
        print(f"  {p.device} — {p.description}")
    print()

def send_trigger(ser):
    """
    Sends a rising-edge TTL pulse on pin 2 (D0, bit 0):
    - Write 0x01 to raise D0 high (3.3V) — rising edge
    - Wait pulse duration
    - Write 0x00 to bring D0 low again (0V)
    """
    ser.write(bytes([0x01]))   # D0 HIGH — rising edge triggers NetForce
    time.sleep(PULSE_DURATION)
    ser.write(bytes([0x00]))   # D0 LOW — return to idle
    print(f"  Trigger sent at {time.strftime('%H:%M:%S')}")

# =====================================================
#  MAIN
# =====================================================

find_usb2ttl8()  # Print available ports on startup

print(f"Connecting to USB2TTL8 on {COM_PORT}...")
try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    time.sleep(1)  # Let port settle
    ser.write(bytes([0x00]))  # Make sure all pins start LOW
    print(f"Connected. All pins set LOW.\n")
except serial.SerialException as e:
    print(f"\nERROR: Could not open {COM_PORT}.\n{e}")
    print("Check Device Manager for the correct COM port and update COM_PORT in this script.")
    exit(1)

print("=" * 45)
print("  Ready. Press SPACEBAR to send trigger.")
print("  Press ESC to quit.")
print("=" * 45 + "\n")

trigger_count = 0

try:
    while True:
        if keyboard.is_pressed("space"):
            trigger_count += 1
            print(f"[{trigger_count}] Spacebar pressed —", end=" ")
            send_trigger(ser)
            time.sleep(0.3)  # Debounce — prevent repeated triggers from one press

        if keyboard.is_pressed("esc"):
            print("\nESC pressed — exiting.")
            break

        time.sleep(0.01)  # Small sleep to avoid hammering the CPU

finally:
    ser.write(bytes([0x00]))  # Ensure all pins LOW on exit
    ser.close()
    print("Serial port closed. Done.")
