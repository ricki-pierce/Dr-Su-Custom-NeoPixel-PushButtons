from pylsl import StreamInfo, StreamOutlet
import time

# ── Create the LSL outlet ──────────────────────────────────────────────────────
info = StreamInfo(
    name='Trigger',
    type='Markers',
    channel_count=1,
    channel_format='int32',
    source_id='ButtonController'
)
outlet = StreamOutlet(info)
print("✅ LSL Trigger stream created successfully")
print("   --> Now open Aurora, load your probe config, and start recording")
print("   --> Then press ENTER here to begin the test sequence\n")
input("Press ENTER when Aurora is recording...")

# ── Marker definitions ─────────────────────────────────────────────────────────
MARKER_BUTTON_SCHEDULED   = 1
MARKER_BUTTON_ILLUMINATED = 2
MARKER_BUTTON_PRESSED     = 4

def send_marker(marker_value, label):
    outlet.push_sample([marker_value])
    print(f"   📍 Sent marker {marker_value} ({label})")

# ── Test sequence ──────────────────────────────────────────────────────────────
print("\n🔵 Starting test sequence — watch for markers in Aurora...\n")

# Round 1
print("--- Trial 1 ---")
send_marker(MARKER_BUTTON_SCHEDULED, "Button Scheduled")
time.sleep(1)
send_marker(MARKER_BUTTON_ILLUMINATED, "Button Illuminated")
time.sleep(0.5)
send_marker(MARKER_BUTTON_PRESSED, "Button Pressed")
time.sleep(2)

# Round 2
print("--- Trial 2 ---")
send_marker(MARKER_BUTTON_SCHEDULED, "Button Scheduled")
time.sleep(1)
send_marker(MARKER_BUTTON_ILLUMINATED, "Button Illuminated")
time.sleep(0.5)
send_marker(MARKER_BUTTON_PRESSED, "Button Pressed")
time.sleep(2)

# Round 3
print("--- Trial 3 ---")
send_marker(MARKER_BUTTON_SCHEDULED, "Button Scheduled")
time.sleep(1)
send_marker(MARKER_BUTTON_ILLUMINATED, "Button Illuminated")
time.sleep(0.5)
send_marker(MARKER_BUTTON_PRESSED, "Button Pressed")
time.sleep(2)

print("\n✅ Test sequence complete!")
print("   --> Check Aurora's timeline for 9 markers total:")
print("       3x marker 1 (Scheduled)")
print("       3x marker 2 (Illuminated)")
print("       3x marker 4 (Pressed)")
print("   --> If you see all 9, your LSL connection is working correctly\n")
```

---

## What to Look for in Aurora

When the test runs, you should see markers drop into the Aurora recording timeline in this repeating pattern:
```
1 -----(1s)----- 2 --(0.5s)-- 4 --(2s)-- 1 -----(1s)----- 2 ...
