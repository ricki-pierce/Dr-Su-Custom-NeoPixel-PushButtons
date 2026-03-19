"""
========================================
Python GUI + Arduino Button Task System (Updated)
========================================

FUNCTION:
- Displays a GUI with a start button, fixation cross, and next-condition button.
- Coordinates timing and presentation of trials for 8 executive-function conditions:
  "Go - Feet Apart", "No Go - Feet Apart", "No Shift - Feet Apart", "Shift - Feet Apart",
  "Go - Feet Together", "No Go - Feet Together", "No Shift - Feet Together", "Shift - Feet Together".
- Sends commands to Arduino to light up buttons in specific color patterns.
- Receives button press data from Arduino.
- Plays beeps between conditions to signal start/end.
- Sends LSL markers to Aurora fNIRS for three events:
    Marker 1 = button commanded to light up
    Marker 2 = button confirmed lit (hardware feedback)
    Marker 4 = button pressed

HARDWARE CONNECTIONS (Arduino side):
Buttons: Pins 2–5
LEDs (NeoPixels): Pins 6–9

TIMING LOGIC (per trial):
- Button lights up and stays lit for the full 10 seconds regardless of any press.
- After 10 seconds, lights turn off automatically.
- A 3-second pause follows before the next trial begins.
- This applies to all patterns: GO_BLUE, STOP_RED, ONLY_BLUE, ONLY_RED.

DEPENDENCIES:
  pip install pyserial pylsl
"""

import os
import serial
import time
import random
import threading
import winsound  # For beeps on Windows systems
import tkinter as tk
import pandas as pd
from tkinter import ttk, messagebox, font
from datetime import datetime
import subprocess
from pylsl import StreamInfo, StreamOutlet  # <<< LSL


# =====================================================
#                LSL SETUP
# =====================================================

# Create the LSL marker outlet — name must match Aurora's "Trigger in stream name"
_lsl_info = StreamInfo(
    name='Trigger',          # <<< LSL — must match Aurora exactly
    type='Markers',
    channel_count=1,
    channel_format='int32',
    source_id='ButtonController'
)
lsl_outlet = StreamOutlet(_lsl_info)  # <<< LSL
print("LSL Trigger stream created — start recording in Aurora before beginning task")

# Marker codes
MARKER_BUTTON_COMMANDED  = 1   # <<< LSL — button told to light up
MARKER_BUTTON_LIT        = 2   # <<< LSL — button confirmed lit by hardware
MARKER_BUTTON_PRESSED    = 4   # <<< LSL — button physically pressed

def send_marker(marker_value, label=""):  # <<< LSL
    """Send a single integer marker to Aurora via LSL."""
    lsl_outlet.push_sample([marker_value])
    print(f"LSL Marker sent: {marker_value} ({label})")


# =====================================================
def sync_windows_time():
    """
    Sync the Windows system clock using w32tm.
    Must be run with administrator privileges for full effect.
    """
    try:
        subprocess.run(["w32tm", "/resync"], check=True, capture_output=True, text=True)
        print("Windows time synced.")
    except subprocess.CalledProcessError as e:
        print("Time sync failed:", e.stdout, e.stderr)
    except Exception as e:
        print("Unexpected error during time sync:", e)

sync_windows_time()


#                ARDUINO SERIAL SETUP
# =====================================================
arduino = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)  # Wait 2 seconds for Arduino to reset

# =====================================================
#                GUI SETUP (Tkinter)
# =====================================================
root = tk.Tk()
root.title("Button Task")
root.geometry("600x400")
root.configure(bg="white")

# Fixation cross (center of screen, hidden initially)
cross_font = font.Font(size=80, weight="bold")
fixation_label = tk.Label(root, text="+", font=cross_font, fg="black", bg="white")
fixation_label.place(relx=0.5, rely=0.5, anchor="center")
fixation_label.lower()  # Hide cross until the task starts

