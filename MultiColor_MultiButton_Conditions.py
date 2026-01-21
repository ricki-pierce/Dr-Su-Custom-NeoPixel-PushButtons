"""
========================================
Python GUI + Arduino Button Task System
========================================

FUNCTION:
- Displays a GUI with a start button and fixation cross.
- Coordinates timing and presentation of trials for 4 executive-function conditions:
  "Go", "No-Go", "No-Shift", and "Shift".
- Sends commands to Arduino to light up buttons in specific color patterns.
- Receives button press data from Arduino.
- Plays beeps between conditions to signal start/end.

HARDWARE CONNECTIONS (Arduino side):
Buttons: Pins 2–5
LEDs (NeoPixels): Pins 6–9

DEPENDENCIES:
  pip install pyserial

----------------------------------------
"""

import tkinter as tk
from tkinter import font
import serial
import time
import random
import threading
import winsound  # For beeps on Windows systems

# =====================================================
#                ARDUINO SERIAL SETUP
# =====================================================
# Adjust COM port to match your Arduino connection
arduino = serial.Serial('COM4', 115200, timeout=1)
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
start_btn.pack(pady=20)

# -----------------------------------------------------
# Status Frame (shows trial information in real time)
# -----------------------------------------------------
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

# =====================================================
#                HELPER FUNCTIONS
# =====================================================

def beep():
    """Plays a 500 Hz tone for 500 milliseconds."""
    winsound.Beep(500, 500)

def send_arduino(cmd):
    """Send a command string to the Arduino."""
    arduino.write((cmd + "\n").encode('utf-8'))

def wait_for_press(timeout_ms, expected_buttons):
    """
    Waits for a button press signal from the Arduino.
    Returns the index of the pressed button or None if timeout.
    Only accepts presses from expected_buttons.
    """
    start_time = time.time()
    while (time.time() - start_time) * 1000 < timeout_ms:
        if arduino.in_waiting:
            line = arduino.readline().decode('utf-8').strip()
            if line.startswith("PRESSED"):
                idx = int(line.split()[1])
                if idx in expected_buttons:
                    return idx  # valid press
        time.sleep(0.01)  # avoid hogging CPU
    return None

def update_status(cond_name, trial_num, pattern, active_buttons, target_button=None):
    """
    Updates the GUI labels to show:
    - Current condition name
    - Trial number
    - Pattern type
    - Which button(s) are lit, highlighting the target one in brackets [ ]
    """
    condition_label.config(text=f"Condition: {cond_name}")
    trial_label.config(text=f"Trial: {trial_num + 1}")
    pattern_label.config(text=f"Pattern: {pattern}")

    # Convert button indices from 0–3 → 1–4 for readability
    btn_texts = []
    for idx in active_buttons:
        display_idx = idx + 1
        if idx == target_button:
            btn_texts.append(f"[{display_idx}]")  # Highlight target
        else:
            btn_texts.append(str(display_idx))

    buttons_label.config(text=f"Active Button(s): {', '.join(btn_texts)}")
    root.update()  # Immediately refresh GUI

def clear_status():
    """Clears all status text from the GUI."""
    condition_label.config(text="Condition: ")
    trial_label.config(text="Trial: ")
    pattern_label.config(text="Pattern: ")
    buttons_label.config(text="Active Button(s): ")
    root.update()


# =====================================================
#                TRIAL PRESENTATION LOGIC
# =====================================================

NUM_BUTTONS = 4  # Total number of buttons/LEDs

