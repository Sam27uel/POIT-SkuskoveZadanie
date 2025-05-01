#include <Servo.h>

const int trigPin = 11;
const int echoPin = 12;
const int servoPin = 9;

const int redLEDPin = 6;
const int greenLEDPin = 7;
const int statusLEDPin = 5;  // LED pre signalizáciu OPEN

#define SOUND_VELOCITY 0.034
#define OPEN_ANGLE 90
#define CLOSE_ANGLE 0

long duration;
float distanceCm;
int threshold = 20;

Servo gateServo;
bool isGateOpen = false;
bool isAutoMode = false;
bool isSystemActive = true;

void setup() {
  Serial.begin(9600);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  pinMode(redLEDPin, OUTPUT);
  pinMode(greenLEDPin, OUTPUT);
  pinMode(statusLEDPin, OUTPUT);

  gateServo.attach(servoPin);
  closeGate();
  digitalWrite(statusLEDPin, LOW);

  Serial.println("Systém pripravený.");
}

void loop() {
  // 💡 Vyčistenie vstupného buffera, ak by tam ostali znaky po CLOSE
  while (Serial.available() > 1) {
    Serial.read();  // zahoď všetky nevybavené znaky okrem aktuálneho
  }

  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();  // odstráni \r a \n

    Serial.print("Prijatý príkaz: ");
    Serial.println(input);

    if (input.startsWith("T")) {
      threshold = input.substring(1).toInt();
      Serial.print("Threshold nastavený na: ");
      Serial.println(threshold);
    } 
    else if (input == "A") {
      isSystemActive = true;
      isAutoMode = true;
      Serial.println("Automatický režim zapnutý");
    } 
    else if (input == "M") {
      isSystemActive = true;
      isAutoMode = false;
      Serial.println("Manuálny režim zapnutý");
    } 
    else if (input == "S") {
      isAutoMode = false;
      closeGate();
      Serial.println("Monitorovanie zastavené príkazom STOP");
    } 
    else if (input == "O" && isSystemActive && !isAutoMode) {
      openGate();
      Serial.println("Brána otvorená (manuálne)");
    } 
    else if (input == "C" && isSystemActive && !isAutoMode) {
      closeGate();
      Serial.println("Brána zatvorená (manuálne)");
    } 
    else if (input == "X") {
      isSystemActive = false;
      isAutoMode = false;
      shutdownSystem();
      Serial.println("Systém deaktivovaný príkazom CLOSE");
    } 
    else if (input == "P") {
      digitalWrite(statusLEDPin, HIGH);
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
  digitalWrite(statusLEDPin, LOW);  // LED OFF pri CLOSE
}
