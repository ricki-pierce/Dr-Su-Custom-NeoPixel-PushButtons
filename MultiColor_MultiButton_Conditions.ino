/*
  ================================
  Multi-Button + NeoPixel Task Code
  ================================

  FUNCTION:
  - Controls 4 buttons and 4 individual NeoPixels.
  - Receives commands from Python via Serial.
  - Lights LEDs according to the current trial pattern (Go-Blue, Stop-Red, Only-Blue, Only-Red).
  - Detects button presses and reports them back to Python.
  - When a button is pressed during an active trial, all LEDs turn off immediately.

  CONNECTIONS:
  Buttons: Digital pins 2, 3, 4, 5 (wired to GND, using INPUT_PULLUP)
  NeoPixels: Digital pins 6, 7, 8, 9 (1 LED each)
*/

#include <Adafruit_NeoPixel.h>

// ----- CONFIGURATION -----
#define NUM_BUTTONS 4  // Number of buttons and NeoPixels

// Assign button and LED pins
const uint8_t buttonPins[NUM_BUTTONS] = {2, 3, 4, 5};
const uint8_t ledPins[NUM_BUTTONS] = {6, 7, 8, 9};

// Create 4 individual NeoPixel objects (one per button)
Adafruit_NeoPixel leds[NUM_BUTTONS] = {
  Adafruit_NeoPixel(1, ledPins[0], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(1, ledPins[1], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(1, ledPins[2], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(1, ledPins[3], NEO_GRB + NEO_KHZ800)
};

// Track LED color state for each button
// -1 = off, 0 = red, 1 = blue
int activeColor[NUM_BUTTONS] = {-1, -1, -1, -1};

// Track if a button is currently pressed (for debounce)
bool buttonPressed[NUM_BUTTONS] = {false, false, false, false};

// ----- SETUP -----
void setup() {
  Serial.begin(115200);  // Match baud rate with Python script

  // Initialize all buttons and LEDs
  for (int i = 0; i < NUM_BUTTONS; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP); // Buttons to GND with internal pullups
    leds[i].begin();                      // Initialize each NeoPixel
    leds[i].show();                       // Turn LEDs off
  }
}

// Utility function to build RGB color
uint32_t colorRGB(uint8_t r, uint8_t g, uint8_t b) {
  return leds[0].Color(r, g, b);
}

// Turn off all LEDs
void clearAll() {
  for (int i = 0; i < NUM_BUTTONS; i++) {
    leds[i].setPixelColor(0, 0);  // Off
    leds[i].show();
    activeColor[i] = -1;
  }
}

// Set one LED to a specific color and record its active color state
void setLED(int index, uint32_t color) {
  leds[index].setPixelColor(0, color);
  leds[index].show();

  // Track color: 0 = red, 1 = blue
  activeColor[index] = (color == colorRGB(255, 0, 0)) ? 0 : 1;
}

// ----- MAIN LOOP -----
void loop() {

  // ===============================
  // Handle incoming serial commands
  // ===============================
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    // ---- Go-Blue pattern ----
    // Command format: "GO_BLUE X"  (X = button index)
    if (line.startsWith("GO_BLUE")) {
      int idx = line.substring(8).toInt();
      clearAll();
      setLED(idx, colorRGB(0, 0, 255)); // Blue target
    }

    // ---- Stop-Red pattern ----
    // Command format: "STOP_RED X"
    else if (line.startsWith("STOP_RED")) {
      int idx = line.substring(9).toInt();
      clearAll();
      setLED(idx, colorRGB(255, 0, 0)); // Red target
    }

    // ---- Only-Blue pattern ----
    // Command format: "ONLY_BLUE a,b,c,d"
    // (Last number = target blue, others = red)
    else if (line.startsWith("ONLY_BLUE")) {
      clearAll();

      int nums[NUM_BUTTONS];
      int start = 10;

      // Parse comma-separated LED indices from command
      for (int i = 0; i < NUM_BUTTONS; i++) {
        int end = line.indexOf(',', start);
        if (end == -1) end = line.length();
        nums[i] = line.substring(start, end).toInt();
        start = end + 1;
      }

      // Light up LEDs: last one blue, others red
      for (int i = 0; i < NUM_BUTTONS; i++) {
        if (i == NUM_BUTTONS - 1)
          setLED(nums[i], colorRGB(0, 0, 255)); // Target blue
        else
          setLED(nums[i], colorRGB(255, 0, 0)); // Distractor red
      }
    }

    // ---- Only-Red pattern ----
    // Command format: "ONLY_RED a,b,c,d"
    // (Last number = target red, others = blue)
    else if (line.startsWith("ONLY_RED")) {
      clearAll();

      int nums[NUM_BUTTONS];
      int start = 9;

      // Parse comma-separated LED indices from command
      for (int i = 0; i < NUM_BUTTONS; i++) {
        int end = line.indexOf(',', start);
        if (end == -1) end = line.length();
        nums[i] = line.substring(start, end).toInt();
        start = end + 1;
      }

      // Light up LEDs: last one red, others blue
      for (int i = 0; i < NUM_BUTTONS; i++) {
        if (i == NUM_BUTTONS - 1)
          setLED(nums[i], colorRGB(255, 0, 0)); // Target red
        else
          setLED(nums[i], colorRGB(0, 0, 255)); // Distractor blue
      }
    }

    // ---- Clear all LEDs ----
    else if (line == "CLEAR") {
      clearAll();
    }
  }

  // ===============================
  // Monitor button presses
  // ===============================
  for (int i = 0; i < NUM_BUTTONS; i++) {
    int state = digitalRead(buttonPins[i]);

    // Button pressed (active LOW)
    if (state == LOW && !buttonPressed[i]) {
      buttonPressed[i] = true;

      // Send press event back to Python
      Serial.print("PRESSED ");
      Serial.println(i);

      // If any LED is active, clear all immediately
      bool anyActive = false;
      for (int j = 0; j < NUM_BUTTONS; j++) {
        if (activeColor[j] != -1) {
          anyActive = true;
          break;
        }
      }

      if (anyActive) {
        clearAll(); // Turn off all LEDs right away
      }
    }

    // Button released — reset pressed state
    if (state == HIGH) {
      buttonPressed[i] = false;
    }
  }
}
