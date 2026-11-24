#include <LiquidCrystal.h>
#include <Servo.h>
#include <SPI.h>
#include <MFRC522.h>

//  Capteurs ultrasons HC-SR04 
const int trigPins[3] = {11, 9, 45};
const int echoPins[3] = {10, 46, 44};

//  LEDs d'état par place (allumée = occupée ou réservée) 
const int ledPins[3] = {30, 31, 32};

//  Lecteur RFID MFRC522 (SPI Mega : 50=MISO, 51=MOSI, 52=SCK, 53=SS) 
const int SS_PIN = 53;
const int RST_PIN = 5;
MFRC522 rfid(SS_PIN, RST_PIN);

//  LCD 1602 (mode 4 bits) 
const int rs = 22, en = 23, d4 = 24, d5 = 25, d6 = 26, d7 = 27;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

//  Barrière Servomoteur SG90 
const int pinServo = 8;
const int angleBarriereFermee = 90;
const int angleBarriereOuverte = 180;
const unsigned long delaiOuverture = 2500; // 2.5 s
Servo barriereServo;

//  Paramètres 
const int totalPlaces = 3;
const float seuilPresence = 30.0; // cm
const unsigned long intervalleEnvoi = 500; // ms

//  États 
bool placeOccupee[3] = {false, false, false};
bool placeReservee[3] = {false, false, false};
bool barriereOuverte = false;
unsigned long heureOuverture = 0;
unsigned long dernierBadgeDetecte = 0;
unsigned long dernierEnvoi = 0;
String bufferSerie = "";

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < 3; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  SPI.begin();
  rfid.PCD_Init();

  barriereServo.attach(pinServo);
  fermerBarriere();

  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SmartSpot");
  lcd.setCursor(0, 1);
  lcd.print("Initialisation..");
  delay(1000);
  lcd.clear();
}

void loop() {
  // 1. Lire les commandes venant du site web (réservations)
  lireCommandesSerie();

  // 2. Mesurer les 3 places (avec pause anti-interférence)
  int placesPrises = 0;
  for (int i = 0; i < 3; i++) {
    float dist = mesurerDistance(trigPins[i], echoPins[i]);
    placeOccupee[i] = (dist > 0 && dist < seuilPresence);

    // Une place est prise si elle est occupée physiquement OU réservée sur le site
    bool prise = placeOccupee[i] || placeReservee[i];
    digitalWrite(ledPins[i], prise ? HIGH : LOW);

    if (prise) placesPrises++;
    delay(25);
  }

  int placesLibres = totalPlaces - placesPrises;

  // 3. Gérer le badge RFID et la fermeture automatique non bloquante
  gererBadgeRFID(placesLibres);
  gererFermetureBarriere();

  // 4. Mettre à jour le LCD sans scintillement
  afficherLCD(placesLibres);

  // 5. Envoyer l'état au site web périodiquement
  if (millis() - dernierEnvoi >= intervalleEnvoi) {
    dernierEnvoi = millis();
    envoyerEtatSerie(placesPrises, placesLibres);
  }
}

float mesurerDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Timeout 30 ms (~5 m) pour éviter de bloquer l'Arduino
  long duree = pulseIn(echoPin, HIGH, 30000);
  if (duree == 0) {
    return 999.0; // Aucun obstacle détecté
  }
  return duree * 0.0343 / 2.0;
}

void gererBadgeRFID(int placesLibres) {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  unsigned long now = millis();
  if (now - dernierBadgeDetecte >= 2000) {
    dernierBadgeDetecte = now;

    // Envoi de l'UID au serveur web
    Serial.print("{\"event\":\"rfid\",\"uid\":\"");
    for (byte i = 0; i < rfid.uid.size; i++) {
      if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
      Serial.print(rfid.uid.uidByte[i], HEX);
    }
    Serial.println("\"}");

    // Ouvre la barrière (si tu veux bloquer quand complet, ajoute: if (placesLibres > 0))
    ouvrirBarriere();
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void ouvrirBarriere() {
  barriereServo.write(angleBarriereOuverte);
  barriereOuverte = true;
  heureOuverture = millis();
}

void fermerBarriere() {
  barriereServo.write(angleBarriereFermee);
  barriereOuverte = false;
}

void gererFermetureBarriere() {
  if (barriereOuverte && (millis() - heureOuverture >= delaiOuverture)) {
    fermerBarriere();
  }
}

void lireCommandesSerie() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      bufferSerie.trim();
      // Format attendu : RES:<place 1-3>:<0 ou 1>  ex: RES:2:1
      if (bufferSerie.startsWith("RES:") && bufferSerie.length() >= 7) {
        int numPlace = bufferSerie.substring(4, 5).toInt();
        int etat = bufferSerie.substring(6, 7).toInt();
        if (numPlace >= 1 && numPlace <= 3) {
          placeReservee[numPlace - 1] = (etat == 1);
        }
      }
      bufferSerie = "";
    } else {
      bufferSerie += c;
    }
  }
}

void envoyerEtatSerie(int placesPrises, int placesLibres) {
  Serial.print("{\"p1\":"); Serial.print(placeOccupee[0] ? 1 : 0);
  Serial.print(",\"p2\":"); Serial.print(placeOccupee[1] ? 1 : 0);
  Serial.print(",\"p3\":"); Serial.print(placeOccupee[2] ? 1 : 0);
  Serial.print(",\"r1\":"); Serial.print(placeReservee[0] ? 1 : 0);
  Serial.print(",\"r2\":"); Serial.print(placeReservee[1] ? 1 : 0);
  Serial.print(",\"r3\":"); Serial.print(placeReservee[2] ? 1 : 0);
  Serial.print(",\"occupees\":"); Serial.print(placesPrises);
  Serial.print(",\"libres\":"); Serial.print(placesLibres);
  Serial.println("}");
}

void afficherLCD(int placesLibres) {
  lcd.setCursor(0, 0);
  lcd.print("Libres: ");
  lcd.print(placesLibres);
  lcd.print("   Bar:");
  lcd.print(barriereOuverte ? "O " : "F ");

  lcd.setCursor(0, 1);
  for (int i = 0; i < 3; i++) {
    lcd.print("P");
    lcd.print(i + 1);
    lcd.print(":");
    if (placeOccupee[i]) lcd.print("O");
    else if (placeReservee[i]) lcd.print("R");
    else lcd.print("L");
    if (i < 2) lcd.print(" ");
  }
  lcd.print("  ");
}