# Start button to begin experiment
start_btn = tk.Button(root, text="Start", font=("Arial", 20))
start_btn.pack(pady=10)
stop_btn = tk.Button(root, text="Stop", font=("Arial", 20), state="disabled")
stop_btn.pack(pady=10)

# Next Condition button (grayed out initially)
next_btn = tk.Button(root, text="Next Condition", font=("Arial", 20), state="disabled")
next_btn.pack(pady=10)

# Condition override dropdown
override_var = tk.StringVar()
condition_dropdown = ttk.Combobox(
    root,
    textvariable=override_var,
    state="readonly",
    font=("Arial", 14)
)
condition_dropdown.pack(pady=10)

redo_btn = tk.Button(
    root,
    text="Redo Current Condition",
    font=("Arial", 16),
    state="disabled"
)
redo_btn.pack(pady=10)


# Status Frame (shows trial information in real time)
status_frame = tk.Frame(root, bg="white")
status_frame.pack(pady=10, fill="x")

condition_label = tk.Label(status_frame, text="Condition: ", font=("Arial", 14), bg="white")
condition_label.pack(anchor="w")

trial_label = tk.Label(status_frame, text="Trial: ", font=("Arial", 14), bg="white")
trial_label.pack(anchor="w")

pattern_label = tk.Label(status_frame, text="Pattern: ", font=("Arial", 14), bg="white")
pattern_label.pack(anchor="w")

buttons_label = tk.Label(status_frame, text="Active Button(s): ", font=("Arial", 14), bg="white")
buttons_label.pack(anchor="w")


stop_requested = False

canonical_conditions = []      # Frozen randomized order
remaining_conditions = []      # Conditions still to run
current_condition_name = None  # Track active condition
condition_history = {}  # {condition_name: completed_trials / total_trials}
event_log = []  # Each entry: dict with timestamp, event type, button, trial info

#====================================================
#                HELPER FUNCTIONS
# =====================================================

def show_instructions(cond_name, trials, is_repeat=False):
    trial_names = [t["pattern"] for t in trials]
    display_name = f"{cond_name} (REPEAT)" if is_repeat else cond_name
    instr_text = f"Condition: {display_name}\n\nTrials:\n" + "\n".join(trial_names) + \
                 "\n\nAfter instructing participant, press SPACEBAR to begin 10-second fixation cross and trials."

    instr_window = tk.Toplevel(root)
    instr_window.title("Instructions")

    # --- FORCE FULLSCREEN ---
    instr_window.attributes("-fullscreen", True)
    instr_window.configure(bg="white")
    instr_window.focus_force()
    tk.Label(instr_window, text=instr_text, font=("Arial", 14), justify="left").pack(pady=20, padx=20)

    space_pressed = threading.Event()

    def on_space(event):
        space_pressed.set()
        instr_window.destroy()

    instr_window.bind("<space>", on_space)
    instr_window.grab_set()  # Make modal
    root.wait_window(instr_window)
    space_pressed.wait()

def show_fixation():
    fixation_label.lift()  # Bring cross to top
    root.update()


def stop_experiment():
    global stop_requested
    log_gui_event("stop_button_clicked")

    stop_requested = True
    send_arduino("ALL_OFF")  # turn everything off
    next_btn.config(state="normal")

def beep():
    """Plays a 500 Hz tone for 500 milliseconds."""
    winsound.Beep(500, 500)

def send_arduino(cmd):
    """Send a command string to the Arduino."""
    arduino.write((cmd + "\n").encode('utf-8'))
    log_gui_event("arduino_command_sent", cmd)

