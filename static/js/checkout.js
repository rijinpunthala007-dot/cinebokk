/**
 * CineBook — Checkout page
 * =========================
 * Reads the seat lock from sessionStorage, renders the price breakdown,
 * continues the lock countdown, validates the simulated payment form,
 * and calls the confirm endpoint (payment simulation happens server-side).
 */

(function () {
  'use strict';

  let lockData = null;
  let lockInterval = null;

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    if (!isAuthenticated()) {
      window.location.href = '/accounts/login/?next=/bookings/checkout/';
      return;
    }

    // Seat lock handoff from the seat map page
    try {
      lockData = JSON.parse(sessionStorage.getItem('cinebook_lock'));
      if (!lockData?.seat_ids?.length) throw new Error('no lock');
    } catch {
      showToast('Your seat selection expired. Let’s pick seats again.', 'warning', 4000);
      setTimeout(() => { window.location.href = '/'; }, 1800);
      return;
    }

    renderSummary();
    startLockTimer();
    initPaymentForm();
  }

  // -------------------------------------------------------------------------
  // Summary
  // -------------------------------------------------------------------------
  function renderSummary() {
    const { seats, movie_title, show_time, screen } = lockData;
    const showDate = show_time
      ? new Date(show_time).toLocaleString('en-IN', {
          weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
        })
      : '';
    const total = seats.reduce((sum, s) => sum + s.price, 0);

    const seatRows = seats.map(s => `
      <div class="summary-row">
        <span class="summary-row__label">${escHtml(s.label)} · ${escHtml(titleCase(s.category))}</span>
        <span class="summary-row__value">₹${s.price.toLocaleString('en-IN')}</span>
      </div>
    `).join('');

    document.getElementById('summaryContent').innerHTML = `
      <div class="summary-movie">${escHtml(movie_title || 'Your movie')}</div>
      <div class="summary-sub">${showDate}</div>
      <div class="summary-sub">${escHtml(screen || '')}</div>
      <div class="summary-divider"></div>
      <div class="summary-label">Seats (${seats.length})</div>
      ${seatRows}
      <div class="summary-row summary-row--total">
        <span class="summary-row__label">Total</span>
        <span class="summary-row__value">₹${total.toLocaleString('en-IN')}</span>
      </div>
    `;
  }

  function titleCase(s) {
    return s ? s.charAt(0) + s.slice(1).toLowerCase() : '';
  }

  // -------------------------------------------------------------------------
  // Lock countdown (continues the hold started on the seat map)
  // -------------------------------------------------------------------------
  function startLockTimer() {
    const expiry = new Date(lockData.lock_expiry);
    clearInterval(lockInterval);
    lockInterval = setInterval(() => tick(expiry), 1000);
    tick(expiry);
  }

  function tick(expiry) {
    const remaining = Math.max(0, Math.floor((expiry - Date.now()) / 1000));
    const mins = Math.floor(remaining / 60);
    const secs = String(remaining % 60).padStart(2, '0');

    const timerEl = document.getElementById('lockTimerText');
    const banner = document.getElementById('lockBanner');
    if (timerEl) timerEl.textContent = `${mins}:${secs}`;
    banner?.classList.toggle('lock-banner--urgent', remaining > 0 && remaining <= 60);

    if (remaining === 0) {
      clearInterval(lockInterval);
      sessionStorage.removeItem('cinebook_lock');
      showToast('Your seat hold expired — they’re back up for grabs. Please reselect.', 'error', 5000);
      const showId = lockData?.show_id;
      setTimeout(() => {
        window.location.href = showId ? `/bookings/seat-map/${showId}/` : '/';
      }, 2200);
    }
  }

  // -------------------------------------------------------------------------
  // Payment form
  // -------------------------------------------------------------------------
  function initPaymentForm() {
    const cardInput = document.getElementById('cardNumber');
    const expiryInput = document.getElementById('expiry');

    // Auto-format: 1234 5678 9012 3456
    cardInput?.addEventListener('input', () => {
      const val = cardInput.value.replace(/\D/g, '').slice(0, 16);
      cardInput.value = val.replace(/(.{4})/g, '$1 ').trim();
    });

    // Auto-format: MM/YY
    expiryInput?.addEventListener('input', () => {
      let val = expiryInput.value.replace(/\D/g, '').slice(0, 4);
      if (val.length >= 3) val = val.slice(0, 2) + '/' + val.slice(2);
      expiryInput.value = val;
    });

    document.getElementById('paymentForm')?.addEventListener('submit', handleSubmit);
  }

  function clearErrors() {
    document.querySelectorAll('.form-error').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.form-input').forEach(el => {
      el.classList.remove('form-input--error');
      el.removeAttribute('aria-invalid');
    });
  }

  function showFieldError(fieldId, msg) {
    const input = document.getElementById(fieldId);
    input?.classList.add('form-input--error');
    input?.setAttribute('aria-invalid', 'true');
    const error = document.getElementById(fieldId + 'Error');
    if (error) { error.textContent = msg; error.classList.remove('hidden'); }
  }

  function validateForm() {
    clearErrors();
    let valid = true;

    const card = document.getElementById('cardNumber').value.replace(/\s/g, '');
    if (card.length < 13 || !/^\d+$/.test(card)) {
      showFieldError('cardNumber', 'That card number looks too short.');
      valid = false;
    }

    const name = document.getElementById('nameOnCard').value.trim();
    if (name.length < 2) {
      showFieldError('nameOnCard', 'Enter the name printed on your card.');
      valid = false;
    }

    const expiry = document.getElementById('expiry').value.trim();
    if (!/^\d{2}\/\d{2}$/.test(expiry)) {
      showFieldError('expiry', 'Use MM/YY, like 12/28.');
      valid = false;
    }

    const cvv = document.getElementById('cvv').value.trim();
    if (!/^\d{3,4}$/.test(cvv)) {
      showFieldError('cvv', 'CVV is the 3 or 4-digit code on the back.');
      valid = false;
    }

    return valid;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validateForm()) return;

    const btn = document.getElementById('payBtn');
    btn.classList.add('btn--loading');
    btn.disabled = true;

    let resp;
    try {
      resp = await api.post('/bookings/confirm/', {
        show_id: lockData.show_id,
        seat_ids: lockData.seat_ids,
        payment: {
          card_number: document.getElementById('cardNumber').value.replace(/\s/g, ''),
          name_on_card: document.getElementById('nameOnCard').value.trim(),
          expiry: document.getElementById('expiry').value.trim(),
          cvv: document.getElementById('cvv').value.trim(),
        },
      });
    } catch {
      resp = { ok: false, status: 0, data: null };
    }

    btn.classList.remove('btn--loading');
    btn.disabled = false;

    if (!resp.ok) {
      // Speak in the product's voice per error type, not raw status codes
      if (resp.status === 410) {
        // Lock expired mid-checkout — send them back to reselect
        sessionStorage.removeItem('cinebook_lock');
        showToast('Your seat hold expired before payment went through. Please reselect.', 'error', 6000);
        setTimeout(() => { window.location.href = `/bookings/seat-map/${lockData.show_id}/`; }, 2200);
      } else if (resp.status === 409) {
        sessionStorage.removeItem('cinebook_lock');
        showToast('Those seats were just taken by someone else. Pick new ones.', 'error', 6000);
        setTimeout(() => { window.location.href = `/bookings/seat-map/${lockData.show_id}/`; }, 2200);
      } else if (resp.status === 402) {
        showToast(resp.data?.message || 'Payment was declined. Check your details and try again.', 'error', 6000);
      } else {
        showToast(resp.data?.message || 'Something went wrong confirming your booking. Try again.', 'error', 6000);
      }
      return;
    }

    // Confirmed — clean up and celebrate on the confirmation page
    clearInterval(lockInterval);
    sessionStorage.removeItem('cinebook_lock');

    const bookingRef = resp.data?.booking?.booking_ref;
    showToast('Booking confirmed — enjoy the show!', 'success', 2000);
    setTimeout(() => {
      window.location.href = bookingRef
        ? `/bookings/confirmation/${bookingRef}/`
        : '/bookings/my-bookings/';
    }, 900);
  }
})();
