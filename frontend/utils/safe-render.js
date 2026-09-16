/**
 * Clarivens Safe DOM Rendering Utilities.
 * Guarantees zero XSS injection by exclusively using textContent and DOM node construction.
 * Never uses innerHTML with untrusted server or user data.
 */

export function escapeHtml(str) {
    if (typeof str !== 'string') return String(str ?? '');
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export function createTextElement(tag, text, className = null, styles = null) {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    if (styles && typeof styles === 'object') {
        Object.assign(el.style, styles);
    }
    return el;
}

export function renderProfile(container, profile) {
    container.textContent = '';
    if (!profile || typeof profile !== 'object') {
        container.textContent = 'No profiling data available.';
        return;
    }

    const fragment = document.createDocumentFragment();

    // Summary header
    const statsDiv = document.createElement('div');
    statsDiv.style.marginBottom = '12px';
    statsDiv.style.color = '#fff';

    const totalCols = profile.columns ? profile.columns.length : 0;
    const numCols = profile.numeric_columns ? profile.numeric_columns.length : 0;
    const catCols = profile.categorical_columns ? profile.categorical_columns.length : 0;

    statsDiv.appendChild(createTextElement('div', `Total Columns: ${totalCols} (${numCols} numeric, ${catCols} categorical)`));
    fragment.appendChild(statsDiv);

    // Inferred types list
    if (profile.inferred_types && typeof profile.inferred_types === 'object') {
        const title = createTextElement('strong', 'Column Type Mapping:', null, { color: '#ff6600', display: 'block', marginBottom: '6px' });
        fragment.appendChild(title);

        const list = document.createElement('ul');
        list.style.listStyle = 'none';
        list.style.paddingLeft = '0';
        list.style.margin = '0 0 10px 0';

        for (const [col, typeStr] of Object.entries(profile.inferred_types)) {
            const li = document.createElement('li');
            li.style.padding = '3px 0';

            const colSpan = createTextElement('span', col, null, { color: '#fff', fontWeight: '600' });
            const sepSpan = createTextElement('span', ': ');
            const typeSpan = createTextElement('span', String(typeStr), null, { color: '#888' });

            li.appendChild(colSpan);
            li.appendChild(sepSpan);
            li.appendChild(typeSpan);
            list.appendChild(li);
        }
        fragment.appendChild(list);
    }

    container.appendChild(fragment);
}

export function renderInsights(container, data) {
    container.textContent = '';
    if (!data) {
        container.textContent = 'No AI insights available.';
        return;
    }

    const fragment = document.createDocumentFragment();

    // Insights List
    const insights = data.insights || [];
    if (insights.length > 0) {
        const h5 = createTextElement('div', 'KEY OBSERVATIONS & ANOMALIES', null, {
            color: '#ff6600',
            fontSize: '11px',
            fontWeight: '700',
            letterSpacing: '0.8px',
            marginBottom: '10px'
        });
        fragment.appendChild(h5);

        insights.forEach(item => {
            const card = document.createElement('div');
            card.style.background = 'rgba(255,255,255,0.03)';
            card.style.border = '1px solid rgba(255,255,255,0.08)';
            card.style.borderRadius = '6px';
            card.style.padding = '10px 12px';
            card.style.marginBottom = '8px';

            const badge = createTextElement('span', (item.type || 'INSIGHT').toUpperCase(), null, {
                fontSize: '10px',
                fontWeight: '700',
                padding: '2px 6px',
                borderRadius: '4px',
                background: item.type === 'anomaly' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 102, 0, 0.2)',
                color: item.type === 'anomaly' ? '#ef4444' : '#ff6600',
                marginRight: '8px',
                display: 'inline-block'
            });

            const text = createTextElement('span', item.text || '', null, { color: '#eee', fontSize: '13px' });

            card.appendChild(badge);
            card.appendChild(text);
            fragment.appendChild(card);
        });
    }

    // Recommendations List
    const recs = data.recommendations || [];
    if (recs.length > 0) {
        const recHeader = createTextElement('div', 'STRATEGIC RECOMMENDATIONS', null, {
            color: '#28a745',
            fontSize: '11px',
            fontWeight: '700',
            letterSpacing: '0.8px',
            marginTop: '16px',
            marginBottom: '10px'
        });
        fragment.appendChild(recHeader);

        recs.forEach(rec => {
            const card = document.createElement('div');
            card.style.background = 'rgba(40,167,69,0.05)';
            card.style.border = '1px solid rgba(40,167,69,0.2)';
            card.style.borderRadius = '6px';
            card.style.padding = '10px 12px';
            card.style.marginBottom = '8px';

            const text = createTextElement('div', rec.text || '', null, { color: '#e5e7eb', fontSize: '13px' });
            card.appendChild(text);
            fragment.appendChild(card);
        });
    }

    if (insights.length === 0 && recs.length === 0) {
        fragment.appendChild(createTextElement('div', 'AI analysis in progress or dataset structure pending.'));
    }

    container.appendChild(fragment);
}

export function renderML(container, mlData) {
    container.textContent = '';
    if (!mlData) {
        container.textContent = 'No predictive modeling results.';
        return;
    }

    const fragment = document.createDocumentFragment();

    if (mlData.status === 'skipped') {
        const msg = createTextElement('div', mlData.message || 'Predictive modeling skipped (insufficient numeric columns or sample size).', null, {
            color: '#888',
            fontStyle: 'italic'
        });
        fragment.appendChild(msg);
        container.appendChild(fragment);
        return;
    }

    if (mlData.best_model) {
        const header = createTextElement('div', `Best Model: ${mlData.best_model}`, null, {
            color: '#ff6600',
            fontWeight: '700',
            fontSize: '14px',
            marginBottom: '8px'
        });
        fragment.appendChild(header);

        if (mlData.target_column) {
            fragment.appendChild(createTextElement('div', `Target Variable: ${mlData.target_column}`, null, {
                color: '#fff',
                marginBottom: '6px'
            }));
        }

        if (mlData.task_type) {
            fragment.appendChild(createTextElement('div', `Task Type: ${mlData.task_type}`, null, {
                color: '#888',
                marginBottom: '10px'
            }));
        }

        if (mlData.models_evaluated && typeof mlData.models_evaluated === 'object') {
            const sub = createTextElement('strong', 'Models Evaluated:', null, { color: '#fff', display: 'block', marginTop: '10px', marginBottom: '6px' });
            fragment.appendChild(sub);

            const list = document.createElement('ul');
            list.style.listStyle = 'none';
            list.style.paddingLeft = '0';
            list.style.margin = '0';

            for (const [mName, metrics] of Object.entries(mlData.models_evaluated)) {
                const li = document.createElement('li');
                li.style.padding = '4px 0';
                li.style.borderBottom = '1px solid rgba(255,255,255,0.05)';

                const title = createTextElement('span', mName, null, { fontWeight: '600', color: '#eee' });
                li.appendChild(title);

                if (typeof metrics === 'object' && metrics !== null) {
                    const metricParts = Object.entries(metrics).map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(4) : v}`);
                    const valSpan = createTextElement('span', ` — ${metricParts.join(', ')}`, null, { color: '#888', fontSize: '12px' });
                    li.appendChild(valSpan);
                }
                list.appendChild(li);
            }
            fragment.appendChild(list);
        }
    } else {
        fragment.appendChild(createTextElement('div', JSON.stringify(mlData, null, 2)));
    }

    container.appendChild(fragment);
}
