#include <LiquidCrystal.h>
#include <Servo.h>
#include <SPI.h>
#include <MFRC522.h>

// Déclaration des broches du module radar 1
const int trigPin1 = 11;   // broche qui envoie l'impulsion sonore
const int echoPin1 = 10;   // broche qui reçoit le signal réfléchi

// Broches radar 2
const int trigPin2 = 9;
const int echoPin2 = 46;    // Broche PWM

// Broches radar 3
const int trigPin3 = 45;    // Broche PWM
const int echoPin3 = 44;    // Broche PWM

// Lecteur RFID MFRC522
const int SS_PIN = 53;
const int RST_PIN = 5;
MFRC522 rfid(SS_PIN, RST_PIN);

// Paramètres du système
const int totalPlaces = 3;
const float seuilPresence = 30.0; // en cm

// Broches du LCD 1602 (mode 4 bits)
const int rs = 22;
const int en = 23;
const int d4 = 24;
const int d5 = 25;
const int d6 = 26;
const int d7 = 27;

// Barrière pilotée par servo motor
const int pinServo = 8;
const int angleBarriereFermee = 90;
const int angleBarriereOuverte = 180;
const unsigned long delaiOuverture = 2500; // 2.5 s

LiquidCrystal lcd(rs, en, d4, d5, d6, d7);
Servo barriereServo;
bool barriereOuverte = false;
unsigned long dernierBadgeDetecte = 0;

void setup() {
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);
  pinMode(trigPin3, OUTPUT);
  pinMode(echoPin3, INPUT);

  SPI.begin();
  rfid.PCD_Init();

  barriereServo.attach(pinServo);
  fermerBarriere();

  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SmartSpot");
  lcd.setCursor(0, 1);
  lcd.print("Initialisation...");

  Serial.begin(9600);
  delay(1000);
}

void loop() {
  float distance1 = mesurerDistance(trigPin1, echoPin1);
  float distance2 = mesurerDistance(trigPin2, echoPin2);
  float distance3 = mesurerDistance(trigPin3, echoPin3);

  bool place1Occupee = (distance1 < seuilPresence);
  bool place2Occupee = (distance2 < seuilPresence);
  bool place3Occupee = (distance3 < seuilPresence);

  int placesOccupees = 0;
  if (place1Occupee) placesOccupees++;
  if (place2Occupee) placesOccupees++;
  if (place3Occupee) placesOccupees++;

  int placesLibres = totalPlaces - placesOccupees;

  Serial.print("Place1: ");
  Serial.print(distance1);
  Serial.print(" cm | Place2: ");
  Serial.print(distance2);
  Serial.print(" cm | Place3: ");
  Serial.print(distance3);
  Serial.print(" cm | Libres: ");
  Serial.println(placesLibres);

  gererBadgeRFID();
  afficherLCD(placesLibres, place1Occupee, place2Occupee, place3Occupee);

  delay(300);
}

float mesurerDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duree = pulseIn(echoPin, HIGH);
  float distance = duree * 0.0343 / 2;

  return distance;
}

void gererBadgeRFID() {
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  unsigned long now = millis();
  if (now - dernierBadgeDetecte < 2000) {
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return;
  }

  dernierBadgeDetecte = now;
  Serial.print("Badge RFID detecte: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    Serial.print(rfid.uid.uidByte[i], HEX);
  }
  Serial.println();

  ouvrirBarriere();
  delay(delaiOuverture);
  fermerBarriere();

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void ouvrirBarriere() {
  barriereServo.write(angleBarriereOuverte);
  barriereOuverte = true;
  Serial.println("Barriere ouverte");
}

void fermerBarriere() {
  barriereServo.write(angleBarriereFermee);
  barriereOuverte = false;
  Serial.println("Barriere fermee");
}

void afficherLCD(int placesLibres, bool place1Occupee, bool place2Occupee, bool place3Occupee) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Libres: ");
  lcd.print(placesLibres);
  lcd.setCursor(12, 0);
  lcd.print(barriereOuverte ? "O" : "F");

  lcd.setCursor(0, 1);
  lcd.print("P1:");
  lcd.print(place1Occupee ? "O" : "L");
  lcd.print(" P2:");
  lcd.print(place2Occupee ? "O" : "L");
  lcd.print(" P3:");
  lcd.print(place3Occupee ? "O" : "L");
}

