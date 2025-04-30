#include <Servo.h>

const int trigPin = 11;
const int echoPin = 12;
const int servoPin = 9;

const int redLEDPin = 6;
const int greenLEDPin = 7;

#define SOUND_VELOCITY 0.034
#define OPEN_ANGLE 90
#define CLOSE_ANGLE 0

long duration;
float distanceCm;
int threshold = 20;

Servo gateServo;
bool isGateOpen = false;
bool isAutoMode = false;

void setup() {
  Serial.begin(9600);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  pinMode(redLEDPin, OUTPUT);
  pinMode(greenLEDPin, OUTPUT);

  gateServo.attach(servoPin);
  closeGate(); // Začneme so zatvorenou bránou
  Serial.println("Systém pripravený.");
}

void loop() {
  // Spracovanie príkazov
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');

    if (input.startsWith("T")) {
      threshold = input.substring(1).toInt();
      Serial.print("Threshold nastavený na: ");
      Serial.println(threshold);
    } else if (input == "A") {
      isAutoMode = true;
      Serial.println("Automatický režim zapnutý");
    } else if (input == "M") {
      isAutoMode = false;
      Serial.println("Manuálny režim zapnutý");
    } else if (input == "O" && !isAutoMode) {
      openGate();
      Serial.println("Brána otvorená (manuálne)");
    } else if (input == "C" && !isAutoMode) {
      closeGate();
      Serial.println("Brána zatvorená (manuálne)");
    }
  }

  // Automatický režim
  if (isAutoMode) {
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
    } else if (distanceCm > threshold + 1 && isGateOpen) {
      closeGate();
      Serial.println("Brána zatvorená (automaticky)");
    }

    delay(500);
  }
}

// Pomocné funkcie
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
