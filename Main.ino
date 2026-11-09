#include <LiquidCrystal.h>
#include <Servo.h>

// Déclaration des broches du module radar 1
const int trigPin1 = 11;   // broche qui envoie l'impulsion sonore
const int echoPin1 = 10;   // broche qui reçoit le signal réfléchi

// Broches radar 2
const int trigPin2 = 9;
const int echoPin2 = 46;    // Broche PWM

// Broches radar 3
const int trigPin3 = 45;    // Broche PWM
const int echoPin3 = 44;    // Broche PWM

// Radar d'entrée pour détecter un véhicule devant la barrière
const int trigPinEntree = 12;
const int echoPinEntree = 13;

// Paramètres du système
const int totalPlaces = 3;
const float seuilPresence = 30.0; // en cm
const float seuilVehicule = 40.0; // en cm

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

LiquidCrystal lcd(rs, en, d4, d5, d6, d7);
Servo barriereServo;
bool barriereOuverte = false;

void setup() {
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);
  pinMode(trigPin3, OUTPUT);
  pinMode(echoPin3, INPUT);
  pinMode(trigPinEntree, OUTPUT);
  pinMode(echoPinEntree, INPUT);

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
  float distanceEntree = mesurerDistance(trigPinEntree, echoPinEntree);

  bool place1Occupee = (distance1 < seuilPresence);
  bool place2Occupee = (distance2 < seuilPresence);
  bool place3Occupee = (distance3 < seuilPresence);
  bool vehiculeDetecte = (distanceEntree < seuilVehicule);

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
  Serial.print(" cm | Entree: ");
  Serial.print(distanceEntree);
  Serial.print(" cm | Libres: ");
  Serial.println(placesLibres);

  gererBarriere(vehiculeDetecte);
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

void gererBarriere(bool vehiculeDetecte) {
  if (vehiculeDetecte && !barriereOuverte) {
    ouvrirBarriere();
  }

  if (!vehiculeDetecte && barriereOuverte) {
    fermerBarriere();
  }
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

