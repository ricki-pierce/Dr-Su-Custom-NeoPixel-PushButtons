#i THINK all these codes are fine as is


#this script lists out all the streams in teh file and includes how many data samples are in the file. once you identify the right ones, ID teh streams appropriately in 
# # lines 20 nd 21 to get the time stamps of where the events occur in the file.
# import pyxdf

# streams, header = pyxdf.load_xdf(r'C:\Users\WanChunSu\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf')
# # See what streams are in the file
# for i, stream in enumerate(streams):
#     name = stream['info']['name'][0]
#     stype = stream['info']['type'][0]
#     n_channels = stream['info']['channel_count'][0]
#     srate = stream['info']['nominal_srate'][0]
#     n_samples = len(stream['time_stamps'])
#     print(f"Stream {i}: '{name}' | type={stype} | channels={n_channels} | srate={srate}Hz | samples={n_samples}")

# import pyxdf
# import numpy as np

# streams, header = pyxdf.load_xdf(r'C:\Users\WanChunSu\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf')

# # Grab streams by index
# eeg_stream    = streams[1]  # LiveAmpSN-055602-0308
# marker_stream = streams[0]  # NIRStarTriggers

# eeg_times     = eeg_stream['time_stamps']
# marker_labels = [m[0] for m in marker_stream['time_series']]
# marker_times  = marker_stream['time_stamps']

# print(f"EEG duration: {eeg_times[0] - eeg_times[1]:.2f}s  |  {len(eeg_times)} samples")
# print(f"Found {len(marker_labels)} markers:\n")

# for label, t in zip(marker_labels, marker_times):
#     idx = np.searchsorted(eeg_times, t)
#     rel = t - eeg_times[0]
#     print(f"  [{idx:6d}]  {rel:8.3f}s  →  '{label}'")

# #this eeg analysis code tells you for the 80 trials, at what time the light came on, when the button was pressed, diff bw those 2, and if it was a HIT or MISS
import pyxdf
import numpy as np

streams, header = pyxdf.load_xdf(r'C:\Users\WanChunSu\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf')

marker_stream = streams[0]
eeg_stream    = streams[1]

eeg_times    = eeg_stream['time_stamps']
raw_markers  = marker_stream['time_series']
marker_times = marker_stream['time_stamps']

# Separate by event code (channel 2)
light_commanded = []  # code 1
light_on        = []  # code 2
button_press    = []  # code 4

for m, t in zip(raw_markers, marker_times):
    code = int(m[0])
    idx  = np.searchsorted(eeg_times, t)
    rel  = t - eeg_times[0]
    entry = (idx, rel, t)
    if code == 1:
        light_commanded.append(entry)
    elif code == 2:
        light_on.append(entry)
    elif code == 4:
        button_press.append(entry)

print(header['info']['datetime'][0])  # UTC datetime string
print(f"Light commanded (1): {len(light_commanded)} events")
print(f"Light on       (2): {len(light_on)} events")
print(f"Button press   (4): {len(button_press)} events")

print("\n--- Button Presses ---")
for idx, rel, t in button_press:
    print(f"  [{idx:6d}]  {rel:8.3f}s")

# Pair each button press with the most recent light_on event before it
print("Trial | Light On (s) | Button Press (s) | RT (ms) | Status")
print("-" * 65)

trial = 0
press_iter = iter(button_press)
next_press = next(press_iter, None)

for i, (cmd_idx, cmd_rel, cmd_t) in enumerate(light_commanded):
    # Find the light_on event for this trial
    # (the first code-2 event at or after this command)
    on_event = next((e for e in light_on if e[2] >= cmd_t), None)
    
    # Find the button press for this trial
    # (first code-4 event after light turned on, before next command)
    next_cmd_t = light_commanded[i+1][2] if i+1 < len(light_commanded) else float('inf')
    
    if on_event:
        press = next((e for e in button_press if on_event[2] <= e[2] < next_cmd_t), None)
    else:
        press = None

    if press and on_event:
        rt_ms = (press[2] - on_event[2]) * 1000
        print(f"  {i+1:3d} | {on_event[1]:10.3f}s  | {press[1]:14.3f}s  | {rt_ms:6.1f}ms | HIT")
    else:
        print(f"  {i+1:3d} | {on_event[1] if on_event else '?':>10}   | {'—':>14}   | {'—':>8} | MISS")


actual_srate = len(eeg_times) / (eeg_times[-1] - eeg_times[0])
print(f"Nominal srate: {eeg_stream['info']['nominal_srate'][0]} Hz")
print(f"Actual srate:  {actual_srate:.4f} Hz")


