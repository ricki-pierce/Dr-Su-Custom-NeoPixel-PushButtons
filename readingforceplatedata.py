"""
AMTI AccuSway Force Plate — Center of Pressure (CoP) Analysis (plate ran at 1000Hz)
=============================================================
Usage:
    python amti_cop_analysis.py
    → You will be prompted to enter the path to your .txt file,
      OR you can hard-code the path in the INPUT section below.

Marker legend (drawn as vertical lines on all time-series plots):
    Marker 1  (blue  dashed) — Button commanded to light up
    Marker 2  (green dashed) — Button actually lit up
    Marker 4  (red   solid)  — Button pressed by subject

Outputs:
    • In Terminal: Marker 1, 2, 4 Frame numbers and timestamps since beginning of recording; reaction time between marker 2 and marker 4
    • Figure 2 : CoP X and CoP Y time series with marker lines
    • Figure 4 : Fz time series with marker lines
    • Saves all figures as PNG files next to the input .txt file
"""

# ─────────────────────────────────────────────────────────────────
#  IMPORTS
# ─────────────────────────────────────────────────────────────────
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from scipy.stats import chi2
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401

# ─────────────────────────────────────────────────────────────────
#  USER INPUT  ← change the hard-coded path here if you prefer
# ─────────────────────────────────────────────────────────────────
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Shift - Feet Apart (1).txt"
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Shift - Feet Together (2).txt"
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Go - Feet Together (3).txt"
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Shift - Feet Together (4).txt"
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Go - Feet Together (5).txt"
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Go - Feet Apart (6).txt"
#HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Go - Feet Apart (7).txt"
HARD_CODED_PATH = r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Shift - Feet Apart (8).txt"

# ─────────────────────────────────────────────────────────────────
#  AMTI PLATE PARAMETERS  — adjust if your calibration sheet differs
# ─────────────────────────────────────────────────────────────────
DZ           = 0.0     # moment-arm offset (m). AccuSway top-surface referenced → 0
FZ_THRESHOLD = 10.0    # N  — frames below this Fz are masked as NaN
SAMPLE_RATE  = 1000.0   # Hz — set to your actual acquisition rate

# ─────────────────────────────────────────────────────────────────
#  MARKER STYLE CONFIG
# ─────────────────────────────────────────────────────────────────
MARKER_STYLE = {
    1: dict(color='#1565C0', linestyle='--', linewidth=1.4, label='Marker 1 — Button commanded ON'),
    2: dict(color='#2E7D32', linestyle='--', linewidth=1.4, label='Marker 2 — Button lit up'),
    4: dict(color='#C62828', linestyle='-',  linewidth=1.6, label='Marker 4 — Button pressed'),
}
# Dot colors for 2-D sway path
MARKER_DOT_COLOR = {1: '#1565C0', 2: '#2E7D32', 4: '#C62828'}
MARKER_DOT_SHAPE = {1: 'D', 2: 's', 4: '*'}
MARKER_DOT_SIZE  = {1: 70,     2: 70,     4: 140}


# ─────────────────────────────────────────────────────────────────
#  HELPER: draw marker lines on a 2-D axes
# ─────────────────────────────────────────────────────────────────
def draw_marker_lines(ax, marker_times, first_only_label=True):
    """Draw vertical lines for each marker value on the given axes."""
    drawn_labels = set()
    for mval, t_list in marker_times.items():
        style = MARKER_STYLE[mval]
        for t in t_list:
            lbl = style['label'] if mval not in drawn_labels else '_nolegend_'
            ax.axvline(t,
                       color=style['color'],
                       linestyle=style['linestyle'],
                       linewidth=style['linewidth'],
                       alpha=0.75,
                       label=lbl)
            drawn_labels.add(mval)

# ─────────────────────────────────────────────────────────────────
#  STEP 1 — resolve file path
# ─────────────────────────────────────────────────────────────────
if HARD_CODED_PATH:
    filepath = HARD_CODED_PATH
