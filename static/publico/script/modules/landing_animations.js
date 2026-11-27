/* =========================================
   Jobdevs // SYSTEM.ROOT — Landing Animations & Interactive Sections
   ========================================= */

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
    this.cardWidth = 0; this.maxScroll = 0; this.maxIndex = 0;
    this.autoAdvance = opts.autoAdvance !== false;
    this.autoInterval = opts.interval || 4500;
    this.autoTimer = null;
    this.resumeTimer = null;
    this.pauseAuto = false;
    this.init();
  }

  init() {
    this.calculateDimensions();
    this.bindEvents();
    this.startAuto();
    window.addEventListener('load', () => {
      this.calculateDimensions();
      this.clamp();
      this.applyTransform(0);
    }, { once: true });
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
    this.maxIndex = this.cardWidth > 0 ? Math.min(this.cards.length - 1, Math.ceil(this.maxScroll / this.cardWidth)) : 0;
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

    this.track.addEventListener('mouseenter', () => { this.pauseAuto = true; });
    this.track.addEventListener('mouseleave', () => { this.pauseAuto = false; });

    const prev = document.getElementById('storyPrev');
    const next = document.getElementById('storyNext');
    if (prev) prev.addEventListener('click', () => this.goTo(this.currentIndex <= 0 ? this.maxIndex : this.currentIndex - 1));
    if (next) next.addEventListener('click', () => this.goTo(this.currentIndex >= this.maxIndex ? 0 : this.currentIndex + 1));
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
    const target = this.currentX + this.velocity * 350;
    const snapIndex = Math.round(-target / this.cardWidth);
    const clampedIndex = Math.max(0, Math.min(this.maxIndex, snapIndex));
    let snappedX = -clampedIndex * this.cardWidth;
    if (snappedX > 0) snappedX = 0;
    if (snappedX < -this.maxScroll) snappedX = -this.maxScroll;
    this.currentX = snappedX; this.currentIndex = clampedIndex;
    this.applyTransform(600);
    this.scheduleAutoResume(1800);
  }

  goTo(idx) {
    this.currentIndex = Math.max(0, Math.min(this.maxIndex, idx));
    let target = -this.currentIndex * this.cardWidth;
    if (target > 0) target = 0;
    if (target < -this.maxScroll) target = -this.maxScroll;
    this.currentX = target; this.applyTransform(600);
    this.scheduleAutoResume(2500);
  }

  clamp() {
    if (this.currentIndex > this.maxIndex) this.currentIndex = this.maxIndex;
    if (this.currentX > 0) this.currentX = 0;
    if (this.currentX < -this.maxScroll) this.currentX = -this.maxScroll;
  }

  applyTransform(duration) {
    this.track.style.transition = duration > 0 ? 'transform ' + duration + 'ms cubic-bezier(0.16, 1, 0.3, 1)' : 'none';
    this.track.style.transform = 'translateX(' + this.currentX + 'px)';
  }

  scheduleAutoResume(delay) {
    this.stopAuto();
    this.resumeTimer = setTimeout(() => this.startAuto(), delay);
  }

  startAuto() {
    if (!this.autoAdvance) return;
    this.stopAuto();
    this.autoTimer = setInterval(() => {
      if (this.pauseAuto || this.isDown) return;
      const nextIdx = this.currentIndex >= this.maxIndex ? 0 : this.currentIndex + 1;
      this.goTo(nextIdx);
    }, this.autoInterval);
  }

  stopAuto() {
    if (this.autoTimer) { clearInterval(this.autoTimer); this.autoTimer = null; }
    if (this.resumeTimer) { clearTimeout(this.resumeTimer); this.resumeTimer = null; }
  }
}

export function initLandingAnimations() {
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
    window.addEventListener('resize', function () {
      clearTimeout(reArmar);
      reArmar = setTimeout(armarMarquee, 200);
    }, { passive: true });
  }

  /* ============================
     HERO REEL — frame cycler
     ============================ */
  let heroVisible = true;
  let tickZoomId = null;
  let tickZoom = null;
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

    setInterval(function () {
      currentFrame = (currentFrame + 1) % frames.length;
      showFrame(currentFrame);
    }, frameDuration);

    tickZoom = function () {
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
    };
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
     HERO VISIBILITY OBSERVER
     ============================ */
  const heroSection = document.getElementById('inicio');
  if (heroSection) {
    const heroObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.target === heroSection) {
          heroVisible = entry.isIntersecting;
          if (heroVisible) {
            if (tickZoomId) cancelAnimationFrame(tickZoomId);
            if (typeof tickZoom === 'function') tickZoomId = requestAnimationFrame(tickZoom);
          } else if (tickZoomId) {
            cancelAnimationFrame(tickZoomId);
            tickZoomId = null;
          }
        }
      });
    }, { threshold: 0 });

    heroObserver.observe(heroSection);
  }

  /* ============================
     GRAIN PARALLAX
     ============================ */
  const grain = document.getElementById('grain');
  if (grain) {
    let targetY = 0;
    let currentY = 0;
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
  new StoriesCarousel(document.getElementById('storyTrack'), { interval: 4500 });

  /* ============================
     HEADLINE CHAR REVEAL (triggers after 400ms)
     ============================ */
  setTimeout(function () {
    const heroContent = document.querySelector('.hero-content');
    if (heroContent) heroContent.classList.add('in-view');
  }, 400);

  /* ============================
     MOBILE MENU
     ============================ */
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const navLinksEl = document.getElementById('navLinks');
  if (mobileMenuBtn && navLinksEl) {
    mobileMenuBtn.addEventListener('click', function () {
      const isOpen = navLinksEl.classList.toggle('active');
      mobileMenuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    navLinksEl.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinksEl.classList.remove('active');
        mobileMenuBtn.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ============================
     ROLES INTERACTIVE SWITCHER
     ============================ */
  const roleNavBtns = document.querySelectorAll('.role-nav-btn');
  const rolePanes = document.querySelectorAll('.role-stage-pane');
  const roleBgFrames = document.querySelectorAll('.role-bg-frame');
  if (roleNavBtns.length && rolePanes.length) {
    roleNavBtns.forEach(btn => {
      btn.addEventListener('click', function () {
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
      item.addEventListener('click', function () {
        userInteracted = true;
        if (tourTimer) clearInterval(tourTimer);
        const stepNum = parseInt(this.dataset.step, 10);
        selectStep(stepNum);
      });
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          userInteracted = true;
          if (tourTimer) clearInterval(tourTimer);
          selectStep(parseInt(this.dataset.step, 10));
        }
      });
    });

    // Auto-advance softly every 6s unless user interacted
    tourTimer = setInterval(function () {
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
    const dot = document.getElementById('cursorDot');
    const ring = document.getElementById('cursorRing');
    if (dot && ring) {
      let mx = 0, my = 0, rx = 0, ry = 0;
      document.addEventListener('mousemove', function (e) {
        mx = e.clientX; my = e.clientY;
        dot.style.left = mx + 'px';
        dot.style.top = my + 'px';
      });
      const hoverTargets = document.querySelectorAll('a, button, .btn-tech, .nav-cta, .story-card, .wf-step-item, input, textarea, select, [role="button"]');
      hoverTargets.forEach(function (el) {
        el.addEventListener('mouseenter', function () { dot.classList.add('hover'); ring.classList.add('hover'); });
        el.addEventListener('mouseleave', function () { dot.classList.remove('hover'); ring.classList.remove('hover'); });
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
}
