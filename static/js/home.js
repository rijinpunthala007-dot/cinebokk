/**
 * CineBook — Home page
 * =====================
 * City pills, genre/language filters, debounced search (via nav event),
 * poster grid with skeleton loading and empty/error states.
 */

(function () {
  'use strict';

  // Flag for auth.js nav search: filter in place instead of navigating
  window.CINEBOOK_HOME = true;

  const state = {
    genre: '',
    lang: '',
    city: getSavedCity(),
    search: new URLSearchParams(window.location.search).get('search') || '',
  };
  // Also honour ?language= deep links from the footer
  state.lang = new URLSearchParams(window.location.search).get('language') || '';

  const grid = document.getElementById('movieGrid');
  const empty = document.getElementById('emptyState');
  const errorState = document.getElementById('errorState');
  const countEl = document.getElementById('movieCount');

  // Tracks the current in-flight /movies/ request so a newer load can abort it
  let inflight = null;

  // -------------------------------------------------------------------------
  // City pills (hero)
  // -------------------------------------------------------------------------
  function renderCityPills() {
    const wrap = document.getElementById('heroCities');
    if (!wrap) return;
    const cities = window.CINEBOOK_CITIES || ['Mumbai', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Pune', 'Kochi'];
    wrap.innerHTML = cities.map(c => `
      <button class="city-pill${c === state.city ? ' active' : ''}" data-city="${c}"
        aria-pressed="${c === state.city}">${c}</button>
    `).join('');
    wrap.querySelectorAll('.city-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        state.city = pill.dataset.city;
        saveCity(state.city);
        updateNavCity();
        renderCityPills();
        loadMovies();
      });
    });
  }

  // Update hero pills once API cities resolve
  if (window.fetchCities) {
    window.fetchCities().then(() => renderCityPills());
  }

  // -------------------------------------------------------------------------
  // Filters
  // -------------------------------------------------------------------------
  async function loadGenres() {
    try {
      const { data, ok } = await api.get('/movies/genres/');
      if (!ok || !Array.isArray(data)) return;
      const bar = document.getElementById('genreFilter');
      data.forEach(g => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.dataset.genre = g.id;
        btn.setAttribute('aria-pressed', 'false');
        btn.textContent = g.name;
        bar.appendChild(btn);
      });
      // One delegated handler covers "All Films" + dynamic chips
      bar.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        state.genre = chip.dataset.genre || '';
        bar.querySelectorAll('.chip').forEach(c => {
          c.classList.remove('active');
          c.setAttribute('aria-pressed', 'false');
        });
        chip.classList.add('active');
        chip.setAttribute('aria-pressed', 'true');
        scheduleLoad();
      });
    } catch {
      // Genre bar is progressive enhancement — fail silently, movies still load
    }
  }

  function initLangFilter() {
    const bar = document.getElementById('langFilter');
    bar.querySelectorAll('.chip').forEach(btn => {
      const on = btn.dataset.lang === state.lang;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-pressed', String(on));
    });
    bar.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      state.lang = chip.dataset.lang || '';
      bar.querySelectorAll('.chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
      });
      chip.classList.add('active');
      chip.setAttribute('aria-pressed', 'true');
      scheduleLoad();
    });
  }

  // Nav search event (debounced in auth.js)
  window.addEventListener('cinebook:search', (e) => {
    state.search = e.detail.query;
    scheduleLoad();
  });

  document.getElementById('clearFiltersBtn')?.addEventListener('click', () => {
    state.genre = ''; state.lang = ''; state.search = '';
    const navSearch = document.getElementById('navSearch');
    if (navSearch) navSearch.value = '';
    document.querySelectorAll('#genreFilter .chip, #langFilter .chip').forEach(c => {
      const on = !c.dataset.genre && !c.dataset.lang;
      c.classList.toggle('active', on);
      c.setAttribute('aria-pressed', String(on));
    });
    scheduleLoad();
  });
  document.getElementById('retryBtn')?.addEventListener('click', () => loadMovies());

  // -------------------------------------------------------------------------
  // Movies
  // -------------------------------------------------------------------------
  function showSkeletons() {
    grid.innerHTML = Array(6).fill('<div class="skeleton skeleton--poster" aria-hidden="true"></div>').join('');
    empty.classList.add('hidden');
    errorState.classList.add('hidden');
  }

  async function loadMovies() {
    showSkeletons();

    // Cancel any in-flight request so rapid filter clicks don't stack up
    if (inflight) inflight.abort();
    inflight = new AbortController();
    const signal = inflight.signal;

    const params = { city: state.city };
    if (state.genre)  params.genre = state.genre;
    if (state.lang)   params.language = state.lang;
    if (state.search) params.search = state.search;

    try {
      const { data, ok } = await api.get('/movies/', params, { signal });
      grid.innerHTML = '';

      if (!ok) {
        errorState.classList.remove('hidden');
        countEl.textContent = '';
        return;
      }

      const movies = data?.results || [];
      if (movies.length === 0) {
        empty.classList.remove('hidden');
        countEl.textContent = '0 films';
        return;
      }

      countEl.textContent = `${data.count} film${data.count !== 1 ? 's' : ''}`;
      movies.forEach(m => grid.appendChild(createMovieCard(m)));
    } catch (err) {
      // A superseded request was aborted — a newer load is already running, ignore
      if (err && err.name === 'AbortError') return;
      grid.innerHTML = '';
      errorState.classList.remove('hidden');
      countEl.textContent = '';
    }
  }

  // Debounced wrapper: clicking through chips quickly coalesces into one fetch
  let debounceTimer;
  function scheduleLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadMovies, 200);
  }

  /**
   * Poster fallback: monogram on a hue derived from the title, so the
   * seeded no-poster grid still reads as six distinct films.
   */
  function titleHue(title) {
    let hash = 0;
    for (const ch of title) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return hash;
  }

  function createMovieCard(movie) {
    const card = document.createElement('a');
    card.className = 'movie-card';
    card.href = `/movies/${movie.id}/`;
    // No role override — stays a link for AT; label carries the summary
    card.setAttribute('aria-label', `${movie.title} — ${movie.language}, rated ${movie.rating}`);

    const title = escHtml(movie.title);
    const lang = escHtml(movie.language);
    const placeholder =
      `<div class="movie-card__placeholder" style="--ph-hue:${titleHue(movie.title)};" role="img" aria-label="${title} film poster placeholder">
           <span class="movie-card__monogram" aria-hidden="true">${escHtml(movie.title[0])}</span>
           <span class="movie-card__placeholder-label" aria-hidden="true">${lang}</span>
         </div>`;
    // Prefer the real TMDb poster_url; the poster ImageField is usually empty.
    // onerror falls back to the monogram so a dead URL never shows a broken icon.
    const posterSrc = movie.poster_url || movie.poster;
    const media = posterSrc
      ? `<img class="movie-card__poster" src="${escHtml(posterSrc)}" alt="${title} film poster" loading="lazy"
             onerror="this.onerror=null;this.outerHTML=this.dataset.fallback;"
             data-fallback="${escHtml(placeholder)}">`
      : placeholder;

    card.innerHTML = `
      <div class="movie-card__media">
        ${media}
        <span class="movie-card__cert">${escHtml(movie.rating)}</span>
      </div>
      <div class="movie-card__body">
        <div class="movie-card__title">${title}</div>
        <div class="movie-card__meta">${escHtml(movie.duration_display || '')} · ${lang}</div>
      </div>
    `;
    return card;
  }

  // Init
  renderCityPills();
  loadGenres();
  initLangFilter();
  loadMovies();
})();