else:
    filepath = input("Enter the full path to your AMTI .txt file:\n> ").strip().strip('"').strip("'")

if not os.path.isfile(filepath):
    sys.exit(f"\n[ERROR] File not found:\n  {filepath}\nPlease check the path and try again.")

output_dir = os.path.dirname(filepath)
base_name  = os.path.splitext(os.path.basename(filepath))[0]
print(f"\n✔  File found: {os.path.basename(filepath)}")

# ─────────────────────────────────────────────────────────────────
#  STEP 2 — load data
# ─────────────────────────────────────────────────────────────────
try:
    df = pd.read_csv(filepath, sep='\t', engine='python')
except Exception as e:
    sys.exit(f"[ERROR] Could not read file: {e}")

df.columns = df.columns.str.strip()

# Auto-detect force/moment columns
col_map = {}
for col in df.columns:
    cl = col.lower()
    if   cl.startswith('fx'):     col_map['Fx'] = col
    elif cl.startswith('fy'):     col_map['Fy'] = col
    elif cl.startswith('fz'):     col_map['Fz'] = col
    elif cl.startswith('mx'):     col_map['Mx'] = col
    elif cl.startswith('my'):     col_map['My'] = col
    elif cl.startswith('mz'):     col_map['Mz'] = col
    elif 'marker' in cl and 'label' not in cl:  col_map['marker'] = col

required = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
missing  = [k for k in required if k not in col_map]
if missing:
    sys.exit(f"[ERROR] Could not find columns for: {missing}\n"
             f"  Columns in file: {list(df.columns)}")

Fx = df[col_map['Fx']].to_numpy(dtype=float)
Fy = df[col_map['Fy']].to_numpy(dtype=float)
Fz = df[col_map['Fz']].to_numpy(dtype=float)
Mx = df[col_map['Mx']].to_numpy(dtype=float)
My = df[col_map['My']].to_numpy(dtype=float)
Mz = df[col_map['Mz']].to_numpy(dtype=float)

n_samples = len(Fz)
time      = np.arange(n_samples) / SAMPLE_RATE   # seconds

print(f"✔  Loaded {n_samples} samples  ({n_samples/SAMPLE_RATE:.2f} s @ {SAMPLE_RATE} Hz)")

# ─────────────────────────────────────────────────────────────────
#  STEP 3 — parse marker column
# ─────────────────────────────────────────────────────────────────
marker_times  = {1: [], 2: [], 4: []}   # time (s) of each occurrence
marker_frames = {1: [], 2: [], 4: []}   # frame index of each occurrence
has_markers   = False

if 'marker' in col_map:
    raw_marker = pd.to_numeric(df[col_map['marker']], errors='coerce').fillna(0).to_numpy(dtype=int)
    for mval in (1, 2, 4):
        idxs = np.where(raw_marker == mval)[0]
        if len(idxs):
            has_markers = True
            marker_frames[mval] = idxs.tolist()
            marker_times[mval]  = (idxs / SAMPLE_RATE).tolist()
else:
    print("  ⚠  No 'marker' column found — marker lines will be skipped.")
    raw_marker = np.zeros(n_samples, dtype=int)

# ─────────────────────────────────────────────────────────────────
#  STEP 4 — print marker timestamps to terminal
# ─────────────────────────────────────────────────────────────────
MARKER_DESC = {
    1: 'Button commanded ON',
    2: 'Button lit up',
    4: 'Button pressed by subject',
}

print("\n" + "═"*62)
print("  MARKER TIMESTAMPS")
print("═"*62)

any_found = False
for mval in (1, 2, 4):
    t_list = marker_times[mval]
    f_list = marker_frames[mval]
    if t_list:
        any_found = True
        print(f"\n  Marker {mval}  —  {MARKER_DESC[mval]}  ({len(t_list)} events)")
        print(f"  {'Event':<8}{'Frame':<10}{'Time (s)':<12}")
        print(f"  {'-'*6:<8}{'-'*8:<10}{'-'*9:<12}")
        for i, (fr, ts) in enumerate(zip(f_list, t_list), 1):
            print(f"  {i:<8}{fr:<10}{ts:<12.4f}")


