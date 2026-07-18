/**
 * CineBook — Register page
 * =========================
 * Client validation + registration with auto-login.
 * API contract: POST /auth/register/ expects `password_confirm`;
 * errors arrive as {details: {field: [msgs]}}; tokens nest under `tokens`.
 */

(function () {
  'use strict';

  if (isAuthenticated()) {
    window.location.href = '/';
    return;
  }

  const FIELDS = ['firstName', 'regUsername', 'email', 'regPassword', 'confirmPassword'];

  function clearErrors() {
    FIELDS.forEach(id => {
      const input = document.getElementById(id);
      input?.classList.remove('form-input--error');
      input?.removeAttribute('aria-invalid');
      const err = document.getElementById(id + 'Error');
      if (err) { err.classList.add('hidden'); err.textContent = ''; }
    });
    const general = document.getElementById('registerError');
    general.classList.add('hidden');
    general.textContent = '';
  }

  function showFieldError(fieldId, msg) {
    const input = document.getElementById(fieldId);
    input?.classList.add('form-input--error');
    input?.setAttribute('aria-invalid', 'true');
    const err = document.getElementById(fieldId + 'Error');
    if (err) { err.textContent = msg; err.classList.remove('hidden'); }
  }

  document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const firstName = document.getElementById('firstName').value.trim();
    const lastName = document.getElementById('lastName').value.trim();
    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('confirmPassword').value;
    let valid = true;

    if (!firstName) { showFieldError('firstName', 'Tell us your first name.'); valid = false; }
    if (!username) { showFieldError('regUsername', 'Pick a username.'); valid = false; }
    if (!email || !email.includes('@')) { showFieldError('email', 'That email doesn’t look right.'); valid = false; }
    if (!password || password.length < 8) { showFieldError('regPassword', 'Use at least 8 characters.'); valid = false; }
    if (password !== confirm) { showFieldError('confirmPassword', 'These passwords don’t match.'); valid = false; }
    if (!valid) return;

    const btn = document.getElementById('registerBtn');
    btn.classList.add('btn--loading');
    btn.disabled = true;

    let resp;
    try {
      resp = await api.post('/auth/register/', {
        username, email, password,
        password_confirm: confirm,
        first_name: firstName,
        last_name: lastName,
      });
    } catch {
      resp = { ok: false, data: null };
    }

    btn.classList.remove('btn--loading');
    btn.disabled = false;

    if (!resp.ok) {
      // Surface DRF field errors from the normalized {details: {...}} shape
      const details = resp.data?.details || {};
      const fieldMap = {
        username: 'regUsername', email: 'email',
        password: 'regPassword', password_confirm: 'confirmPassword',
        first_name: 'firstName',
      };
      let shown = false;
      Object.entries(fieldMap).forEach(([apiField, domId]) => {
        if (details[apiField]?.length) {
          showFieldError(domId, details[apiField][0]);
          shown = true;
        }
      });
      if (!shown) {
        const general = document.getElementById('registerError');
        general.textContent = resp.data?.message || 'We couldn’t create your account. Try again.';
        general.classList.remove('hidden');
      }
      return;
    }

    // Auto-login: tokens nest under data.tokens
    const tokens = resp.data?.tokens;
    if (tokens?.access) {
      storeTokens(tokens.access, tokens.refresh);
      showToast('Account created — welcome to CineBook!', 'success');
      setTimeout(() => { window.location.href = '/'; }, 800);
    } else {
      showToast('Account created! Please log in.', 'success');
      setTimeout(() => { window.location.href = '/accounts/login/'; }, 1000);
    }
  });
})();
