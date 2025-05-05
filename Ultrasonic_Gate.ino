#include <Servo.h>

const int trigPin = 11;
const int echoPin = 12;
const int servoPin = 9;
const int buzzerPin = 3;

const int redLEDPin = 6;
const int greenLEDPin = 7;
const int statusLEDPin = 5;

#define SOUND_VELOCITY 0.034
#define OPEN_ANGLE 90
#define CLOSE_ANGLE 0

long duration;
float distanceCm;
int threshold = 10;

Servo gateServo;
bool isGateOpen = false;
bool isAutoMode = false;
bool isSystemActive = true;

bool lastAuto = false;
bool lastManual = false;

void setup() {
  Serial.begin(9600);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  pinMode(redLEDPin, OUTPUT);
  pinMode(greenLEDPin, OUTPUT);
  pinMode(statusLEDPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  gateServo.attach(servoPin);
  closeGate();
  digitalWrite(statusLEDPin, LOW);

  Serial.println("Systém pripravený.");
}

void loop() {
  if (Serial.available()) {
    String input = "";
    while (Serial.available()) {
      char ch = Serial.read();
      if (ch == '\n') break;
      input += ch;
    }
    input.trim();

    Serial.print("📥 Prijatý príkaz: >");
    Serial.print(input);
    Serial.println("<");

    if (input.startsWith("T")) {
      String numPart = input.substring(1);
      Serial.print("➡️ Čítam threshold: ");
      Serial.println(numPart);
      threshold = numPart.toInt();
      Serial.print("✅ Threshold nastavený na: ");
      Serial.println(threshold);
      playTick();
    } 
    else if (input == "A") {
      isSystemActive = true;
      isAutoMode = true;
      Serial.println("Automatický režim zapnutý");
      if (!lastAuto) {
        playAutoModeSound();
        lastAuto = true;
        lastManual = false;
      }
    } 
    else if (input == "M") {
      isSystemActive = true;
      isAutoMode = false;
      Serial.println("Manuálny režim zapnutý");
      if (!lastManual) {
        playManualModeSound();
        lastManual = true;
        lastAuto = false;
      }
    } 
    else if (input == "S") {
      isAutoMode = false;
      closeGate();
      playStopMonitoringSound();  // 🆕 Nový zvuk pri stopnutí monitorovania
      Serial.println("Monitorovanie zastavené príkazom STOP");
    } 
    else if (input == "O" && isSystemActive && !isAutoMode) {
      openGate();
      Serial.println("Brána otvorená (manuálne)");
      playTick();
    } 
    else if (input == "C" && isSystemActive && !isAutoMode) {
      closeGate();
      Serial.println("Brána zatvorená (manuálne)");
      playTick();
    } 
    else if (input == "X") {
      isSystemActive = false;
      isAutoMode = false;
      shutdownSystem();
      playShutdownSound();  // 🆕 Nová "game over" melódia
      Serial.println("Systém deaktivovaný príkazom CLOSE");
    } 
    else if (input == "P") {
      digitalWrite(statusLEDPin, HIGH);
      playStartupSound();
      Serial.println("Pripojenie nadviazané – LED ON");
    }
  }

  if (isSystemActive && isAutoMode) {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    duration = pulseIn(echoPin, HIGH);
    distanceCm = duration * SOUND_VELOCITY / 2;

    Serial.print("Vzdialenosť: ");
    Serial.print(distanceCm);
    Serial.println(" cm");

    if (distanceCm < 3.0) {
      playWarningMelody();
    }

    if (distanceCm < threshold && !isGateOpen) {
      openGate();
      Serial.println("Brána otvorená (automaticky)");
    } 
    else if (distanceCm > threshold + 1 && isGateOpen) {
      closeGate();
      Serial.println("Brána zatvorená (automaticky)");
    }

    delay(500);
  }
}

// === Pomocné funkcie ===

void openGate() {
  gateServo.write(OPEN_ANGLE);
  isGateOpen = true;
  digitalWrite(redLEDPin, LOW);
  digitalWrite(greenLEDPin, HIGH);
}

void closeGate() {
  gateServo.write(CLOSE_ANGLE);
  isGateOpen = false;
  digitalWrite(greenLEDPin, LOW);
  digitalWrite(redLEDPin, HIGH);
}

void shutdownSystem() {
  gateServo.write(CLOSE_ANGLE);
  digitalWrite(greenLEDPin, LOW);
  digitalWrite(redLEDPin, LOW);
  digitalWrite(statusLEDPin, LOW);
}

// === Zvukové upozornenia ===

void playWarningMelody() {
  int melody[] = { 784, 659, 880, 988 }; // G5, E5, A5, B5
  int durations[] = { 150, 150, 150, 300 };

  for (int i = 0; i < 4; i++) {
    tone(buzzerPin, melody[i]);
    delay(durations[i]);
    noTone(buzzerPin);
    delay(50);
  }
}

void playManualModeSound() {
  int melody[] = { 523, 440, 392 }; // C5, A4, G4
  int duration = 200;
  for (int i = 0; i < 3; i++) {
    tone(buzzerPin, melody[i]);
    delay(duration);
    noTone(buzzerPin);
    delay(50);
  }
}

void playAutoModeSound() {
  int melody[] = { 659, 784 }; // E5, G5
  int duration = 250;
  for (int i = 0; i < 2; i++) {
    tone(buzzerPin, melody[i]);
    delay(duration);
    noTone(buzzerPin);
    delay(70);
  }
}

void playStartupSound() {
  int melody[] = { 262, 294, 330, 392 }; // C4, D4, E4, G4
  for (int i = 0; i < 4; i++) {
    tone(buzzerPin, melody[i]);
    delay(180);
    noTone(buzzerPin);
    delay(40);
  }
}

void playShutdownSound() {
  int melody[] = { 659, 587, 523, 440 }; // E5, D5, C5, A4 (game over štýl)
  int durations[] = { 200, 200, 200, 400 };

  for (int i = 0; i < 4; i++) {
    tone(buzzerPin, melody[i]);
    delay(durations[i]);
    noTone(buzzerPin);
    delay(60);
  }
}

void playStopMonitoringSound() {
  int melody[] = { 392, 330, 294, 262 }; // G4, E4, D4, C4
  for (int i = 0; i < 4; i++) {
    tone(buzzerPin, melody[i]);
    delay(160);
    noTone(buzzerPin);
    delay(40);
  }
}

void playTick() {
  tone(buzzerPin, 1046); // C6
  delay(100);
  noTone(buzzerPin);
}
