"""
align_events.py
================
Builds a side-by-side comparison of "button lit" / "button pressed" events
across four data sources for a single session:

    1. Button task log   (xlsx)  - PC clock timestamps
    2. Terminal log       (xlsx)  - used only to get force-plate recording
                                     start times per condition
    3. Force plate files   (txt)  - one .txt per condition, events marked
                                     by an integer "counter" (1000 Hz)
    4. EEG / LSL markers    (xdf)  - relative-to-recording-start timestamps
    NOTE: fNIRS has not beeen included yet!!!!!!!!!!!!!!!!!!!!!!!

For every trial it prints two rows (Button Lit, Button Pressed) with:
    Event | Button Log | Force Plate raw | Force Plate converted |
    EEG raw | Diff Button Log (ms) | Diff EEG (ms) | Diff Force Plate (ms)

Run this on the machine where the force-plate .txt files and the .xdf file
actually live -- just edit the CONFIG block below.
"""

import os
import re
from datetime import datetime, time as dtime

import pandas as pd

# ============================================================================
# CONFIG -- edit these paths for your machine
# ============================================================================

BUTTON_LOG_PATH   = r"C:\Users\rpier12\Python Results\Ricki full run (nofnirs)\button_task_log_20260716_081806.xlsx"
TERMINAL_LOG_PATH = r"C:\Users\rpier12\Python Results\Ricki full run (nofnirs)\terminal_log_20260716_081806.xlsx"

# EEG/LSL recording. Leave as-is; script degrades gracefully if not found
# or if pyxdf isn't installed.
EEG_XDF_PATH = r"C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf"

# Force plate txt files, keyed by session "order" number (matches the
# "(order #N)" in the terminal log's RUNNING CONDITION lines, and the (N)
# in your filenames below).
FORCE_PLATE_FILES = {
    1: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Shift - Feet Apart (1).txt",
    2: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Shift - Feet Together (2).txt",
    3: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Go - Feet Together (3).txt",
    4: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Shift - Feet Together (4).txt",
    5: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Go - Feet Together (5).txt",
    6: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Go - Feet Apart (6).txt",
    7: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\No Go - Feet Apart (7).txt",
    8: r"C:\AMTI\PythonResults\Ricki full run (nofnirs)\Shift - Feet Apart (8).txt",
}

FORCE_PLATE_SRATE = 1000.0  # Hz -- counter units per second

# Marker-1/2/4 codes used by both the terminal log ("LSL Marker sent: N ...")
# and the force plate "marker" column, and the EEG marker stream:
#   1 = button_commanded, 2 = button_lit, 4 = button_pressed
CODE_COMMANDED = 1
CODE_LIT = 2
CODE_PRESSED = 4

# When grouping repeated "button_lit" marker rows in the force plate file
# into one trial (multi-button-light trials fire several close together),
# any gap larger than this many counter units (=ms, since plate is 1000 Hz)
# starts a new trial group. Real within-trial gaps in the sample data are
# ~16 counts; real between-trial gaps are in the thousands.
GROUP_GAP_COUNTS = 500

# ============================================================================
# Loaders
# ============================================================================

