const tablist = document.getElementById('metodoTab');
const content = document.getElementById('metodoTabContent');

if (tablist && content) {
  const tabs = Array.from(tablist.querySelectorAll('[data-tab-target]'));
  const panes = Array.from(content.querySelectorAll('.tab-pane'));

  const activateTab = (tab) => {
    const targetSelector = tab.getAttribute('data-tab-target');
    const targetPane = targetSelector ? document.querySelector(targetSelector) : null;
    if (!targetPane) return;

    tabs.forEach((btn) => {
      const isCurrent = btn === tab;
      btn.classList.toggle('active', isCurrent);
      btn.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
      btn.setAttribute('tabindex', isCurrent ? '0' : '-1');
    });

    panes.forEach((pane) => {
      const isCurrent = pane === targetPane;
      pane.classList.toggle('active', isCurrent);
      pane.classList.toggle('show', isCurrent);
    });
  };

  tabs.forEach((tab, index) => {
    tab.setAttribute('tabindex', tab.classList.contains('active') ? '0' : '-1');

    tab.addEventListener('click', () => {
      activateTab(tab);
    });

    tab.addEventListener('keydown', (event) => {
      let nextIndex = null;
      if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') nextIndex = 0;
      else if (event.key === 'End') nextIndex = tabs.length - 1;

      if (nextIndex !== null) {
        event.preventDefault();
        tabs[nextIndex].focus();
        activateTab(tabs[nextIndex]);
      }
    });
  });
}