# #this script lists the streams found in the file and then prints the first 20 marker values from those streams with content
# import pyxdf
# import numpy as np

# streams, header = pyxdf.load_xdf(r'C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf')

# print("Streams found in this file:")
# for i, s in enumerate(streams):
#     info = s['info']
#     name = info['name'][0]
#     stype = info['type'][0] if info['type'][0] is not None else 'None'
#     n_samples = len(s['time_stamps'])
#     n_channels = info['channel_count'][0]
#     print(f"  [{i}] name={name!r}, type={stype!r}, channels={n_channels}, samples={n_samples}")

# # EEG stream: pick by type, skipping None safely
# eeg_stream = None
# for s in streams:
#     stype = s['info']['type'][0]
#     if stype is not None and stype.lower() == 'eeg':
#         eeg_stream = s
#         break

# if eeg_stream is None:
#     raise RuntimeError("No EEG stream found.")

# print(f"\nUsing EEG stream: {eeg_stream['info']['name'][0]} ({len(eeg_stream['time_stamps'])} samples)")

# # Inspect BOTH candidate marker streams so you can tell which one has your codes
# for name in ('BV_Markers', 'Trigger'):
#     for s in streams:
#         if s['info']['name'][0] == name:
#             vals = [row[0] for row in s['time_series'][:20]]  # first 20 entries
#             print(f"\n{name} — first 20 marker values: {vals}")

# #this code tells you how many of each event occurred in the eeg file
# import pyxdf
# import numpy as np

# streams, header = pyxdf.load_xdf(r'C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf')

# eeg_stream = None
# marker_stream = None
# for s in streams:
#     stype = s['info']['type'][0]
#     name = s['info']['name'][0]
#     if stype is not None and stype.lower() == 'eeg':
#         eeg_stream = s
#     if name == 'Trigger':
#         marker_stream = s

# if eeg_stream is None or marker_stream is None:
#     raise RuntimeError("Could not find EEG or Trigger marker stream.")

# eeg_times    = eeg_stream['time_stamps']
# raw_markers  = marker_stream['time_series']
# marker_times = marker_stream['time_stamps']

# print(f"Using EEG stream: {eeg_stream['info']['name'][0]} ({len(eeg_times)} samples)")
# print(f"Using Marker stream: {marker_stream['info']['name'][0]} ({len(marker_times)} samples)")

# light_commanded = []
# light_on        = []
# button_press    = []

# for m, t in zip(raw_markers, marker_times):
#     code = int(m[0])          # <-- was m[1], fixed to m[0]
#     idx  = np.searchsorted(eeg_times, t)
#     rel  = t - eeg_times[0]
#     entry = (idx, rel, t)
#     if code == 1:
#         light_commanded.append(entry)
#     elif code == 2:
#         light_on.append(entry)
#     elif code == 4:
#         button_press.append(entry)

# print(f"Light commanded (1): {len(light_commanded)} events")
# print(f"Light on       (2): {len(light_on)} events")
# print(f"Button press   (4): {len(button_press)} events")





#this script visualizes theeeg streams with the overlaid markers on top
import pyxdf
import mne

streams, header = pyxdf.load_xdf(r"C:\Users\WanChunSu\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf")

# Find the EEG stream (check stream['info']['type'])
for s in streams:
    print(s['info']['name'], s['info']['type'])

eeg_stream = [s for s in streams if s['info']['type'][0] == 'EEG'][0]
data = eeg_stream['time_series'].T  # channels x samples
sfreq = float(eeg_stream['info']['nominal_srate'][0])

ch_names = [c['label'][0] for c in eeg_stream['info']['desc'][0]['channels'][0]['channel']]
info = mne.create_info(ch_names, sfreq, ch_types='eeg')
raw = mne.io.RawArray(data, info)
raw.plot()

import numpy as np
import mne

# Find the BV_Markers stream
marker_stream = [s for s in streams if s['info']['name'][0] == 'BV_Markers'][0]

# Marker timestamps are in the same LSL clock as your EEG stream
marker_times = np.array(marker_stream['time_stamps'])

# Marker labels/values (usually strings, sometimes nested lists)
marker_labels = [str(val[0]) if isinstance(val, list) else str(val) 
                  for val in marker_stream['time_series']]

# Get the EEG stream's first timestamp to compute relative onsets
eeg_first_ts = eeg_stream['time_stamps'][0]
onsets = marker_times - eeg_first_ts

# Build annotations
annotations = mne.Annotations(onset=onsets,
                               duration=[0]*len(onsets),
                               description=marker_labels)

raw.set_annotations(annotations)
raw.plot()

import matplotlib.pyplot as plt
plt.show(block=True)