def load_button_log(path):
    df = pd.read_excel(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_terminal_log(path):
    df = pd.read_excel(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_condition_windows(terminal_df):
    """
    Returns {order_number: {'condition': name, 'fp_start': datetime}}
    by pairing each "Force plate recording started: HH:MM:SS.mmm" line
    with the RUNNING CONDITION line that follows it (they alternate 1:1,
    in session order, in the terminal log).
    """
    fp_starts, run_conditions = [], []

    for _, row in terminal_df.iterrows():
        msg = str(row["message"])

        m = re.search(r"Force plate recording started:\s*([\d:.]+)", msg)
        if m:
            fp_starts.append((row["timestamp"], m.group(1)))

        m = re.search(r"RUNNING CONDITION:\s*(.+?)\s*\(order #(\d+)", msg)
        if m:
            run_conditions.append((m.group(1).strip(), int(m.group(2))))

    if len(fp_starts) != len(run_conditions):
        print(
            f"WARNING: found {len(fp_starts)} 'Force plate recording started' "
            f"lines but {len(run_conditions)} 'RUNNING CONDITION' lines -- "
            "these should match 1:1. Check the terminal log."
        )

    windows = {}
    for (fp_ts, fp_time_str), (cond_name, order) in zip(fp_starts, run_conditions):
        h, mi, rest = fp_time_str.split(":")
        sec_f = float(rest)
        sec = int(sec_f)
        micro = int(round((sec_f - sec) * 1_000_000))
        fp_dt = datetime.combine(fp_ts.date(), dtime(int(h), int(mi), sec, micro))
        windows[order] = {"condition": cond_name, "fp_start": fp_dt}

    return windows


def build_button_log_trials(button_df):
    """
    One row per trial: condition, trial_num, lit_time (first
    button_lit_actual), press_time (button_pressed, or None), and
    global_order -- a 0-based index across the WHOLE session in
    chronological order. global_order is what lines a trial up with its
    position in the EEG marker stream (light_commanded[i], etc.), since
    trials run sequentially in real time across the whole recording.
    """
    df = button_df.dropna(subset=["condition", "trial_num"]).copy()

    trials = []
    for (cond, tnum), g in df.groupby(["condition", "trial_num"], sort=False):
        lit_rows = g[g["event"] == "button_lit_actual"]
        press_rows = g[g["event"] == "button_pressed"]
        if lit_rows.empty:
            continue
        trials.append(
            {
                "condition": cond,
                "trial_num": int(tnum),
                "lit_time": lit_rows.iloc[0]["timestamp"],       # first instance
                "press_time": press_rows.iloc[0]["timestamp"] if not press_rows.empty else None,
            }
        )

    trials_df = pd.DataFrame(trials).sort_values("lit_time").reset_index(drop=True)
    trials_df["global_order"] = trials_df.index
    return trials_df


def load_force_plate_trials(filepath, gap_counts=GROUP_GAP_COUNTS):
    """
    Reads one force-plate txt file and returns one trial per LIGHT event.

    For each light trial:
        - lit_counter = first counter in that light group
        - press_counter = first button press AFTER that light and BEFORE the next light

    This correctly handles No-Go trials where no press occurs.
    """

    fp = pd.read_csv(
        filepath,
        sep="\t",
        low_memory=False
    )

    fp.columns = [c.strip() for c in fp.columns]

    # Only keep marker/counter columns
    fp = fp[["marker", "counter"]].copy()

    # ---- Group consecutive LIGHT markers into trials ----
    light_rows = fp[fp["marker"] == CODE_LIT]["counter"].tolist()

    groups = []
    current = []

    for c in light_rows:
        if current and (c - current[-1]) > gap_counts:
            groups.append(current)
            current = []
        current.append(c)

    if current:
        groups.append(current)

    light_starts = [min(g) for g in groups]

    # All button presses
    press_counters = fp.loc[
        fp["marker"] == CODE_PRESSED,
        "counter"
    ].tolist()

    trials = []

    for i, light_counter in enumerate(light_starts):

        next_light = (
            light_starts[i + 1]
            if i + 1 < len(light_starts)
            else float("inf")
        )

        # First press after this light but before the next light
        press_counter = next(
            (
                p
                for p in press_counters
                if light_counter <= p < next_light
            ),
            None
        )

        trials.append(
            {
                "trial_num": i + 1,
                "lit_counter": light_counter,
                "press_counter": press_counter,
                "lit_group_size": len(groups[i]),
            }
        )
    # print(filepath)
    # print(fp["marker"].value_counts().sort_index())
    # print(fp[fp["marker"] == CODE_PRESSED][["counter"]].head(20))
    # print("Light counters:")
    # print(light_starts)

    # print()

    # print("Press counters:")
    # print(press_counters)

    return trials


def load_eeg_trials(xdf_path):
    """
    Returns {global_order: {'light_rel': seconds_or_None, 'press_rel': seconds_or_None}}
    using the same pairing logic as your EEG analysis script (first
    code-2 event at/after the command, first code-4 event between light-on
    and the next command). Degrades gracefully -- returns None if pyxdf
    isn't installed or the file isn't found, so the rest of the comparison
    still runs.
    """
    try:
        import pyxdf
    except ImportError:
        print("[EEG] pyxdf not installed (pip install pyxdf) -- EEG columns will show N/A")
        return None

    if not os.path.exists(xdf_path):
        print(f"[EEG] file not found: {xdf_path} -- EEG columns will show N/A")
        return None

    streams, _header = pyxdf.load_xdf(xdf_path)
    marker_stream = streams[0]
    eeg_stream = streams[4]

    eeg_times = eeg_stream["time_stamps"]
    raw_markers = marker_stream["time_series"]
    marker_times = marker_stream["time_stamps"]

    light_commanded, light_on, button_press = [], [], []
    for m, t in zip(raw_markers, marker_times):
        code = int(m[0])
        rel = t - eeg_times[0]
        if code == CODE_COMMANDED:
            light_commanded.append((t, rel))
        elif code == CODE_LIT:
            light_on.append((t, rel))
        elif code == CODE_PRESSED:
            button_press.append((t, rel))

    eeg_by_order = {}
    for i, (cmd_t, _cmd_rel) in enumerate(light_commanded):
        next_cmd_t = light_commanded[i + 1][0] if i + 1 < len(light_commanded) else float("inf")
        on_event = next((e for e in light_on if e[0] >= cmd_t), None)
        press_event = None
        if on_event:
            press_event = next(
                (e for e in button_press if on_event[0] <= e[0] < next_cmd_t), None
            )
        eeg_by_order[i] = {
            "light_rel": on_event[1] if on_event else None,
            "press_rel": press_event[1] if press_event else None,
        }
    return eeg_by_order


# ============================================================================
# Formatting helpers
# ============================================================================

COL_WIDTHS = [22, 20, 18, 26, 16, 20, 18, 22]
HEADERS = [
    "Event", "Button Log", "Force Plate raw", "Force Plate converted",
    "EEG raw", "Diff Button (ms)", "Diff EEG (ms)", "Diff ForcePlate (ms)",
]


def _fmt(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def _row(*vals):
    return "".join(_fmt(v).ljust(w) for v, w in zip(vals, COL_WIDTHS))


def fmt_time(dt):
    if pd.isna(dt):
        return None
    return dt.strftime("%H:%M:%S.%f")


def fmt_fp_converted(fp_start, counter):
    if fp_start is None or counter is None:
        return None
    seconds = counter / FORCE_PLATE_SRATE
    total_micro = int(round(seconds * 1_000_000))
    dt = fp_start + pd.Timedelta(microseconds=total_micro)
    return dt.strftime("%H:%M:%S.%f")[:-3]  # ms precision (plate resolution)


def fmt_eeg_raw(rel):
    return None if rel is None else f"{rel:.6f}"


# ============================================================================
# Main
# ============================================================================

def main():
    button_df = load_button_log(BUTTON_LOG_PATH)
    terminal_df = load_terminal_log(TERMINAL_LOG_PATH)
    windows = get_condition_windows(terminal_df)
    trial_table = build_button_log_trials(button_df)
    eeg_by_order = load_eeg_trials(EEG_XDF_PATH)

    for order in sorted(windows):
        info = windows[order]
        condition, fp_start = info["condition"], info["fp_start"]

        fp_path = FORCE_PLATE_FILES.get(order)
        if not fp_path or not os.path.exists(fp_path):
            print(f"\n[order {order}] {condition}: force plate file not found ({fp_path}) -- skipping\n")
            continue

        fp_trials = load_force_plate_trials(fp_path)
        fp_by_trial_num = {t["trial_num"]: t for t in fp_trials}

        cond_trials = trial_table[trial_table["condition"] == condition].sort_values("trial_num")

        #print(cond_trials[["trial_num", "lit_time", "press_time"]])

        print("=" * sum(COL_WIDTHS))
        print(f"CONDITION: {condition}  (order #{order})   Force plate start: {fp_start.strftime('%H:%M:%S.%f')[:-3]}")
        print("=" * sum(COL_WIDTHS))
        print(_row(*HEADERS))
        print("-" * sum(COL_WIDTHS))

        for _, bl in cond_trials.iterrows():
            tnum = int(bl["trial_num"])
            fp = fp_by_trial_num.get(tnum, {})
            eeg = (eeg_by_order or {}).get(int(bl["global_order"]), {})

            bl_lit, bl_press = bl["lit_time"], bl["press_time"]
            fp_lit, fp_press = fp.get("lit_counter"), fp.get("press_counter")
            eeg_lit, eeg_press = eeg.get("light_rel"), eeg.get("press_rel")

            diff_button = (
                (bl_press - bl_lit).total_seconds() * 1000
                if pd.notna(bl_press) and pd.notna(bl_lit)
                else None
            )
            diff_eeg = (
                (eeg_press - eeg_lit) * 1000 if eeg_press is not None and eeg_lit is not None else None
            )
            diff_fp = (
                (fp_press - fp_lit) / FORCE_PLATE_SRATE * 1000 if fp_press is not None and fp_lit is not None else None
            )

            print(
                _row(
                    f"Trial {tnum} - Lit",
                    fmt_time(bl_lit),
                    fp_lit,
                    fmt_fp_converted(fp_start, fp_lit),
                    fmt_eeg_raw(eeg_lit),
                    "", "", "",
                )
            )
            print(
                _row(
                    f"Trial {tnum} - Pressed",
                    fmt_time(bl_press),
                    fp_press,
                    fmt_fp_converted(fp_start, fp_press),
                    fmt_eeg_raw(eeg_press),
                    f"{diff_button:.3f}" if diff_button is not None else "",
                    f"{diff_eeg:.3f}" if diff_eeg is not None else "",
                    f"{diff_fp:.3f}" if diff_fp is not None else "",
                )
            )
        print()


if __name__ == "__main__":
    main()
