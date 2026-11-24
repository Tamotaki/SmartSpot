/* ════════════════════════════════════════════════════════════
   SmartSpot — reservation.js
   Gestion de la page de réservation
   ════════════════════════════════════════════════════════════ */

let placeSelectionnee = null;

// ─── Chargement des places pour sélection ──────────────────────
async function chargerPlacesReservation() {
  const grid = document.getElementById('places-grid');
  if (!grid) return;

  grid.innerHTML = '<p class="loading-cell">Chargement…</p>';

  try {
    const res   = await fetch('/api/places');
    const places = await res.json();

    grid.innerHTML = '';

    places.forEach(p => {
      const card = document.createElement('div');
      card.className = `place-select-card ${p.statut}`;

      const labels = { libre: 'Disponible', occupee: 'Occupée', reservee: 'Réservée' };

      card.innerHTML = `
        <div class="place-select-num">${p.numero}</div>
        <div class="place-select-label">${labels[p.statut] || p.statut}</div>
      `;

      if (p.statut === 'libre') {
        card.addEventListener('click', () => selectionnerPlace(p));
      }

      grid.appendChild(card);
    });

  } catch (err) {
    grid.innerHTML = '<p class="loading-cell">Erreur de chargement.</p>';
  }
}

// ─── Sélectionner une place ────────────────────────────────────
function selectionnerPlace(place) {
  placeSelectionnee = place;

  // Afficher le formulaire
  const formSection = document.getElementById('form-section');
  const label       = document.getElementById('place-selected-label');
  const input       = document.getElementById('place-id-input');
  const msgDiv      = document.getElementById('resa-message');

  if (formSection) formSection.style.display = 'block';
  if (label)  label.textContent  = `Nº ${place.numero}`;
  if (input)  input.value        = place.id;
  if (msgDiv) msgDiv.style.display = 'none';

  // Scroll vers le formulaire
  formSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Pré-remplir les heures (maintenant + 1h)
  const now    = new Date();
  const later  = new Date(now.getTime() + 60 * 60 * 1000);
  const toInput = d => d.toISOString().slice(0, 16);

  const heureDebut = document.getElementById('heure-debut');
  const heureFin   = document.getElementById('heure-fin');
  if (heureDebut) heureDebut.value = toInput(now);
  if (heureFin)   heureFin.value   = toInput(later);
}

// ─── Annuler la sélection ──────────────────────────────────────
function annulerSelection() {
  placeSelectionnee = null;
  const formSection = document.getElementById('form-section');
  if (formSection) formSection.style.display = 'none';
}

// ─── Confirmer la réservation ──────────────────────────────────
async function confirmerReservation() {
  const placeId   = document.getElementById('place-id-input')?.value;
  const heureDebut = document.getElementById('heure-debut')?.value;
  const heureFin   = document.getElementById('heure-fin')?.value;
  const msgDiv     = document.getElementById('resa-message');

  if (!placeId || !heureDebut || !heureFin) {
    afficherMessage('Veuillez remplir tous les champs.', 'error');
    return;
  }

  if (new Date(heureFin) <= new Date(heureDebut)) {
    afficherMessage("L'heure de fin doit être après l'heure de début.", 'error');
    return;
  }

  try {
    const res  = await fetch('/api/reserver', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        place_id:    parseInt(placeId),
        heure_debut: heureDebut,
        heure_fin:   heureFin
      })
    });

    const data = await res.json();

    if (res.ok) {
      afficherMessage(`${data.message} (Place Nº ${placeSelectionnee?.numero})`, 'success');
      annulerSelection();
      chargerPlacesReservation(); // recharger les places
    } else {
      afficherMessage(data.error || 'Erreur lors de la réservation.', 'error');
    }

  } catch (err) {
    afficherMessage('Erreur réseau. Vérifiez votre connexion.', 'error');
  }
}

// ─── Icônes de message ──────────────────────────────────────────
const ICONES_MESSAGE = {
  success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="8 12 11 15 16 9"/></svg>',
  error:   '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
};

// ─── Afficher un message ───────────────────────────────────────
function afficherMessage(texte, type) {
  const msgDiv = document.getElementById('resa-message');
  if (!msgDiv) return;
  msgDiv.innerHTML   = `${ICONES_MESSAGE[type] || ''}<span>${texte}</span>`;
  msgDiv.className   = `resa-message ${type}`;
  msgDiv.style.display = 'block';
  setTimeout(() => { msgDiv.style.display = 'none'; }, 5000);
}

// ─── Démarrage ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  chargerPlacesReservation();
  // Actualiser les places toutes les 5 secondes
  setInterval(chargerPlacesReservation, 5000);
});
