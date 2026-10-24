/*
  Quantum Inspired Early Warning System for Structural Failure
  Arduino UNO firmware

  - Reads a flexible (bend/strain) sensor on A0 and an SW420 vibration sensor on A1
  - Streams the raw readings to the host over serial as:  FLEX:<0-1023>,VIB:<0-1023>
  - Receives a one-character status command from the Python risk monitor:
        'S' = SAFE    -> green LED, buzzer off
        'W' = WARNING -> yellow LED, buzzer beeps
        'D' = DANGER  -> red LED, buzzer continuous
*/

// ---------- Pin configuration ----------
const int FLEX_PIN   = A0;   // flexible sensor (voltage divider)
const int VIB_PIN    = A1;   // SW420 vibration sensor (analog / output pin)
const int GREEN_LED  = 8;    // traffic light module: green
const int YELLOW_LED = 9;    // traffic light module: yellow
const int RED_LED    = 10;   // traffic light module: red
const int BUZZER_PIN = 11;   // 5V active buzzer

// ---------- Timing ----------
const unsigned long SAMPLE_INTERVAL_MS = 100;   // 10 readings per second
const unsigned long BEEP_PERIOD_MS     = 1000;  // warning beep cycle
const unsigned long BEEP_ON_MS         = 150;   // beep length inside the cycle

char status = 'S';
unsigned long lastSample = 0;

void applyStatus() {
  digitalWrite(GREEN_LED,  status == 'S' ? HIGH : LOW);
  digitalWrite(YELLOW_LED, status == 'W' ? HIGH : LOW);
  digitalWrite(RED_LED,    status == 'D' ? HIGH : LOW);
}

void readCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'S' || c == 'W' || c == 'D') {
      status = c;
      applyStatus();
    }
  }
}

void sendReadings() {
  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_INTERVAL_MS) {
    lastSample = now;
    int flex = analogRead(FLEX_PIN);
    int vib  = analogRead(VIB_PIN);
    Serial.print("FLEX:");
    Serial.print(flex);
    Serial.print(",VIB:");
    Serial.println(vib);
  }
}

void updateBuzzer() {
  if (status == 'D') {
    digitalWrite(BUZZER_PIN, HIGH);                       // continuous alarm
  } else if (status == 'W') {
    bool on = (millis() % BEEP_PERIOD_MS) < BEEP_ON_MS;   // short beep every second
    digitalWrite(BUZZER_PIN, on ? HIGH : LOW);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  applyStatus();
}

void loop() {
  readCommands();
  sendReadings();
  updateBuzzer();
}
