/* =========================================
   JobDevs // SYSTEM.ROOT — Landing Interactions
   ========================================= */
document.addEventListener('DOMContentLoaded', function () {

  /* ============================
     MARQUEE — clone for seamless loop
     ============================ */
  const marqueeTrack = document.getElementById('marqueeTrack');
  if (marqueeTrack) {
    // El keyframe mueve la pista un -50%: para que el loop cierre sin hueco, esa
    // mitad tiene que ser al menos tan ancha como la pantalla. Con una sola copia
    // de 1578px, en pantallas de 1920px la banda se cortaba.
    const baseHTML = marqueeTrack.innerHTML;

    function armarMarquee() {
      marqueeTrack.innerHTML = baseHTML;
      let copias = 0;
      while (marqueeTrack.scrollWidth < window.innerWidth && copias < 12) {
        marqueeTrack.insertAdjacentHTML('beforeend', baseHTML);
        copias += 1;
      }
      const anchoMitad = marqueeTrack.scrollWidth;
      marqueeTrack.innerHTML += marqueeTrack.innerHTML;  // segunda mitad identica
      // velocidad constante (~70 px/s) en vez de duracion fija
      marqueeTrack.style.animationDuration = Math.max(20, Math.round(anchoMitad / 70)) + 's';
    }

    armarMarquee();
    let reArmar;
    window.addEventListener('resize', function() {
      clearTimeout(reArmar);
      reArmar = setTimeout(armarMarquee, 200);
    }, { passive: true });
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
        tickZoomId = null;
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

  document.querySelectorAll('.reveal').forEach(el => {
    revealObserver.observe(el);
  });

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
          if (heroVisible) {
            if (tickZoomId) cancelAnimationFrame(tickZoomId);
            if (typeof tickZoom === 'function') tickZoomId = requestAnimationFrame(tickZoom);
          } else if (tickZoomId) {
            cancelAnimationFrame(tickZoomId);
            tickZoomId = null;
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
    let grainAnimId = null;

    function animateGrain() {
      const diff = targetY - currentY;
      if (Math.abs(diff) < 0.05) {
        currentY = targetY;
        grain.style.transform = 'translateY(' + currentY + 'px)';
        grainAnimId = null;
        return;
      }
      currentY += diff * 0.06;
      grain.style.transform = 'translateY(' + currentY + 'px)';
      grainAnimId = requestAnimationFrame(animateGrain);
    }

    window.addEventListener('scroll', () => {
      targetY = window.scrollY * 0.12;
      if (!grainAnimId) {
        grainAnimId = requestAnimationFrame(animateGrain);
      }
    }, { passive: true });
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
      let resizeTimer = null;
      window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
          this.calculateDimensions();
          this.clamp();
          this.applyTransform(0);
        }, 150);
      }, { passive: true });
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
      var mostrando = this.getAttribute('aria-pressed') === 'true';
      input.type = mostrando ? 'password' : 'text';
      // El estado lo pinta el CSS con aria-pressed; los dos ojos ya estan en el DOM.
      this.setAttribute('aria-pressed', mostrando ? 'false' : 'true');
    });
  }

  /* ============================
     MODAL DE LOGIN — controlador propio
     ============================ */
  // Bootstrap se cargaba entero (80 KB desde un segundo CDN) solo para abrir este
  // modal. Este controlador cubre lo que aportaba: ESC, clic en el fondo, bloqueo
  // del scroll del body, aria correcto, foco inicial, retorno del foco y trampa
  // de tabulacion. Un unico estado, sin instancias paralelas sobre el elemento.
  var loginModalEl = document.getElementById('loginModal');
  var focoPrevio = null;

  var SELECTOR_FOCALIZABLES = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  function focalizablesDelModal() {
    if (!loginModalEl) return [];
    return Array.prototype.filter.call(
      loginModalEl.querySelectorAll(SELECTOR_FOCALIZABLES),
      function (el) { return el.offsetWidth > 0 || el.offsetHeight > 0; }
    );
  }

  function modalAbierto() {
    return !!(loginModalEl && loginModalEl.classList.contains('show'));
  }

  function abrirLoginModal() {
    if (!loginModalEl || modalAbierto()) return;
    focoPrevio = document.activeElement;
    loginModalEl.classList.add('show');
    loginModalEl.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    var primero = loginModalEl.querySelector('#username') || focalizablesDelModal()[0];
    if (primero) primero.focus();
  }

  function cerrarLoginModal() {
    if (!modalAbierto()) return;
    loginModalEl.classList.remove('show');
    document.body.classList.remove('modal-open');
    // El foco vuelve al control que abrio el modal y recien despues se oculta
    // para lectores de pantalla: al reves, quedaria dentro de un nodo aria-hidden.
    if (focoPrevio && typeof focoPrevio.focus === 'function') focoPrevio.focus();
    focoPrevio = null;
    loginModalEl.setAttribute('aria-hidden', 'true');
    showLogin();
  }

  document.querySelectorAll('[data-abrir-login]').forEach(function (abridor) {
    abridor.addEventListener('click', function (e) {
      e.preventDefault();
      abrirLoginModal();
    });
  });

  if (loginModalEl) {
    // Clic en el fondo: el velo lo pinta el propio .modal, asi que el blanco es
    // el elemento y no un backdrop aparte.
    loginModalEl.addEventListener('click', function (e) {
      if (e.target === loginModalEl) cerrarLoginModal();
    });
    var botonCerrar = loginModalEl.querySelector('[data-cerrar-login]');
    if (botonCerrar) {
      botonCerrar.addEventListener('click', function () { cerrarLoginModal(); });
    }
  }

  document.addEventListener('keydown', function (e) {
    if (!modalAbierto()) return;
    if (e.key === 'Escape') { e.preventDefault(); cerrarLoginModal(); return; }
    if (e.key !== 'Tab') return;
    var focos = focalizablesDelModal();
    if (!focos.length) return;
    var primero = focos[0];
    var ultimo = focos[focos.length - 1];
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault(); ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault(); primero.focus();
    }
  });

  /* ============================
     DJANGO MESSAGES MODAL
     ============================ */
  var djangoMsgs = document.getElementById('django-messages');
  if (djangoMsgs) {
    var spans = djangoMsgs.querySelectorAll('span');
    var form = document.querySelector('#loginModal form');
    if (spans.length && form) {
      var msgContainer = document.createElement('div');
      msgContainer.style.marginBottom = '14px';
      spans.forEach(function(s) {
        var msgDiv = document.createElement('div');
        msgDiv.style.cssText = 'background:rgba(220,38,38,0.06);border:1px solid rgba(220,38,38,0.15);padding:10px 14px;margin-bottom:8px;font-size:13px;color:#fca5a5;display:flex;align-items:center;gap:8px;';
        var icon = document.createElement('span');
        icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-alert icono-linea" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>';
        icon.style.display = 'flex';
        msgDiv.appendChild(icon);
        var textNode = document.createTextNode(' ' + s.textContent.trim());
        msgDiv.appendChild(textNode);
        msgContainer.appendChild(msgDiv);
      });
      form.insertBefore(msgContainer, form.firstChild);
      abrirLoginModal();
    }
  }

  /* ============================
     URL PARAM MODAL
     ============================ */
  if (new URLSearchParams(window.location.search).get('login') === '1') {
    abrirLoginModal();
  }

  /* ============================
     RECOVERY FORM TOGGLE (inside modal)
     ============================ */
  var recoveryLink = document.getElementById('recoveryLink');
  // Textos traducidos por el template: el JS no guarda copias en español.
  var TEXTOS_I18N = (function () {
    var nodo = document.getElementById('textos-i18n');
    if (!nodo) return {};
    try { return JSON.parse(nodo.textContent) || {}; } catch (e) { return {}; }
  })();

  function texto(clave, porDefecto) {
    var valor = TEXTOS_I18N[clave];
    return (typeof valor === 'string' && valor) ? valor : porDefecto;
  }

  var loginFormDiv = document.getElementById('loginForm');
  var recoveryFormDiv = document.getElementById('recoveryForm');
  var recoveryInner;
  var modalTitle = document.querySelector('#loginModal .modal-title');
  var recoveryOriginalHTML = recoveryFormDiv ? recoveryFormDiv.innerHTML : '';

  function showLogin() {
    if (loginFormDiv) loginFormDiv.style.display = 'block';
    if (recoveryFormDiv) recoveryFormDiv.style.display = 'none';
    if (modalTitle) modalTitle.textContent = texto('authTitle', 'AUTENTICACIÓN SEGURA');
  }

  function showRecovery() {
    if (loginFormDiv) loginFormDiv.style.display = 'none';
    if (recoveryFormDiv) { recoveryFormDiv.style.display = 'block'; recoveryFormDiv.innerHTML = recoveryOriginalHTML; reattachRecovery(); }
    if (modalTitle) modalTitle.textContent = texto('recoveryTitle', 'RECUPERAR CONTRASEÑA');
  }

  function reattachRecovery() {
    recoveryInner = document.getElementById('recoveryFormInner');
    if (recoveryInner) {
      recoveryInner.addEventListener('submit', function(e) {
        e.preventDefault();
        var btn = this.querySelector('button');
        var orig = btn.textContent;
        btn.textContent = texto('sending', '[ ENVIANDO... ]');
        btn.disabled = true;
        fetch(this.action, { method: 'POST', body: new FormData(this) })
          .then(function() {
            recoveryFormDiv.innerHTML = '<div style="background: rgba(var(--accent-rgb), 0.08); border-left: 3px solid var(--accent); color: var(--accent-bright); padding: 12px 16px; font-family: var(--font-mono); font-size: 0.75rem; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-check icono-linea" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg> ' + texto('recoveryOk', 'Si el correo existe, recibirás instrucciones para restablecer tu contraseña.') + '</div><div style="text-align: center; margin-top: 20px;"><a href="#" id="backToLoginLink2" class="login-link" style="color: var(--accent);">' + texto('backToLogin', '&larr; VOLVER AL INICIO DE SESIÓN') + '</a></div>';
            document.getElementById('backToLoginLink2').addEventListener('click', function(e) { e.preventDefault(); showLogin(); });
          })
          .catch(function() {
            btn.textContent = orig;
            btn.disabled = false;
            alert(texto('connectionError', 'Error de conexión. Intenta de nuevo.'));
          });
      });
    }
    var bl = document.getElementById('backToLoginLink');
    if (bl) bl.addEventListener('click', function(e) { e.preventDefault(); showLogin(); });
  }

  if (recoveryLink) {
    recoveryLink.addEventListener('click', function(e) { e.preventDefault(); showRecovery(); });
  }

  /* ============================
     ROLES INTERACTIVE SWITCHER
     ============================ */
  const roleNavBtns = document.querySelectorAll('.role-nav-btn');
  const rolePanes = document.querySelectorAll('.role-stage-pane');
  const roleBgFrames = document.querySelectorAll('.role-bg-frame');
  if (roleNavBtns.length && rolePanes.length) {
    roleNavBtns.forEach(btn => {
      btn.addEventListener('click', function() {
        const targetRole = this.dataset.role;
        roleNavBtns.forEach(b => {
          const isActive = (b === this);
          b.classList.toggle('active', isActive);
          b.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });
        rolePanes.forEach(pane => {
          const isTarget = (pane.id === (targetRole === 'empresa' ? 'paneEmpresa' : 'paneDev'));
          pane.classList.toggle('active', isTarget);
        });
        roleBgFrames.forEach(frame => {
          const isTarget = (frame.id === (targetRole === 'empresa' ? 'bgRoleEmpresa' : 'bgRoleDev'));
          frame.classList.toggle('active', isTarget);
        });
      });
    });
  }

  /* ============================
     WORKFLOW HERO-STYLE STEPPER
     ============================ */
  const stepItems = document.querySelectorAll('.wf-step-item');
  const wfBgFrames = document.querySelectorAll('.wf-bg-frame');

  if (stepItems.length && wfBgFrames.length) {
    let currentStep = 1;
    let tourTimer = null;
    let userInteracted = false;

    function selectStep(stepNum) {
      stepItems.forEach(item => {
        const isActive = (item.dataset.step === String(stepNum));
        item.classList.toggle('active', isActive);
        item.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      wfBgFrames.forEach((frame, i) => {
        frame.classList.toggle('active', i === (stepNum - 1));
      });
      currentStep = stepNum;
    }

    stepItems.forEach(item => {
      item.addEventListener('click', function() {
        userInteracted = true;
        if (tourTimer) clearInterval(tourTimer);
        const stepNum = parseInt(this.dataset.step, 10);
        selectStep(stepNum);
      });
      item.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          userInteracted = true;
          if (tourTimer) clearInterval(tourTimer);
          selectStep(parseInt(this.dataset.step, 10));
        }
      });
    });

    // Auto-advance softly every 6s unless user interacted
    tourTimer = setInterval(function() {
      if (!userInteracted) {
        currentStep = (currentStep % stepItems.length) + 1;
        selectStep(currentStep);
      }
    }, 6000);
  }

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
      var hoverTargets = document.querySelectorAll('a, button, .btn-tech, .nav-cta, .story-card, input, textarea, select, [role="button"]');
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
     TEMA CLARO / OSCURO
     El tema inicial ya lo fijó el script de <head> antes del primer paint.
     Acá solo se sincroniza la UI, se alterna y se recuerda la elección.
     ============================ */
  var CLAVE_TEMA = 'jobdevs-theme';
  var botonTema = document.getElementById('themeToggle');

  function temaActual() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  // El switch muestra las dos posiciones: el estado lo comunica aria-pressed y
  // el CSS enciende el icono que corresponde, así que acá sólo se expone el estado.
  function pintarBotonTema(tema) {
    if (!botonTema) return;
    botonTema.setAttribute('aria-pressed', tema === 'light' ? 'true' : 'false');
  }

  function aplicarTema(tema, recordar) {
    document.documentElement.setAttribute('data-theme', tema);
    pintarBotonTema(tema);
    if (recordar) {
      try { localStorage.setItem(CLAVE_TEMA, tema); } catch (e) { /* modo privado */ }
    }
  }

  pintarBotonTema(temaActual());

  if (botonTema) {
    botonTema.addEventListener('click', function () {
      aplicarTema(temaActual() === 'light' ? 'dark' : 'light', true);
    });
  }

  // Sin elección guardada, el tema sigue al sistema mientras la página está abierta.
  if (window.matchMedia) {
    var consultaSistema = window.matchMedia('(prefers-color-scheme: light)');
    var seguimientoSistema = function (evento) {
      var guardado = null;
      try { guardado = localStorage.getItem(CLAVE_TEMA); } catch (e) { /* modo privado */ }
      if (guardado === 'light' || guardado === 'dark') return;
      aplicarTema(evento.matches ? 'light' : 'dark', false);
    };
    if (consultaSistema.addEventListener) {
      consultaSistema.addEventListener('change', seguimientoSistema);
    } else if (consultaSistema.addListener) {
      consultaSistema.addListener(seguimientoSistema);
    }
  }

});