def run_trials(trials, cond_name):
    """
    Executes all trials for a given condition.
    Handles randomization rules, button lighting, timing, and responses.
    """
    last_blue = None       # Track last blue button to avoid repeats
    last_only_red = None   # Track last red button for Shift condition

    for trial_num, trial in enumerate(trials):
        pattern = trial["pattern"]
        blue_button = None
        red_button = None
        active_buttons = []

        # ---------- Go-Blue Pattern ----------
        if pattern == "GO_BLUE":
            options = [i for i in range(NUM_BUTTONS) if i != last_blue]
            blue_button = random.choice(options)
            active_buttons = [blue_button]

            update_status(cond_name, trial_num, pattern, active_buttons, target_button=blue_button)
            send_arduino(f"GO_BLUE {blue_button}")

            # Wait up to 10s for correct press
            wait_for_press(10000, [blue_button])

            last_blue = blue_button
            time.sleep(3)  # 3-second inter-trial interval

        # ---------- Stop-Red Pattern ----------
        elif pattern == "STOP_RED":
            options = list(range(NUM_BUTTONS))
            red_button = random.choice(options)
            active_buttons = [red_button]

            update_status(cond_name, trial_num, pattern, active_buttons)
            send_arduino(f"STOP_RED {red_button}")

            # Light stays on for 10 seconds, no button press expected
            time.sleep(10)

        # ---------- Only-Blue Pattern ----------
        elif pattern == "ONLY_BLUE":
            options = [i for i in range(NUM_BUTTONS) if i != last_blue]
            blue_button = random.choice(options)
            red_buttons = [i for i in range(NUM_BUTTONS) if i != blue_button]
            active_buttons = red_buttons + [blue_button]

            update_status(cond_name, trial_num, pattern, active_buttons, target_button=blue_button)
            send_arduino(f"ONLY_BLUE {','.join(map(str, red_buttons + [blue_button]))}")

            # Wait up to 10s for correct blue press
            wait_for_press(10000, [blue_button])
            last_blue = blue_button
            time.sleep(3)

        # ---------- Only-Red Pattern ----------
        elif pattern == "ONLY_RED":
            options = [i for i in range(NUM_BUTTONS) if i != last_only_red]
            red_button = random.choice(options)
            blue_buttons = [i for i in range(NUM_BUTTONS) if i != red_button]
            active_buttons = blue_buttons + [red_button]

            update_status(cond_name, trial_num, pattern, active_buttons, target_button=red_button)
            send_arduino(f"ONLY_RED {','.join(map(str, blue_buttons + [red_button]))}")

            # Wait up to 10s for correct red press
            wait_for_press(10000, [red_button])
            last_only_red = red_button
            time.sleep(3)


# =====================================================
#                CONDITION SEQUENCES
# =====================================================

def build_conditions():
    """
    Builds 4 experimental conditions with required randomization rules.
    Returns a list of 4 lists, each containing trial pattern dictionaries.
    """
    conditions = []

    # --- Condition 1: Go (10 Go-Blue) ---
    conditions.append([{"pattern": "GO_BLUE"} for _ in range(10)])

    # --- Condition 2: No-Go (8 Go-Blue + 2 Stop-Red, no consecutive reds) ---
    trials = [{"pattern": "GO_BLUE"}] * 8 + [{"pattern": "STOP_RED"}] * 2
    while True:
        random.shuffle(trials)
        consecutive = any(
            trials[i]["pattern"] == "STOP_RED" and trials[i + 1]["pattern"] == "STOP_RED"
            for i in range(len(trials) - 1)
        )
        if not consecutive:
            break
    conditions.append(trials)

    # --- Condition 3: No-Shift (10 Only-Blue) ---
    conditions.append([{"pattern": "ONLY_BLUE"} for _ in range(10)])

    # --- Condition 4: Shift (8 Only-Blue + 2 Only-Red, no consecutive reds) ---
    trials = [{"pattern": "ONLY_BLUE"}] * 8 + [{"pattern": "ONLY_RED"}] * 2
    while True:
        random.shuffle(trials)
        consecutive = any(
            trials[i]["pattern"] == "ONLY_RED" and trials[i + 1]["pattern"] == "ONLY_RED"
            for i in range(len(trials) - 1)
        )
        if not consecutive:
            break
    conditions.append(trials)

    return conditions


# =====================================================
#                EXPERIMENT THREAD
# =====================================================

def start_experiment():
    """Runs the entire experiment sequence (in a background thread)."""
    start_btn.config(state="disabled")  # Prevent re-clicking
    fixation_label.lift()  # Show fixation cross
    clear_status() # Clear GUI
    root.update()

    time.sleep(10)  # 10-second fixation
    beep()  # Start beep

    conditions = build_conditions()
    cond_names = ["Go", "No-Go", "No-Shift", "Shift"]

    for cond_idx, trials in enumerate(conditions):
        run_trials(trials, cond_names[cond_idx])
        beep()  # End-of-condition beep

        # Wait 10 seconds before next condition (if not last)
        if cond_idx < len(conditions) - 1:
            clear_status()      # <-- CLEAR STATUS HERE
            fixation_label.lift()
            time.sleep(10)

    # Experiment done
    start_btn.config(state="normal")
    fixation_label.lower()  # Hide fixation cross


# =====================================================
#                BUTTON CALLBACK
# =====================================================

def on_start():
    """Starts the experiment on a new thread so GUI remains responsive."""
    threading.Thread(target=start_experiment).start()

start_btn.config(command=on_start)

# =====================================================
#                RUN GUI MAIN LOOP
# =====================================================
root.mainloop()
