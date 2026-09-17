/**
 * Clarivens AI Widget — Self-Contained Frontend
 * 
 * Injects the Clarivens AI assistant widget into any page.
 * Uses only the existing Clarivens design system.
 * 
 * NO dependencies. NO framework. NO modifications to existing code.
 * Lazy-loaded (defer) so it never blocks the 3D canvas or page paint.
 * 
 * API Base: /api/ai  (same origin — no CORS needed)
 */
(function (window, document) {
  'use strict';

  // ============================================================
  // Config
  // ============================================================
  const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  // Connected to live Render backend
  const API_BASE = isLocalDev ? 'http://127.0.0.1:8000/api/ai' : 'https://clarivens.onrender.com/api/ai';
  const STORAGE_KEY = 'cai_session_id';
  const STORAGE_MSG_KEY = 'cai_last_msg_id';

  // ============================================================
  // Inject CSS
  // ============================================================
  function injectCSS() {
    if (document.getElementById('clarivens-ai-css')) return;
    const link = document.createElement('link');
    link.id = 'clarivens-ai-css';
    link.rel = 'stylesheet';
    link.href = '/clarivens-ai-widget.css';
    document.head.appendChild(link);
  }

  // ============================================================
  // SVG Icons
  // ============================================================
  const ICONS = {
    chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" color="white">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>`,
    close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" color="white">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>`,
    send: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" color="white">
      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>`,
    ai: `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round">
      <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
      <circle cx="9" cy="10" r="1.5" fill="white"/><circle cx="15" cy="10" r="1.5" fill="white"/>
    </svg>`,
    user: `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>`,
    thumbsup: '👍',
    thumbsdown: '👎',
  };

  // ============================================================
  // State
  // ============================================================
  let state = {
    isOpen: false,
    sessionId: sessionStorage.getItem(STORAGE_KEY) || null,
    isLoading: false,
    lastMessageId: null,
    hasUnread: false,
    projectId: null,
  };

  // ============================================================
  // DOM References
  // ============================================================
  let elements = {};

  // ============================================================
  // Build Widget DOM
  // ============================================================
  function buildWidget() {
    const root = document.getElementById('clarivens-ai-root');
    if (!root) return;

    root.innerHTML = `
      <!-- FAB Button -->
      <button id="clarivens-ai-fab" aria-label="Open Clarivens AI" title="Clarivens AI">
        <span class="cai-icon-chat">${ICONS.chat}</span>
        <span class="cai-icon-close">${ICONS.close}</span>
        <span id="clarivens-ai-badge" role="status" aria-label="Unread message"></span>
      </button>

      <!-- Chat Panel -->
      <div id="clarivens-ai-panel" role="dialog" aria-modal="true" aria-label="Clarivens AI Assistant" aria-hidden="true">
        
        <!-- Header -->
        <div class="cai-header">
          <div class="cai-header-avatar">${ICONS.ai}</div>
          <div class="cai-header-text">
            <div class="cai-header-name">Clarivens AI</div>
            <div class="cai-header-status">
              <span class="cai-status-dot"></span>
              Analytics Consultant
            </div>
          </div>
          <div class="cai-header-tag">AI&thinsp;v1</div>
        </div>

        <!-- Messages -->
        <div class="cai-messages" id="cai-messages" role="log" aria-live="polite" aria-label="Conversation"></div>

        <!-- Lead capture form (shown when required) -->
        <div class="cai-lead-form" id="cai-lead-form" aria-label="Contact form">
          <div class="cai-form-title">Share your details — we'll be in touch.</div>
          <input class="cai-lead-input" id="cai-lead-name" type="text" placeholder="Your name" autocomplete="name"/>
          <input class="cai-lead-input" id="cai-lead-email" type="email" placeholder="Work email *" required autocomplete="email"/>
          <input class="cai-lead-input" id="cai-lead-company" type="text" placeholder="Company (optional)" autocomplete="organization"/>
          <button class="cai-lead-submit" id="cai-lead-submit">Send to Clarivens</button>
        </div>

        <!-- File upload form (shown when required) -->
        <div class="cai-lead-form cai-upload-form" id="cai-upload-form" aria-label="Upload dataset">
          <div class="cai-form-title">Upload your dataset for analysis.</div>
          <input class="cai-lead-input" id="cai-upload-file" type="file" accept=".csv,.json,.xlsx" style="background:rgba(255,255,255,0.05); color:#fff; border:1px dashed rgba(255,255,255,0.2); padding: 8px;" />
          <button class="cai-lead-submit" id="cai-upload-submit">Upload & Analyze</button>
        </div>

        <!-- Input Bar -->
        <div class="cai-input-bar">
          <textarea
            class="cai-input"
            id="cai-input"
            placeholder="Ask about our services, your data..."
            rows="1"
            aria-label="Message Clarivens AI"
            maxlength="4000"
          ></textarea>
          <button class="cai-send-btn" id="cai-send-btn" aria-label="Send message" title="Send">
            ${ICONS.send}
          </button>
        </div>

        <!-- Footer -->
        <div class="cai-footer">
          <span>Powered by Clarivens Intelligence Platform</span>
        </div>
      </div>
    `;

    // Cache references
    elements = {
      fab: document.getElementById('clarivens-ai-fab'),
      panel: document.getElementById('clarivens-ai-panel'),
      badge: document.getElementById('clarivens-ai-badge'),
      messages: document.getElementById('cai-messages'),
      input: document.getElementById('cai-input'),
      sendBtn: document.getElementById('cai-send-btn'),
      leadForm: document.getElementById('cai-lead-form'),
      leadName: document.getElementById('cai-lead-name'),
      leadEmail: document.getElementById('cai-lead-email'),
      leadCompany: document.getElementById('cai-lead-company'),
      leadSubmit: document.getElementById('cai-lead-submit'),
      uploadForm: document.getElementById('cai-upload-form'),
      uploadFile: document.getElementById('cai-upload-file'),
      uploadSubmit: document.getElementById('cai-upload-submit'),
    };

    bindEvents();
  }

  // ============================================================
  // Events
  // ============================================================
  function bindEvents() {
    // FAB toggle
    elements.fab.addEventListener('click', togglePanel);

    // Send button
    elements.sendBtn.addEventListener('click', sendMessage);

    // Enter to send (Shift+Enter for newline)
    elements.input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    elements.input.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 100) + 'px';
    });

    // Lead form submit
    elements.leadSubmit.addEventListener('click', submitLead);

    // Upload form submit
    elements.uploadSubmit.addEventListener('click', submitFileUpload);

    // Close panel on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && state.isOpen) togglePanel();
    });

    // Close on outside click (but not the FAB itself)
    document.addEventListener('click', function (e) {
      if (state.isOpen &&
          !elements.panel.contains(e.target) &&
          !elements.fab.contains(e.target)) {
        closePanel();
      }
    });
  }

  // ============================================================
  // Panel Open / Close
  // ============================================================
  function togglePanel() {
    if (state.isOpen) {
      closePanel();
    } else {
      openPanel();
    }
  }

  function openPanel() {
    state.isOpen = true;
    elements.fab.classList.add('cai-open');
    elements.panel.classList.add('cai-panel-open');
    elements.panel.setAttribute('aria-hidden', 'false');
    clearBadge();

    // Initialize session if we don't have one yet
    if (!state.sessionId) {
      initSession();
    }

    // Focus input
    requestAnimationFrame(function () {
      elements.input.focus();
    });
  }

  function closePanel() {
    state.isOpen = false;
    elements.fab.classList.remove('cai-open');
    elements.panel.classList.remove('cai-panel-open');
    elements.panel.setAttribute('aria-hidden', 'true');
  }

  function showBadge(count) {
    state.hasUnread = true;
    elements.badge.classList.add('cai-visible');
    elements.badge.textContent = count || '1';
  }

  function clearBadge() {
    state.hasUnread = false;
    elements.badge.classList.remove('cai-visible');
  }

  // ============================================================
  // Session Management
  // ============================================================
  async function initSession() {
    try {
      const body = {};
      if (state.projectId) body.project_id = state.projectId;

      const resp = await apiPost('/session', body);
      if (resp && resp.session_id) {
        state.sessionId = resp.session_id;
        sessionStorage.setItem(STORAGE_KEY, resp.session_id);

        // Show greeting
        showGreeting();
      }
    } catch (err) {
      console.warn('[ClarivensAI] Session init failed:', err);
      showGreeting();
    }
  }

  function showGreeting() {
    const hour = new Date().getHours();
    const timeGreeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

    addAIMessage(
      `${timeGreeting}! I'm **Clarivens AI**, your dedicated analytics consultant.\n\nI can help you:\n• Understand our data analytics services\n• Identify the right solution for your business challenge\n• Explore your uploaded datasets\n• Explain your analysis results\n\nWhat business challenge can I help you with today?`,
      { hideTime: false }
    );
  }

  // ============================================================
  // Message Sending
  // ============================================================
  async function sendMessage() {
    const text = elements.input.value.trim();
    if (!text || state.isLoading) return;

    // Clear input
    elements.input.value = '';
    elements.input.style.height = 'auto';

    // Show user message immediately
    addUserMessage(text);

    // Ensure session exists
    if (!state.sessionId) {
      await initSession();
    }

    // Show typing
    const typingEl = showTyping();
    state.isLoading = true;
    elements.sendBtn.disabled = true;

    try {
      const resp = await apiPost('/chat', {
        message: text,
        session_id: state.sessionId,
        project_id: state.projectId || undefined,
      });

      removeTyping(typingEl);
      state.isLoading = false;
      elements.sendBtn.disabled = false;

      if (resp) {
        // Update session id in case it was created
        if (resp.session_id && !state.sessionId) {
          state.sessionId = resp.session_id;
          sessionStorage.setItem(STORAGE_KEY, resp.session_id);
        }

        // Show AI response
        const aiMsgEl = addAIMessage(resp.message, { messageId: resp.last_message_id });
        
        // Show suggested actions
        if (resp.suggested_actions && resp.suggested_actions.length > 0) {
          addSuggestions(resp.suggested_actions);
        }

        // Show lead form if required
        if (resp.requires_lead_capture) {
          showLeadForm();
        }

        // Show upload form if file upload required
        if (resp.requires_file_upload) {
          showFileUploadForm();
        }
      } else {
        addAIMessage("I'm having trouble connecting right now. Please try again in a moment.");
      }
    } catch (err) {
      removeTyping(typingEl);
      state.isLoading = false;
      elements.sendBtn.disabled = false;
      addAIMessage("I encountered an error. Please try again or contact us directly at clarivens.com/contact");
      console.error('[ClarivensAI] Chat error:', err);
    }

    scrollToBottom();
    elements.input.focus();
  }

  // ============================================================
  // Message Rendering
  // ============================================================
  function addUserMessage(text) {
    const el = createMessageEl('user', text);
    elements.messages.appendChild(el);
    scrollToBottom();
  }

  function addAIMessage(text, opts = {}) {
    const el = createMessageEl('ai', text, opts);
    elements.messages.appendChild(el);
    scrollToBottom();

    // Show notification badge if panel is closed
    if (!state.isOpen) {
      showBadge(1);
    }

    return el;
  }

  function createMessageEl(role, text, opts = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = `cai-message cai-${role}`;

    const avatarEl = document.createElement('div');
    avatarEl.className = `cai-msg-avatar${role === 'user' ? ' cai-user-avatar' : ''}`;
    avatarEl.innerHTML = role === 'ai' ? ICONS.ai : ICONS.user;
    avatarEl.setAttribute('aria-hidden', 'true');

    const contentEl = document.createElement('div');
    contentEl.className = 'cai-msg-content';

    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'cai-msg-bubble';
    bubbleEl.innerHTML = renderMarkdown(text);

    const timeEl = document.createElement('div');
    timeEl.className = 'cai-msg-time';
    timeEl.textContent = formatTime(new Date());

    contentEl.appendChild(bubbleEl);
    contentEl.appendChild(timeEl);

    // Feedback buttons for AI messages
    if (role === 'ai' && opts.messageId) {
      const feedbackRow = createFeedbackRow(opts.messageId);
      contentEl.appendChild(feedbackRow);
    }

    wrapper.appendChild(avatarEl);
    wrapper.appendChild(contentEl);

    return wrapper;
  }

  function createFeedbackRow(messageId) {
    const row = document.createElement('div');
    row.className = 'cai-feedback-row';
    row.setAttribute('aria-label', 'Rate this response');

    [
      { emoji: ICONS.thumbsup, label: 'Helpful', rating: 'helpful' },
      { emoji: ICONS.thumbsdown, label: 'Not helpful', rating: 'not_helpful' },
    ].forEach(function (item) {
      const btn = document.createElement('button');
      btn.className = 'cai-feedback-btn';
      btn.textContent = item.emoji + ' ' + item.label;
      btn.setAttribute('aria-label', item.label);
      btn.addEventListener('click', function () {
        submitFeedback(messageId, item.rating, btn, row);
      });
      row.appendChild(btn);
    });

    return row;
  }

  function addSuggestions(actions) {
    const suggestions = document.createElement('div');
    suggestions.className = 'cai-suggestions';

    actions.forEach(function (action) {
      const chip = document.createElement('button');
      chip.className = 'cai-suggestion-chip';
      chip.textContent = action;
      chip.addEventListener('click', function () {
        elements.input.value = action;
        sendMessage();
        suggestions.remove();
      });
      suggestions.appendChild(chip);
    });

    elements.messages.appendChild(suggestions);
  }

  function showTyping() {
    const el = document.createElement('div');
    el.className = 'cai-typing-indicator';
    el.setAttribute('aria-label', 'Clarivens AI is typing');
    el.setAttribute('role', 'status');
    el.innerHTML = `
      <div class="cai-msg-avatar" aria-hidden="true">${ICONS.ai}</div>
      <div class="cai-typing-dots">
        <span></span><span></span><span></span>
      </div>
    `;
    elements.messages.appendChild(el);
    scrollToBottom();
    return el;
  }

  function removeTyping(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function showLeadForm() {
    elements.leadForm.classList.add('cai-visible');
    requestAnimationFrame(function () {
      elements.leadName.focus();
    });
  }

  function hideLeadForm() {
    elements.leadForm.classList.remove('cai-visible');
  }

  function showFileUploadForm() {
    elements.uploadForm.classList.add('cai-visible');
  }

  function hideFileUploadForm() {
    elements.uploadForm.classList.remove('cai-visible');
  }

  // ============================================================
  // Lead Form
  // ============================================================
  async function submitLead() {
    const email = elements.leadEmail.value.trim();
    if (!email || !email.includes('@')) {
      elements.leadEmail.focus();
      elements.leadEmail.style.borderColor = 'rgba(255,59,48,0.6)';
      setTimeout(function () {
        elements.leadEmail.style.borderColor = '';
      }, 1500);
      return;
    }

    elements.leadSubmit.textContent = 'Sending...';
    elements.leadSubmit.disabled = true;

    try {
      const resp = await apiPost('/lead', {
        session_id: state.sessionId,
        name: elements.leadName.value.trim() || undefined,
        email: email,
        company: elements.leadCompany.value.trim() || undefined,
      });

      hideLeadForm();
      addAIMessage(
        resp && resp.success
          ? "✅ Thank you! A Clarivens consultant will reach out to you at **" + email + "** shortly.\n\nIn the meantime, feel free to ask me anything about our services."
          : "We couldn't save your details right now. Please email us directly at **hello@clarivens.com**."
      );
    } catch (err) {
      addAIMessage("Something went wrong. Please email us at **hello@clarivens.com** directly.");
    }

    elements.leadSubmit.textContent = 'Send to Clarivens';
    elements.leadSubmit.disabled = false;
  }

  // ============================================================
  // File Upload
  // ============================================================
  async function submitFileUpload() {
    const files = elements.uploadFile.files;
    if (!files || files.length === 0) {
      alert("Please select a file first.");
      return;
    }

    elements.uploadSubmit.textContent = 'Uploading...';
    elements.uploadSubmit.disabled = true;

    const formData = new FormData();
    formData.append('file', files[0]);
    formData.append('session_id', state.sessionId);

    try {
      const resp = await fetch(API_BASE + '/upload', {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header manually when sending FormData
      });

      if (!resp.ok) {
        const err = await resp.json().catch(function () { return {}; });
        throw new Error(err.detail || 'Upload failed with status ' + resp.status);
      }

      const data = await resp.json();
      hideFileUploadForm();

      if (data.project_id) {
        state.projectId = data.project_id;
      }

      addAIMessage(
        "✅ *Your dataset has been uploaded and analysis has begun!*\n\n" +
        "You can view the full dashboard in your [Workspace](/workspace.html?project_id=" + data.project_id + "), or ask me questions about the data right here."
      );
      
    } catch (err) {
      console.error('[ClarivensAI] Upload error:', err);
      addAIMessage("Failed to upload the file. Please check the file format and try again.");
    }

    elements.uploadSubmit.textContent = 'Upload & Analyze';
    elements.uploadSubmit.disabled = false;
    elements.uploadFile.value = ''; // Reset input
  }

  // ============================================================
  // Feedback
  // ============================================================
  async function submitFeedback(messageId, rating, btn, row) {
    if (!state.sessionId) return;

    // Mark button as active immediately
    row.querySelectorAll('.cai-feedback-btn').forEach(function (b) {
      b.classList.remove('cai-active');
    });
    btn.classList.add('cai-active');

    try {
      await apiPost('/feedback', {
        session_id: state.sessionId,
        message_id: messageId,
        rating: rating,
      });
    } catch (err) {
      // Feedback failure is non-critical
      console.warn('[ClarivensAI] Feedback failed:', err);
    }
  }

  // ============================================================
  // API Helpers
  // ============================================================
  async function apiPost(path, body) {
    const resp = await fetch(API_BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(function () { return {}; });
      throw new Error(err.detail || 'API error ' + resp.status);
    }
    return resp.json();
  }

  // ============================================================
  // Minimal Markdown Renderer
  // ============================================================
  function renderMarkdown(text) {
    if (!text) return '';

    // Escape HTML first
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Bold **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code style="font-family:\'JetBrains Mono\',monospace;font-size:12px;background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:4px;">$1</code>');

    // Links [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--cai-orange);text-decoration:none;" target="_self">$1</a>');

    // Bullet lists: lines starting with •, -, *
    html = html.replace(/^[•\-\*]\s+(.+)$/gm, '<li style="margin-left:1em;margin-bottom:2px;">$1</li>');
    html = html.replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul style="margin:6px 0;padding:0;list-style:none;">$&</ul>');

    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p style="margin:0 0 8px;">');
    html = '<p style="margin:0 0 8px;">' + html + '</p>';

    // Single newlines → <br>
    html = html.replace(/\n/g, '<br>');

    return html;
  }

  // ============================================================
  // Utilities
  // ============================================================
  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      elements.messages.scrollTop = elements.messages.scrollHeight;
    });
  }

  // ============================================================
  // Project ID Detection
  // ============================================================
  function detectProjectId() {
    // Check URL params: ?project=123
    const params = new URLSearchParams(window.location.search);
    const pid = params.get('project');
    if (pid && !isNaN(parseInt(pid))) {
      state.projectId = parseInt(pid);
    }
    // Check page-level data attribute: <body data-project-id="123">
    const bodyPid = document.body.getAttribute('data-project-id');
    if (bodyPid && !isNaN(parseInt(bodyPid))) {
      state.projectId = parseInt(bodyPid);
    }
  }

  // ============================================================
  // Greeting Trigger — show badge after delay on first visit
  // ============================================================
  function triggerFirstVisitGreeting() {
    const seen = sessionStorage.getItem('cai_greeted');
    if (seen) return;

    setTimeout(function () {
      if (!state.isOpen) {
        showBadge(1);
        sessionStorage.setItem('cai_greeted', '1');
      }
    }, 4000);
  }

  // ============================================================
  // Initialize
  // ============================================================
  function init() {
    injectCSS();
    detectProjectId();
    buildWidget();
    triggerFirstVisitGreeting();
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(window, document);
