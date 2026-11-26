from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SMARTSPOT_SECRET', 'smartspot_secret_2024')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
# Recharge les templates HTML à chaque requête (sinon Flask les met en cache quand Debug est désactivé)
app.config['TEMPLATES_AUTO_RELOAD'] = True
# Désactive la mise en cache des fichiers statiques (CSS/JS) par le navigateur
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

DB_PATH = os.path.join(os.path.dirname(__file__), 'smartspot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def liberer_reservations_expirees(db):
    """Libère automatiquement les réservations dont l'heure de fin est dépassée."""
    maintenant = datetime.now().strftime('%Y-%m-%dT%H:%M')
    expirees = db.execute(
        "SELECT id, place_id FROM RESERVATION WHERE statut='confirmee' AND heure_fin <= ?",
        (maintenant,)
    ).fetchall()
    for r in expirees:
        db.execute("UPDATE RESERVATION SET statut='terminee' WHERE id=?", (r['id'],))
        db.execute("UPDATE PLACE SET statut='libre' WHERE id=? AND statut='reservee'", (r['place_id'],))
    if expirees:
        db.commit()

# ROUTES HTML

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

@app.route('/historique')
def historique():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('historique.html', username=session.get('username'), role=session.get('role'))

#  API JSON

@app.route('/api/places')
def api_places():
    db = get_db()
    liberer_reservations_expirees(db)
    places = db.execute('''
        SELECT PLACE.*,
               RESERVATION.heure_debut AS resa_debut,
               RESERVATION.heure_fin   AS resa_fin,
               UTILISATEUR.username    AS resa_user
        FROM PLACE
        LEFT JOIN RESERVATION ON RESERVATION.place_id = PLACE.id AND RESERVATION.statut = 'confirmee'
        LEFT JOIN UTILISATEUR ON UTILISATEUR.id = RESERVATION.utilisateur_id
        ORDER BY PLACE.id
    ''').fetchall()
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
    limit = request.args.get('limit', 50, type=int)
    place_id = request.args.get('place_id', type=int)
    db = get_db()
    if place_id:
        historique = db.execute('''
            SELECT h.*, p.numero as place_numero
            FROM HISTORIQUE h
            JOIN PLACE p ON h.place_id = p.id
            WHERE h.place_id = ?
            ORDER BY h.heure_entree DESC
            LIMIT ?
        ''', (place_id, limit)).fetchall()
    else:
        historique = db.execute('''
            SELECT h.*, p.numero as place_numero
            FROM HISTORIQUE h
            JOIN PLACE p ON h.place_id = p.id
            ORDER BY h.heure_entree DESC
            LIMIT ?
        ''', (limit,)).fetchall()
    db.close()
    return jsonify([dict(h) for h in historique])


@app.route('/api/historique/stats')
def api_historique_stats():
    db = get_db()
    rows = db.execute('''
        SELECT h.place_id, p.numero as place_numero, h.heure_entree, h.heure_sortie
        FROM HISTORIQUE h
        JOIN PLACE p ON h.place_id = p.id
    ''').fetchall()
    db.close()

    par_heure = [0] * 24
    durees_min = []
    stats_places = {1: {'numero': 1, 'passages': 0, 'durees': []},
                    2: {'numero': 2, 'passages': 0, 'durees': []},
                    3: {'numero': 3, 'passages': 0, 'durees': []}}

    for r in rows:
        entree_str = r['heure_entree']
        sortie_str = r['heure_sortie']
        pid = r['place_id']
        if pid in stats_places:
            stats_places[pid]['passages'] += 1

        try:
            dt_in = datetime.strptime(entree_str[:19], '%Y-%m-%d %H:%M:%S')
            par_heure[dt_in.hour] += 1
            if sortie_str:
                dt_out = datetime.strptime(sortie_str[:19], '%Y-%m-%d %H:%M:%S')
                diff_min = max(0, round((dt_out - dt_in).total_seconds() / 60))
                durees_min.append(diff_min)
                if pid in stats_places:
                    stats_places[pid]['durees'].append(diff_min)
        except ValueError:
            pass

    total_passages = len(rows)
    duree_totale_min = sum(durees_min)
    duree_moyenne_min = round(duree_totale_min / len(durees_min)) if durees_min else 0
    max_h = max(par_heure)
    heure_pointe = par_heure.index(max_h) if max_h > 0 else None

    par_place = []
    for pid in sorted(stats_places.keys()):
        d = stats_places[pid]['durees']
        par_place.append({
            'place_id': pid,
            'numero': stats_places[pid]['numero'],
            'passages': stats_places[pid]['passages'],
            'duree_moyenne_min': round(sum(d) / len(d)) if d else 0,
            'duree_totale_min': sum(d)
        })

    return jsonify({
        'total_passages': total_passages,
        'duree_moyenne_min': duree_moyenne_min,
        'duree_totale_min': duree_totale_min,
        'heure_pointe': heure_pointe,
        'par_heure': par_heure,
        'par_place': par_place
    })

@app.route('/api/stats')
def api_stats():
    db = get_db()
    liberer_reservations_expirees(db)
    total = db.execute('SELECT COUNT(*) as cnt FROM PLACE').fetchone()['cnt']
    occupees = db.execute("SELECT COUNT(*) as cnt FROM PLACE WHERE statut IN ('occupee', 'reservee')").fetchone()['cnt']
    reservees = db.execute("SELECT COUNT(*) as cnt FROM PLACE WHERE statut='reservee'").fetchone()['cnt']
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
        'reservees': reservees,
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
    liberer_reservations_expirees(db)
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


@app.route('/api/annuler/<int:place_id>', methods=['POST'])
def api_annuler(place_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    db = get_db()
    place = db.execute("SELECT * FROM PLACE WHERE id=? AND statut='reservee'", (place_id,)).fetchone()
    if not place:
        db.close()
        return jsonify({'error': 'Aucune réservation active sur cette place'}), 404
    db.execute(
        "UPDATE RESERVATION SET statut='annulee' WHERE place_id=? AND statut='confirmee'",
        (place_id,)
    )
    db.execute("UPDATE PLACE SET statut='libre' WHERE id=?", (place_id,))
    db.commit()
    db.close()
    return jsonify({'message': 'Réservation annulée', 'place_id': place_id})


@app.route('/api/update_place', methods=['POST'])
def api_update_place():
    """Endpoint appelé par serial_reader.py pour mettre à jour les statuts depuis Arduino"""
    data = request.get_json()
    statuts = data.get('statuts', [])  # liste: [{"id":1,"statut":"occupee"}, ...]
    db = get_db()
    liberer_reservations_expirees(db)
    for item in statuts:
        place_id = item.get('id')
        statut = item.get('statut')
        if place_id and statut in ('libre', 'occupee'):
            ancien = db.execute("SELECT statut FROM PLACE WHERE id=?", (place_id,)).fetchone()
            if not ancien:
                continue

            if statut == 'occupee':
                if ancien['statut'] in ('libre', 'reservee'):
                    db.execute(
                        'INSERT INTO HISTORIQUE (place_id, heure_entree) VALUES (?,?)',
                        (place_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                if ancien['statut'] == 'reservee':
                    db.execute(
                        "UPDATE RESERVATION SET statut='terminee' WHERE place_id=? AND statut='confirmee'",
                        (place_id,)
                    )
                db.execute("UPDATE PLACE SET statut='occupee' WHERE id=?", (place_id,))

            elif statut == 'libre':
                # Ne pas écraser une réservation active tant qu'aucune voiture n'est arrivée
                if ancien['statut'] == 'reservee':
                    continue
                dernier = db.execute(
                    "SELECT id FROM HISTORIQUE WHERE place_id=? AND heure_sortie IS NULL ORDER BY heure_entree DESC LIMIT 1",
                    (place_id,)
                ).fetchone()
                if dernier:
                    db.execute(
                        "UPDATE HISTORIQUE SET heure_sortie=? WHERE id=?",
                        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), dernier['id'])
                    )
                db.execute("UPDATE PLACE SET statut='libre' WHERE id=?", (place_id,))
    db.commit()
    db.close()
    return jsonify({'message': 'Statuts mis à jour'})

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
