/* =========================================
   JobDevs // SYSTEM.ROOT — Landing Interactions
   ========================================= */
document.addEventListener('DOMContentLoaded', function () {

  /* ============================
     MARQUEE — clone for seamless loop
     ============================ */
  const marqueeTrack = document.getElementById('marqueeTrack');
  if (marqueeTrack) {
    marqueeTrack.insertAdjacentHTML('beforeend', marqueeTrack.innerHTML);
  }

  /* ============================
     HERO REEL — frame cycler
     ============================ */
  var heroVisible = true;
  var tickZoomId = null;
  var tickZoom = null;
  const frames = document.querySelectorAll('.reel-frame');
  if (frames.length) {
    let currentFrame = 0;
    const frameDuration = 8000;
    let frameStartTime = performance.now();

    function showFrame(idx) {
      frames.forEach((f, i) => {
        f.classList.toggle('active', i === idx);
        f.style.opacity = i === idx ? '1' : '0';
        f.style.zIndex = i === idx ? 2 : 1;
      });
      const newImg = frames[idx].querySelector('img');
      if (newImg) newImg.style.transform = 'scale(1.0)';
      frameStartTime = performance.now();
    }

    setInterval(function() {
      currentFrame = (currentFrame + 1) % frames.length;
      showFrame(currentFrame);
    }, frameDuration);

    tickZoom = function() {
      if (!heroVisible) {
        tickZoomId = requestAnimationFrame(tickZoom);
        return;
      }
      const elapsed = performance.now() - frameStartTime;
      const progress = Math.min(elapsed / frameDuration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const scale = 1.0 + eased * 0.15;
      const activeImg = document.querySelector('.reel-frame.active img');
      if (activeImg) activeImg.style.transform = 'scale(' + scale + ')';
      tickZoomId = requestAnimationFrame(tickZoom);
    }
    tickZoomId = requestAnimationFrame(tickZoom);
  }

  /* ============================
     REVEAL ON SCROLL
     ============================ */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => {
    revealObserver.observe(el);
  });

  /* ============================
     NUMBER COUNTERS
     ============================ */
  const counters = document.querySelectorAll('.number-display');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const raw = el.dataset.count;
        const suffix = el.dataset.suffix || '';
        const numeric = parseFloat(raw);
        if (isNaN(numeric)) { counterObserver.unobserve(el); return; }

        const duration = 1800;
        const start = performance.now();

        function step(now) {
          const elapsed = now - start;
          const progress = Math.min(elapsed / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          const value = Math.floor(eased * numeric);
          if (progress < 1) {
            el.textContent = value + suffix;
            requestAnimationFrame(step);
          } else {
            el.textContent = raw + suffix;
          }
        }
        requestAnimationFrame(step);
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.4 });

  counters.forEach(c => counterObserver.observe(c));

  /* ============================
     STICKY CTA BAR
     ============================ */
  const stickyCta = document.getElementById('stickyCta');
  const heroSection = document.getElementById('inicio');
  const bookingAnchor = document.getElementById('comenzar');

  if (stickyCta && heroSection) {
    let heroPassed = false;
    let atBooking = false;

    const stickyObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.target === heroSection) {
          heroPassed = !entry.isIntersecting;
          heroVisible = entry.isIntersecting;
          if (heroVisible && tickZoomId) {
            cancelAnimationFrame(tickZoomId);
            tickZoomId = requestAnimationFrame(tickZoom);
          }
        }
        if (entry.target === bookingAnchor) atBooking = entry.isIntersecting;
        updateSticky();
      });
    }, { threshold: 0 });

    stickyObserver.observe(heroSection);
    if (bookingAnchor) stickyObserver.observe(bookingAnchor);

    function updateSticky() {
      stickyCta.classList.toggle('visible', heroPassed && !atBooking);
    }
  }

  /* ============================
     GRAIN PARALLAX
     ============================ */
  const grain = document.getElementById('grain');
  if (grain) {
    let targetY = 0, currentY = 0;
    window.addEventListener('scroll', () => {
      targetY = window.scrollY * 0.12;
    }, { passive: true });

    function animateGrain() {
      currentY += (targetY - currentY) * 0.06;
      grain.style.transform = 'translateY(' + currentY + 'px)';
      requestAnimationFrame(animateGrain);
    }
    animateGrain();
  }

  /* ============================
     HERO REEL PARALLAX & NAVBAR SCROLL
     ============================ */
  const reelContainer = document.getElementById('reelContainer');
  const navbarEl = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    if (navbarEl) {
      if (scrolled > 20) {
        navbarEl.classList.add('scrolled');
      } else {
        navbarEl.classList.remove('scrolled');
      }
    }
    if (reelContainer && scrolled < window.innerHeight) {
      reelContainer.style.transform = 'translateY(' + (scrolled * 0.25) + 'px)';
    }
  }, { passive: true });

  /* ============================
     STORIES CAROUSEL — drag/snap
     ============================ */
  class StoriesCarousel {
    constructor(track, opts = {}) {
      this.track = track;
      if (!track) return;
      this.cards = Array.from(track.children);
      if (this.cards.length === 0) return;
      this.currentIndex = 0;
      this.isDown = false;
      this.startX = 0; this.startOffset = 0; this.currentX = 0;
      this.velocity = 0; this.lastX = 0; this.lastTime = 0;
      this.cardWidth = 0; this.maxScroll = 0;
      this.autoAdvance = opts.autoAdvance !== false;
      this.autoInterval = opts.interval || 4500;
      this.autoTimer = null;
      this.pauseAuto = false;
      this.init();
    }

    init() {
      this.calculateDimensions();
      this.bindEvents();
      this.buildDots();
      this.startAuto();
      window.addEventListener('resize', () => {
        this.calculateDimensions();
        this.clamp();
        this.applyTransform(0);
      });
    }

    calculateDimensions() {
      if (this.cards.length === 0) return;
      const trackStyle = window.getComputedStyle(this.track);
      const gap = parseFloat(trackStyle.gap) || 24;
      const paddingLeft = parseFloat(trackStyle.paddingLeft) || 0;
      this.cardWidth = this.cards[0].offsetWidth + gap;
      const containerWidth = this.track.parentElement.offsetWidth;
      const totalWidth = (this.cards.length * this.cardWidth) - gap + paddingLeft * 2;
      this.maxScroll = Math.max(0, totalWidth - containerWidth);
    }

    bindEvents() {
      const down = (e) => this.handleDown(e);
      const move = (e) => this.handleMove(e);
      const up = () => this.handleUp();

      this.track.addEventListener('mousedown', down);
      this.track.addEventListener('touchstart', down, { passive: true });
      window.addEventListener('mousemove', move);
      window.addEventListener('touchmove', move, { passive: false });
      window.addEventListener('mouseup', up);
      window.addEventListener('touchend', up);
      window.addEventListener('touchcancel', up);

      this.track.addEventListener('mouseenter', () => this.pauseAuto = true);
      this.track.addEventListener('mouseleave', () => this.pauseAuto = false);

      const prev = document.getElementById('storyPrev');
      const next = document.getElementById('storyNext');
      if (prev) prev.addEventListener('click', () => this.goTo(this.currentIndex - 1));
      if (next) next.addEventListener('click', () => this.goTo(this.currentIndex + 1));
    }

    handleDown(e) {
      this.isDown = true;
      this.track.classList.add('dragging');
      const x = e.type.includes('touch') ? e.touches[0].pageX : e.pageX;
      this.startX = x; this.startOffset = this.currentX;
      this.lastX = x; this.lastTime = Date.now();
      this.velocity = 0; this.stopAuto();
    }

    handleMove(e) {
      if (!this.isDown) return;
      if (e.cancelable) e.preventDefault();
      const x = e.type.includes('touch') ? e.touches[0].pageX : e.pageX;
      const delta = x - this.startX;
      let newX = this.startOffset + delta;
      if (newX > 0) newX = newX * 0.3;
      else if (newX < -this.maxScroll) { const over = newX + this.maxScroll; newX = -this.maxScroll + over * 0.3; }
      const now = Date.now();
      const dt = now - this.lastTime;
      if (dt > 0) this.velocity = (x - this.lastX) / dt;
      this.lastX = x; this.lastTime = now;
      this.currentX = newX;
      this.applyTransform(0);
    }

    handleUp() {
      if (!this.isDown) return;
      this.isDown = false;
      this.track.classList.remove('dragging');
      let target = this.currentX + this.velocity * 350;
      const snapIndex = Math.round(-target / this.cardWidth);
      const clampedIndex = Math.max(0, Math.min(this.cards.length - 1, snapIndex));
      let snappedX = -clampedIndex * this.cardWidth;
      if (snappedX > 0) snappedX = 0;
      if (snappedX < -this.maxScroll) snappedX = -this.maxScroll;
      this.currentX = snappedX; this.currentIndex = clampedIndex;
      this.applyTransform(600); this.updateDots();
      setTimeout(() => this.startAuto(), 1800);
    }

    goTo(idx) {
      this.currentIndex = Math.max(0, Math.min(this.cards.length - 1, idx));
      let target = -this.currentIndex * this.cardWidth;
      if (target > 0) target = 0;
      if (target < -this.maxScroll) target = -this.maxScroll;
      this.currentX = target; this.applyTransform(600); this.updateDots();
      this.stopAuto(); setTimeout(() => this.startAuto(), 2500);
    }

    clamp() {
      if (this.currentX > 0) this.currentX = 0;
      if (this.currentX < -this.maxScroll) this.currentX = -this.maxScroll;
    }

    applyTransform(duration) {
      this.track.style.transition = duration > 0 ? 'transform ' + duration + 'ms cubic-bezier(0.16, 1, 0.3, 1)' : 'none';
      this.track.style.transform = 'translateX(' + this.currentX + 'px)';
    }

    buildDots() {
      const container = document.getElementById('storyDots');
      if (!container) return;
      container.innerHTML = '';
      this.cards.forEach((_, i) => {
        const dot = document.createElement('button');
        dot.className = 'carousel-dot';
        if (i === 0) dot.classList.add('active');
        dot.addEventListener('click', () => this.goTo(i));
        container.appendChild(dot);
      });
    }

    updateDots() {
      const dots = document.querySelectorAll('#storyDots .carousel-dot');
      dots.forEach((dot, i) => dot.classList.toggle('active', i === this.currentIndex));
    }

    startAuto() { if (!this.autoAdvance) return; this.stopAuto(); this.autoTimer = setInterval(() => { if (this.pauseAuto || this.isDown) return; this.goTo((this.currentIndex + 1) % this.cards.length); }, this.autoInterval); }
    stopAuto() { if (this.autoTimer) { clearInterval(this.autoTimer); this.autoTimer = null; } }
  }

  new StoriesCarousel(document.getElementById('storyTrack'), { interval: 4500 });

  /* ============================
     HEADLINE CHAR REVEAL (triggers after 400ms)
     ============================ */
  setTimeout(function() {
    var heroContent = document.querySelector('.hero-content');
    if (heroContent) heroContent.classList.add('in-view');
  }, 400);

  /* ============================
     MOBILE MENU
     ============================ */
  var mobileMenuBtn = document.getElementById('mobileMenuBtn');
  var navLinksEl = document.getElementById('navLinks');
  if (mobileMenuBtn && navLinksEl) {
    mobileMenuBtn.addEventListener('click', function() { navLinksEl.classList.toggle('active'); });
    navLinksEl.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() { navLinksEl.classList.remove('active'); });
    });
  }

  /* ============================
     TOGGLE PASSWORD
     ============================ */
  var togglePassBtn = document.getElementById('togglePassTech');
  if (togglePassBtn) {
    togglePassBtn.addEventListener('click', function() {
      var input = document.getElementById('password');
      var ico = this.querySelector('i');
      if (input.type === 'password') { input.type = 'text'; ico.classList.replace('fa-eye', 'fa-eye-slash'); }
      else { input.type = 'password'; ico.classList.replace('fa-eye-slash', 'fa-eye'); }
    });
  }

  /* ============================
     DJANGO MESSAGES MODAL
     ============================ */
  var djangoMsgs = document.getElementById('django-messages');
  if (djangoMsgs) {
    var spans = djangoMsgs.querySelectorAll('span');
    var err = '';
    spans.forEach(function(s) { err += '<div style="background:rgba(220,38,38,0.06);border:1px solid rgba(220,38,38,0.15);padding:10px 14px;margin-bottom:14px;font-size:13px;color:#fca5a5;display:flex;align-items:center;gap:8px;"><i class="fa fa-circle-exclamation" style="color:#ef4444;"></i>' + s.textContent.trim() + '</div>'; });
    if (err) {
      var form = document.querySelector('#loginModal form');
      if (form) { var c = document.createElement('div'); c.innerHTML = err; form.insertBefore(c, form.firstChild); }
      new bootstrap.Modal(document.getElementById('loginModal')).show();
    }
  }

  /* ============================
     URL PARAM MODAL
     ============================ */
  if (new URLSearchParams(window.location.search).get('login') === '1') {
    new bootstrap.Modal(document.getElementById('loginModal')).show();
  }

  /* ============================
     RECOVERY FORM TOGGLE (inside modal)
     ============================ */
  var recoveryLink = document.getElementById('recoveryLink');
  var loginFormDiv = document.getElementById('loginForm');
  var recoveryFormDiv = document.getElementById('recoveryForm');
  var recoveryInner;
  var modalTitle = document.querySelector('#loginModal .modal-title');
  var recoveryOriginalHTML = recoveryFormDiv ? recoveryFormDiv.innerHTML : '';

  function showLogin() {
    if (loginFormDiv) loginFormDiv.style.display = 'block';
    if (recoveryFormDiv) recoveryFormDiv.style.display = 'none';
    if (modalTitle) modalTitle.textContent = 'AUTENTICACIÓN SEGURA';
  }

  function showRecovery() {
    if (loginFormDiv) loginFormDiv.style.display = 'none';
    if (recoveryFormDiv) { recoveryFormDiv.style.display = 'block'; recoveryFormDiv.innerHTML = recoveryOriginalHTML; reattachRecovery(); }
    if (modalTitle) modalTitle.textContent = 'RECUPERAR CONTRASEÑA';
  }

  function reattachRecovery() {
    recoveryInner = document.getElementById('recoveryFormInner');
    if (recoveryInner) {
      recoveryInner.addEventListener('submit', function(e) {
        e.preventDefault();
        var btn = this.querySelector('button');
        var orig = btn.textContent;
        btn.textContent = '[ ENVIANDO... ]';
        btn.disabled = true;
        fetch(this.action, { method: 'POST', body: new FormData(this) })
          .then(function() {
            recoveryFormDiv.innerHTML = '<div class="alert alert-success" style="background: rgba(var(--accent-rgb), 0.08); border-left: 3px solid var(--accent); color: var(--accent-bright); padding: 12px 16px; font-family: var(--font-mono); font-size: 0.75rem; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;"><i class="fa fa-check-circle"></i> Si el correo existe, recibirás instrucciones para restablecer tu contraseña.</div><div style="text-align: center; margin-top: 20px;"><a href="#" id="backToLoginLink2" class="login-link" style="color: var(--accent);">&larr; VOLVER AL INICIO DE SESIÓN</a></div>';
            document.getElementById('backToLoginLink2').addEventListener('click', function(e) { e.preventDefault(); showLogin(); });
          })
          .catch(function() {
            btn.textContent = orig;
            btn.disabled = false;
            alert('Error de conexión. Intenta de nuevo.');
          });
      });
    }
    var bl = document.getElementById('backToLoginLink');
    if (bl) bl.addEventListener('click', function(e) { e.preventDefault(); showLogin(); });
  }

  if (recoveryLink) {
    recoveryLink.addEventListener('click', function(e) { e.preventDefault(); showRecovery(); });
  }

  var loginModalEl = document.getElementById('loginModal');
  if (loginModalEl) {
    loginModalEl.addEventListener('hidden.bs.modal', function() { showLogin(); });
  }

  /* ============================
     FLIP CARDS TOUCH
     ============================ */
  var isTouchDevice = !window.matchMedia('(hover: hover)').matches;
  document.querySelectorAll('.flip-card').forEach(function(card) {
    card.addEventListener('click', function(e) {
      if (isTouchDevice && !e.target.closest('a')) {
        card.classList.toggle('flipped');
      }
    });
  });

  /* ============================
     CUSTOM CURSOR
     ============================ */
  if (window.matchMedia('(hover: hover)').matches) {
    var dot = document.getElementById('cursorDot');
    var ring = document.getElementById('cursorRing');
    if (dot && ring) {
      var mx = 0, my = 0, rx = 0, ry = 0;
      document.addEventListener('mousemove', function(e) {
        mx = e.clientX; my = e.clientY;
        dot.style.left = mx + 'px';
        dot.style.top = my + 'px';
      });
      var hoverTargets = document.querySelectorAll('a, button, .btn-tech, .btn-tech-sec, .nav-cta, .tab-tech, .flip-card, .story-card, .goal-pill, input, textarea, select, [role="button"]');
      hoverTargets.forEach(function(el) {
        el.addEventListener('mouseenter', function() { dot.classList.add('hover'); ring.classList.add('hover'); });
        el.addEventListener('mouseleave', function() { dot.classList.remove('hover'); ring.classList.remove('hover'); });
      });
      function animateRing() {
        rx += (mx - rx) * 0.12;
        ry += (my - ry) * 0.12;
        ring.style.left = rx + 'px';
        ring.style.top = ry + 'px';
        requestAnimationFrame(animateRing);
      }
      animateRing();
    }
  }

  /* ============================
     PROJECT FORM
     ============================ */
  var projectForm = document.getElementById('projectForm');
  var toast = document.getElementById('toast');
  if (projectForm && toast) {
    projectForm.addEventListener('submit', function(e) {
      e.preventDefault();
      document.getElementById('toastTitle').textContent = 'Solicitud recibida';
      document.getElementById('toastMsg').textContent = 'Recibimos tu solicitud. Te contactaremos pronto.';
      toast.classList.add('visible');
      setTimeout(function() { toast.classList.remove('visible'); }, 4500);
      projectForm.reset();
      document.querySelectorAll('#projectTypeSelector .goal-pill').forEach(function(p, i) { p.classList.toggle('active', i === 0); });
    });
  }

  /* ============================
     Auto-open login modal via ?login=1
     ============================ */
  if (window.location.search.includes('login=1')) {
    var loginModal = document.getElementById('loginModal');
    if (loginModal && typeof bootstrap !== 'undefined') {
      var modal = new bootstrap.Modal(loginModal);
      modal.show();
    }
  }

});
