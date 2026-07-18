/**
 * CineBook — Showtimes page
 * ==========================
 * 7-day date strip, theaters grouped with scan-at-a-glance showtime chips,
 * language filter derived from results, empty + error states.
 */

(function () {
  'use strict';

  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const movieId = pathParts[pathParts.indexOf('movies') + 1];
  if (!movieId) return;

  const state = {
    date: localISODate(new Date()),
    lang: '',
  };

  const list = document.getElementById('showsList');
  const empty = document.getElementById('emptyShows');
  const errorEl = document.getElementById('errorShows');

  // Local (not UTC) ISO date — toISOString() would shift the date near midnight IST
  function localISODate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // -------------------------------------------------------------------------
  // Date strip
  // -------------------------------------------------------------------------
  function buildDateTabs() {
    const tabs = document.getElementById('dateTabs');
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

      document.title = `${data.title} — Showtimes — CineBook`;
      const title = escHtml(data.title);
      document.getElementById('movieBar').innerHTML = `
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
          </svg>${getSavedCity()}
        </div>
      `;
    } catch {
      // Summary bar is secondary — shows list has its own error handling
    }
  }

  // -------------------------------------------------------------------------
  // Shows list
  // -------------------------------------------------------------------------
  function showSkeletons() {
    list.innerHTML = '<div class="skeleton skeleton--block" aria-hidden="true"></div><div class="skeleton skeleton--block" aria-hidden="true"></div>';
    empty.classList.add('hidden');
    errorEl.classList.add('hidden');
  }

  async function loadShows() {
    showSkeletons();

    const params = { movie: movieId, date: state.date, city: getSavedCity() };
    if (state.lang) params.language = state.lang;

    let resp;
    try {
      resp = await api.get('/shows/', params);
    } catch {
      list.innerHTML = '';
      errorEl.classList.remove('hidden');
      return;
    }

    const { data, ok } = resp;
    list.innerHTML = '';

    if (!ok) {
      errorEl.classList.remove('hidden');
      return;
    }

    const shows = data?.results || [];
    if (shows.length === 0) {
      empty.classList.remove('hidden');
      return;
    }

    renderTheaterGroups(shows);
    buildLangFilter(shows);
  }

  function renderTheaterGroups(shows) {
    // Group by theater — BookMyShow's pattern: scan every theater's slate at once
    const byTheater = new Map();
    shows.forEach(show => {
      if (!byTheater.has(show.theater_name)) byTheater.set(show.theater_name, []);
      byTheater.get(show.theater_name).push(show);
    });

    byTheater.forEach((theaterShows, theaterName) => {
      const el = document.createElement('section');
      el.className = 'theater-group';
      el.setAttribute('aria-label', `Showtimes at ${theaterName}`);

      const chips = theaterShows.map(show => {
        const time = new Date(show.start_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
        const lang = escHtml(show.language);
        const soldOut = show.available_seats === 0;
        // Scarcity hint only when <20% remain — keeps chips calm otherwise
        const scarce = !soldOut && show.available_seats > 0 && show.available_seats <= 25;

        if (soldOut) {
          return `
            <span class="showtime-chip showtime-chip--soldout" aria-label="Show at ${time}, ${lang}, sold out">
              <span class="showtime-chip__time">${time}</span>
              <span class="showtime-chip__left">Sold out</span>
            </span>`;
        }
        return `
          <a href="/bookings/seat-map/${show.id}/" class="showtime-chip"
             aria-label="Show at ${time}, ${lang}, ${show.available_seats} seats available">
            <span class="showtime-chip__time">${time}</span>
            <span class="showtime-chip__lang">${lang}</span>
            ${scarce ? `<span class="showtime-chip__left">${show.available_seats} left</span>` : ''}
          </a>`;
      }).join('');

      el.innerHTML = `
        <div class="theater-group__header">
          <div class="theater-group__icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M2 20h20M4 20V8l8-5 8 5v12"/>
              <path d="M9 20v-6h6v6"/>
            </svg>
          </div>
          <div>
            <h2 class="theater-group__name">${escHtml(theaterName)}</h2>
            <div class="theater-group__sub">${escHtml(theaterShows[0].theater_city)}</div>
          </div>
        </div>
        <div class="showtime-chips">${chips}</div>
      `;
      list.appendChild(el);
    });
  }

  function buildLangFilter(shows) {
    const langs = [...new Set(shows.map(s => s.language))];
    const bar = document.getElementById('langFilter');
    // Only rebuild when unfiltered — otherwise filtering to one language
    // would collapse the bar to a single chip
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

  // Init
  buildDateTabs();
  loadMovie();
  loadShows();
})();