def wait_for_press(timeout_ms, expected_buttons):
    """
    Waits for a button press from Arduino for up to timeout_ms.
    Returns a tuple: (pressed_button, is_correct)
    pressed_button: int index of button actually pressed, or None if timeout
    is_correct: True if pressed button is in expected_buttons, False if not
    """
    start_time = time.time()
    while (time.time() - start_time) * 1000 < timeout_ms:
        if stop_requested:
            return None, False
        if arduino.in_waiting:
            line = arduino.readline().decode('utf-8').strip()
            if line.startswith("LIT"):
                parts = line.split()
                lit_btn = int(parts[1])
                send_marker(MARKER_BUTTON_LIT, f"Button {lit_btn} confirmed lit (wait_for_press)")  # <<< LSL
                log_event(
                    "button_lit_actual",
                    cond_name=current_condition_name,
                    trial_num=0,
                    trial_type="hardware_feedback",
                    target_button=lit_btn,
                    pressed_button=None
                )
            if line.startswith("PRESSED"):
                idx = int(line.split()[1])
                return idx, idx in expected_buttons
        time.sleep(0.01)
    return None, False

def update_status(cond_name, trial_num, pattern, active_buttons, target_button=None):
    def _update():
        condition_label.config(text=f"Condition: {cond_name}")
        trial_label.config(text=f"Trial: {trial_num + 1}")
        pattern_label.config(text=f"Pattern: {pattern}")

        btn_texts = []
        for idx in active_buttons:
            display_idx = idx + 1
            if idx == target_button:
                btn_texts.append(f"[{display_idx}]")
            else:
                btn_texts.append(str(display_idx))

        buttons_label.config(text=f"Active Button(s): {', '.join(btn_texts)}")
    root.after(0, _update)  # Schedule on main thread

def clear_status():
    """Clears all status text from the GUI."""
    condition_label.config(text="Condition: ")
    trial_label.config(text="Trial: ")
    pattern_label.config(text="Pattern: ")
    buttons_label.config(text="Active Button(s): ")
    root.update()

def select_override(event):
    global override_condition_name, is_redo_run, is_manual_selection

    selected = override_var.get()

    if confirm_manual_selection(selected):
        override_condition_name = selected
        is_manual_selection = True
        is_redo_run = False
        next_btn.config(state="disabled")
        threading.Thread(target=run_current_condition).start()
    else:
        # Revert dropdown to next canonical condition
        if remaining_conditions:
            override_var.set(remaining_conditions[0][0])

def confirm_manual_selection(cond_name):
    return messagebox.askyesno(
        "Confirm Condition Selection",
        f"Run condition next:\n\n{cond_name}\n\nThis will advance the experiment."
    )


def confirm_override(cond_name):
    return messagebox.askyesno(
        "Confirm Condition Override",
        f"Redo condition:\n\n{cond_name}\n\n"
        "This will NOT advance the experiment.\n\nProceed?"
    )

def redo_current_condition():
    global override_condition_name, is_redo_run, is_manual_selection

    log_gui_event("redo_condition_clicked")

    cond_name = current_condition_name  # Redo current condition

    if confirm_override(cond_name):
        override_condition_name = cond_name
        is_redo_run = True
        is_manual_selection = False
        next_btn.config(state="disabled")
        threading.Thread(target=run_current_condition, daemon=True).start()

def update_history():
    def _update():
        history_text.config(state="normal")
        history_text.delete(1.0, tk.END)
        for cond_name, runs in condition_history.items():
            for run in runs:
                history_text.insert(
                    tk.END,
                    f"{run['label']}: {run['completed']}/{run['total']}\n"
                )
        history_text.config(state="disabled")
    root.after(0, _update)

def log_event(event_type, cond_name, trial_num, trial_type, target_button=None, pressed_button=None, active_buttons=None, is_repeat=False):
    """
    Log trial events with both target and actual pressed button.
    """
    event_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "event": event_type,
        "condition": cond_name,
        "trial_num": trial_num + 1 if trial_num is not None else "",
        "trial_type": trial_type,
        "target_button": target_button if target_button is not None else "",
        "pressed_button": pressed_button if pressed_button is not None else "",
        "active_buttons": ",".join(map(str, active_buttons)) if active_buttons else "",
        "is_repeat": is_repeat
    })

def log_gui_event(event_type, extra=None):
    """
    General timestamped GUI/system event logger.
    """
    event_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "event": event_type,
        "details": extra if extra else "",
        "condition": current_condition_name,
        "trial_num": "",
        "trial_type": "",
        "button": ""
    })

