/* =========================================
   Jobdevs // SYSTEM.ROOT — Landing Interactions (ES Module Orchestrator)
   ========================================= */

import { initLandingAnimations } from './modules/landing_animations.js';
import { initLoginModal } from './modules/login_modal.js';
import { initThemeLang } from './modules/theme_lang.js';

function initLanding() {
  initLandingAnimations();
  initLoginModal();
  initThemeLang();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLanding);
} else {
  initLanding();
}
