/**
 * CineBook — Shared UI: auth state, toasts, city selector, nav search.
 * Runs on every page via base.html.
 */

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {number} duration ms
 */
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  // Line-style SVG icons in the status palette — no emoji.
  const icons = {
    success: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="7" stroke="#147A43" stroke-width="1.5"/><path d="M5 8l2 2 4-4" stroke="#147A43" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    error:   '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="7" stroke="#CE2F3F" stroke-width="1.5"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#CE2F3F" stroke-width="1.5" stroke-linecap="round"/></svg>',
    warning: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 2L14 13H2L8 2z" stroke="#935800" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 7v3" stroke="#935800" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.5" r="0.5" fill="#935800"/></svg>',
    info:    '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="7" stroke="#1668C7" stroke-width="1.5"/><path d="M8 7v4" stroke="#1668C7" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="5" r="0.75" fill="#1668C7"/></svg>',
  };
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  // Errors/warnings interrupt (alert); success/info wait their turn (status)
  toast.setAttribute('role', type === 'error' || type === 'warning' ? 'alert' : 'status');
  toast.innerHTML = `
    <span class="toast__icon">${icons[type] || icons.info}</span>
    <span class="toast__message"></span>
  `;
  // textContent, not innerHTML — messages may echo user/server text
  toast.querySelector('.toast__message').textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => toast.remove());
    // Fallback removal if animations are disabled (prefers-reduced-motion)
    setTimeout(() => toast.remove(), 400);
  }, duration);
}
window.showToast = showToast;

/**
 * Escape text for interpolation into HTML strings (attribute or content).
 * @param {any} s
 * @returns {string}
 */
function escHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
window.escHtml = escHtml;

/**
 * Parse JWT payload (base64 decode claims).
 * @param {string} token
 * @returns {object|null}
 */
