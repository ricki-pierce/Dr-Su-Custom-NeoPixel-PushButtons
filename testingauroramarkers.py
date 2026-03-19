from pylsl import StreamInfo, StreamOutlet, resolve_streams
import time

# First, let's see what LSL streams Aurora is already broadcasting
print("Searching for existing LSL streams (Aurora should show up here)...")
streams = resolve_streams(wait_time=3.0)

if streams:
    for s in streams:
        print(f"  Found stream: name='{s.name()}' type='{s.type()}' source='{s.source_id()}'")
else:
    print("  No LSL streams found!")

print()

# Now create our marker outlet
print("Creating marker outlet...")
info = StreamInfo(
    name='MyMarkerStream',
    type='Markers',
    channel_count=1,
    nominal_srate=0,
    channel_format='int32',
    source_id='my_experiment'
)
outlet = StreamOutlet(info)
print("Outlet created. Waiting 3 seconds for Aurora to detect it...")
time.sleep(3)

print("Sending marker 1...")
outlet.push_sample([1])
time.sleep(2)
print("Sending marker 2...")
outlet.push_sample([2])
time.sleep(2)

print("Done — check Aurora!")
