#this Python code is to be run with Arduino GUI complement
#the Python script allows user to choose which buttons should be lit and which colors to light them up as
#push button component not included
#this script was designed to simply test if we could control the individual NeoPixels when all connected to the same Elegoo Mega 2560 R3
#^this was done via breadboard for shared ground, 5V
#each NeoPixel connected to digital input pin

import tkinter as tk
from tkinter import ttk
import serial
import time

# ------------------- Configure Serial -------------------
arduino = serial.Serial('COM4', 115200, timeout=2)
time.sleep(2)  # Wait for Mega reset

# ------------------- Color Mapping -------------------
color_dict = {
    "Not lit": (0,0,0),
    "Red": (255,0,0),
    "Orange": (255,165,0),
    "Yellow": (255,255,0),
    "Green": (0,255,0),
    "Blue": (0,0,255),
    "Purple": (128,0,128),
    "Pink": (255,192,203)
}

# ------------------- GUI Setup -------------------
root = tk.Tk()
root.title("LED Control")

# Store dropdown variables
selected_colors = []
led_rects = []

canvas = tk.Canvas(root, width=400, height=100)
canvas.grid(row=0, column=0, columnspan=4, pady=10)

# Create 4 LED representations
for i in range(4):
    x0 = 50 + i*90
    y0 = 20
    x1 = x0 + 50
    y1 = y0 + 50
    rect = canvas.create_oval(x0, y0, x1, y1, fill="black")
    led_rects.append(rect)
    var = tk.StringVar()
    var.set("Not lit")
    selected_colors.append(var)
    # Dropdown below each LED
    dropdown = ttk.Combobox(root, textvariable=var, values=list(color_dict.keys()), state="readonly")
    dropdown.grid(row=1, column=i, padx=5, pady=5)

# ------------------- Send Function -------------------
def send_colors():
    command = "C"
    for var in selected_colors:
        rgb = color_dict[var.get()]
        command += f",{rgb[0]},{rgb[1]},{rgb[2]}"
    command += "\n"
    arduino.write(command.encode('utf-8'))
    # Update GUI LEDs
    for i, var in enumerate(selected_colors):
        rgb = color_dict[var.get()]
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        canvas.itemconfig(led_rects[i], fill=hex_color)

# ------------------- Send Button -------------------
send_btn = tk.Button(root, text="Send", command=send_colors)
send_btn.grid(row=2, column=0, columnspan=4, pady=10)

root.mainloop()