function parseJwt(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

/**
 * Update the navbar to reflect auth state.
 */
function updateNavbarAuth() {
  const section = document.getElementById('navAuthSection');
  if (!section) return;

  if (!isAuthenticated()) {
    section.innerHTML = `
      <a href="/accounts/login/" class="navbar__btn navbar__btn--ghost">Login</a>
      <a href="/accounts/register/" class="navbar__btn navbar__btn--dark">Sign Up</a>
    `;
    return;
  }

  const claims = parseJwt(getAccessToken());
  const username = escHtml(claims?.username || 'User');
  const initial = username[0].toUpperCase();
  const isStaff = claims?.is_staff;

  section.innerHTML = `
    <div class="navbar__user-menu" tabindex="0" role="button" aria-haspopup="true" aria-label="User menu for ${username}">
      <div class="navbar__avatar" title="${username}">${initial}</div>
      <div class="navbar__dropdown" role="menu">
        <div class="navbar__dropdown-item navbar__dropdown-item--user">${username}</div>
        <div class="navbar__dropdown-divider"></div>
        <a href="/bookings/my-bookings/" class="navbar__dropdown-item" role="menuitem">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M8 2v4M16 2v4M3 10h18"/></svg>
          My Bookings
        </a>
        ${isStaff ? `<a href="/admin/" class="navbar__dropdown-item" role="menuitem"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg> Admin</a>` : ''}
        <div class="navbar__dropdown-divider"></div>
        <button class="navbar__dropdown-item navbar__dropdown-item--danger" id="navLogoutBtn" role="menuitem">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          Logout
        </button>
      </div>
    </div>
  `;

  document.getElementById('navLogoutBtn')?.addEventListener('click', handleLogout);
}

/**
 * Logout: blacklist refresh token server-side, clear local state, go home.
 */
async function handleLogout() {
  try {
    await api.post('/auth/logout/', { refresh: getRefreshToken() });
  } catch {
    // Clear client state regardless of server result
  } finally {
    clearTokens();
    showToast('You\u2019re logged out. See you at the movies!', 'success');
    setTimeout(() => { window.location.href = '/'; }, 900);
  }
}

// ---------------------------------------------------------------------------
// City persistence & API
// ---------------------------------------------------------------------------

// Cached cities list — populated on first fetch
let _citiesCache = null;

function getSavedCity() {
  return localStorage.getItem('cinebook_city') || 'Mumbai';
}
function saveCity(city) {
  localStorage.setItem('cinebook_city', city);
}
function updateNavCity() {
  const label = document.getElementById('navCityLabel');
  if (label) label.textContent = getSavedCity();
}
window.getSavedCity = getSavedCity;
window.saveCity = saveCity;

/**
 * Fetch cities from the API and cache them.
 * Falls back to a default list on failure.
 */
async function fetchCities() {
  if (_citiesCache) return _citiesCache;
  try {
    const { data, ok } = await api.get('/cities/');
    if (ok && Array.isArray(data)) {
      _citiesCache = data.map(c => c.name);
      return _citiesCache;
    }
  } catch { /* fall through */ }
  _citiesCache = ['Mumbai', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Pune', 'Kochi'];
  return _citiesCache;
}
window.fetchCities = fetchCities;

// Expose CINEBOOK_CITIES for backward compat (home.js hero pills use it)
// It starts as a default and gets updated after the API call resolves.
window.CINEBOOK_CITIES = ['Mumbai', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Pune', 'Kochi'];

/**
 * City selector: searchable modal anchored to the nav pill.
 * Features filter-as-you-type, keyboard nav, and accessible markup.
 */
function initCitySelector() {
  const btn = document.getElementById('navCityBtn');
  if (!btn) return;

  let panel = null;
  btn.setAttribute('aria-haspopup', 'true');
  btn.setAttribute('aria-expanded', 'false');

  function closePanel() {
    panel?.remove();
    panel = null;
    btn.setAttribute('aria-expanded', 'false');
    document.removeEventListener('click', onDocClick);
    document.removeEventListener('keydown', onEsc);
  }
  function onDocClick(e) {
    if (panel && !panel.contains(e.target) && !btn.contains(e.target)) closePanel();
  }
  function onEsc(e) {
    if (e.key === 'Escape') { closePanel(); btn.focus(); }
  }

  btn.addEventListener('click', async () => {
    if (panel) { closePanel(); return; }

    const cities = await fetchCities();
    // Also update global array for hero pills
    window.CINEBOOK_CITIES = cities;

    panel = document.createElement('div');
    panel.className = 'city-modal';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Choose your city');
    btn.setAttribute('aria-expanded', 'true');

    const current = getSavedCity();
    panel.innerHTML = `
      <div class="city-modal__search-wrap">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input type="search" class="city-modal__search" placeholder="Search cities..." aria-label="Search cities" autocomplete="off">
      </div>
      <div class="city-modal__list" role="listbox" aria-label="Cities"></div>
    `;

    const listEl = panel.querySelector('.city-modal__list');
    const searchInput = panel.querySelector('.city-modal__search');

    function renderCities(filter = '') {
      const filtered = filter
        ? cities.filter(c => c.toLowerCase().includes(filter.toLowerCase()))
        : cities;
      if (filtered.length === 0) {
        listEl.innerHTML = '<div class="city-modal__empty">No cities found</div>';
        return;
      }
      listEl.innerHTML = filtered.map(c => `
        <button class="city-modal__item${c === current ? ' active' : ''}"
                role="option" aria-selected="${c === current}" data-city="${escHtml(c)}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
          </svg>
          ${escHtml(c)}
        </button>
      `).join('');

      listEl.querySelectorAll('.city-modal__item').forEach(item => {
        item.addEventListener('click', () => {
          saveCity(item.dataset.city);
          updateNavCity();
          closePanel();
          // Dispatch city change event for pages that want to react without reload
          window.dispatchEvent(new CustomEvent('cinebook:citychange', { detail: { city: item.dataset.city } }));
          window.location.reload();
        });
      });
    }

    renderCities();

    searchInput.addEventListener('input', () => {
      renderCities(searchInput.value.trim());
    });

    // Position anchored below the button
    const rect = btn.getBoundingClientRect();
    panel.style.top = `${rect.bottom + 8}px`;
    panel.style.left = `${Math.max(8, rect.left - 40)}px`;
    document.body.appendChild(panel);

    // Auto-focus the search input
    searchInput.focus();

    setTimeout(() => {
      document.addEventListener('click', onDocClick);
      document.addEventListener('keydown', onEsc);
    }, 0);
  });
}

// ---------------------------------------------------------------------------
// Nav search (debounced)
// ---------------------------------------------------------------------------
function initNavSearch() {
  const input = document.getElementById('navSearch');
  if (!input) return;

  // Pre-fill from URL if we're already on a search
  const urlQ = new URLSearchParams(window.location.search).get('search');
  if (urlQ) input.value = urlQ;

  let debounceTimer;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const q = input.value.trim();
      // On the home page, home.js listens for this event and filters in place;
      // elsewhere, navigate to home with the query.
      if (q.length >= 2 || q.length === 0) {
        const evt = new CustomEvent('cinebook:search', { detail: { query: q } });
        const handled = window.dispatchEvent(evt);
        if (!window.CINEBOOK_HOME && q.length >= 2) {
          window.location.href = `/?search=${encodeURIComponent(q)}`;
        }
      }
    }, 400);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = input.value.trim();
      if (q && !window.CINEBOOK_HOME) window.location.href = `/?search=${encodeURIComponent(q)}`;
    }
  });
}

// Initialise on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  updateNavbarAuth();
  updateNavCity();
  initNavSearch();
  initCitySelector();
  // Pre-fetch cities to populate the global array for hero pills etc.
  fetchCities().then(cities => { window.CINEBOOK_CITIES = cities; });
});
