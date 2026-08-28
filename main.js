// Custom cursor (glow dot + lagging ring)
(function(){
  const cursorDot = document.getElementById('cursorDot');
  const cursorRing = document.getElementById('cursorRing');
  if(!cursorDot || !cursorRing) return;
  const isCoarse = window.matchMedia('(pointer:coarse)').matches;
  if(isCoarse) return;

  let mx = window.innerWidth/2, my = window.innerHeight/2;
  let rx = mx, ry = my;
  window.addEventListener('mousemove', (e) => {
    mx = e.clientX; my = e.clientY;
    cursorDot.style.left = mx + 'px'; cursorDot.style.top = my + 'px';
  });
  function ringLoop(){
    rx += (mx - rx) * 0.16; ry += (my - ry) * 0.16;
    cursorRing.style.left = rx + 'px'; cursorRing.style.top = ry + 'px';
    requestAnimationFrame(ringLoop);
  }
  ringLoop();
  document.querySelectorAll('a, button, .tilt, input, textarea').forEach(el => {
    el.addEventListener('mouseenter', () => cursorRing.classList.add('active'));
    el.addEventListener('mouseleave', () => cursorRing.classList.remove('active'));
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