/**
 * CineBook — API Client
 * ======================
 * Centralised fetch() wrapper with JWT handling, CSRF support, and error normalisation.
 * All API calls go through this module — never use raw fetch() in page scripts.
 */

const API_BASE = '/api/v1';
const TOKEN_KEY = 'cinebook_access';
const REFRESH_KEY = 'cinebook_refresh';

/**
 * Get the current access token from localStorage.
 * @returns {string|null}
 */
function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Get the current refresh token.
 * @returns {string|null}
 */
function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

/**
 * Store JWT tokens after login/registration.
 * @param {string} access
 * @param {string} refresh
 */
function storeTokens(access, refresh) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

/**
 * Clear tokens (logout).
 */
function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/**
 * Check if the user is currently authenticated (has a token stored).
 * @returns {boolean}
 */
function isAuthenticated() {
  return !!getAccessToken();
}

/**
 * Get the CSRF token from the cookie (required for state-changing requests).
 * @returns {string}
 */
function getCsrfToken() {
  const name = 'csrftoken';
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

/**
 * Attempt to refresh the access token using the stored refresh token.
 * @returns {Promise<string|null>} New access token, or null on failure.
 */
async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  try {
    const resp = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });

    if (!resp.ok) {
      clearTokens();
      return null;
    }

    const data = await resp.json();
    localStorage.setItem(TOKEN_KEY, data.access);
    if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh);
    return data.access;
  } catch {
    clearTokens();
    return null;
  }
}

/**
 * Core API request function.
 * Automatically attaches Bearer token, CSRF cookie, and handles 401 → token refresh.
 *
 * @param {string} endpoint - API path (e.g. '/movies/')
 * @param {object} options  - fetch() options override
 * @returns {Promise<{data: any, ok: boolean, status: number}>}
 */
async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken(),
    ...options.headers,
  };

  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let resp = await fetch(url, {
    ...options,
    headers,
    credentials: 'same-origin',
  });

  // 401 → try refresh once
  if (resp.status === 401 && getRefreshToken()) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      resp = await fetch(url, { ...options, headers, credentials: 'same-origin' });
    }
  }

  let data = null;
  const contentType = resp.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try { data = await resp.json(); } catch { data = null; }
  }

  return { data, ok: resp.ok, status: resp.status };
}

// ---------------------------------------------------------------------------
// Convenience methods
// ---------------------------------------------------------------------------

const api = {
  get: (endpoint, params = {}, options = {}) => {
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `${endpoint}?${qs}` : endpoint;
    return apiRequest(url, { method: 'GET', ...options });
  },

  post: (endpoint, body = {}) =>
    apiRequest(endpoint, { method: 'POST', body: JSON.stringify(body) }),

  patch: (endpoint, body = {}) =>
    apiRequest(endpoint, { method: 'PATCH', body: JSON.stringify(body) }),

  delete: (endpoint) =>
    apiRequest(endpoint, { method: 'DELETE' }),
};

// Export for use in page scripts
window.api = api;
window.storeTokens = storeTokens;
window.clearTokens = clearTokens;
window.isAuthenticated = isAuthenticated;
window.getAccessToken = getAccessToken;
window.getRefreshToken = getRefreshToken;
