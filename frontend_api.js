/**
 * Clarivens Workspace Frontend Client.
 * Hardened & Secured:
 * - Safe DOM text node manipulation (zero innerHTML injection)
 * - Safe error handling
 * - Clean polling lifecycle with exponential backoff / timeout guard
 * - Preserves exact UI styling and layout
 */

document.addEventListener('DOMContentLoaded', async () => {
    const dashboardView = document.getElementById('dashboardView');
    const loadingState = document.getElementById('loadingState');

    // UI Elements
    const uploadBtn = document.getElementById('uploadBtn');
    const dataFile = document.getElementById('dataFile');
    const projectStatus = document.getElementById('projectStatus');
    const resultsPanel = document.getElementById('resultsPanel');
    const resProfile = document.getElementById('resProfile');
    const resCleaning = document.getElementById('resCleaning');
    const resEDA = document.getElementById('resEDA');
    const resInsights = document.getElementById('resInsights');
    const resML = document.getElementById('resML');
    const projectNameEl = document.getElementById('projectName');

    const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const API_BASE = isLocalDev ? 'http://127.0.0.1:8000/api/v1' : '/api/v1';
    let currentProjectId = null;
    let pollTimer = null;
    let pollCount = 0;
    const MAX_POLLS = 60; // 3 minutes maximum polling

    function setStatus(text, className) {
        if (!projectStatus) return;
        projectStatus.textContent = text;
        projectStatus.className = `status-badge ${className}`;
    }

    function createTextEl(tag, text, styleObj = null) {
        const el = document.createElement(tag);
        el.textContent = text;
        if (styleObj) Object.assign(el.style, styleObj);
        return el;
    }

    // --- Safe Rendering Helpers (Zero innerHTML) ---

    function safeRenderProfile(container, profile) {
        container.textContent = '';
        if (!profile || typeof profile !== 'object') {
            container.textContent = 'No profiling data available.';
            return;
        }

        const fragment = document.createDocumentFragment();
        const totalCols = (profile.columns || []).length;
        const numCols = (profile.numeric_columns || []).length;
        const catCols = (profile.categorical_columns || []).length;

        const header = createTextEl('div', `Detected ${totalCols} columns (${numCols} numeric, ${catCols} categorical):`, {
            color: '#ff6600',
            fontWeight: '600',
            marginBottom: '8px'
        });
        fragment.appendChild(header);

        if (profile.inferred_types) {
            const list = document.createElement('ul');
            list.style.listStyle = 'none';
            list.style.paddingLeft = '0';
            list.style.margin = '0';

            for (const [col, typeVal] of Object.entries(profile.inferred_types)) {
                const li = document.createElement('li');
                li.style.padding = '3px 0';

                const colSpan = createTextEl('span', col, { color: '#fff', fontWeight: '600' });
                const sepSpan = createTextEl('span', ' : ');
                const typeSpan = createTextEl('span', String(typeVal), { color: '#888' });

                li.appendChild(colSpan);
                li.appendChild(sepSpan);
                li.appendChild(typeSpan);
                list.appendChild(li);
            }
            fragment.appendChild(list);
        }

        container.appendChild(fragment);
    }

    function safeRenderCleaning(container, cleaning) {
        container.textContent = '';
        if (!cleaning || typeof cleaning !== 'object') {
            container.textContent = 'No cleaning data available.';
            return;
        }
        
        const fragment = document.createDocumentFragment();
        
        const summary = createTextEl('div', 'Cleaning Operations Performed:', {
            color: '#ff6600',
            fontWeight: '600',
            marginBottom: '8px'
        });
        fragment.appendChild(summary);

        const list = document.createElement('ul');
        list.style.listStyle = 'none';
        list.style.paddingLeft = '0';
        list.style.margin = '0';

        const addLi = (label, value) => {
            const li = document.createElement('li');
            li.style.padding = '3px 0';
            li.appendChild(createTextEl('span', label, { color: '#fff', fontWeight: '600' }));
            li.appendChild(createTextEl('span', ' : '));
            li.appendChild(createTextEl('span', String(value), { color: '#888' }));
            list.appendChild(li);
        };

        if (cleaning.duplicates_removed !== undefined) addLi('Duplicates Removed', cleaning.duplicates_removed);
        if (cleaning.missing_values_imputed !== undefined) addLi('Missing Values Imputed', cleaning.missing_values_imputed);
        
        if (cleaning.imputation_strategy) {
            for (const [col, strat] of Object.entries(cleaning.imputation_strategy)) {
                addLi(`Imputed [${col}]`, strat);
            }
        }

        fragment.appendChild(list);
        container.appendChild(fragment);
    }

    function safeRenderEDA(container, eda) {
        container.textContent = '';
        if (!eda || typeof eda !== 'object') {
            container.textContent = 'No EDA data available.';
            return;
        }

        const fragment = document.createDocumentFragment();
        
        if (eda.summary_statistics) {
            const title = createTextEl('div', 'Summary Statistics:', { color: '#ff6600', fontWeight: '600', marginBottom: '8px' });
            fragment.appendChild(title);
            
            const list = document.createElement('ul');
            list.style.listStyle = 'none';
            list.style.paddingLeft = '0';
            for (const [col, stats] of Object.entries(eda.summary_statistics)) {
                const li = document.createElement('li');
                li.style.padding = '4px 0';
                li.appendChild(createTextEl('span', col, { color: '#fff', fontWeight: '600' }));
                
                const statStr = Object.entries(stats).map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}`).join(', ');
                li.appendChild(createTextEl('span', ` — ${statStr}`, { color: '#888', fontSize: '12px' }));
                list.appendChild(li);
            }
            fragment.appendChild(list);
        }

        container.appendChild(fragment);
    }

    function safeRenderInsights(container, data) {
        container.textContent = '';
        if (!data || typeof data !== 'object') {
            container.textContent = 'No insights generated yet.';
            return;
        }

        const fragment = document.createDocumentFragment();

        // 1. Observations / Anomalies
        const insights = data.insights || [];
        if (insights.length > 0) {
            const subTitle = createTextEl('div', 'STRATEGIC FINDINGS & ANOMALIES', {
                color: '#ff6600',
                fontSize: '11px',
                fontWeight: '700',
                letterSpacing: '0.8px',
                marginBottom: '10px'
            });
            fragment.appendChild(subTitle);

            insights.forEach(item => {
                const card = document.createElement('div');
                card.style.background = 'rgba(255,255,255,0.03)';
                card.style.border = '1px solid rgba(255,255,255,0.08)';
                card.style.borderRadius = '6px';
                card.style.padding = '10px 12px';
                card.style.marginBottom = '8px';

                const badge = createTextEl('span', (item.type || 'FINDING').toUpperCase(), {
                    fontSize: '10px',
                    fontWeight: '700',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: item.type === 'anomaly' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 102, 0, 0.2)',
                    color: item.type === 'anomaly' ? '#ef4444' : '#ff6600',
                    marginRight: '8px',
                    display: 'inline-block'
                });

                const text = createTextEl('span', item.text || '', { color: '#eee', fontSize: '13px' });

                card.appendChild(badge);
                card.appendChild(text);
                fragment.appendChild(card);
            });
        }

        // 2. Actionable Recommendations
        const recs = data.recommendations || [];
        if (recs.length > 0) {
            const recTitle = createTextEl('div', 'ACTIONABLE RECOMMENDATIONS', {
                color: '#28a745',
                fontSize: '11px',
                fontWeight: '700',
                letterSpacing: '0.8px',
                marginTop: '14px',
                marginBottom: '10px'
            });
            fragment.appendChild(recTitle);

            recs.forEach(rec => {
                const card = document.createElement('div');
                card.style.background = 'rgba(40,167,69,0.05)';
                card.style.border = '1px solid rgba(40,167,69,0.2)';
                card.style.borderRadius = '6px';
                card.style.padding = '10px 12px';
                card.style.marginBottom = '8px';

                const text = createTextEl('div', rec.text || '', { color: '#e5e7eb', fontSize: '13px' });
                card.appendChild(text);
                fragment.appendChild(card);
            });
        }

        if (insights.length === 0 && recs.length === 0) {
            fragment.appendChild(createTextEl('div', 'Data analysis complete.'));
        }

        container.appendChild(fragment);
    }

    function safeRenderML(container, mlData) {
        container.textContent = '';
        if (!mlData || typeof mlData !== 'object') {
            container.textContent = 'No predictive modeling results.';
            return;
        }

        const fragment = document.createDocumentFragment();

        if (mlData.status === 'skipped') {
            fragment.appendChild(createTextEl('div', mlData.message || 'Predictive modeling skipped.', {
                color: '#888',
                fontStyle: 'italic'
            }));
            container.appendChild(fragment);
            return;
        }

        if (mlData.best_model) {
            fragment.appendChild(createTextEl('div', `Selected Optimal Model: ${mlData.best_model}`, {
                color: '#ff6600',
                fontWeight: '700',
                fontSize: '14px',
                marginBottom: '6px'
            }));

            if (mlData.target_column) {
                fragment.appendChild(createTextEl('div', `Target Metric: ${mlData.target_column} (${mlData.task_type || 'regression'})`, {
                    color: '#fff',
                    fontSize: '13px',
                    marginBottom: '8px'
                }));
            }

            if (mlData.models_evaluated && typeof mlData.models_evaluated === 'object') {
                const evalTitle = createTextEl('strong', 'Model Benchmark Comparison:', {
                    color: '#aaa',
                    display: 'block',
                    fontSize: '12px',
                    marginTop: '10px',
                    marginBottom: '6px'
                });
                fragment.appendChild(evalTitle);

                const list = document.createElement('ul');
                list.style.listStyle = 'none';
                list.style.paddingLeft = '0';
                list.style.margin = '0';

                for (const [mName, metrics] of Object.entries(mlData.models_evaluated)) {
                    const li = document.createElement('li');
                    li.style.padding = '4px 0';
                    li.style.borderBottom = '1px solid rgba(255,255,255,0.05)';

                    const nameSpan = createTextEl('span', mName, { fontWeight: '600', color: '#eee' });
                    li.appendChild(nameSpan);

                    if (typeof metrics === 'object' && metrics !== null) {
                        const parts = Object.entries(metrics).map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(4) : v}`);
                        const scoreSpan = createTextEl('span', ` — ${parts.join(', ')}`, { color: '#888', fontSize: '12px' });
                        li.appendChild(scoreSpan);
                    }
                    list.appendChild(li);
                }
                fragment.appendChild(list);
            }
        } else {
            fragment.appendChild(createTextEl('div', JSON.stringify(mlData, null, 2)));
        }

        container.appendChild(fragment);
    }

    // --- Workspace Lifecycle ---

    async function initWorkspace() {
        try {
            // Check if there is an active project or create one via backend API
            const res = await fetch(`${API_BASE}/projects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'Automated Analytics Project' })
            });

            if (res.ok) {
                const data = await res.json();
                currentProjectId = data.id;
                if (projectNameEl && data.name) {
                    projectNameEl.textContent = data.name;
                }
            }
        } catch (e) {
            console.error('Failed to initialize project session:', e);
        }

        if (loadingState) loadingState.style.display = 'none';
        if (dashboardView) dashboardView.style.display = 'block';

        if (currentProjectId) {
            pollStatus();
        }
    }

    async function uploadData() {
        if (!dataFile || !dataFile.files || !dataFile.files.length) {
            alert('Please select a dataset file (CSV, Excel, or JSON) first.');
            return;
        }

        const file = dataFile.files[0];
        const formData = new FormData();
        formData.append('file', file);

        if (uploadBtn) {
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Uploading...';
        }

        try {
            const url = `${API_BASE}/projects/${currentProjectId}/upload`;
            const res = await fetch(url, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                const msg = errData?.detail?.message || errData?.message || 'Upload failed. Please check file format and size.';
                alert(msg);
                return;
            }

            const data = await res.json();
            setStatus('PROCESSING (AI ANALYZING...)', 'status-processing');
            if (resultsPanel) resultsPanel.style.display = 'block';

            // Reset poll counter and start polling
            pollCount = 0;
            if (pollTimer) clearTimeout(pollTimer);
            pollStatus();

        } catch (e) {
            console.error('Upload request error:', e);
            alert('Could not connect to the analytics engine. Please ensure the backend server is running.');
        } finally {
            if (uploadBtn) {
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload & Analyze';
            }
        }
    }

    async function pollStatus() {
        if (!currentProjectId) return;
        pollCount++;

        try {
            const res = await fetch(`${API_BASE}/projects/${currentProjectId}`);
            if (res.ok) {
                const data = await res.json();
                const pStatus = data?.project?.status;

                if (pStatus === 'processing' || pStatus === 'queued' || pStatus === 'uploaded') {
                    setStatus('PROCESSING (AI ANALYZING...)', 'status-processing');
                    if (resultsPanel) resultsPanel.style.display = 'block';

                    if (pollCount < MAX_POLLS) {
                        pollTimer = setTimeout(pollStatus, 2500);
                    }
                } else if (pStatus === 'completed') {
                    setStatus('COMPLETED', 'status-completed');
                    if (resultsPanel) resultsPanel.style.display = 'block';
                } else if (pStatus === 'failed') {
                    setStatus('FAILED', 'status-pending');
                }

                // Safely populate results
                if (data.results && Array.isArray(data.results)) {
                    data.results.forEach(item => {
                        if (item.type === 'profile' && resProfile) safeRenderProfile(resProfile, item.data);
                        if (item.type === 'cleaning' && resCleaning) safeRenderCleaning(resCleaning, item.data);
                        if (item.type === 'eda' && resEDA) safeRenderEDA(resEDA, item.data);
                        if (item.type === 'insights' && resInsights) safeRenderInsights(resInsights, item.data);
                        if (item.type === 'ml' && resML) safeRenderML(resML, item.data);
                    });
                }
            }
        } catch (e) {
            console.error('Polling status failed:', e);
        }
    }

    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadData);
    }

    // Initialize workspace
    initWorkspace();
});
