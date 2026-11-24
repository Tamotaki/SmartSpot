"""
database.py — Initialisation de la base de données SQLite SmartSpot
Exécuter ce fichier une seule fois : python database.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'smartspot.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Table PLACE ──────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PLACE (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            numero  INTEGER NOT NULL UNIQUE,
            statut  TEXT    NOT NULL DEFAULT 'libre'
                            CHECK(statut IN ('libre','occupee','reservee'))
        )
    ''')

    # ── Table UTILISATEUR ─────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS UTILISATEUR (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'etudiant'
                             CHECK(role IN ('admin','etudiant','professeur'))
        )
    ''')

    # ── Table HISTORIQUE ──────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS HISTORIQUE (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id     INTEGER NOT NULL,
            heure_entree TEXT    NOT NULL,
            heure_sortie TEXT,
            FOREIGN KEY (place_id) REFERENCES PLACE(id)
        )
    ''')

    # ── Table RESERVATION ─────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RESERVATION (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id        INTEGER NOT NULL,
            utilisateur_id  INTEGER NOT NULL,
            heure_debut     TEXT    NOT NULL,
            heure_fin       TEXT    NOT NULL,
            statut          TEXT    NOT NULL DEFAULT 'confirmee'
                                    CHECK(statut IN ('confirmee','annulee','terminee')),
            FOREIGN KEY (place_id)       REFERENCES PLACE(id),
            FOREIGN KEY (utilisateur_id) REFERENCES UTILISATEUR(id)
        )
    ''')

    # ── Données initiales ─────────────────────────────────────
    # 3 places de parking
    cursor.executemany(
        'INSERT OR IGNORE INTO PLACE (numero, statut) VALUES (?, ?)',
        [(1, 'libre'), (2, 'libre'), (3, 'libre')]
    )

    # Comptes par défaut
    cursor.executemany(
        'INSERT OR IGNORE INTO UTILISATEUR (username, password, role) VALUES (?, ?, ?)',
        [
            ('admin',    'admin123',   'admin'),
            ('prof',     'prof123',    'professeur'),
            ('etudiant', 'etudiant123','etudiant'),
        ]
    )

    conn.commit()
    conn.close()
    print("[OK] Base de données SmartSpot initialisée avec succès !")
    print(f"   Fichier : {DB_PATH}")
    print("   Comptes créés :")
    print("     admin / admin123       (administrateur)")
    print("     prof  / prof123        (professeur)")
    print("     etudiant / etudiant123 (étudiant)")

if __name__ == '__main__':
    init_db()
