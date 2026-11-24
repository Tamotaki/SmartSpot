"""
serial_reader.py — Lit les données Arduino via USB et les envoie au serveur Flask
─────────────────────────────────────────────────────────────────────────────────
Format attendu depuis Arduino (via Serial.println) :
  "1,0,1"  →  Place 1 occupée, Place 2 libre, Place 3 occupée

Usage :
  python serial_reader.py
  python serial_reader.py --port COM3       (Windows)
  python serial_reader.py --port /dev/ttyUSB0  (Linux/Mac)
""" 
import serial
import requests
import time
import argparse
import sys

FLASK_URL = 'http://localhost:5000/api/update_place'
BAUD_RATE = 9600
INTERVAL  = 1  # secondes entre chaque lecture

def detecter_port():
    """Essaie de détecter automatiquement le port Arduino"""
    ports_linux = [f'/dev/ttyUSB{i}' for i in range(4)] + [f'/dev/ttyACM{i}' for i in range(4)]
    ports_win   = [f'COM{i}' for i in range(1, 10)]
    for port in ports_linux + ports_win:
        try:
            s = serial.Serial(port, BAUD_RATE, timeout=1)
            s.close()
            print(f"[OK] Arduino détecté sur {port}")
            return port
        except:
            pass
    return None

def lire_arduino(port):
    print(f"[INFO] Connexion à Arduino sur {port} à {BAUD_RATE} bauds...")
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2)
        time.sleep(2)  # Attendre l'initialisation Arduino
        print("[OK] Connecté ! Lecture en cours...\n")

        while True:
            if ser.in_waiting > 0:
                ligne = ser.readline().decode('utf-8', errors='ignore').strip()
                if ligne:
                    traiter_ligne(ligne)
            time.sleep(INTERVAL)

    except serial.SerialException as e:
        print(f"[ERREUR] Erreur série : {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[STOP] Arrêt du lecteur série.")
        ser.close()

def traiter_ligne(ligne):
    """
    Parse la ligne Arduino "1,0,1" et envoie à Flask.
    1 = occupée, 0 = libre
    """
    parties = ligne.split(',')
    if len(parties) != 3:
        print(f"[ATTENTION] Format inattendu : '{ligne}'")
        return

    statuts = []
    for i, val in enumerate(parties, start=1):
        val = val.strip()
        if val == '1':
            statut = 'occupee'
        elif val == '0':
            statut = 'libre'
        else:
            print(f"[ATTENTION] Valeur inconnue pour place {i} : '{val}'")
            continue
        statuts.append({'id': i, 'statut': statut})

    # Affichage console
    affichage = []
    for s in statuts:
        etat = 'OCC' if s['statut'] == 'occupee' else 'LIBRE'
        affichage.append(f"P{s['id']} {etat}")
    print(f"[Arduino] {' | '.join(affichage)}")

    # Envoi au serveur Flask
    try:
        r = requests.post(FLASK_URL, json={'statuts': statuts}, timeout=3)
        if r.status_code == 200:
            print(f"   [OK] Serveur mis à jour")
        else:
            print(f"   [ATTENTION] Serveur a répondu {r.status_code}")
    except requests.exceptions.ConnectionError:
        print("   [ERREUR] Impossible de joindre le serveur Flask (démarré ?)")

# ── MODE SIMULATION (sans Arduino) ────────────────────────────
def mode_simulation():
    """Simule des données Arduino pour tester sans matériel"""
    import random
    print("[SIMULATION] Pas d'Arduino connecté")
    print("   Les statuts sont générés aléatoirement.\n")
    try:
        while True:
            statuts = []
            for i in range(1, 4):
                statut = random.choice(['libre', 'occupee'])
                statuts.append({'id': i, 'statut': statut})
            affichage = []
            for s in statuts:
                etat = 'OCC' if s['statut'] == 'occupee' else 'LIBRE'
                affichage.append(f"P{s['id']} {etat}")
            print(f"[SIMULATION] {' | '.join(affichage)}")
            try:
                r = requests.post(FLASK_URL, json={'statuts': statuts}, timeout=3)
                print(f"   [OK] Serveur mis à jour") if r.status_code == 200 else print(f"   [ATTENTION] {r.status_code}")
            except:
                print("   [ERREUR] Serveur Flask non joignable")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[STOP] Simulation arrêtée.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SmartSpot — Lecteur série Arduino')
    parser.add_argument('--port', help='Port série (ex: COM3 ou /dev/ttyUSB0)')
    parser.add_argument('--sim', action='store_true', help='Mode simulation sans Arduino')
    args = parser.parse_args()

    if args.sim:
        mode_simulation()
    else:
        port = args.port or detecter_port()
        if not port:
            print("[ATTENTION] Aucun Arduino détecté automatiquement.")
            print("    Utilise --port pour spécifier manuellement.")
            print("    Ou --sim pour lancer la simulation.\n")
            mode_simulation()
        else:
            lire_arduino(port)
