/**
 * CineBook — Confirmation page
 * =============================
 * Loads one booking by ref and renders the printable ticket card.
 * Also serves as the "view booking" detail page from My Bookings,
 * so it adapts its header for cancelled bookings.
 */

(function () {
  'use strict';

  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const idx = pathParts.indexOf('confirmation');
  const bookingRef = idx !== -1 ? pathParts[idx + 1] : null;

  const details = document.getElementById('ticketDetails');

  document.getElementById('printBtn')?.addEventListener('click', () => window.print());

  if (!bookingRef) {
    details.innerHTML = '<p class="text-secondary text-center">No booking reference in this link.</p>';
    return;
  }

  if (!isAuthenticated()) {
    window.location.href = `/accounts/login/?next=${encodeURIComponent(window.location.pathname)}`;
    return;
  }

  async function loadBooking() {
    let resp;
    try {
      resp = await api.get(`/bookings/my-bookings/${bookingRef}/`);
    } catch {
      resp = { ok: false, data: null };
    }

    const { data, ok } = resp;
    if (!ok || !data) {
      details.innerHTML = `
        <p class="text-secondary text-center" style="padding:16px 0;">
          We couldn't find this booking. It may belong to another account.
        </p>`;
      return;
    }

    document.title = `${data.movie_title} Ticket — CineBook`;
    document.getElementById('confirmMovieTitle').textContent = data.movie_title;

    // Adapt header when viewing a cancelled booking
    if (data.status === 'CANCELLED') {
      document.getElementById('ticket').classList.add('ticket__status-cancelled');
      document.getElementById('confirmSub').textContent = 'This booking was cancelled.';
      document.getElementById('ticketCheck').innerHTML = `
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path d="M6 6l12 12M18 6L6 18" stroke="#CE2F3F" stroke-width="2.5" stroke-linecap="round"/>
        </svg>`;
    }

    const showTime = new Date(data.show_start_time).toLocaleString('en-IN', {
      weekday: 'long', day: 'numeric', month: 'long',
      hour: '2-digit', minute: '2-digit',
    });
    const seats = (data.booking_seats || []).map(s => s.seat_label).join(', ');
    // Short human-friendly ref: first UUID block
    document.getElementById('bookingRefCode').textContent =
      String(data.booking_ref).split('-')[0].toUpperCase();

    details.innerHTML = `
      <div class="ticket-row">
        <span class="ticket-row__label">Show</span>
        <span class="ticket-row__value">${showTime}</span>
      </div>
      <div class="ticket-row">
        <span class="ticket-row__label">Venue</span>
        <span class="ticket-row__value">${escHtml(data.theater_name)}, ${escHtml(data.theater_city)}</span>
      </div>
      <div class="ticket-row">
        <span class="ticket-row__label">Screen</span>
        <span class="ticket-row__value">${escHtml(data.screen_name)}</span>
      </div>
      <div class="ticket-row">
        <span class="ticket-row__label">Seats</span>
        <span class="ticket-row__value">${escHtml(seats)}</span>
      </div>
      <div class="ticket-row">
        <span class="ticket-row__label">Total Paid</span>
        <span class="ticket-row__value ticket-row__value--total">₹${parseFloat(data.total_amount).toLocaleString('en-IN')}</span>
      </div>
    `;
  }

  loadBooking();
})();
