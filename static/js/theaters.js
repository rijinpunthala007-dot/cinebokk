/**
 * CineBook — Theater Selection Screen (theaters.js)
 * ==================================================
 * Per-movie theater list comparison screen (BookMyShow pattern).
 * Displays theater info popover, favorite hearts, amenity badges,
 * format-tagged showtime chips, cancellation policies, and seat availability hints.
 */

(function () {
  'use strict';

  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const movieId = pathParts[pathParts.indexOf('movies') + 1];
  if (!movieId) return;

  const state = {
    date: localISODate(new Date()),
    lang: '',
    favTheaters: getFavTheaters(),
  };

  const listContainer = document.getElementById('showsList');
  const emptyState = document.getElementById('emptyShows');
  const errorState = document.getElementById('errorShows');

  function localISODate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function getFavTheaters() {
    try {
      return JSON.parse(localStorage.getItem('cinebook_fav_theaters') || '[]');
    } catch {
      return [];
    }
  }

  function saveFavTheater(name) {
    const set = new Set(getFavTheaters());
    if (set.has(name)) set.delete(name);
    else set.add(name);
    const arr = Array.from(set);
    localStorage.setItem('cinebook_fav_theaters', JSON.stringify(arr));
    state.favTheaters = arr;
    return set.has(name);
  }

  // -------------------------------------------------------------------------
  // Date strip
  // -------------------------------------------------------------------------
  function buildDateTabs() {
    const tabs = document.getElementById('dateTabs');
    if (!tabs) return;
    tabs.innerHTML = '';

    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    for (let i = 0; i < 7; i++) {
      const d = new Date();
      d.setDate(d.getDate() + i);
      const iso = localISODate(d);

      const btn = document.createElement('button');
      btn.className = 'date-tab' + (iso === state.date ? ' active' : '');
      btn.setAttribute('aria-pressed', String(iso === state.date));
      btn.setAttribute('aria-label', d.toLocaleDateString('en-IN', { weekday: 'long', month: 'long', day: 'numeric' }));
      btn.innerHTML = `
        <span class="date-tab__day">${i === 0 ? 'Today' : i === 1 ? 'Tmrw' : dayNames[d.getDay()]}</span>
        <span class="date-tab__num">${d.getDate()}</span>
        <span class="date-tab__month">${monthNames[d.getMonth()]}</span>
      `;
      btn.addEventListener('click', () => {
        tabs.querySelectorAll('.date-tab').forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
        state.date = iso;
        loadShows();
      });
      tabs.appendChild(btn);
    }
  }

  // -------------------------------------------------------------------------
  // Movie summary bar
  // -------------------------------------------------------------------------
  function titleHue(title) {
    let hash = 0;
    for (const ch of title) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return hash;
  }

  async function loadMovie() {
    try {
      const { data, ok } = await api.get(`/movies/${movieId}/`);
      if (!ok || !data) return;

      document.title = `${data.title} — Select Theater — CineBook`;
      const title = escHtml(data.title);
      const bar = document.getElementById('movieBar');
      if (bar) {
        bar.innerHTML = `
          <div class="movie-bar__poster" style="--ph-hue:${titleHue(data.title)};">
            ${data.poster
              ? `<img src="${escHtml(data.poster)}" alt="${title} poster">`
              : `<span class="movie-bar__monogram" role="img" aria-label="${title} poster placeholder">${escHtml(data.title[0])}</span>`
            }
          </div>
          <div>
            <a href="/movies/${data.id}/" class="movie-bar__title">${title}</a>
            <div class="movie-bar__meta">
              <span class="cert-badge" style="font-size:var(--text-2xs);padding:2px 8px;background:var(--surface-sunken);border-radius:var(--radius-pill);font-weight:700;">${escHtml(data.rating)}</span>
              <span>${escHtml(data.duration_display || '')}</span>
              <span aria-hidden="true">·</span>
              <span>${escHtml(data.language)}</span>
            </div>
          </div>
          <div class="movie-bar__city">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:-1px;margin-right:4px;" aria-hidden="true">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
            </svg>${escHtml(getSavedCity())}
          </div>
        `;
      }
    } catch { /* summary bar is progressive */ }
  }

  // -------------------------------------------------------------------------
  // Shows & Theater Card Rendering
  // -------------------------------------------------------------------------
  function showSkeletons() {
    listContainer.innerHTML = '<div class="skeleton skeleton--block" aria-hidden="true"></div><div class="skeleton skeleton--block" aria-hidden="true"></div>';
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
  }

  async function loadShows() {
    showSkeletons();

    const params = { movie: movieId, date: state.date, city: getSavedCity() };
    if (state.lang) params.language = state.lang;

    let resp;
    try {
      resp = await api.get('/shows/', params);
    } catch {
      listContainer.innerHTML = '';
      errorState.classList.remove('hidden');
      return;
    }

    const { data, ok } = resp;
    listContainer.innerHTML = '';

    if (!ok) {
      errorState.classList.remove('hidden');
      return;
    }

    const shows = data?.results || [];
    if (shows.length === 0) {
      emptyState.classList.remove('hidden');
      return;
    }

    renderTheaterCards(shows);
    buildLangFilter(shows);
  }

  function renderTheaterCards(shows) {
    // Group shows by theater
    const byTheater = new Map();
    shows.forEach(show => {
      if (!byTheater.has(show.theater_name)) {
        byTheater.set(show.theater_name, {
          name: show.theater_name,
          city: show.theater_city,
          address: show.theater_address || `${show.theater_name}, ${show.theater_city}`,
          amenities: show.theater_amenities || [],
          shows: [],
        });
      }
      byTheater.get(show.theater_name).shows.push(show);
    });

    byTheater.forEach(tData => {
      const isFav = state.favTheaters.includes(tData.name);

      const card = document.createElement('article');
      card.className = 'theater-card';
      card.setAttribute('aria-label', `Theater ${tData.name}`);

      // Amenities pills HTML
      const amenitiesHtml = tData.amenities.map(a =>
        `<span class="amenity-badge">${escHtml(a)}</span>`
      ).join('');

      // Check cancellation policy (if any show is cancellable, show Cancellable)
      const isCancellable = tData.shows.some(s => s.is_cancellable);

      // Render showtime chips
      const chipsHtml = tData.shows.map(show => {
        const timeStr = new Date(show.start_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
        const soldOut = show.available_seats === 0;
        const almostFull = !soldOut && show.availability_pct <= 25;
        const fmtTag = show.format ? `<span class="show-chip__fmt">${escHtml(show.format)}</span>` : '';

        if (soldOut) {
          return `
            <span class="show-chip show-chip--soldout" aria-label="${timeStr}, sold out">
              <span class="show-chip__time">${timeStr}</span>
              ${fmtTag}
            </span>`;
        }

        const chipClasses = ['show-chip'];
        if (almostFull) chipClasses.push('show-chip--almost-full');

        return `
          <a href="/bookings/seat-map/${show.id}/" class="${chipClasses.join(' ')}"
             aria-label="Showtime ${timeStr}, ${show.format || ''}, ${show.available_seats} seats remaining">
            <span class="show-chip__time">${timeStr}</span>
            ${fmtTag}
          </a>`;
      }).join('');

      card.innerHTML = `
        <div class="theater-card__header">
          <div>
            <div class="theater-card__title-row">
              <h2 class="theater-card__name">${escHtml(tData.name)}</h2>
              <div class="theater-info-wrap">
                <button class="theater-info-btn" aria-label="Info for ${escHtml(tData.name)}">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                </button>
                <div class="theater-info-tooltip">
                  <strong>${escHtml(tData.name)}</strong><br>
                  ${escHtml(tData.address)}
                </div>
              </div>
              <button class="theater-fav-btn${isFav ? ' active' : ''}" data-name="${escHtml(tData.name)}" aria-label="Favorite ${escHtml(tData.name)}">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.78-8.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
              </button>
            </div>
            <div class="theater-amenities">${amenitiesHtml}</div>
          </div>
        </div>
        <div class="theater-card__shows-body">
          <div class="showtime-chips-grid">${chipsHtml}</div>
          <div class="theater-card__status-line">
            <span class="status-indicator ${isCancellable ? 'status-indicator--cancellable' : 'status-indicator--non-cancellable'}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                ${isCancellable
                  ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
                  : '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'}
              </svg>
              ${isCancellable ? 'Cancellation available' : 'Non-cancellable'}
            </span>
          </div>
        </div>
      `;

      // Wire favorite button event
      const favBtn = card.querySelector('.theater-fav-btn');
      if (favBtn) {
        favBtn.addEventListener('click', () => {
          const active = saveFavTheater(tData.name);
          favBtn.classList.toggle('active', active);
        });
      }

      listContainer.appendChild(card);
    });
  }

  function buildLangFilter(shows) {
    const langs = [...new Set(shows.map(s => s.language))];
    const bar = document.getElementById('langFilter');
    if (!bar) return;
    if (!state.lang) {
      bar.innerHTML = `<button class="chip active" data-lang="" aria-pressed="true">All Languages</button>` +
        langs.map(l => `<button class="chip" data-lang="${escHtml(l)}" aria-pressed="false">${escHtml(l)}</button>`).join('');
    }
    bar.querySelectorAll('.chip').forEach(btn => {
      const on = (btn.dataset.lang || '') === state.lang;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-pressed', String(on));
      btn.onclick = () => {
        state.lang = btn.dataset.lang || '';
        loadShows();
      };
    });
  }

  document.getElementById('retryShowsBtn')?.addEventListener('click', loadShows);

  // Re-load on city change event from nav city selector
  window.addEventListener('cinebook:citychange', () => {
    loadShows();
  });

  // Init
  buildDateTabs();
  loadMovie();
  loadShows();
})();