# If markers 2 and 4 both exist, print reaction time (lit → pressed)
# Pair each button press with its corresponding trial using marker 1 as trial boundaries
if marker_times[2] and marker_times[4]:
    print(f"\n  Trial-by-trial reaction time (light on → button pressed):")
    print(f"  {'Trial':<8} {'Light On (s)':>14} {'Button Press (s)':>18} {'RT (ms)':>10} {'Status'}")
    print(f"  {'-'*6:<8} {'-'*12:>14} {'-'*16:>18} {'-'*8:>10} {'-'*6}")

    on_times    = marker_times[2]
    press_times = marker_times[4]

    for i, on_t in enumerate(on_times):
        next_on_t = on_times[i+1] if i+1 < len(on_times) else float('inf')

        # First button press after this light_on, before next light_on
        press_candidates = [t for t in press_times if on_t <= t < next_on_t]
        press_t = press_candidates[0] if press_candidates else None

        if press_t is not None:
            rt_ms = (press_t - on_t) * 1000
            print(f"  {i+1:<8} {on_t:>14.4f} {press_t:>18.4f} {rt_ms:>10.1f}ms   HIT")
        else:
            print(f"  {i+1:<8} {on_t:>14.4f} {'---':>18} {'---':>10}   MISS")

if not any_found:
    print("  No marker events (1, 2, or 4) found in this file.")

print("═"*62)

# ─────────────────────────────────────────────────────────────────
#  STEP 5 — compute CoP
# ─────────────────────────────────────────────────────────────────
valid = np.abs(Fz) > FZ_THRESHOLD
cop_x = np.where(valid, -(My + Fx * DZ) / Fz, np.nan)
cop_y = np.where(valid,  (Mx - Fy * DZ) / Fz, np.nan)

cx_cm = cop_x * 100
cy_cm = cop_y * 100

# ─────────────────────────────────────────────────────────────────
#  STEP 6 — summary statistics
# ─────────────────────────────────────────────────────────────────
cx_valid = cx_cm[~np.isnan(cx_cm)]
cy_valid = cy_cm[~np.isnan(cy_cm)]

dx = np.diff(cx_valid)
dy = np.diff(cy_valid)
path_length = np.sum(np.sqrt(dx**2 + dy**2))

mean_x = np.nanmean(cx_cm)
mean_y = np.nanmean(cy_cm)
std_x  = np.nanstd(cx_cm)
std_y  = np.nanstd(cy_cm)
rms_x  = np.sqrt(np.nanmean((cx_cm - mean_x)**2))
rms_y  = np.sqrt(np.nanmean((cy_cm - mean_y)**2))
range_x = np.nanmax(cx_cm) - np.nanmin(cx_cm)
range_y = np.nanmax(cy_cm) - np.nanmin(cy_cm)
mean_vel = path_length / (n_samples / SAMPLE_RATE)

print("\n" + "═"*52)
print("  CENTER OF PRESSURE  —  SUMMARY")
print("═"*52)
print(f"  Mean CoP X (ML)      : {mean_x:+.3f} cm")
print(f"  Mean CoP Y (AP)      : {mean_y:+.3f} cm")
print(f"  Std  CoP X           : {std_x:.3f} cm")
print(f"  Std  CoP Y           : {std_y:.3f} cm")
print(f"  RMS  CoP X           : {rms_x:.3f} cm")
print(f"  RMS  CoP Y           : {rms_y:.3f} cm")
print(f"  Range CoP X          : {range_x:.3f} cm")
print(f"  Range CoP Y          : {range_y:.3f} cm")
print(f"  Total Path Length    : {path_length:.2f} cm")
print(f"  Mean Sway Velocity   : {mean_vel:.2f} cm/s")
print("═"*52 + "\n")

