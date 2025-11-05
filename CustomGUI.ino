#this code is to be run with Python complement
#the Python script allows user to choose which buttons should be lit and which colors to light them up as
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
    pixels[i].show();
  }
}

void loop() {
  if(Serial.available()){
    String line = Serial.readStringUntil('\n');
    line.trim();
    if(line.startsWith("C,")){
      // line format: C,R1,G1,B1,R2,G2,B2,R3,G3,B3,R4,G4,B4
      int vals[NUM_PIXELS*3];
      int idx = 0;
      char *str = (char*)line.c_str();
      char *tok = strtok(str, ",");
      while(tok != NULL && idx < NUM_PIXELS*3+1){ // +1 because first "C"
        if(idx > 0){
          vals[idx-1] = atoi(tok);
        }
        idx++;
        tok = strtok(NULL, ",");
      }
      for(int i = 0; i < NUM_PIXELS; i++){
        pixels[i].setPixelColor(0, pixels[0].Color(vals[i*3], vals[i*3+1], vals[i*3+2]));
        pixels[i].show();
      }
    }
  }
}