# =====================================================
#                TRIAL PRESENTATION LOGIC
# =====================================================

NUM_BUTTONS = 4  # Total number of buttons/LEDs

def run_trials(trials, cond_name):
    """
    Executes all trials for a given condition.

    TIMING PER TRIAL (identical for all 4 patterns):
    - Button(s) light up.
    - Wait up to 10 seconds for a press.
    - If pressed: log it, break immediately, turn off lights, wait 3 seconds.
    - If not pressed in 10s: turn off lights, wait 3 seconds.
    """
    last_blue = None       # Track last blue button to avoid repeats
    last_only_red = None   # Track last red button for Shift condition

    for trial_num, trial in enumerate(trials):
        pattern = trial["pattern"]
        target_button = None
        active_buttons = []
        arduino_cmd = ""

        if stop_requested:
            current_run = condition_history[cond_name][-1]
            current_run['completed'] = trial_num
            update_history()
            return

        # ---------- Build trial parameters ----------
        if pattern == "GO_BLUE":
            options = [i for i in range(NUM_BUTTONS) if i != last_blue]
            target_button = random.choice(options)
            active_buttons = [target_button]
            arduino_cmd = f"GO_BLUE {target_button}"

        elif pattern == "STOP_RED":
            target_button = random.choice(range(NUM_BUTTONS))
            active_buttons = [target_button]
            arduino_cmd = f"STOP_RED {target_button}"

        elif pattern == "ONLY_BLUE":
            options = [i for i in range(NUM_BUTTONS) if i != last_blue]
            target_button = random.choice(options)
            active_buttons = [i for i in range(NUM_BUTTONS) if i != target_button] + [target_button]
            arduino_cmd = f"ONLY_BLUE {','.join(map(str, active_buttons))}"

        elif pattern == "ONLY_RED":
            options = [i for i in range(NUM_BUTTONS) if i != last_only_red]
            target_button = random.choice(options)
            active_buttons = [i for i in range(NUM_BUTTONS) if i != target_button] + [target_button]
            arduino_cmd = f"ONLY_RED {','.join(map(str, active_buttons))}"

        # ---------- Light up buttons + Marker 1 ----------
        update_status(cond_name, trial_num, pattern, active_buttons, target_button=target_button)
        send_arduino(arduino_cmd)
        send_marker(MARKER_BUTTON_COMMANDED, f"Button commanded to light: {arduino_cmd}")  # <<< LSL

        log_event(
            event_type="button_lit",
            cond_name=cond_name,
            trial_num=trial_num,
            trial_type=pattern,
            target_button=target_button,
            pressed_button=None,
            active_buttons=active_buttons,
            is_repeat=is_redo_run
        )

        # ---------- Wait for press OR 10s timeout ----------
        start_time = time.time()
        pressed_button = None
        while (time.time() - start_time) < 10.0:
            if stop_requested:
                return
            if arduino.in_waiting > 0:
                line = arduino.readline().decode('utf-8').strip()
                if line.startswith("LIT"):                                          # <<< LSL
                    lit_btn = int(line.split()[1])                                  # <<< LSL
                    send_marker(MARKER_BUTTON_LIT, f"Button {lit_btn} confirmed lit")  # <<< LSL
                    log_event(                                                       # <<< LSL
                        event_type="button_lit_actual",                             # <<< LSL
                        cond_name=cond_name,                                        # <<< LSL
                        trial_num=trial_num,                                        # <<< LSL
                        trial_type=pattern,                                         # <<< LSL
                        target_button=lit_btn,                                      # <<< LSL
                        pressed_button=None,                                        # <<< LSL
                        active_buttons=active_buttons,                              # <<< LSL
                        is_repeat=is_redo_run                                       # <<< LSL
                    )                                                               # <<< LSL
                if line.startswith("PRESSED"):
                    pressed_button = int(line.split()[1])
                    send_marker(MARKER_BUTTON_PRESSED, f"Button {pressed_button} pressed")  # <<< LSL
                    log_event(
                        event_type="button_pressed",
                        cond_name=cond_name,
                        trial_num=trial_num,
                        trial_type=pattern,
                        target_button=target_button,
                        pressed_button=pressed_button,
                        active_buttons=active_buttons,
                        is_repeat=is_redo_run
                    )
                    break  # Exit immediately on any press
            time.sleep(0.005)

        # ---------- Turn off lights, then 3s pause ----------
        send_arduino("ALL_OFF")
        time.sleep(3)

        # ---------- Track last buttons to avoid repeats ----------
        if pattern in ("GO_BLUE", "ONLY_BLUE"):
            last_blue = target_button
        elif pattern == "ONLY_RED":
            last_only_red = target_button

    # After all trials, update history
    current_run = condition_history[cond_name][-1]
    current_run['completed'] = trial_num + 1
    update_history()


