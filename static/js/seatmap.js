/**
 * CineBook — Seat map page (signature screen)
 * ============================================
 * Optimistic seat selection with server reconciliation:
 *  - clicking a seat highlights INSTANTLY (no network wait)
 *  - "Proceed" locks the batch server-side; on 409 the rejected seats
 *    shake + revert and the map refreshes with fresh availability
 *  - a visible 5-minute lock countdown runs after a successful lock
 * Rapid clicks are throttled per-seat; the whole grid is keyboard operable.
 */

(function () {
  'use strict';

  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const showId = pathParts[pathParts.indexOf('seat-map') + 1];

  const MAX_SEATS = 10;
  const CLICK_THROTTLE_MS = 150; // ignore hyper-rapid double taps per seat

  const state = {
    seatMap: null,
    selected: new Map(),   // seat_id → { label, price, category }
    lockExpiry: null,
    lockInterval: null,
    lastClickAt: new Map(), // seat_id → timestamp (throttle)
    locking: false,
  };

  const els = {
    grid: document.getElementById('seatGridContainer'),
    error: document.getElementById('seatError'),
    footer: document.getElementById('bookingFooter'),
    count: document.getElementById('selectedCount'),
    tags: document.getElementById('selectedSeatTags'),
    price: document.getElementById('totalPrice'),
    timer: document.getElementById('lockTimer'),
    proceed: document.getElementById('proceedBtn'),
    showBar: document.getElementById('showBar'),
  };

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    if (!showId) {
      showError('This link looks broken', 'Head back and pick a showtime again.');
      return;
    }
    if (!isAuthenticated()) {
      showToast('Log in to pick your seats.', 'info');
      setTimeout(() => {
        window.location.href = `/accounts/login/?next=${encodeURIComponent(window.location.pathname)}`;
      }, 1200);
      return;
    }
    loadSeatMap();
    els.proceed.addEventListener('click', handleProceed);
    document.getElementById('seatRetryBtn')?.addEventListener('click', loadSeatMap);
  }

  // -------------------------------------------------------------------------
  // Load & render
  // -------------------------------------------------------------------------
  async function loadSeatMap() {
    els.error.classList.add('hidden');
    els.grid.innerHTML = '<div class="skeleton" style="height:280px;max-width:560px;margin:0 auto;border-radius:20px;" aria-hidden="true"></div>';

    let resp;
    try {
      resp = await api.get(`/shows/${showId}/seat-map/`);
    } catch {
      showError();
      return;
    }
    if (!resp.ok || !resp.data) {
      showError();
      return;
    }

    state.seatMap = resp.data;
    renderShowBar(resp.data);
    renderSeatGrid(resp.data);
  }

  function renderShowBar(data) {
    const startTime = new Date(data.start_time).toLocaleString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    });
    els.showBar.innerHTML = `
      <h1 class="show-bar__movie">${escHtml(data.movie_title)}</h1>
      <div class="show-bar__details">${startTime} &nbsp;·&nbsp; ${escHtml(data.screen_name)}</div>
    `;
    document.title = `Select Seats — ${data.movie_title} — CineBook`;
  }

  function renderSeatGrid(data) {
    els.grid.innerHTML = '';
    const rows = data.rows || {};
    const rowLabels = Object.keys(rows).sort();

    if (rowLabels.length === 0) {
      showError('No seats configured', 'This show has no seat map yet. Try another showtime.');
      return;
    }

    const grid = document.createElement('div');
    grid.className = 'seat-grid';

    let lastCategory = null;
    // Server pre-sorts each row; keep our selection across re-renders
    const prevSelected = new Set(state.selected.keys());
    state.selected.clear();

    rowLabels.forEach(rowLabel => {
      const seats = rows[rowLabel];
      if (!seats?.length) return;

      // Category section label whenever the tier changes going down the grid.
      // (Colorblind-safe: tier is named in text, not just tinted.)
      const cat = seats[0].category;
      if (cat !== lastCategory) {
        lastCategory = cat;
        const price = data.categories?.[cat];
        const section = document.createElement('div');
        section.className = 'seat-section';
        section.setAttribute('aria-hidden', 'true');
        section.textContent = price != null ? `${titleCase(cat)} · ₹${Number(price)}` : titleCase(cat);
        grid.appendChild(section);
      }

      const rowEl = document.createElement('div');
      rowEl.className = 'seat-row';

      const labelEl = document.createElement('span');
      labelEl.className = 'seat-row__label';
      labelEl.setAttribute('aria-hidden', 'true');
      labelEl.textContent = rowLabel;
      rowEl.appendChild(labelEl);

      const midpoint = Math.ceil(seats.length / 2);
      seats.forEach((seat, i) => {
        rowEl.appendChild(createSeatButton(seat, prevSelected));
        // Central aisle: single gap at the row midpoint (calm, symmetric)
        if (i + 1 === midpoint && seats.length > 4) {
          const aisle = document.createElement('span');
          aisle.className = 'seat-aisle';
          aisle.setAttribute('aria-hidden', 'true');
          rowEl.appendChild(aisle);
        }
      });

      grid.appendChild(rowEl);
    });

    els.grid.appendChild(grid);
    syncFooter();
  }

  function createSeatButton(seat, prevSelected) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `seat seat--${seat.category.toLowerCase()}`;
    btn.dataset.seatId = seat.seat_id;
    btn.textContent = seat.number;
    btn.setAttribute('aria-label',
      `Seat ${seat.label}, ${titleCase(seat.category)}, ₹${Number(seat.price)}${seat.status === 'BOOKED' ? ', booked' : ''}`);

    if (seat.status === 'BOOKED' || (seat.status === 'LOCKED' && !seat.is_mine)) {
      btn.classList.add('seat--booked');
      btn.disabled = true;
      return btn;
    }

    btn.setAttribute('aria-pressed', 'false');

    // Re-apply selection that survived a map refresh (incl. our own locks)
    if (seat.is_mine || prevSelected.has(seat.seat_id)) {
      selectSeat(seat, btn);
    }

    btn.addEventListener('click', () => {
      // Throttle rapid re-clicks on the same seat
      const now = Date.now();
      const last = state.lastClickAt.get(seat.seat_id) || 0;
      if (now - last < CLICK_THROTTLE_MS) return;
      state.lastClickAt.set(seat.seat_id, now);
      toggleSeat(seat, btn);
    });

    return btn;
  }

  function titleCase(s) {
    return s.charAt(0) + s.slice(1).toLowerCase();
  }

  // -------------------------------------------------------------------------
  // Selection (optimistic — instant visual, server reconciles at lock time)
  // -------------------------------------------------------------------------
  function selectSeat(seat, btn) {
    state.selected.set(seat.seat_id, {
      label: seat.label,
      price: parseFloat(seat.price),
      category: seat.category,
    });
    btn.classList.add('seat--selected');
    btn.setAttribute('aria-pressed', 'true');
  }

  function deselectSeat(seatId, btn) {
    state.selected.delete(seatId);
    btn.classList.remove('seat--selected');
    btn.setAttribute('aria-pressed', 'false');
  }

  function toggleSeat(seat, btn) {
    if (state.selected.has(seat.seat_id)) {
      deselectSeat(seat.seat_id, btn);
    } else {
      if (state.selected.size >= MAX_SEATS) {
        showToast(`You can book up to ${MAX_SEATS} seats at once.`, 'warning');
        return;
      }
      selectSeat(seat, btn);
    }
    syncFooter();
  }

  function syncFooter() {
    const seats = [...state.selected.values()];
    const total = seats.reduce((sum, s) => sum + s.price, 0);

    els.count.textContent = seats.length;
    els.price.textContent = `₹${total.toLocaleString('en-IN')}`;
    els.tags.innerHTML = seats.map(s => `<span class="booking-footer__seat-tag">${escHtml(s.label)}</span>`).join('');

    if (seats.length > 0) {
      els.footer.classList.add('visible');
      els.proceed.disabled = false;
    } else {
      els.footer.classList.remove('visible');
      els.proceed.disabled = true;
      stopLockTimer();
    }
  }

  // -------------------------------------------------------------------------
  // Lock & proceed
  // -------------------------------------------------------------------------
  async function handleProceed() {
    if (state.locking) return;
    const seatIds = [...state.selected.keys()];
    if (seatIds.length === 0) return;

    state.locking = true;
    els.proceed.classList.add('btn--loading');
    els.proceed.disabled = true;

    let resp;
    try {
      resp = await api.post('/bookings/lock-seats/', {
        show_id: parseInt(showId, 10),
        seat_ids: seatIds,
      });
    } catch {
      resp = { ok: false, status: 0, data: null };
    }

    state.locking = false;
    els.proceed.classList.remove('btn--loading');
    els.proceed.disabled = false;

    if (!resp.ok) {
      if (resp.status === 409) {
        // Reconcile: someone beat us to it. Shake the map, tell them plainly,
        // refresh availability (server sweeps expired locks on this GET).
        showToast('One of those seats was just taken. Pick another one.', 'error', 6000);
        document.querySelectorAll('.seat--selected').forEach(el => el.classList.add('seat--reverting'));
        setTimeout(loadSeatMap, 500);
      } else {
        showToast(resp.data?.message || 'We couldn’t hold those seats. Please try again.', 'error', 6000);
      }
      return;
    }

    // Locked — hand off to checkout with everything it needs
    state.lockExpiry = new Date(resp.data.lock_expiry);
    startLockTimer();

    sessionStorage.setItem('cinebook_lock', JSON.stringify({
      show_id: parseInt(showId, 10),
      seat_ids: seatIds,
      lock_expiry: resp.data.lock_expiry,
      seats: [...state.selected.entries()].map(([id, s]) => ({
        id, label: s.label, price: s.price, category: s.category,
      })),
      movie_title: state.seatMap?.movie_title,
      show_time: state.seatMap?.start_time,
      screen: state.seatMap?.screen_name,
    }));

    showToast(`${seatIds.length} seat(s) held for 5 minutes — complete payment to confirm.`, 'success', 2500);
    setTimeout(() => { window.location.href = '/bookings/checkout/'; }, 900);
  }

  // -------------------------------------------------------------------------
  // Lock countdown
  // -------------------------------------------------------------------------
  function startLockTimer() {
    stopLockTimer();
    els.timer.classList.remove('hidden');
    state.lockInterval = setInterval(tickLockTimer, 1000);
    tickLockTimer();
  }

  function tickLockTimer() {
    if (!state.lockExpiry) return;
    const remaining = Math.max(0, Math.floor((state.lockExpiry - Date.now()) / 1000));
    const mins = Math.floor(remaining / 60);
    const secs = String(remaining % 60).padStart(2, '0');

    els.timer.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/>
      </svg>
      Held for ${mins}:${secs}`;

    els.timer.classList.toggle('lock-timer--warning', remaining > 0 && remaining <= 60);

    if (remaining === 0) {
      stopLockTimer();
      els.timer.classList.remove('hidden');
      els.timer.classList.add('lock-timer--expired');
      els.timer.textContent = 'Hold expired';
      showToast('Your seat hold expired — they’re back up for grabs. Please reselect.', 'error', 6000);
      sessionStorage.removeItem('cinebook_lock');
      state.selected.clear();
      state.lockExpiry = null;
      syncFooter();
      loadSeatMap();
    }
  }

  function stopLockTimer() {
    if (state.lockInterval) {
      clearInterval(state.lockInterval);
      state.lockInterval = null;
    }
    els.timer.classList.add('hidden');
    els.timer.classList.remove('lock-timer--warning', 'lock-timer--expired');
  }

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------
  function showError(title, desc) {
    els.grid.innerHTML = '';
    els.error.classList.remove('hidden');
    if (title) document.getElementById('seatErrorTitle').textContent = title;
    if (desc) document.getElementById('seatErrorDesc').textContent = desc;
  }
})();
