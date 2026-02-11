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

HARDWARE CONNECTIONS (Arduino side):
Buttons: Pins 2–5
LEDs (NeoPixels): Pins 6–9

DEPENDENCIES:
  pip install pyserial
"""

import serial
import time
import random
import threading
import winsound  # For beeps on Windows systems
from tkinter import tk, ttk, messagebox, font

# =====================================================
#                ARDUINO SERIAL SETUP
# =====================================================
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
current_condition_name = None  # Track active condition# =====================================================
#                HELPER FUNCTIONS
# =====================================================
def stop_experiment():
    global stop_requested
    stop_requested = True
    next_btn.config(state="normal")

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
        if stop_requested:
          return
        if arduino.in_waiting:
            line = arduino.readline().decode('utf-8').strip()
            if line.startswith("PRESSED"):
                idx = int(line.split()[1])
                if idx in expected_buttons:
                    return idx  # valid press
        time.sleep(0.01)  # avoid hogging CPU
    return None

def update_status(cond_name, trial_num, pattern, active_buttons, target_button=None):
    """Updates the GUI labels with current trial information."""
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
    root.update()  # Immediately refresh GUI

def clear_status():
    """Clears all status text from the GUI."""
    condition_label.config(text="Condition: ")
    trial_label.config(text="Trial: ")
    pattern_label.config(text="Pattern: ")
    buttons_label.config(text="Active Button(s): ")
    root.update()

def select_override(event):
    global override_condition_name, is_redo_run

    selected = override_var.get()

    if confirm_override(selected):
        override_condition_name = selected
        is_redo_run = True
        next_btn.config(state="disabled")
        threading.Thread(target=run_current_condition).start()
    else:
        # Revert dropdown to current canonical condition
        override_var.set(current_conditions[current_index][0])


def confirm_override(cond_name):
    return messagebox.askyesno(
        "Confirm Condition Override",
        f"Redo condition:\n\n{cond_name}\n\n"
        "This will NOT advance the experiment.\n\nProceed?"
    )

def redo_current_condition():
    global override_condition_name, is_redo_run

    cond_name = current_conditions[current_index][0]

    if confirm_override(cond_name):
        override_condition_name = cond_name
        is_redo_run = True
        next_btn.config(state="disabled")
        threading.Thread(target=run_current_condition).start()


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
      
        if stop_requested:
          return

        # ---------- Go-Blue Pattern ----------
        if pattern == "GO_BLUE":
            options = [i for i in range(NUM_BUTTONS) if i != last_blue]
            blue_button = random.choice(options)
            active_buttons = [blue_button]

            update_status(cond_name, trial_num, pattern, active_buttons, target_button=blue_button)
            send_arduino(f"GO_BLUE {blue_button}")

            wait_for_press(10000, [blue_button])
            last_blue = blue_button
            time.sleep(3)

        # ---------- Stop-Red Pattern ----------
        elif pattern == "STOP_RED":
            options = list(range(NUM_BUTTONS))
            red_button = random.choice(options)
            active_buttons = [red_button]

            update_status(cond_name, trial_num, pattern, active_buttons)
            send_arduino(f"STOP_RED {red_button}")

            # Wait up to 10 seconds for press
            press = wait_for_press(10000, [red_button])
            if press is not None:
                time.sleep(3)  # only 3s pause if button pressed
            # else: move to next trial immediately

        # ---------- Only-Blue Pattern ----------
        elif pattern == "ONLY_BLUE":
            options = [i for i in range(NUM_BUTTONS) if i != last_blue]
            blue_button = random.choice(options)
            red_buttons = [i for i in range(NUM_BUTTONS) if i != blue_button]
            active_buttons = red_buttons + [blue_button]

            update_status(cond_name, trial_num, pattern, active_buttons, target_button=blue_button)
            send_arduino(f"ONLY_BLUE {','.join(map(str, red_buttons + [blue_button]))}")

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

            wait_for_press(10000, [red_button])
            last_only_red = red_button
            time.sleep(3)

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

current_conditions = []
current_index = 0  # Track which condition is next
override_condition_name = None
is_redo_run = False


def start_experiment():
    """Starts the first condition of the experiment."""
    global current_conditions, current_index
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

    # Determine condition source
    if override_condition_name:
        cond_name = override_condition_name
        trials = next(c[1] for c in canonical_conditions if c[0] == cond_name)
        run_type = "REDO/MANUAL"
    else:
        cond_name, trials = remaining_conditions[0]
        run_type = "CANONICAL"

    current_condition_name = cond_name

    display_name = f"{cond_name} (REPEAT)" if override_condition_name else cond_name
    override_var.set(display_name)

    fixation_label.lower()
    stop_requested = False

    print(f"RUNNING CONDITION: {cond_name} | TYPE: {run_type}")

    run_trials(trials, cond_name)

    if stop_requested:
        print("CONDITION STOPPED EARLY")
        stop_requested = False
        return

    beep()

    # If canonical run finished, remove from remaining
    if not override_condition_name:
        remaining_conditions.pop(0)

    # If manual selection and condition still in remaining → remove it
    if override_condition_name:
        for i, (name, _) in enumerate(remaining_conditions):
            if name == cond_name:
                remaining_conditions.pop(i)
                break

    override_condition_name = None
    is_redo_run = False

    next_btn.config(state="normal")




def next_condition():
    next_btn.config(state="disabled")
    threading.Thread(target=run_current_condition).start()


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
root.mainloop()
