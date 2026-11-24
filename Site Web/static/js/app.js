/* ════════════════════════════════════════════════════════════
   SmartSpot — app.js
   Mise à jour automatique toutes les 2 secondes
   ════════════════════════════════════════════════════════════ */

// ─── Mise à jour de l'heure ────────────────────────────────────
function majHeure() {
  const el = document.getElementById('last-update');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('fr-FR');
  }
}

// ─── Chargement des places (statuts + cartes parking) ──────────
async function chargerPlaces() {
  try {
    const res  = await fetch('/api/places');
    const data = await res.json();

    rendreParkingLot(data);
    majHeure();
  } catch (err) {
    console.warn('Erreur places :', err);
  }
}

function rendreParkingLot(places) {
  const lot = document.getElementById('parking-lot');
  if (!lot) return;

  lot.innerHTML = '';
  places.forEach(p => {
    const statut = p.statut; // 'libre' | 'occupee' | 'reservee'
    const card = document.createElement('div');
    card.className = `place-card ${statut}`;

    // Icône statut
    const dot = '<svg class="status-dot" width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="5"/></svg>';
    const labels = {
      libre:    'Libre',
      occupee:  'Occupée',
      reservee: 'Réservée'
    };

    // Voiture vue du dessus si occupée, sinon espace vide
    let visualHTML;
    if (statut === 'occupee') {
      visualHTML = `
        <div class="car-top-view ${statut}">
          <div class="car-body">
            <div class="car-windshield"></div>
            <div class="car-wheel fl"></div>
            <div class="car-wheel fr"></div>
            <div class="car-wheel bl"></div>
            <div class="car-wheel br"></div>
          </div>
        </div>`;
    } else {
      visualHTML = `<div class="parking-empty">P</div>`;
    }

    card.innerHTML = `
      <div class="place-card-header">
        <span>Place ${p.numero}</span>
        <span>${dot}</span>
      </div>
      <div class="place-visual">
        ${visualHTML}
      </div>
      <div class="place-status-text">${labels[statut]}</div>
    `;

    lot.appendChild(card);
  });
}

// ─── Chargement des statistiques ───────────────────────────────
async function chargerStats() {
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();

    const setEl = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setEl('stat-total',    data.total);
    setEl('stat-libres',   data.libres);
    setEl('stat-occupees', data.occupees);
    setEl('stat-passages', data.passages_today);

  } catch (err) {
    console.warn('Erreur stats :', err);
  }
}

// ─── Chargement de l'historique ────────────────────────────────
async function chargerHistorique() {
  const tbody = document.getElementById('historique-body');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Chargement…</td></tr>';

  try {
    const res  = await fetch('/api/historique');
    const data = await res.json();

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Aucun passage enregistré.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    data.forEach(h => {
      const entree = formatDate(h.heure_entree);
      const sortie = h.heure_sortie ? formatDate(h.heure_sortie) : '';
      const duree  = h.heure_sortie ? calculerDuree(h.heure_entree, h.heure_sortie) : 'En cours';

      const statut = h.heure_sortie
        ? `<span class="badge badge-gray">Terminé</span>`
        : `<span class="badge badge-green">En cours</span>`;

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>Place ${h.place_numero}</td>
        <td>${entree}</td>
        <td>${sortie}</td>
        <td>${duree}</td>
        <td>${statut}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.warn('Erreur historique :', err);
    tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Erreur de chargement.</td></tr>';
  }
}

// ─── Utilitaires date ──────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
  } catch { return dateStr; }
}

function calculerDuree(debut, fin) {
  try {
    const diff = new Date(fin) - new Date(debut);
    const min  = Math.floor(diff / 60000);
    if (min < 60) return `${min} min`;
    const h = Math.floor(min / 60);
    const m = min % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  } catch { return ''; }
}

// ─── Boucle principale ─────────────────────────────────────────
function demarrerMiseAJour() {
  chargerPlaces();
  chargerStats();
  chargerHistorique();

  // Rafraîchissement automatique toutes les 2 secondes
  setInterval(() => {
    chargerPlaces();
    chargerStats();
  }, 2000);

  // Historique toutes les 15 secondes
  setInterval(() => {
    chargerHistorique();
  }, 15000);
}

// ─── Démarrage ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', demarrerMiseAJour);
