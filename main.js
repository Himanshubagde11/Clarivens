// Custom cursor (glow dot + lagging ring)
(function(){
  const cursorDot = document.getElementById('cursorDot');
  const cursorRing = document.getElementById('cursorRing');
  if(!cursorDot || !cursorRing) return;

  const isCoarse = window.matchMedia('(pointer:coarse)').matches;
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(isCoarse || prefersReducedMotion) {
    cursorDot.style.display = 'none';
    cursorRing.style.display = 'none';
    return;
  }

  let mx = -100, my = -100;
  let rx = -100, ry = -100;
  let isVisible = false;

  function showCursor() {
    if (!isVisible) {
      isVisible = true;
      cursorDot.classList.add('visible');
      cursorRing.classList.add('visible');
    }
  }

  function hideCursor() {
    if (isVisible) {
      isVisible = false;
      cursorDot.classList.remove('visible');
      cursorRing.classList.remove('visible');
      cursorRing.classList.remove('active');
      cursorRing.classList.remove('clicking');
      cursorDot.classList.remove('active');
      cursorDot.classList.remove('clicking');
    }
  }

  window.addEventListener('mousemove', (e) => {
    mx = e.clientX;
    my = e.clientY;
    if (!isVisible) {
      rx = mx;
      ry = my;
      showCursor();
    }
    cursorDot.style.left = mx + 'px';
    cursorDot.style.top = my + 'px';
  }, { passive: true });

  document.addEventListener('mouseleave', hideCursor);
  document.addEventListener('mouseenter', showCursor);
  window.addEventListener('blur', hideCursor);

  window.addEventListener('mousedown', () => {
    if (!isVisible) return;
    cursorRing.classList.add('clicking');
    cursorDot.classList.add('clicking');
  });

  window.addEventListener('mouseup', () => {
    cursorRing.classList.remove('clicking');
    cursorDot.classList.remove('clicking');
  });

  function ringLoop(){
    if (isVisible) {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      cursorRing.style.left = rx + 'px';
      cursorRing.style.top = ry + 'px';
    }
    requestAnimationFrame(ringLoop);
  }
  requestAnimationFrame(ringLoop);

  // Delegation for hover interactions across all interactive elements
  const INTERACTIVE_SEL = 'a, button, .btn, .tilt, select, summary, [role="button"], .nav-toggle, .filter-btn, .project-card, .faq-question, .faq-item, .pricing-card, .modal-close';
  const INPUT_SEL = 'input, textarea, [contenteditable="true"]';

  document.addEventListener('mouseover', (e) => {
    const target = e.target;
    if (target.closest(INPUT_SEL)) {
      cursorDot.classList.add('hidden-input');
      cursorRing.classList.add('hidden-input');
    } else if (target.closest(INTERACTIVE_SEL)) {
      cursorRing.classList.add('active');
      cursorDot.classList.add('active');
    }
  });

  document.addEventListener('mouseout', (e) => {
    const target = e.target;
    if (target.closest(INPUT_SEL)) {
      cursorDot.classList.remove('hidden-input');
      cursorRing.classList.remove('hidden-input');
    }
    if (target.closest(INTERACTIVE_SEL)) {
      const rel = e.relatedTarget;
      if (!rel || !rel.closest(INTERACTIVE_SEL)) {
        cursorRing.classList.remove('active');
        cursorDot.classList.remove('active');
      }
    }
  });

  // Magnetic buttons
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const bx = e.clientX - rect.left - rect.width/2;
      const by = e.clientY - rect.top - rect.height/2;
      btn.style.transform = `translate(${bx*0.28}px, ${by*0.35}px)`;
    });
    btn.addEventListener('mouseleave', () => { btn.style.transform = 'translate(0,0)'; });
  });
})();

// Cookie consent banner
(function(){
  const banner = document.getElementById('cookieBanner');
  const acceptBtn = document.getElementById('cookieAccept');
  const declineBtn = document.getElementById('cookieDecline');
  if(!banner) return;

  const STORAGE_KEY = 'clarivens_cookie_consent';
  let existing = null;
  try { existing = localStorage.getItem(STORAGE_KEY); } catch(e) { /* storage unavailable, e.g. private mode */ }

  if(!existing){
    setTimeout(() => banner.classList.add('visible'), 600);
  }

  function setConsent(value){
    try { localStorage.setItem(STORAGE_KEY, value); } catch(e) { /* ignore */ }
    banner.classList.remove('visible');
  }

  if(acceptBtn) acceptBtn.addEventListener('click', () => setConsent('accepted'));
  if(declineBtn) declineBtn.addEventListener('click', () => setConsent('declined'));
})();

// Services tabs (interactive tab switcher on the home page)
(function(){
  const tabBtns = document.querySelectorAll('.tab-btn');
  if(!tabBtns.length) return;
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-tab');
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
      });
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.getAttribute('data-panel') === target);
      });
    });
  });
})();

// Generic accordion toggle (used by Process steps, FAQ, etc. — any [data-accordion-trigger])
(function(){
  const triggers = document.querySelectorAll('[data-accordion-trigger]');
  if(!triggers.length) return;
  triggers.forEach(trigger => {
    trigger.addEventListener('click', () => {
      const isOpen = trigger.getAttribute('aria-expanded') === 'true';
      trigger.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
    });
  });
})();

// Mobile nav
(function(){
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');
  if(!navToggle || !navLinks) return;
  navToggle.addEventListener('click', () => navLinks.classList.toggle('open'));
  navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => navLinks.classList.remove('open')));
})();

// Scroll reveal
(function(){
  const els = document.querySelectorAll('.reveal');
  if(!els.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => { if(entry.isIntersecting){ entry.target.classList.add('in'); io.unobserve(entry.target); } });
  }, {threshold:0.15});
  els.forEach(el => io.observe(el));
})();

// 3D tilt interaction for cards
(function(){
  const tiltEls = document.querySelectorAll('.tilt');
  tiltEls.forEach(el => {
    el.style.perspective = '900px';
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left, y = e.clientY - rect.top;
      const rx = ((y / rect.height) - 0.5) * -10;
      const ry = ((x / rect.width) - 0.5) * 10;
      el.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg) translateZ(4px)`;
      el.style.setProperty('--mx', x + 'px');
      el.style.setProperty('--my', y + 'px');
    });
    el.addEventListener('mouseleave', () => { el.style.transform = 'rotateX(0deg) rotateY(0deg) translateZ(0)'; });
  });
})();