#this code is to be run with Python complement
#pre set trials: the Python script allows users to hard code which buttons should be lit and which colors to light them up as
#push button component not included
#this script was designed to simply test if we could control the individual NeoPixels when all connected to the same Elegoo Mega 2560 R3
#^this was done via breadboard for shared ground, 5V
#each NeoPixel connected to digital input pin


#include <Adafruit_NeoPixel.h>

#define NUM_PIXELS 4
const uint8_t dataPins[NUM_PIXELS] = {6, 7, 8, 9};
Adafruit_NeoPixel pixels[NUM_PIXELS] = {
  Adafruit_NeoPixel(1, dataPins[0], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(1, dataPins[1], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(1, dataPins[2], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(1, dataPins[3], NEO_GRB + NEO_KHZ800)
};

void setup() {
  Serial.begin(115200);
  for(int i = 0; i < NUM_PIXELS; i++){
    pixels[i].begin();
    pixels[i].show(); // start off
  }
}

uint32_t colorRGB(uint8_t r, uint8_t g, uint8_t b){
  return pixels[0].Color(r,g,b);
}

void loop() {
  if(Serial.available()){
    String line = Serial.readStringUntil('\n');
    line.trim();
    if(line.startsWith("TRIAL")){
      int trial = line.substring(6).toInt();
      runTrial(trial);
    }
  }
}

void runTrial(int trial){
  // Clear all first
  for(int i = 0; i < NUM_PIXELS; i++){
    pixels[i].setPixelColor(0, 0);
  }
  
  switch(trial){
    case 1: pixels[0].setPixelColor(0, colorRGB(255,0,0)); break; // LED 1 red
    case 2: pixels[1].setPixelColor(0, colorRGB(0,0,255)); break; // LED 2 blue
    case 3: pixels[2].setPixelColor(0, colorRGB(0,255,0)); break; // LED 3 green
    case 4: pixels[3].setPixelColor(0, colorRGB(255,255,0)); break; // LED 4 yellow
    case 5: {
      // Two random LEDs, one green, one red
      int first = random(0, NUM_PIXELS);
      int second;
      do { second = random(0, NUM_PIXELS); } while(second == first);
      pixels[first].setPixelColor(0, colorRGB(0,255,0)); // green
      pixels[second].setPixelColor(0, colorRGB(255,0,0)); // red
      break;
    }
    case 6: {
      // Three random LEDs, two green, one red
      int indices[NUM_PIXELS] = {0,1,2,3};
      // shuffle
      for(int i = NUM_PIXELS-1; i>0; i--){
        int j = random(0,i+1);
        int temp = indices[i]; indices[i]=indices[j]; indices[j]=temp;
      }
      pixels[indices[0]].setPixelColor(0, colorRGB(0,255,0));
      pixels[indices[1]].setPixelColor(0, colorRGB(0,255,0));
      pixels[indices[2]].setPixelColor(0, colorRGB(255,0,0));
      break;
    }
  }
  for(int i=0; i<NUM_PIXELS; i++) pixels[i].show();
}
