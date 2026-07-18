/**
 * CineBook — Movie details page (movie_detail.js)
 * ================================================
 * Renders movie backdrop hero, poster, metadata, synopsis,
 * "Book Tickets" CTA, "Watch Trailer" YouTube modal, and interactive cast strip
 * with actor biography popovers.
 *
 * Accessibility features: focus trapping inside open modals, focus restoration
 * on close, Escape key handler, backdrop click close, and prefers-reduced-motion.
 */

(function () {
  'use strict';

  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const movieId = pathParts[pathParts.indexOf('movies') + 1];
  const header = document.getElementById('movieHeader');
  const backdropContainer = document.getElementById('movieBackdrop');
  const backdropImg = document.getElementById('backdropImg');

  // Modals
  const trailerModal = document.getElementById('trailerModal');
  const trailerFrame = document.getElementById('trailerFrame');
  const closeTrailerBtn = document.getElementById('closeTrailerBtn');
  const trailerYoutubeLink = document.getElementById('trailerYoutubeLink');

  const personModal = document.getElementById('personModal');
  const personModalContent = document.getElementById('personModalContent');
  const closePersonBtn = document.getElementById('closePersonBtn');

  let activeModal = null;
  let previouslyFocusedElement = null;

  if (!movieId) {
    renderError('Film not found');
    return;
  }

  function renderError(title) {
    header.innerHTML = `
      <div class="empty-state">
        <svg width="52" height="52" viewBox="0 0 48 48" fill="none" aria-hidden="true">
          <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/>
          <path d="M24 16v10M24 32v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <h3>${title}</h3>
        <p>This film may have finished its run, or the link is broken.</p>
        <a href="/" class="btn btn--soft">Back to Movies</a>
      </div>
    `;
  }

  function titleHue(title) {
    let hash = 0;
    for (const ch of title) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
    return hash;
  }

  async function loadMovie() {
    let resp;
    try {
      resp = await api.get(`/movies/${movieId}/`);
    } catch {
      renderError('We couldn’t load this film');
      return;
    }

    const { data, ok } = resp;
    if (!ok || !data) {
      renderError('Film not found');
      return;
    }

    document.title = `${data.title} — CineBook`;

    const title = escHtml(data.title);
    const genres = (data.genres || []).map(g => `<span class="genre-tag">${escHtml(g.name)}</span>`).join('');
    const hue = titleHue(data.title);

    // 16:9 Backdrop Banner (custom /static/img/backdrops/ -> YouTube trailer thumbnail -> fallback)
    const isCustomUpload = Boolean(data.backdrop_url && data.backdrop_url.startsWith('/static/img/backdrops/'));
    let backdropSrc = null;
    if (isCustomUpload) {
      backdropSrc = data.backdrop_url;
    } else {
      const trUrl = data.trailer_youtube_url || data.trailer_url;
      let ytId = data.trailer_youtube_key;
      if (!ytId && trUrl) {
        const match = trUrl.match(/(?:v=|\/embed\/|youtu\.be\/|\/v\/)([a-zA-Z0-9_-]{11})/);
        ytId = match ? match[1] : null;
      }
      if (ytId) {
        backdropSrc = `https://img.youtube.com/vi/${ytId}/maxresdefault.jpg`;
      } else {
        backdropSrc = data.backdrop_url;
      }
    }

    if (backdropSrc && backdropContainer && backdropImg) {
      backdropImg.style.backgroundImage = `url("${backdropSrc}")`;
      if (!isCustomUpload) {
        backdropImg.classList.add('movie-backdrop__img--yt');
      } else {
        backdropImg.classList.remove('movie-backdrop__img--yt');
      }
      backdropContainer.classList.remove('hidden');
    } else if (backdropContainer) {
      backdropContainer.classList.add('hidden');
    }

    // Poster (remote URL -> local file -> monogram)
    const posterSrc = data.poster_url || data.poster;
    const placeholderHTML =
      `<div class="movie-card__placeholder" style="--ph-hue:${hue};height:100%;" role="img" aria-label="${title} film poster placeholder">
           <span class="movie-card__monogram" aria-hidden="true">${escHtml(data.title[0])}</span>
           <span class="movie-card__placeholder-label" aria-hidden="true">${escHtml(data.language)}</span>
         </div>`;
    const posterHTML = posterSrc
      ? `<img src="${escHtml(posterSrc)}" alt="${title} film poster"
             onerror="this.onerror=null;this.outerHTML=this.dataset.fallback;"
             data-fallback="${escHtml(placeholderHTML)}">`
      : placeholderHTML;

    // Trailer Button
    const ytKey = data.trailer_youtube_key;
    const trailerBtnHTML = (ytKey || data.trailer_youtube_url || data.trailer_url) ? `
      <button class="btn btn--play btn--lg" id="watchTrailerBtn" aria-label="Watch trailer for ${title}">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M8 5v14l11-7z"/>
        </svg>
        Watch Trailer
      </button>
    ` : '';

    header.innerHTML = `
      <div class="movie-detail">
        <div class="movie-detail__poster-wrap">${posterHTML}</div>
        <div>
          <div class="movie-detail__certline">
            <span class="cert-badge">${escHtml(data.rating)}</span>
            <span>${escHtml(data.language)}</span>
            <span aria-hidden="true">·</span>
            <span>${escHtml(data.duration_display || data.duration_minutes + ' min')}</span>
            <span aria-hidden="true">·</span>
            <span>${formatDate(data.release_date)}</span>
          </div>
          <h1 class="movie-detail__title">${title}</h1>
          <div class="movie-detail__genres">${genres}</div>
          ${data.description ? `<p class="movie-detail__desc">${escHtml(data.description)}</p>` : ''}
          <div class="movie-detail__actions">
            <a href="/movies/${data.id}/shows/" class="btn btn--cta btn--lg">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M3 9a2 2 0 012-2h14a2 2 0 012 2v1a2 2 0 000 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1a2 2 0 000-4V9z"/>
                <path d="M12 7v10" stroke-dasharray="2 3"/>
              </svg>
              Book Tickets
            </a>
            ${trailerBtnHTML}
          </div>
        </div>
      </div>
    `;

    // Trailer Modal Event Listener
    const watchBtn = document.getElementById('watchTrailerBtn');
    if (watchBtn) {
      watchBtn.addEventListener('click', () => {
        let key = ytKey;
        const url = data.trailer_youtube_url || data.trailer_url;
        if (!key && url) {
          const match = url.match(/(?:v=|\/embed\/|youtu\.be\/|\/v\/)([a-zA-Z0-9_-]{11})/);
          key = match ? match[1] : null;
        } else if (url && !key) {
          const match = url.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
          key = match ? match[1] : key;
        }
        if (!key && url) {
          const urlObj = new URL(url, window.location.origin);
          key = urlObj.searchParams.get('v');
        }

        if (key && trailerFrame && trailerModal) {
          trailerFrame.src = `https://www.youtube.com/embed/${key}?autoplay=1&enablejsapi=1`;
          const ytLink = document.getElementById('trailerYoutubeLink');
          if (ytLink) {
            ytLink.href = `https://www.youtube.com/watch?v=${key}`;
          }
          openModal(trailerModal, closeTrailerBtn);
        }
      });
    }

    // Cast Members (TMDb structured cast -> legacy JSON fallback)
    const castMembers = (data.cast && data.cast.length > 0)
      ? data.cast.map(c => ({
          name: c.name,
          role: c.character_name,
          image: c.photo_url,
          tmdb_person_id: c.tmdb_person_id,
        }))
      : (data.cast_info || []).map(c => ({
          name: c.name,
          role: c.role,
          image: c.image,
          tmdb_person_id: null,
        }));

    if (castMembers.length > 0) {
      const grid = document.getElementById('castGrid');
      grid.innerHTML = '';

      castMembers.forEach(member => {
        const el = document.createElement('div');
        el.className = 'cast-member';
        el.setAttribute('tabindex', '0');
        el.setAttribute('role', 'button');
        el.setAttribute('aria-label', `${member.name} as ${member.role || 'Cast'}`);

        const photoHtml = member.image
          ? `<img src="${escHtml(member.image)}" alt="Photo of ${escHtml(member.name)}">`
          : `<svg width="32" height="32" viewBox="0 0 28 28" fill="none" style="color:var(--text-tertiary);" aria-hidden="true"><circle cx="14" cy="10" r="5" stroke="currentColor" stroke-width="1.5"/><path d="M4 26c0-5.5 4.5-9 10-9s10 3.5 10 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`;

        el.innerHTML = `
          <div class="cast-member__photo">${photoHtml}</div>
          <div class="cast-member__name">${escHtml(member.name || '')}</div>
          <div class="cast-member__role">${escHtml(member.role || '')}</div>
        `;

        el.addEventListener('click', () => openPersonModal(member, data.title));
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openPersonModal(member, data.title);
          }
        });

        grid.appendChild(el);
      });
      document.getElementById('castSection').classList.remove('hidden');
    }
  }

  // Actor Biography Popover Modal
  async function openPersonModal(member, movieTitle) {
    if (!personModal || !personModalContent) return;

    const name = escHtml(member.name || 'Actor');
    const role = escHtml(member.role || 'Cast Member');
    const photoHtml = member.image
      ? `<img src="${escHtml(member.image)}" alt="${name}">`
      : `<svg width="40" height="40" viewBox="0 0 28 28" fill="none" style="color:var(--text-tertiary);"><circle cx="14" cy="10" r="5" stroke="currentColor" stroke-width="1.5"/><path d="M4 26c0-5.5 4.5-9 10-9s10 3.5 10 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`;

    personModalContent.innerHTML = `
      <div class="person-modal__photo">${photoHtml}</div>
      <div class="person-modal__info">
        <h3 class="person-modal__name">${name}</h3>
        <div class="person-modal__char">as ${role}</div>
        <div class="person-modal__meta">Appears in ${escHtml(movieTitle)}</div>
        <div class="person-modal__bio" id="personBioText" tabindex="0" aria-label="Biography content">
          ${name} stars as ${role} in ${escHtml(movieTitle)}.
        </div>
      </div>
    `;

    openModal(personModal, closePersonBtn);
  }

  // Accessibility Modal Management: Focus Trapping & Focus Restoration
  function openModal(modalEl, initialFocusTarget) {
    previouslyFocusedElement = document.activeElement;
    activeModal = modalEl;
    modalEl.classList.remove('hidden');

    if (initialFocusTarget) {
      setTimeout(() => initialFocusTarget.focus(), 50);
    }
  }

  function closeModals() {
    if (trailerModal) {
      trailerModal.classList.add('hidden');
      if (trailerFrame) trailerFrame.src = '';
    }
    if (personModal) {
      personModal.classList.add('hidden');
    }
    activeModal = null;
    if (previouslyFocusedElement) {
      previouslyFocusedElement.focus();
      previouslyFocusedElement = null;
    }
  }

  // Focus trap inside open modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModals();
      return;
    }

    if (e.key === 'Tab' && activeModal) {
      const focusables = activeModal.querySelectorAll('button, [href], input, select, textarea, [tabindex="0"]');
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          last.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === last) {
          first.focus();
          e.preventDefault();
        }
      }
    }
  });

  closeTrailerBtn?.addEventListener('click', closeModals);
  closePersonBtn?.addEventListener('click', closeModals);

  [trailerModal, personModal].forEach(modal => {
    modal?.addEventListener('click', (e) => {
      if (e.target === modal) closeModals();
    });
  });

  function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  loadMovie();
})();
