#this code is to be run with Arduino complement
#pre set trials: the Arduino script allows users to hard code which buttons should be lit and which colors to light them up as
#push button component not included
#this script was designed to simply test if we could control the individual NeoPixels when all connected to the same Elegoo Mega 2560 R3
#^this was done via breadboard for shared ground, 5V
#each NeoPixel connected to digital input pin

import serial
import time
import random

# Update COM port to match your Mega
arduino = serial.Serial('COM4', 115200, timeout=3)
time.sleep(2)  # give Mega time to reset

def send_trial(trial_num):
    cmd = f"TRIAL {trial_num}\n"
    arduino.write(cmd.encode('utf-8'))
    print(f"Sent: {cmd.strip()}")

# Example sequence
trial_sequence = [1,2,3,4,5,6]

for t in trial_sequence:
    send_trial(t)
    time.sleep(2)  # hold pattern for 2 seconds
