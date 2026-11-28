function switchModuloTab(tab) {
  const esAvances = tab === 'avances';

  const panelHitos = document.getElementById('panelHitos');
  const panelAvances = document.getElementById('panelAvances');
  const tabHitos = document.getElementById('tabHitos');
  const tabAvances = document.getElementById('tabAvances');

  if (panelHitos) panelHitos.style.display = esAvances ? 'none' : '';
  if (panelAvances) panelAvances.style.display = esAvances ? '' : 'none';

  if (tabHitos) {
    tabHitos.classList.toggle('active', !esAvances);
    tabHitos.setAttribute('aria-selected', esAvances ? 'false' : 'true');
  }
  if (tabAvances) {
    tabAvances.classList.toggle('active', esAvances);
    tabAvances.setAttribute('aria-selected', esAvances ? 'true' : 'false');
  }

  document.querySelectorAll('.sidebar .nav-item').forEach((item) => {
    const href = item.getAttribute('href') || '';
    if (href === '#hitos' || href === '#avances') {
      item.classList.toggle('active', href === `#${tab}`);
    }
  });

  if (window.history && window.history.replaceState) {
    window.history.replaceState(null, '', `#${tab}`);
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
  return false;
}

window.switchModuloTab = switchModuloTab;

const initModuloTabs = () => {
  const scriptEl = document.querySelector('script[data-modulo-default-tab]');
  const defaultTab = scriptEl?.dataset.moduloDefaultTab === 'avances' ? 'avances' : 'hitos';
  const hash = (window.location.hash || '').replace('#', '');
  const activeTab = hash === 'hitos' || hash === 'avances' ? hash : defaultTab;
  switchModuloTab(activeTab);

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initModuloTabs);
} else {
  initModuloTabs();
}
