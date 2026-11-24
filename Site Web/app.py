from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'smartspot_secret_2024'

DB_PATH = os.path.join(os.path.dirname(__file__), 'smartspot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─── ROUTES HTML ─────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        user = db.execute(
            'SELECT * FROM UTILISATEUR WHERE username=? AND password=?',
            (username, password)
        ).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            error = 'Identifiants incorrects. Réessayez.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session.get('username'), role=session.get('role'))

@app.route('/reservation')
def reservation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('reservation.html', username=session.get('username'))

# ─── API JSON ─────────────────────────────────────────────────

@app.route('/api/places')
def api_places():
    db = get_db()
    places = db.execute('SELECT * FROM PLACE ORDER BY id').fetchall()
    db.close()
    return jsonify([dict(p) for p in places])

@app.route('/api/places/<int:place_id>')
def api_place(place_id):
    db = get_db()
    place = db.execute('SELECT * FROM PLACE WHERE id=?', (place_id,)).fetchone()
    db.close()
    if place:
        return jsonify(dict(place))
    return jsonify({'error': 'Place introuvable'}), 404

@app.route('/api/historique')
def api_historique():
    db = get_db()
    historique = db.execute('''
        SELECT h.*, p.numero as place_numero
        FROM HISTORIQUE h
        JOIN PLACE p ON h.place_id = p.id
        ORDER BY h.heure_entree DESC
        LIMIT 20
    ''').fetchall()
    db.close()
    return jsonify([dict(h) for h in historique])

@app.route('/api/stats')
def api_stats():
    db = get_db()
    total = db.execute('SELECT COUNT(*) as cnt FROM PLACE').fetchone()['cnt']
    occupees = db.execute("SELECT COUNT(*) as cnt FROM PLACE WHERE statut='occupee'").fetchone()['cnt']
    libres = total - occupees
    today = datetime.now().strftime('%Y-%m-%d')
    passages = db.execute(
        "SELECT COUNT(*) as cnt FROM HISTORIQUE WHERE heure_entree LIKE ?",
        (today + '%',)
    ).fetchone()['cnt']
    db.close()
    return jsonify({
        'total': total,
        'occupees': occupees,
        'libres': libres,
        'passages_today': passages
    })

@app.route('/api/reserver', methods=['POST'])
def api_reserver():
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    data = request.get_json()
    place_id = data.get('place_id')
    heure_debut = data.get('heure_debut')
    heure_fin = data.get('heure_fin')
    if not all([place_id, heure_debut, heure_fin]):
        return jsonify({'error': 'Données manquantes'}), 400
    db = get_db()
    place = db.execute("SELECT * FROM PLACE WHERE id=? AND statut='libre'", (place_id,)).fetchone()
    if not place:
        db.close()
        return jsonify({'error': 'Place non disponible'}), 409
    db.execute(
        'INSERT INTO RESERVATION (place_id, utilisateur_id, heure_debut, heure_fin, statut) VALUES (?,?,?,?,?)',
        (place_id, session['user_id'], heure_debut, heure_fin, 'confirmee')
    )
    db.execute("UPDATE PLACE SET statut='reservee' WHERE id=?", (place_id,))
    db.commit()
    db.close()
    return jsonify({'message': 'Réservation confirmée', 'place_id': place_id})

@app.route('/api/update_place', methods=['POST'])
def api_update_place():
    """Endpoint appelé par serial_reader.py pour mettre à jour les statuts depuis Arduino"""
    data = request.get_json()
    statuts = data.get('statuts', [])  # liste: [{"id":1,"statut":"occupee"}, ...]
    db = get_db()
    for item in statuts:
        place_id = item.get('id')
        statut = item.get('statut')
        if place_id and statut in ('libre', 'occupee'):
            # Si la place devient occupée, on enregistre l'entrée
            if statut == 'occupee':
                ancien = db.execute("SELECT statut FROM PLACE WHERE id=?", (place_id,)).fetchone()
                if ancien and ancien['statut'] == 'libre':
                    db.execute(
                        'INSERT INTO HISTORIQUE (place_id, heure_entree) VALUES (?,?)',
                        (place_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
            # Si la place devient libre, on enregistre la sortie
            elif statut == 'libre':
                dernier = db.execute(
                    "SELECT id FROM HISTORIQUE WHERE place_id=? AND heure_sortie IS NULL ORDER BY heure_entree DESC LIMIT 1",
                    (place_id,)
                ).fetchone()
                if dernier:
                    db.execute(
                        "UPDATE HISTORIQUE SET heure_sortie=? WHERE id=?",
                        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), dernier['id'])
                    )
            db.execute("UPDATE PLACE SET statut=? WHERE id=?", (statut, place_id))
    db.commit()
    db.close()
    return jsonify({'message': 'Statuts mis à jour'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