# =====================================================
#                CONDITION SEQUENCES
# =====================================================

def build_conditions():
    """Builds 8 conditions with trial lists and random order."""
    base_conditions = [
        ("Go - Feet Apart", [{"pattern": "GO_BLUE"} for _ in range(10)]),
        ("No Go - Feet Apart", [{"pattern": "GO_BLUE"}]*8 + [{"pattern": "STOP_RED"}]*2),
        ("No Shift - Feet Apart", [{"pattern": "ONLY_BLUE"} for _ in range(10)]),
        ("Shift - Feet Apart", [{"pattern": "ONLY_BLUE"}]*8 + [{"pattern": "ONLY_RED"}]*2),
        ("Go - Feet Together", [{"pattern": "GO_BLUE"} for _ in range(10)]),
        ("No Go - Feet Together", [{"pattern": "GO_BLUE"}]*8 + [{"pattern": "STOP_RED"}]*2),
        ("No Shift - Feet Together", [{"pattern": "ONLY_BLUE"} for _ in range(10)]),
        ("Shift - Feet Together", [{"pattern": "ONLY_BLUE"}]*8 + [{"pattern": "ONLY_RED"}]*2),
    ]

    # Shuffle No-Go and Shift trials to avoid consecutive red buttons
    for i in [1, 3, 5, 7]:
        trials = base_conditions[i][1]
        while True:
            random.shuffle(trials)
            consecutive_red = any(
                (trials[j]["pattern"] in ["STOP_RED","ONLY_RED"]) and
                (trials[j+1]["pattern"] in ["STOP_RED","ONLY_RED"])
                for j in range(len(trials)-1)
            )
            if not consecutive_red:
                break
        base_conditions[i] = (base_conditions[i][0], trials)

    # Randomize order of all 8 conditions
    random.shuffle(base_conditions)
    return base_conditions

# =====================================================
#                EXPERIMENT THREAD
# =====================================================

canonical_conditions = []
remaining_conditions = 0  # Track which condition is next
override_condition_name = None
is_redo_run = False


def start_experiment():
    global canonical_conditions, remaining_conditions
    start_btn.config(state="disabled")
    next_btn.config(state="disabled")
    fixation_label.lift()
    clear_status()
    root.update()

    time.sleep(2)  # Short fixation before starting
    beep()

    canonical_conditions = build_conditions()
    remaining_conditions = canonical_conditions.copy()
    stop_btn.config(state="normal")

    condition_names = [c[0] for c in canonical_conditions]
    condition_dropdown["values"] = condition_names
    override_var.set(condition_names[0])

    redo_btn.config(state="normal")

    # Run first condition
    run_current_condition()