# ─────────────────────────────────────────────────────────────────
#  STEP 7 — build shared legend handles for markers
# ─────────────────────────────────────────────────────────────────
marker_legend_handles = [
    Line2D([0], [0],
           color=MARKER_STYLE[mv]['color'],
           linestyle=MARKER_STYLE[mv]['linestyle'],
           linewidth=MARKER_STYLE[mv]['linewidth'],
           label=MARKER_STYLE[mv]['label'])
    for mv in (1, 2, 4) if marker_times[mv]
]

# ─────────────────────────────────────────────────────────────────
#  STEP 8 — plotting
# ─────────────────────────────────────────────────────────────────
FIGSIZE_SQ   = (7, 7)
FIGSIZE_WIDE = (13, 4.5)
CMAP         = 'plasma'
ALPHA_PATH   = 0.75

# ── Figure 2 : CoP time series ────────────────────────────────────
fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=FIGSIZE_WIDE, sharex=True)

ax2a.plot(time, cx_cm, color='#E91E63', linewidth=0.9, label='CoP X (ML)')
ax2a.axhline(mean_x, color='k', linewidth=1, linestyle='--',
             label=f'Mean = {mean_x:.2f} cm')
draw_marker_lines(ax2a, marker_times)
ax2a.set_ylabel("CoP X (cm)", fontsize=11)
ax2a.set_title(f"CoP Time Series — {base_name}", fontsize=12, fontweight='bold')
ax2a.legend(fontsize=8, loc='upper right')
ax2a.grid(True, alpha=0.3)

ax2b.plot(time, cy_cm, color='#009688', linewidth=0.9, label='CoP Y (AP)')
ax2b.axhline(mean_y, color='k', linewidth=1, linestyle='--',
             label=f'Mean = {mean_y:.2f} cm')
draw_marker_lines(ax2b, marker_times)
ax2b.set_xlabel("Time (s)", fontsize=11)
ax2b.set_ylabel("CoP Y (cm)", fontsize=11)
ax2b.legend(fontsize=8, loc='upper right')
ax2b.grid(True, alpha=0.3)

# shared marker legend below both axes
if marker_legend_handles:
    fig2.legend(handles=marker_legend_handles,
                loc='lower center', ncol=3, fontsize=9,
                bbox_to_anchor=(0.5, -0.04), framealpha=0.9)

fig2.tight_layout()
fig2_path = os.path.join(output_dir, f"{base_name}_CoP_timeseries.png")
fig2.savefig(fig2_path, dpi=150, bbox_inches='tight')
print(f"  Saved → {fig2_path}")


# ── Figure 4 : Fz time series ─────────────────────────────────────
fig4, ax4 = plt.subplots(figsize=FIGSIZE_WIDE)
ax4.plot(time, Fz, color='#FF9800', linewidth=0.9, label='Fz')
#ax4.axhline(FZ_THRESHOLD, color='red', linewidth=1, linestyle='--',
            #label=f'Fz threshold = {FZ_THRESHOLD} N')
draw_marker_lines(ax4, marker_times)
ax4.set_xlabel("Time (s)", fontsize=11)
ax4.set_ylabel("Fz (N)",   fontsize=11)
ax4.set_title(f"Vertical Ground Reaction Force — {base_name}",
              fontsize=12, fontweight='bold')
handles4, _ = ax4.get_legend_handles_labels()
ax4.legend(handles=handles4 + marker_legend_handles, fontsize=9)
ax4.grid(True, alpha=0.3)
fig4.tight_layout()

fig4_path = os.path.join(output_dir, f"{base_name}_Fz_timeseries.png")
fig4.savefig(fig4_path, dpi=150)
print(f"  Saved → {fig4_path}")

print("\n✔  All figures saved.  Displaying plots …\n")
plt.show()
