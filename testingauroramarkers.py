from pylsl import StreamInfo, StreamOutlet
import time

# Aurora is listening for triggers on a stream called 'NIRStarTriggers'
# We create an outlet with that exact name/type so Aurora picks it up

info = StreamInfo(
    name='NIRStarTriggers',   # ← must match exactly what Aurora expects
    type='Triggers',           # ← must match exactly
    channel_count=1,
    nominal_srate=0,           # irregular/event-based
    channel_format='int32',
    source_id='my_experiment'
)

outlet = StreamOutlet(info)

print("Stream created. Waiting 3 seconds for Aurora to detect it...")
time.sleep(3)

print("Sending trigger 1...")
outlet.push_sample([1])
time.sleep(2)

print("Sending trigger 2...")
outlet.push_sample([2])
time.sleep(2)

print("Sending trigger 3...")
outlet.push_sample([3])
time.sleep(2)

print("Done — check Aurora for markers!")
