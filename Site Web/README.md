SmartSpot : Application web de gestion de places de parking en temps réel (Flask + SQLite).

Prérequis : Python 3.10+, pip

Installation :

git clone (le url)

cd smartspot

pip install -r requirements.txt


Base de données : smartspot.db est déjà inclus dans le repo, rien à faire. Pour la recréer vierge :

python database.py


Comptes de test : admin/admin123, prof/prof123, etudiant/etudiant123

Lancer l'appli :

python app.py

Puis ouvrir http://localhost:5000


Mode simulation (sans Arduino), dans un second terminal :

python serial_reader.py --sim


Avec un vrai Arduino :

python serial_reader.py
