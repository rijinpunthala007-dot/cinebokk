/**
 * CineBook — Login page
 * ======================
 * Client validation + JWT login, honours ?next= redirect.
 */

(function () {
  'use strict';

  // Already logged in → straight through
  if (isAuthenticated()) {
    const next = new URLSearchParams(window.location.search).get('next');
    window.location.href = next || '/';
    return;
  }

  function clearErrors() {
    ['usernameError', 'passwordError', 'loginError'].forEach(id => {
      const el = document.getElementById(id);
      el.classList.add('hidden');
      el.textContent = '';
    });
    ['username', 'password'].forEach(id => {
      const el = document.getElementById(id);
      el.classList.remove('form-input--error');
      el.removeAttribute('aria-invalid');
    });
  }

  function showFieldError(fieldId, errorId, msg) {
    const err = document.getElementById(errorId);
    err.textContent = msg;
    err.classList.remove('hidden');
    const input = document.getElementById(fieldId);
    input.classList.add('form-input--error');
    input.setAttribute('aria-invalid', 'true');
  }

  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    let valid = true;

    if (!username) { showFieldError('username', 'usernameError', 'Enter your username.'); valid = false; }
    if (!password) { showFieldError('password', 'passwordError', 'Enter your password.'); valid = false; }
    if (!valid) return;

    const btn = document.getElementById('loginBtn');
    btn.classList.add('btn--loading');
    btn.disabled = true;

    let resp;
    try {
      resp = await api.post('/auth/login/', { username, password });
    } catch {
      resp = { ok: false, data: null };
    }

    btn.classList.remove('btn--loading');
    btn.disabled = false;

    if (!resp.ok || !resp.data?.access) {
      const msg = resp.data?.detail || resp.data?.message ||
        'That username and password didn’t match. Try again.';
      const errEl = document.getElementById('loginError');
      errEl.textContent = msg;
      errEl.classList.remove('hidden');
      return;
    }

    storeTokens(resp.data.access, resp.data.refresh);
    showToast(`Welcome back${resp.data.user?.first_name ? ', ' + resp.data.user.first_name : ''}!`, 'success');

    const next = new URLSearchParams(window.location.search).get('next');
    setTimeout(() => { window.location.href = next || '/'; }, 600);
  });
})();
