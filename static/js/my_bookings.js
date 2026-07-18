/**
 * CineBook — My Bookings page
 * ============================
 * Paginated booking list, status filter, ticket detail link, and
 * cancel flow with a confirmation modal (focus-managed, Esc to close).
 */

(function () {
  'use strict';

  if (!isAuthenticated()) {
    window.location.href = '/accounts/login/?next=/bookings/my-bookings/';
    return;
  }

  const state = {
    page: 1,
    status: '',
    cancelTarget: null,
    modalReturnFocus: null,
  };

  const els = {
    list: document.getElementById('bookingsList'),
    empty: document.getElementById('emptyBookings'),
    error: document.getElementById('errorBookings'),
    pagination: document.getElementById('pagination'),
    modal: document.getElementById('cancelModal'),
  };

  const SVG = {
    calendar: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M8 2v4M16 2v4M3 10h18"/></svg>',
    pin:      '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    seat:     '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="5" y="8" width="14" height="10" rx="3"/><path d="M5 18v2M19 18v2M7 8V6a5 5 0 0110 0v2"/></svg>',
  };

  function titleHue(title) {
    let hash = 0;
    for (const ch of title) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return hash;
  }

  // -------------------------------------------------------------------------
  // Load & render
  // -------------------------------------------------------------------------
  async function loadBookings(page = 1) {
    state.page = page;
    els.list.innerHTML = Array(3).fill('<div class="skeleton skeleton--block" aria-hidden="true"></div>').join('');
    els.empty.classList.add('hidden');
    els.error.classList.add('hidden');
    els.pagination.classList.add('hidden');

    let resp;
    try {
      resp = await api.get('/bookings/my-bookings/', { page });
    } catch {
      resp = { ok: false, data: null };
    }

    els.list.innerHTML = '';

    if (!resp.ok) {
      els.error.classList.remove('hidden');
      return;
    }

    const data = resp.data;
    if (!data || data.count === 0) {
      els.empty.classList.remove('hidden');
      return;
    }

    // Status filter is client-side within the current page
    let results = data.results;
    if (state.status) results = results.filter(b => b.status === state.status);

    if (results.length === 0) {
      document.getElementById('emptyBookingsTitle').textContent = 'Nothing here';
      document.getElementById('emptyBookingsDesc').textContent = `No ${state.status.toLowerCase()} bookings on this page.`;
      els.empty.classList.remove('hidden');
      return;
    }

    results.forEach(b => els.list.appendChild(createBookingItem(b)));
    renderPagination(data);
  }

  function createBookingItem(booking) {
    const el = document.createElement('div');
    const statusClass = booking.status.toLowerCase();
    el.className = `booking-item booking-item--${statusClass}`;

    const showTime = booking.show_start_time
      ? new Date(booking.show_start_time).toLocaleString('en-IN', {
          weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
        })
      : '';
    const seats = (booking.booking_seats || []).map(s => s.seat_label).join(', ');
    const canCancel = booking.status === 'CONFIRMED';
    const title = escHtml(booking.movie_title);

    const poster = booking.movie_poster
      ? `<img src="${escHtml(booking.movie_poster)}" alt="${title} poster">`
      : `<span class="booking-item__monogram" style="--ph-hue:${titleHue(booking.movie_title)};" aria-hidden="true">${escHtml(booking.movie_title[0])}</span>`;

    el.innerHTML = `
      <div class="booking-item__poster">${poster}</div>
      <div class="booking-item__info">
        <div class="booking-item__movie">${title}</div>
        <div class="booking-item__meta">
          <span class="booking-item__meta-row">${SVG.calendar}${showTime}</span>
          <span class="booking-item__meta-row">${SVG.pin}${escHtml(booking.theater_name)} · ${escHtml(booking.screen_name)}</span>
          <span class="booking-item__meta-row">${SVG.seat}${escHtml(seats)}</span>
          <span class="booking-item__price">₹${parseFloat(booking.total_amount).toLocaleString('en-IN')}</span>
        </div>
      </div>
      <div class="booking-item__actions">
        <span class="status-badge status-badge--${statusClass}">${escHtml(booking.status)}</span>
        <a href="/bookings/confirmation/${escHtml(booking.booking_ref)}/" class="btn btn--soft btn--sm">View Ticket</a>
        ${canCancel ? `<button class="btn btn--ghost btn--sm" data-cancel="${escHtml(booking.booking_ref)}">Cancel</button>` : ''}
      </div>
    `;

    el.querySelector('[data-cancel]')?.addEventListener('click', () => openCancelModal(booking.booking_ref));
    return el;
  }

  function renderPagination(data) {
    if (!data.total_pages || data.total_pages <= 1) return;
    els.pagination.classList.remove('hidden');
    els.pagination.innerHTML = '';
    for (let p = 1; p <= data.total_pages; p++) {
      const btn = document.createElement('button');
      btn.className = 'pagination__btn' + (p === state.page ? ' active' : '');
      btn.textContent = p;
      btn.setAttribute('aria-label', `Page ${p}`);
      if (p === state.page) btn.setAttribute('aria-current', 'page');
      btn.addEventListener('click', () => loadBookings(p));
      els.pagination.appendChild(btn);
    }
  }

  // -------------------------------------------------------------------------
  // Status filter
  // -------------------------------------------------------------------------
  document.querySelectorAll('#statusFilter .chip').forEach(btn => {
    btn.addEventListener('click', () => {
      state.status = btn.dataset.status;
      document.querySelectorAll('#statusFilter .chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-pressed', 'true');
      loadBookings(1);
    });
  });

  document.getElementById('retryBookingsBtn')?.addEventListener('click', () => loadBookings(state.page));

  // -------------------------------------------------------------------------
  // Cancel modal
  // -------------------------------------------------------------------------
  function openCancelModal(ref) {
    state.cancelTarget = ref;
    state.modalReturnFocus = document.activeElement;
    els.modal.classList.remove('hidden');
    document.getElementById('cancelReason').value = '';
    document.getElementById('cancelModalClose').focus();
  }

  function closeCancelModal() {
    els.modal.classList.add('hidden');
    state.cancelTarget = null;
    // Return focus to the button that opened the dialog
    if (state.modalReturnFocus?.isConnected) state.modalReturnFocus.focus();
    state.modalReturnFocus = null;
  }

  document.getElementById('cancelModalClose').addEventListener('click', closeCancelModal);
  els.modal.addEventListener('click', (e) => { if (e.target === els.modal) closeCancelModal(); });
  document.addEventListener('keydown', (e) => {
    if (els.modal.classList.contains('hidden')) return;
    if (e.key === 'Escape') { closeCancelModal(); return; }
    // Simple focus trap: keep Tab cycling inside the dialog
    if (e.key === 'Tab') {
      const focusables = els.modal.querySelectorAll('button, input, [href]');
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  document.getElementById('cancelModalConfirm').addEventListener('click', async () => {
    if (!state.cancelTarget) return;

    const btn = document.getElementById('cancelModalConfirm');
    const reason = document.getElementById('cancelReason').value.trim();
    btn.classList.add('btn--loading');
    btn.disabled = true;

    let resp;
    try {
      resp = await api.post(`/bookings/cancel/${state.cancelTarget}/`, { reason });
    } catch {
      resp = { ok: false, data: null };
    }

    btn.classList.remove('btn--loading');
    btn.disabled = false;

    if (!resp.ok) {
      // Backend enforces the ≥1h-before-show rule — relay its message
      showToast(resp.data?.message || 'We couldn’t cancel this booking.', 'error', 6000);
    } else {
      showToast('Booking cancelled. Your seats are back on sale.', 'success');
    }

    closeCancelModal();
    loadBookings(state.page);
  });

  // Init
  loadBookings();
})();
