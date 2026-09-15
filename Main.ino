//Déclaration des broches du module radar 1
const int trigPin1 = 11;   // broche qui envoie l'impulsion sonore
const int echoPin1 = 10;  // broche qui reçoit le signal réfléchi
//Broches radar 2
const int trigPin2 = 9;  
const int echoPin2 = 46; //Broche PWM
//Broches radar 3
const int trigPin3 = 45; //Broche PWM
const int echoPin3 = 44; //Borhce PWM

// Broches de l'écran
const int segA = 2;
const int segB = 3;
const int segC = 4;
const int segD = 5;
const int segE = 6;
const int segF = 7;
const int segG = 8;

void setup() {
  // put your setup code here, to run once: 
//COMPTEUR PRESENCE
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);
  pinMode(trigPin3, OUTPUT);
  pinMode(echoPin3, INPUT);

//AFFICHAGE LED
  pinMode(segA, OUTPUT);
  pinMode(segB, OUTPUT);
  pinMode(segC, OUTPUT);
  pinMode(segD, OUTPUT);
  pinMode(segE, OUTPUT);
  pinMode(segF, OUTPUT);
  pinMode(segG, OUTPUT);

// Initialiser l'écran serial du terminal Arduino
  Serial.begin(9600);
  
}

void loop() {
  // put your main code here, to run repeatedly:
// On mesure la distance sur chaque place
  float distance1 = mesurerDistance(trigPin1, echoPin1);
  float distance2 = mesurerDistance(trigPin2, echoPin2);
  float distance3 = mesurerDistance(trigPin3, echoPin3);

  // On détermine si chaque place est occupée (true) ou libre (false)
  bool place1Occupee = (distance1 < seuilPresence);
  bool place2Occupee = (distance2 < seuilPresence);
  bool place3Occupee = (distance3 < seuilPresence);

  // On compte le nombre de places occupées
  int placesOccupees = 0;
  if (place1Occupee) placesOccupees++;
  if (place2Occupee) placesOccupees++;
  if (place3Occupee) placesOccupees++;

  // On en déduit le nombre de places libres
  int placesLibres = totalPlaces - placesOccupees;

  // Affichage sur le moniteur série pour vérifier pendant les tests
  Serial.print("Place1: ");
  Serial.print(distance1);
  Serial.print(" cm | Place2: ");
  Serial.print(distance2);
  Serial.print(" cm | Place3: ");
  Serial.print(distance3);
  Serial.print(" cm | Libres: ");
  Serial.println(placesLibres);

  // On affiche le résultat sur l'afficheur 7 segments
  afficherChiffre(placesLibres);

  // Petite pause avant de refaire une mesure
  delay(300);
}

// Fonction qui mesure la distance (en cm) avec un capteur HC-SR04
float mesurerDistance(int trigPin, int echoPin) {
  // On envoie une impulsion ultrason avec TRIG
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // On mesure le temps mis par le signal pour revenir sur ECHO
  long duree = pulseIn(echoPin, HIGH);

  // On convertit ce temps en distance (vitesse du son = 343 m/s)
  float distance = duree * 0.0343 / 2;

  return distance;
}

// Fonction qui allume les bons segments pour afficher un chiffre de 0 à 9
void afficherChiffre(int chiffre) {
  // Pour chaque chiffre, on définit quels segments doivent être allumés
  bool segments[10][7] = {
    // A,     B,     C,     D,     E,     F,     G
    {true,  true,  true,  true,  true,  true,  false}, // 0
    {false, true,  true,  false, false, false, false}, // 1
    {true,  true,  false, true,  true,  false, true},  // 2
    {true,  true,  true,  true,  false, false, true},  // 3
    {false, true,  true,  false, false, true,  true},  // 4
    {true,  false, true,  true,  false, true,  true},  // 5
    {true,  false, true,  true,  true,  true,  true},  // 6
    {true,  true,  true,  false, false, false, false}, // 7
    {true,  true,  true,  true,  true,  true,  true},  // 8
    {true,  true,  true,  true,  false, true,  true}   // 9
  };

  // Sécurité : si le chiffre est en dehors de 0-9, on ne fait rien
  if (chiffre < 0 || chiffre > 9) {
    return;
  }

  // On écrit l'état de chaque segment sur la broche correspondante
  digitalWrite(segA, segments[chiffre][0]);
  digitalWrite(segB, segments[chiffre][1]);
  digitalWrite(segC, segments[chiffre][2]);
  digitalWrite(segD, segments[chiffre][3]);
  digitalWrite(segE, segments[chiffre][4]);
  digitalWrite(segF, segments[chiffre][5]);
  digitalWrite(segG, segments[chiffre][6]);
}

