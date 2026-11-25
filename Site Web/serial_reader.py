"""
serial_reader.py — Pont série bidirectionnel Arduino <-> Serveur Flask SmartSpot
Arduino -> Python (JSON, 9600 bauds) :
  {"p1":1,"p2":0,"p3":0,"r1":0,"r2":1,"r3":0,"occupees":2,"libres":1}
  {"event":"rfid","uid":"A1B2C3D4"}

Python -> Arduino (Commandes texte terminées par \n) :
  RES:1:1  -> Réserver la place 1 (allume sa LED)
  RES:1:0  -> Libérer la réservation de la place 1

Usage :
  python serial_reader.py
  python serial_reader.py --port /dev/cu.usbmodem1101
  python serial_reader.py --sim
"""
import argparse
import json
import sys
import time
import requests
import serial
import serial.tools.list_ports

import os

FLASK_BASE = os.environ.get('SMARTSPOT_URL', 'http://localhost:5000')
FLASK_UPDATE_URL = f'{FLASK_BASE}/api/update_place'
FLASK_PLACES_URL = f'{FLASK_BASE}/api/places'
BAUD_RATE = 9600
SYNC_INTERVAL = 1.0  # secondes entre chaque synchro des réservations


def detecter_port():
    """Détecte automatiquement le port série Arduino (macOS, Linux, Windows)."""
    ports = list(serial.tools.list_ports.comports())
    mots_cles = ('arduino', 'usbmodem', 'usbserial', 'ch340', 'cp210', 'ttyacm', 'ttyusb')

    for p in ports:
        desc = f"{p.device} {p.description} {p.manufacturer or ''}".lower()
        if any(k in desc for k in mots_cles):
            print(f"[OK] Arduino détecté sur {p.device} ({p.description})")
            return p.device
    return None


def synchroniser_reservations(ser, dernier_etat_reserve, force=False):
    """Récupère les réservations depuis Flask et envoie RES:<id>:<0|1> à l'Arduino."""
    try:
        r = requests.get(FLASK_PLACES_URL, timeout=2)
        if r.status_code != 200:
            return
        for place in r.json():
            pid = place.get('id')
            est_reservee = (place.get('statut') == 'reservee')
            if pid in dernier_etat_reserve and (force or dernier_etat_reserve[pid] != est_reservee):
                cmd = f"RES:{pid}:{1 if est_reservee else 0}\n"
                ser.write(cmd.encode('utf-8'))
                dernier_etat_reserve[pid] = est_reservee
                print(f"[Site -> Arduino] {cmd.strip()}")
    except requests.exceptions.RequestException:
        pass


def lire_arduino(port):
    print(f"[INFO] Connexion à Arduino sur {port} à {BAUD_RATE} bauds...")
    ser = None
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=0.5)
        time.sleep(2)  # Attendre le redémarrage de l'Arduino
        print("[OK] Connecté ! Lecture/écriture en cours...\n")

        dernier_etat_reserve = {1: False, 2: False, 3: False}
        synchroniser_reservations(ser, dernier_etat_reserve, force=True)
        derniere_synchro = time.time()

        while True:
            while ser.in_waiting > 0:
                ligne = ser.readline().decode('utf-8', errors='ignore').strip()
                if ligne:
                    traiter_ligne(ligne)

            if time.time() - derniere_synchro >= SYNC_INTERVAL:
                synchroniser_reservations(ser, dernier_etat_reserve)
                derniere_synchro = time.time()

            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"[ERREUR] Erreur série : {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[STOP] Arrêt du lecteur série.")
        if ser and ser.is_open:
            ser.close()


def traiter_ligne(ligne):
    """Parse une ligne JSON (ou CSV en secours) envoyée par l'Arduino et met à jour Flask."""
    statuts = []

    if ligne.startswith('{'):
        try:
            data = json.loads(ligne)
        except json.JSONDecodeError:
            print(f"[ATTENTION] JSON invalide : '{ligne}'")
            return

        if data.get('event') == 'rfid':
            print(f"[RFID] Badge détecté : {data.get('uid')}")
            return

        if 'p1' in data and 'p2' in data and 'p3' in data:
            for i in range(1, 4):
                statut = 'occupee' if data.get(f'p{i}') == 1 else 'libre'
                statuts.append({'id': i, 'statut': statut})
        else:
            return
    else:
        parties = ligne.split(',')
        if len(parties) != 3:
            print(f"[ATTENTION] Format inattendu : '{ligne}'")
            return
        for i, val in enumerate(parties, start=1):
            val = val.strip()
            if val == '1':
                statuts.append({'id': i, 'statut': 'occupee'})
            elif val == '0':
                statuts.append({'id': i, 'statut': 'libre'})

    if not statuts:
        return

    affichage = [f"P{s['id']} {'OCC' if s['statut'] == 'occupee' else 'LIBRE'}" for s in statuts]
    print(f"[Arduino] {' | '.join(affichage)}")

    try:
        r = requests.post(FLASK_UPDATE_URL, json={'statuts': statuts}, timeout=3)
        if r.status_code != 200:
            print(f"   [ATTENTION] Serveur a répondu {r.status_code}")
    except requests.exceptions.ConnectionError:
        print("   [ERREUR] Impossible de joindre le serveur Flask (démarré ?)")


def mode_simulation():
    """Simule des données Arduino pour tester sans matériel."""
    import random
    print("[SIMULATION] Pas d'Arduino connecté — statuts générés aléatoirement.\n")
    try:
        while True:
            statuts = [{'id': i, 'statut': random.choice(['libre', 'occupee'])} for i in range(1, 4)]
            affichage = [f"P{s['id']} {'OCC' if s['statut'] == 'occupee' else 'LIBRE'}" for s in statuts]
            print(f"[SIMULATION] {' | '.join(affichage)}")
            try:
                r = requests.post(FLASK_UPDATE_URL, json={'statuts': statuts}, timeout=3)
                if r.status_code != 200:
                    print(f"   [ATTENTION] {r.status_code}")
            except requests.exceptions.RequestException:
                print("   [ERREUR] Serveur Flask non joignable")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[STOP] Simulation arrêtée.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SmartSpot — Lecteur série Arduino')
    parser.add_argument('--port', help='Port série (ex: COM3, /dev/ttyUSB0, /dev/cu.usbmodem1101)')
    parser.add_argument('--sim', action='store_true', help='Mode simulation sans Arduino')
    args = parser.parse_args()

    if args.sim:
        mode_simulation()
    else:
        port = args.port or detecter_port()
        if not port:
            print("[ATTENTION] Aucun Arduino détecté automatiquement.")
            print("    Utilise --port pour spécifier manuellement, ou --sim pour la simulation.\n")
            mode_simulation()
        else:
            lire_arduino(port)
