/* SmartSpot — historique.js
   Statistiques d'occupation et journal complet */

let filtrePlaceActif = '';

function formaterDureeMin(minutes) {
  if (!minutes || minutes <= 0) return '0 min';
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr.replace(' ', 'T'));
    return d.toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
  } catch { return dateStr; }
}

function calculerDuree(debut, fin) {
  try {
    const diff = new Date(fin.replace(' ', 'T')) - new Date(debut.replace(' ', 'T'));
    const min = Math.max(0, Math.round(diff / 60000));
    return formaterDureeMin(min);
  } catch { return '—'; }
}

async function chargerStatsHistorique() {
  try {
    const res = await fetch('/api/historique/stats');
    const data = await res.json();

    document.getElementById('hist-total').textContent = data.total_passages;
    document.getElementById('hist-moyenne').textContent = formaterDureeMin(data.duree_moyenne_min);
    document.getElementById('hist-cumul').textContent = formaterDureeMin(data.duree_totale_min);
    document.getElementById('hist-pointe').textContent =
      data.heure_pointe !== null ? `${String(data.heure_pointe).padStart(2, '0')}h` : '--';

    rendreGraphiqueHoraire(data.par_heure || []);
    rendreStatsPlaces(data.par_place || []);
  } catch (err) {
    console.warn('Erreur stats historique :', err);
  }
}

function rendreGraphiqueHoraire(parHeure) {
  const container = document.getElementById('hourly-chart');
  if (!container) return;

  const maxVal = Math.max(...parHeure, 1);
  container.innerHTML = '';

  parHeure.forEach((count, hour) => {
    const pct = Math.round((count / maxVal) * 100);
    const barCol = document.createElement('div');
    barCol.className = 'hourly-bar-col';
    barCol.title = `${String(hour).padStart(2, '0')}h : ${count} passage(s)`;

    barCol.innerHTML = `
      <span class="hourly-count">${count > 0 ? count : ''}</span>
      <div class="hourly-track">
        <div class="hourly-fill ${count > 0 ? 'has-data' : ''}" style="height: ${pct}%"></div>
      </div>
      <span class="hourly-label">${String(hour).padStart(2, '0')}h</span>
    `;
    container.appendChild(barCol);
  });
}

function rendreStatsPlaces(parPlace) {
  const grid = document.getElementById('place-stats-grid');
  if (!grid) return;
  grid.innerHTML = '';

  parPlace.forEach(p => {
    const card = document.createElement('div');
    card.className = 'place-stat-card';
    card.innerHTML = `
      <div class="place-stat-title">Place ${p.numero}</div>
      <div class="place-stat-row">
        <span>Passages</span>
        <strong>${p.passages}</strong>
      </div>
      <div class="place-stat-row">
        <span>Durée moyenne</span>
        <strong class="green">${formaterDureeMin(p.duree_moyenne_min)}</strong>
      </div>
      <div class="place-stat-row">
        <span>Temps cumulé</span>
        <strong class="blue">${formaterDureeMin(p.duree_totale_min)}</strong>
      </div>
    `;
    grid.appendChild(card);
  });
}

async function chargerJournal() {
  const tbody = document.getElementById('historique-full-body');
  if (!tbody) return;

  const url = filtrePlaceActif
    ? `/api/historique?limit=100&place_id=${filtrePlaceActif}`
    : '/api/historique?limit=100';

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Aucun passage enregistré.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    data.forEach(h => {
      const entree = formatDate(h.heure_entree);
      const sortie = h.heure_sortie ? formatDate(h.heure_sortie) : '—';
      const duree = h.heure_sortie ? calculerDuree(h.heure_entree, h.heure_sortie) : 'En cours';
      const statut = h.heure_sortie
        ? '<span class="badge badge-gray">Terminé</span>'
        : '<span class="badge badge-green">En cours</span>';

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
    tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Erreur de chargement.</td></tr>';
  }
}

function rafraichirTout() {
  chargerStatsHistorique();
  chargerJournal();
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('#filter-pills .filter-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#filter-pills .filter-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filtrePlaceActif = btn.dataset.place || '';
      chargerJournal();
    });
  });

  rafraichirTout();
  setInterval(rafraichirTout, 10000);
});
