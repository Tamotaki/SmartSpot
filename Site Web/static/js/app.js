/* SmartSpot — app.js
   Mise à jour automatique toutes les 2 secondes */

// ─── Horloge géante (analogique + numérique) ────────────────────
function initHorloge() {
  const ticks = document.getElementById('clock-ticks');
  if (!ticks || ticks.childElementCount) return; // déjà généré

  for (let i = 0; i < 60; i++) {
    const angle   = i * 6; // 360/60
    const majeur  = i % 5 === 0;
    const r1      = majeur ? 78 : 86;
    const r2      = 92;
    const rad     = (angle - 90) * Math.PI / 180;
    const x1 = 100 + r1 * Math.cos(rad);
    const y1 = 100 + r1 * Math.sin(rad);
    const x2 = 100 + r2 * Math.cos(rad);
    const y2 = 100 + r2 * Math.sin(rad);

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1.toFixed(2));
    line.setAttribute('y1', y1.toFixed(2));
    line.setAttribute('x2', x2.toFixed(2));
    line.setAttribute('y2', y2.toFixed(2));
    line.setAttribute('class', majeur ? 'clock-tick major' : 'clock-tick');
    ticks.appendChild(line);
  }
}

function majHorloge() {
  const now = new Date();

  const h = now.getHours();
  const m = now.getMinutes();
  const s = now.getSeconds();

  const handHour = document.getElementById('hand-hour');
  const handMin  = document.getElementById('hand-min');
  const handSec  = document.getElementById('hand-sec');

  if (handHour) handHour.style.transform = `rotate(${(h % 12) * 30 + m * 0.5}deg)`;
  if (handMin)  handMin.style.transform  = `rotate(${m * 6 + s * 0.1}deg)`;
  if (handSec)  handSec.style.transform  = `rotate(${s * 6}deg)`;

  const timeEl = document.getElementById('clock-time');
  const dateEl = document.getElementById('clock-date');
  if (timeEl) timeEl.textContent = now.toLocaleTimeString('fr-FR');
  if (dateEl) {
    dateEl.textContent = now.toLocaleDateString('fr-FR', {
      weekday: 'long', day: 'numeric', month: 'long'
    });
  }
}

// Chargement des places (statuts + cartes parking)
async function chargerPlaces() {
  try {
    const res  = await fetch('/api/places');
    const data = await res.json();

    rendreParkingLot(data);
  } catch (err) {
    console.warn('Erreur places :', err);
  }
}

// Photo voiture vue du dessus (se recolore en CSS selon le statut)
function iconeVoiture() {
  return `<img class="car-icon" src="/static/img/voiture-vue-dessus.png" alt="Voiture">`;
}

function heureCourte(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

const ICONE_CADENAS = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';
const ICONE_HORLOGE  = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';

function rendreParkingLot(places) {
  const lot = document.getElementById('parking-lot');
  if (!lot) return;

  lot.innerHTML = '';
  places.forEach(p => {
    const statut = p.statut; // 'libre' | 'occupee' | 'reservee'
    const card = document.createElement('div');
    card.className = `place-card ${statut}`;

    const dot = '<svg class="status-dot" width="8" height="8" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="5"/></svg>';
    const labels = {
      libre:    'Disponible',
      occupee:  'Occupée',
      reservee: 'Réservée'
    };

    // Voiture vue du dessus si occupée/réservée, sinon emplacement vide rayé
    let visualHTML;
    if (statut === 'occupee' || statut === 'reservee') {
      visualHTML = iconeVoiture();
    } else {
      visualHTML = `<div class="parking-empty"><span>P</span></div>`;
    }

    // Détails de réservation (si une réservation active existe)
    let footerHTML;
    if (statut === 'reservee' && p.resa_debut) {
      footerHTML = `
        <div class="place-resa-details">
          <span class="place-resa-row">${ICONE_HORLOGE} ${heureCourte(p.resa_debut)} → ${heureCourte(p.resa_fin)}</span>
          ${p.resa_user ? `<span class="place-resa-user">réservée par ${p.resa_user}</span>` : ''}
        </div>`;
    } else if (statut === 'occupee') {
      footerHTML = `<div class="place-resa-details"><span class="place-resa-row">Véhicule stationné</span></div>`;
    } else {
      footerHTML = `<div class="place-resa-details"><span class="place-resa-row">Prête à l'emploi</span></div>`;
    }

    card.innerHTML = `
      <div class="place-card-top">
        <span class="place-card-num">Place ${p.numero}</span>
        <span class="place-pill ${statut}">${statut === 'reservee' ? ICONE_CADENAS : dot} ${labels[statut]}</span>
      </div>
      <div class="place-visual">
        ${visualHTML}
      </div>
      ${footerHTML}
    `;

    lot.appendChild(card);
  });
}

// Anneau de progression des cartes KPI
const RING_CIRCONFERENCE = 2 * Math.PI * 27;

function majAnneau(id, pct) {
  const ring = document.getElementById(id);
  if (!ring) return;
  const offset = RING_CIRCONFERENCE * (1 - Math.min(Math.max(pct, 0), 100) / 100);
  ring.style.strokeDasharray  = RING_CIRCONFERENCE;
  ring.style.strokeDashoffset = offset;
}

// Chargement des statistiques
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

    const total = data.total || 1;
    majAnneau('ring-total',    100);
    majAnneau('ring-libres',   (data.libres   / total) * 100);
    majAnneau('ring-occupees', (data.occupees / total) * 100);
    majAnneau('ring-passages', Math.min((data.passages_today / (total * 4)) * 100, 100));

  } catch (err) {
    console.warn('Erreur stats :', err);
  }
}

// Chargement de l'historique 
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

// Utilitaires date 
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

// Boucle principale
function demarrerMiseAJour() {
  initHorloge();
  majHorloge();
  setInterval(majHorloge, 1000);

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

// Démarrage
document.addEventListener('DOMContentLoaded', demarrerMiseAJour);