def run_current_condition():
    global remaining_conditions
    global override_condition_name, is_redo_run
    global stop_requested, current_condition_name

    if not remaining_conditions and not override_condition_name:
        start_btn.config(state="normal")
        next_btn.config(state="disabled")
        redo_btn.config(state="disabled")
        stop_btn.config(state="disabled")
        fixation_label.lower()
        return

    # ---------------- DETERMINE CONDITION ----------------

    if override_condition_name:
        cond_name = override_condition_name
        trials = next(c[1] for c in canonical_conditions if c[0] == cond_name)
    else:
        cond_name, trials = remaining_conditions[0]

    current_condition_name = cond_name

    # ---------------- SHOW INSTRUCTIONS ----------------

    show_instructions(cond_name, trials, is_redo_run)

    # ---------------- 10 SECOND FIXATION ----------------

    fixation_label.lift()
    root.update()
    time.sleep(10)
    fixation_label.lower()

    # ---------------- HISTORY SETUP ----------------

    display_name = f"{cond_name} (REPEAT)" if is_redo_run else cond_name
    total_trials = len(trials)

    if cond_name not in condition_history:
        condition_history[cond_name] = []

    condition_history[cond_name].append({
        'label': display_name,
        'completed': 0,
        'total': total_trials
    })

    update_history()
    override_var.set(display_name)

    stop_requested = False

    print(f"RUNNING CONDITION: {cond_name}")

    # ---------------- RUN TRIALS ----------------

    run_trials(trials, cond_name)

    if stop_requested:
        stop_requested = False
        return

    send_arduino("ALL_OFF")
    log_gui_event("condition_end_all_off")

    beep()

    # ---------------- REMOVE FROM REMAINING ----------------

    if not override_condition_name:
        remaining_conditions.pop(0)
    else:
        remaining_conditions = [
            (name, t) for name, t in remaining_conditions
            if name != cond_name
        ]

    override_condition_name = None
    is_redo_run = False

    next_btn.config(state="normal")


def next_condition():
    global override_condition_name, is_manual_selection, is_redo_run

    log_gui_event("next_condition_clicked")

    override_condition_name = None
    is_manual_selection = False
    is_redo_run = False

    if not remaining_conditions:
        messagebox.showinfo("Experiment Complete", "All conditions have been presented.")
        return

    idx = random.randint(0, len(remaining_conditions)-1)
    cond_name, _ = remaining_conditions[idx]
    override_condition_name = cond_name

    threading.Thread(target=run_current_condition, daemon=True).start()


history_frame = tk.Frame(root, bg="white")
history_text = tk.Text(history_frame, height=8, font=("Arial", 12), bg="lightgray")
history_text.pack(fill="both", expand=True)
history_frame.place(relx=0.0, rely=0.6, relwidth=1.0, relheight=0.35)


def save_log_on_exit():
    global stop_requested
    stop_requested = True

    try:
        send_arduino("ALL_OFF")
        log_gui_event("gui_closed_all_off")
    except Exception as e:
        print("Error turning off Arduino LEDs:", e)

    try:
        if event_log:
            df = pd.DataFrame(event_log)
            df.sort_values("timestamp", inplace=True)
            save_folder = r"C:\Users\rpier12\Python Results"
            os.makedirs(save_folder, exist_ok=True)
            file_path = os.path.join(
                save_folder,
                f"button_task_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            df.to_excel(file_path, index=False)
            print(f"Log saved to {file_path}")
        else:
            print("No events to save.")
    except Exception as e:
        print("Error saving Excel log:", e)

    try:
        arduino.close()
    except Exception as e:
        print("Error closing Arduino serial:", e)

    root.destroy()

# =====================================================
#                BUTTON CALLBACKS
# =====================================================

start_btn.config(command=lambda: threading.Thread(target=start_experiment).start())
next_btn.config(command=lambda: threading.Thread(target=next_condition).start())
stop_btn.config(command=stop_experiment)

# =====================================================
#                WIDGET BINDINGS
# =====================================================
condition_dropdown.bind("<<ComboboxSelected>>", select_override)
redo_btn.config(command=redo_current_condition)

# =====================================================
#                RUN GUI MAIN LOOP
# =====================================================
root.protocol("WM_DELETE_WINDOW", save_log_on_exit)
root.mainloop()
