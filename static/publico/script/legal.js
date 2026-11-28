const btn = document.getElementById('legalThemeToggle');
if (btn) {
  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem('jobdevs-theme', next);
    } catch {
      // Ignore storage errors in restricted browsing modes.
    }
  });
}

const tocLinks = Array.from(document.querySelectorAll('.legal-toc-list a[href^="#"]'));
if (tocLinks.length && 'IntersectionObserver' in window) {
  const map = {};
  tocLinks.forEach((link) => {
    const id = link.getAttribute('href').slice(1);
    const el = document.getElementById(id);
    if (el) map[id] = { link, el };
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && map[entry.target.id]) {
          tocLinks.forEach((l) => l.classList.remove('is-current'));
          map[entry.target.id].link.classList.add('is-current');
        }
      });
    },
    { rootMargin: '-18% 0px -70% 0px', threshold: 0 }
  );

  Object.keys(map).forEach((id) => observer.observe(map[id].el));
}
