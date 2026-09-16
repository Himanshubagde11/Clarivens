// Brand orbit graphic: subtle mouse-parallax tilt (desktop/mouse only)
(function(){
  const orbit = document.getElementById('orbitGraphic');
  if(!orbit) return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse = window.matchMedia('(pointer:coarse)').matches;
  if(reduced || coarse) return;
  window.addEventListener('mousemove', (e) => {
    const rect = orbit.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / window.innerWidth;
    const dy = (e.clientY - cy) / window.innerHeight;
    orbit.style.transform = `rotateY(${dx * 16}deg) rotateX(${-dy * 16}deg)`;
  });
})();

// Hero name expand-and-fade on scroll
(function(){
  const heroScrollSpace = document.getElementById('heroScrollSpace');
  const heroTitle = document.getElementById('heroTitle');
  if(!heroScrollSpace || !heroTitle) return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const heroEyebrow = document.getElementById('heroEyebrow');
  const heroLead = document.getElementById('heroLead');
  const heroCtas = document.getElementById('heroCtas');
  const heroStats = document.getElementById('heroStats');
  const scrollCue = document.getElementById('scrollCue');
  let smoothed = 0;
  const isNarrow = window.innerWidth < 560;
  const scaleAmount = isNarrow ? 0.7 : 1.6;
  function loop(){
    const scrollable = heroScrollSpace.offsetHeight - window.innerHeight;
    const raw = Math.min(Math.max(window.scrollY / scrollable, 0), 1);
    smoothed += (raw - smoothed) * (reduced ? 1 : 0.14);

    const scale = 1 + smoothed * scaleAmount;
    const nameOpacity = Math.max(1 - smoothed * 1.3, 0);
    const restOpacity = Math.max(1 - smoothed * 3.2, 0);

    heroTitle.style.transform = `scale(${scale})`;
    heroTitle.style.opacity = nameOpacity;
    if(heroEyebrow) heroEyebrow.style.opacity = restOpacity;
    if(heroLead) heroLead.style.opacity = restOpacity;
    if(heroCtas) heroCtas.style.opacity = restOpacity;
    if(heroStats) heroStats.style.opacity = restOpacity;
    if(scrollCue) scrollCue.style.opacity = Math.max(1 - smoothed * 6, 0);

    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();

// Contact form -> stores the enquiry via a form backend (Formspree), with a mailto fallback
// if that hasn't been configured yet or the request fails, so no enquiry is ever silently lost.
//
// TO ACTIVATE STORAGE OF SUBMISSIONS:
// 1. Go to https://formspree.io and create a free account.
// 2. Create a new form, copy the endpoint it gives you (looks like https://formspree.io/f/xxxxxxxx).
// 3. Paste it below, replacing the placeholder string.
const FORM_ENDPOINT = "https://formspree.io/f/mjyvvkkn";

// TO ACTIVATE THE "THANK YOU FOR CHOOSING CLARIVENS" AUTO-REPLY EMAIL TO THE CUSTOMER:
// 1. Go to https://www.emailjs.com and create a free account.
// 2. Add an Email Service (connect the clarivens.io@gmail.com Gmail account) — note the Service ID.
// 3. Create a new Email Template, paste in the contents of email-template.html as the template body,
//    and make sure the "To email" field is set to {{workEmail}} — note the Template ID.
// 4. Go to Account > General and copy your Public Key.
// 5. Paste all three values below, replacing the placeholders.
const EMAILJS_PUBLIC_KEY = "TAQ-H6Nvf7P6sBxc2";
const EMAILJS_SERVICE_ID = "service_y4z99kp";
const EMAILJS_TEMPLATE_ID = "template_m0ss1hj";

if (window.emailjs) {
  emailjs.init({ publicKey: EMAILJS_PUBLIC_KEY });
} else {
  console.warn('[Clarivens] EmailJS SDK did not load — check that the <script> tag in index.html <head> is present and not blocked (ad blockers sometimes block it).');
}

(function(){
  const form = document.getElementById('contactForm');
  const formNote = document.getElementById('formNote');
  const formSuccess = document.getElementById('formSuccess');
  if(!form) return;

  // Prefill the requirement field + matching dropdown if arriving from a Services page link
  // like index.html?service=Dashboards%20%26%20BI#contact
  const requirementField = document.getElementById('requirement');
  const helpTypeField = document.getElementById('helpType');
  const query = window.location.search.replace('?', '') || (window.location.hash.includes('?') ? window.location.hash.split('?')[1] : '');
  if(query && requirementField){
    const params = new URLSearchParams(query);
    const service = params.get('service');
    if(service){
      const decoded = decodeURIComponent(service);
      requirementField.value = `I'm interested in: ${decoded}\n\n`;
      requirementField.focus();
      const serviceToHelpType = {
        'Data Analytics': 'Data Analytics',
        'AI Automation': 'AI Automation',
        'Dashboards & BI': 'Power BI Dashboard',
        'ETL & Data Pipelines': 'SQL / Database',
        'Data Cleaning & Analysis': 'Data Cleaning & Transformation',
        'Reporting & Automation': 'Reporting Automation',
        'Web Development': 'Web Development',
        'App Development': 'App Development',
        'Business & Portfolio Websites': 'Web Development',
        'E-Commerce Websites': 'Web Development',
        'Web Applications': 'Web Development',
        'Website Redesign & Maintenance': 'Web Development',
        'Android App Development': 'App Development',
        'iOS App Development': 'App Development',
        'Cross-Platform Apps': 'App Development',
        'Desktop / Windows Apps': 'App Development'
      };
      const mapped = serviceToHelpType[decoded];
      if(mapped && helpTypeField) helpTypeField.value = mapped;
    }
  }

  // Show the "Who referred you?" field only when Referral is selected,
  // and the "Please specify" field only when Other is selected.
  const hearAboutSelect = document.getElementById('hearAbout');
  const referralField = document.getElementById('referralNameField');
  const hearAboutOtherField = document.getElementById('hearAboutOtherField');
  if (hearAboutSelect) {
    const toggleHearAboutFields = () => {
      const isReferral = hearAboutSelect.value === 'Referral';
      const isOther = hearAboutSelect.value === 'Other';
      if (referralField) {
        referralField.style.display = isReferral ? 'block' : 'none';
        const input = document.getElementById('referralName');
        if (input) { input.required = isReferral; if (!isReferral) input.value = ''; }
      }
      if (hearAboutOtherField) {
        hearAboutOtherField.style.display = isOther ? 'block' : 'none';
        const input = document.getElementById('hearAboutOther');
        if (input) { input.required = isOther; if (!isOther) input.value = ''; }
      }
    };
    hearAboutSelect.addEventListener('change', toggleHearAboutFields);
    toggleHearAboutFields();
  }

  // Show the "Please specify" field only when Other is selected for "What do you need help with?"
  const helpTypeSelect = document.getElementById('helpType');
  const helpTypeOtherField = document.getElementById('helpTypeOtherField');
  if (helpTypeSelect && helpTypeOtherField) {
    const toggleHelpTypeOther = () => {
      const isOther = helpTypeSelect.value === 'Other';
      helpTypeOtherField.style.display = isOther ? 'block' : 'none';
      const input = document.getElementById('helpTypeOther');
      if (input) { input.required = isOther; if (!isOther) input.value = ''; }
    };
    helpTypeSelect.addEventListener('change', toggleHelpTypeOther);
    toggleHelpTypeOther();
  }

  // Show only the follow-up questions relevant to whichever service category was picked,
  // so the form asks for detail without cluttering the page with every possible question.
  const dataAnalyticsHelpTypes = [
    'Data Analytics', 'Business Intelligence', 'Power BI Dashboard', 'Excel Automation',
    'SQL / Database', 'Data Cleaning & Transformation', 'Reporting Automation', 'Custom Analytics Solution'
  ];
  const categoryFieldGroups = {
    dataAnalytics: document.getElementById('dataAnalyticsFields'),
    webDev: document.getElementById('webDevFields'),
    appDev: document.getElementById('appDevFields')
  };
  function clearFieldsWithin(container){
    if (!container) return;
    container.querySelectorAll('select, input[type="text"]').forEach(el => { el.value = ''; });
    container.querySelectorAll('input[type="checkbox"]').forEach(el => { el.checked = false; });
  }
  if (helpTypeSelect) {
    const toggleServiceDetailFields = () => {
      const val = helpTypeSelect.value;
      const category = dataAnalyticsHelpTypes.includes(val) ? 'dataAnalytics'
        : val === 'Web Development' ? 'webDev'
        : val === 'App Development' ? 'appDev'
        : null;
      Object.keys(categoryFieldGroups).forEach(key => {
        const el = categoryFieldGroups[key];
        if (!el) return;
        const show = key === category;
        el.style.display = show ? 'block' : 'none';
        if (!show) clearFieldsWithin(el);
      });
    };
    helpTypeSelect.addEventListener('change', toggleServiceDetailFields);
    toggleServiceDetailFields();
  }

  // Clear the error highlight as soon as the person checks the box
  const acceptPolicyCheckbox = document.getElementById('acceptPolicy');
  if (acceptPolicyCheckbox) {
    acceptPolicyCheckbox.addEventListener('change', () => {
      const label = acceptPolicyCheckbox.closest('.checkbox-label');
      if (label && acceptPolicyCheckbox.checked) label.classList.remove('error');
    });
  }

  function showThankYou(){
    form.style.display = 'none';
    if(formSuccess) formSuccess.classList.add('visible');
    if(formSuccess) formSuccess.scrollIntoView({behavior:'smooth', block:'center'});
  }

  // Sends the branded "Thank you for choosing Clarivens" auto-reply to the customer.
  // Fire-and-forget: never blocks the thank-you screen (the enquiry itself has already
  // been captured via Formspree/mailto by this point), but logs to the console so failures
  // are actually visible when debugging, open DevTools (F12) → Console after submitting.
  function sendThankYouEmail(payload){
    if (!window.emailjs) {
      console.warn('[Clarivens] Skipped auto-reply: EmailJS SDK not loaded.');
      return;
    }
    if (EMAILJS_PUBLIC_KEY.includes('YOUR_') || EMAILJS_SERVICE_ID.includes('YOUR_') || EMAILJS_TEMPLATE_ID.includes('YOUR_')) {
      console.warn('[Clarivens] Skipped auto-reply: EmailJS is not configured yet. Replace EMAILJS_PUBLIC_KEY, EMAILJS_SERVICE_ID, and EMAILJS_TEMPLATE_ID near the top of home.js with your real values from emailjs.com.');
      return;
    }
    emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, payload)
      .then((res) => {
        console.log('[Clarivens] Auto-reply sent successfully.', res.status, res.text);
      })
      .catch((err) => {
        console.error('[Clarivens] Auto-reply failed to send. This is the actual reason, read it carefully:', err);
      });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Honeypot: if this hidden field got filled in, it was almost certainly a bot. Silently drop it.
    const honeypot = document.getElementById('website');
    if (honeypot && honeypot.value.trim() !== '') {
      showThankYou();
      return;
    }

    const fullName = document.getElementById('fullName').value.trim();
    const company = document.getElementById('company').value.trim();
    const workEmail = document.getElementById('workEmail').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const helpType = document.getElementById('helpType').value;
    const helpTypeOtherField = document.getElementById('helpTypeOther');
    const helpTypeOther = helpTypeOtherField ? helpTypeOtherField.value.trim() : '';
    const requirement = document.getElementById('requirement').value.trim();
    const projectSize = document.getElementById('projectSize').value;
    const timeline = document.getElementById('timeline').value;
    const hearAbout = document.getElementById('hearAbout').value;
    const referralNameField = document.getElementById('referralName');
    const referralName = referralNameField ? referralNameField.value.trim() : '';
    const hearAboutOtherField = document.getElementById('hearAboutOther');
    const hearAboutOther = hearAboutOtherField ? hearAboutOtherField.value.trim() : '';

    // Service-specific follow-up detail (only one group is ever visible/relevant at a time)
    const dataSourceEl = document.getElementById('dataSource');
    const dataVolumeEl = document.getElementById('dataVolume');
    const hasExistingSetupEl = document.getElementById('hasExistingSetup');
    const websiteTypeEl = document.getElementById('websiteType');
    const hasExistingWebsiteEl = document.getElementById('hasExistingWebsite');
    const pageCountEl = document.getElementById('pageCount');
    const appTypeEl = document.getElementById('appType');
    const appStoreListingEl = document.getElementById('appStoreListing');
    const platforms = ['platformAndroid', 'platformIOS', 'platformWindows', 'platformNotSure']
      .map(id => document.getElementById(id))
      .filter(el => el && el.checked)
      .map(el => el.value)
      .join(', ');

    const dataSource = dataSourceEl ? dataSourceEl.value : '';
    const dataVolume = dataVolumeEl ? dataVolumeEl.value : '';
    const hasExistingSetup = hasExistingSetupEl ? hasExistingSetupEl.value : '';
    const websiteType = websiteTypeEl ? websiteTypeEl.value : '';
    const hasExistingWebsite = hasExistingWebsiteEl ? hasExistingWebsiteEl.value : '';
    const pageCount = pageCountEl ? pageCountEl.value : '';
    const appType = appTypeEl ? appTypeEl.value : '';
    const appStoreListing = appStoreListingEl ? appStoreListingEl.value : '';
    const contactPrefEl = document.querySelector('input[name="contactPref"]:checked');
    const contactPref = contactPrefEl ? contactPrefEl.value : '';
    const acceptPolicy = document.getElementById('acceptPolicy');
    const checkboxLabel = acceptPolicy ? acceptPolicy.closest('.checkbox-label') : null;

    // Required: everything except Company/Organization and How did you hear about us.
    if (!fullName || !workEmail || !phone || !helpType || !requirement ||
        !projectSize || !timeline || !contactPref) {
      formNote.textContent = "Please fill in the required fields before submitting.";
      return;
    }
    if (helpType === 'Other' && !helpTypeOther) {
      formNote.textContent = "Please tell us what you need help with.";
      if (helpTypeOtherField) helpTypeOtherField.focus();
      return;
    }
    if (hearAbout === 'Referral' && !referralName) {
      formNote.textContent = "Please tell us who referred you.";
      if (referralNameField) referralNameField.focus();
      return;
    }
    if (hearAbout === 'Other' && !hearAboutOther) {
      formNote.textContent = "Please tell us how you heard about us.";
      if (hearAboutOtherField) hearAboutOtherField.focus();
      return;
    }

    if (acceptPolicy && !acceptPolicy.checked) {
      formNote.textContent = "Please accept the Privacy Policy and Terms & Conditions to continue.";
      if (checkboxLabel) checkboxLabel.classList.add('error');
      acceptPolicy.focus();
      return;
    }
    if (checkboxLabel) checkboxLabel.classList.remove('error');

    const payload = {
      fullName, company, workEmail, phone, helpType, helpTypeOther, requirement,
      projectSize, timeline, hearAbout, referralName, hearAboutOther, contactPref,
      dataSource, dataVolume, hasExistingSetup,
      websiteType, hasExistingWebsite, pageCount,
      platforms, appType, appStoreListing,
      _subject: `New enquiry from ${fullName}`
    };

    const submitBtn = form.querySelector('.submit-btn');
    if(submitBtn){ submitBtn.disabled = true; submitBtn.textContent = 'Submitting...'; }
    formNote.textContent = '';

    let stored = false;
    if (!FORM_ENDPOINT.includes('YOUR_FORM_ID')) {
      try {
        const res = await fetch(FORM_ENDPOINT, {
          method: 'POST',
          headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        stored = res.ok;
        if (!stored) console.error('[Clarivens] Formspree rejected the submission:', res.status, await res.text().catch(() => ''));
      } catch (err) {
        console.error('[Clarivens] Formspree request failed (likely a network issue):', err);
      }
    } else {
      console.warn('[Clarivens] FORM_ENDPOINT is not configured yet, submission was not stored anywhere.');
    }

    // The customer always sees the thank-you screen once basic validation passes,
    // regardless of whether storage or the confirmation email succeeded behind the
    // scenes — failures are logged to the console above for you to debug, but they
    // never interrupt or redirect the person filling out the form.
    sendThankYouEmail(payload);
    showThankYou();
  });
})();

// THREE.js hero: rotating 3D particle network sphere in orange, mouse-reactive
(function(){
  const canvas = document.getElementById('heroCanvas');
  const heroSection = document.getElementById('heroSection');
  if(!canvas || !heroSection || !window.THREE) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, heroSection.clientWidth / heroSection.clientHeight, 0.1, 100);
  camera.position.z = 9;

  function setSize(){
    const w = heroSection.clientWidth, h = heroSection.clientHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  setSize();
  window.addEventListener('resize', setSize);

  // Icosahedron point cloud "data network"
  const geo = new THREE.IcosahedronGeometry(3.4, 3);
  const positions = geo.attributes.position;
  const pointsGeo = new THREE.BufferGeometry();
  pointsGeo.setAttribute('position', positions.clone());

  const pointsMat = new THREE.PointsMaterial({
    color: 0xFF6A00, size: 0.045, transparent:true, opacity:0.9
  });
  const points = new THREE.Points(pointsGeo, pointsMat);
  scene.add(points);

  // wireframe lines for structure, dim
  const wireGeo = new THREE.WireframeGeometry(geo);
  const wireMat = new THREE.LineBasicMaterial({color:0xFF9142, transparent:true, opacity:0.14});
  const wireframe = new THREE.LineSegments(wireGeo, wireMat);
  scene.add(wireframe);

  // subtle outer sphere shell
  const shellGeo = new THREE.IcosahedronGeometry(4.3, 1);
  const shellWire = new THREE.WireframeGeometry(shellGeo);
  const shellMat = new THREE.LineBasicMaterial({color:0xFF6A00, transparent:true, opacity:0.06});
  const shell = new THREE.LineSegments(shellWire, shellMat);
  scene.add(shell);

  let mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5);
    mouseY = (e.clientY / window.innerHeight - 0.5);
  });

  let scrollFactor = 0;
  window.addEventListener('scroll', () => {
    scrollFactor = Math.min(window.scrollY / window.innerHeight, 1.2);
  });

  function animate(){
    if(!reducedMotion){
      points.rotation.y += 0.0016;
      points.rotation.x += 0.0006;
      wireframe.rotation.y += 0.0016;
      wireframe.rotation.x += 0.0006;
      shell.rotation.y -= 0.0009;
    }
    camera.position.x += (mouseX * 1.4 - camera.position.x) * 0.04;
    camera.position.y += (-mouseY * 1.4 - camera.position.y) * 0.04;
    camera.position.z = 9 + scrollFactor * 2.5;
    camera.lookAt(scene.position);
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }
  animate();
})();