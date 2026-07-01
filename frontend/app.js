// Frontend JavaScript for MindTherapy Check-in Journal
// Author: Antigravity Agent
// This script handles UI interactions, API communication, and dynamic updates.

(() => {
    // ----------------------------
    // Utility Functions
    // ----------------------------
    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => Array.from(document.querySelectorAll(selector));
    const createElement = (tag, options = {}) => {
        const el = document.createElement(tag);
        Object.entries(options).forEach(([key, value]) => {
            if (key === 'class') el.className = value;
            else if (key === 'html') el.innerHTML = value;
            else if (key === 'text') el.textContent = value;
            else if (key.startsWith('data-')) el.dataset[key.slice(5)] = value;
            else el.setAttribute(key, value);
        });
        return el;
    };
    const formatDate = (iso) => {
        const d = new Date(iso);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    };
    const generateUserId = () => {
        // Persistent UUID stored in localStorage for demo purposes
        let uid = localStorage.getItem('mindtherapy_user_id');
        if (!uid) {
            uid = crypto.randomUUID();
            localStorage.setItem('mindtherapy_user_id', uid);
        }
        return uid;
    };
    const USER_ID = generateUserId();

    // ----------------------------
    // State Management
    // ----------------------------
    const state = {
        history: [], // Filled from API on load
        chart: null,
        chartData: {
            labels: [],
            scores: []
        }
    };

    // ----------------------------
    // API Helpers
    // ----------------------------
    const api = {
        async postCheckin(text) {
            const resp = await fetch('/api/checkin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: USER_ID, text })
            });
            if (!resp.ok) throw new Error('Check-in request failed');
            return resp.json();
        },
        async getHistory() {
            const resp = await fetch(`/api/history?user_id=${encodeURIComponent(USER_ID)}`);
            if (!resp.ok) throw new Error('Failed to fetch history');
            return resp.json();
        },
        async runEvaluation() {
            const resp = await fetch('/api/eval/run', { method: 'POST' });
            if (!resp.ok) throw new Error('Failed to run evaluation');
            return resp.json();
        },
        async getEvaluationResults() {
            const resp = await fetch('/api/eval/results');
            if (!resp.ok) throw new Error('Failed to fetch evaluation results');
            return resp.json();
        }
    };

    // ----------------------------
    // UI Rendering Functions
    // ----------------------------
    const renderMessage = (content, type = 'system') => {
        const msgEl = createElement('div', { class: `message ${type}-message` });
        const inner = createElement('div', { class: 'message-content', text: content });
        msgEl.appendChild(inner);
        $('#chat-messages').appendChild(msgEl);
        // Auto-scroll
        $('#chat-messages').scrollTop = $('#chat-messages').scrollHeight;
    };

    const renderUserMessage = (text) => {
        const msgEl = createElement('div', { class: 'message user-message' });
        const inner = createElement('div', { class: 'message-content', text });
        msgEl.appendChild(inner);
        $('#chat-messages').appendChild(msgEl);
        $('#chat-messages').scrollTop = $('#chat-messages').scrollHeight;
    };

    const renderResources = (resources) => {
        // Build a stylized resource list inside a dedicated message card
        const container = createElement('div', { class: 'resource-list-container' });
        resources.forEach((res) => {
            const item = createElement('div', { class: 'resource-item' });
            const info = createElement('div', { class: 'resource-info' });
            const title = createElement('h4', { text: res.name || 'Resource' });
            const desc = createElement('p', { text: res.description || '' });
            info.appendChild(title);
            if (res.description) info.appendChild(desc);
            const actions = createElement('div', { class: 'resource-actions' });
            if (res.phone) {
                const tel = createElement('a', { class: 'btn-resource primary', href: `tel:${res.phone}`, text: `Call ${res.phone}` });
                actions.appendChild(tel);
            }
            if (res.url) {
                const link = createElement('a', { class: 'btn-resource secondary', href: res.url, target: '_blank', rel: 'noopener', text: 'Open Link' });
                actions.appendChild(link);
            }
            if (res.text) {
                const sms = createElement('a', { class: 'btn-resource secondary', href: `sms:${res.text}`, text: 'Send Text' });
                actions.appendChild(sms);
            }
            item.appendChild(info);
            if (actions.childElementCount) item.appendChild(actions);
            container.appendChild(item);
        });
        const msg = createElement('div', { class: 'message system-message' });
        const inner = createElement('div', { class: 'message-content' });
        inner.appendChild(container);
        msg.appendChild(inner);
        $('#chat-messages').appendChild(msg);
        $('#chat-messages').scrollTop = $('#chat-messages').scrollHeight;
    };

    const updateQuickMood = (trend, description) => {
        const el = $('#quick-mood-trend');
        const descEl = $('#quick-mood-desc');
        el.textContent = trend.charAt(0).toUpperCase() + trend.slice(1);
        // Color badge based on trend
        el.className = '';
        if (trend === 'routine') el.classList.add('badge', 'routine');
        else if (trend === 'elevated') el.classList.add('badge', 'elevated');
        else if (trend === 'crisis') el.classList.add('badge', 'crisis');
        descEl.textContent = description;
    };

    const updateQuickThemes = (themes) => {
        const container = $('#quick-themes');
        container.innerHTML = '';
        if (!themes || themes.length === 0) {
            container.innerHTML = '<div class="empty-state">No themes detected yet.</div>';
            return;
        }
        themes.forEach((t) => {
            const tag = createElement('span', { class: 'theme-tag', text: t });
            container.appendChild(tag);
        });
    };

    const addHistoryItem = (entry) => {
        const item = createElement('div', { class: 'history-item' });
        const header = createElement('div', { class: 'history-item-header' });
        const date = createElement('span', { class: 'history-date', text: formatDate(entry.timestamp) });
        const moodBadge = createElement('span', { class: `history-mood badge ${entry.mood_score <= 4 ? 'crisis' : entry.mood_score <= 6 ? 'elevated' : 'routine'}`, text: `Mood ${entry.mood_score}` });
        header.appendChild(date);
        header.appendChild(moodBadge);
        const txt = createElement('p', { class: 'history-text', text: entry.text });
        item.appendChild(header);
        item.appendChild(txt);
        $('#history-list').appendChild(item);
    };

    const refreshHistoryUI = () => {
        $('#history-list').innerHTML = '';
        if (state.history.length === 0) {
            $('#history-list').innerHTML = '<div class="empty-state">No entries logged yet.</div>';
            return;
        }
        state.history.forEach(addHistoryItem);
    };

    const initChart = () => {
        const ctx = $('#mood-chart').getContext('2d');
        state.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: state.chartData.labels,
                datasets: [{
                    label: 'Mood Score (1‑10)',
                    data: state.chartData.scores,
                    borderColor: 'var(--color-primary)',
                    backgroundColor: 'rgba(99,102,241,0.2)',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 1,
                        max: 10,
                        ticks: { stepSize: 1, color: 'var(--text-primary)' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    x: {
                        ticks: { color: 'var(--text-primary)' },
                        grid: { display: false }
                    }
                },
                plugins: { legend: { display: false } }
            }
        });
    };

    const updateChart = () => {
        if (!state.chart) return;
        state.chart.data.labels = state.chartData.labels;
        state.chart.data.datasets[0].data = state.chartData.scores;
        state.chart.update();
    };

    // ----------------------------
    // Debug Drawer Updates
    // ----------------------------
    const updateDebugDrawer = (payload) => {
        // Classifier result
        const classRes = payload.classifier_result;
        $('#debug-class-tier').textContent = classRes.tier;
        $('#debug-class-conf').textContent = (classRes.confidence * 100).toFixed(1) + '%';
        $('#debug-class-reason').textContent = classRes.reasoning;
        // Memory trend
        const trendRes = payload.trend_result;
        $('#debug-mem-mood').textContent = payload.entry_analysis.mood_score;
        $('#debug-mem-trend').textContent = trendRes.trend;
        $('#debug-mem-reason').textContent = trendRes.reason;
        // Router decisions
        $('#debug-router-route').textContent = payload.route;
        $('#debug-router-action').textContent = payload.response;
        const themesContainer = $('#debug-router-themes');
        themesContainer.innerHTML = '';
        const themes = payload.entry_analysis.themes;
        if (themes && themes.length) {
            themes.forEach(t => {
                const tag = createElement('span', { class: 'theme-tag', text: t });
                themesContainer.appendChild(tag);
            });
        } else {
            themesContainer.innerHTML = '<span class="empty-state">None</span>';
        }
    };

    // ----------------------------
    // Evaluation UI Functions
    // ----------------------------
    const renderEvalMetrics = (summary) => {
        $('#eval-accuracy').textContent = (summary.overall_accuracy * 100).toFixed(2) + '%';
        const crisisRecall = summary.metrics.crisis.recall;
        $('#eval-crisis-recall').textContent = (crisisRecall * 100).toFixed(2) + '%';
        $('#eval-routine-precision').textContent = (summary.metrics.routine.precision * 100).toFixed(2) + '%';
        $('#eval-total-cases').textContent = summary.total_cases;
        $('#eval-time-taken').textContent = `Completed in ${summary.duration_seconds}s`;
        // Fill confusion matrix cells
        const matrix = summary.confusion_matrix;
        const mapCell = (exp, act) => {
            const key = `m-${exp[0]}${act[0]}`; // e.g., m-rr
            const el = $(`#${key}`);
            const count = matrix[exp] && matrix[exp][act] ? matrix[exp][act] : 0;
            el.textContent = count;
            // Apply simple heat coloration based on count magnitude
            if (count === 0) el.className = 'cell-zero';
            else if (count < 3) el.className = 'cell-low';
            else if (count < 6) el.className = 'cell-medium';
            else el.className = 'cell-high';
        };
        ['routine', 'elevated', 'crisis'].forEach(e => {
            ['routine', 'elevated', 'crisis'].forEach(a => mapCell(e, a));
        });
        // Populate test cases table
        const tbody = $('#eval-cases-body');
        tbody.innerHTML = '';
        summary.results.forEach((r, idx) => {
            const tr = document.createElement('tr');
            const cells = [
                idx + 1,
                r.text.length > 60 ? r.text.slice(0, 57) + '...' : r.text,
                r.expected,
                r.actual,
                r.correct ? '<span class="badge pass">PASS</span>' : '<span class="badge fail">FAIL</span>'
            ];
            cells.forEach(c => {
                const td = document.createElement('td');
                td.innerHTML = c;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    };

    // ----------------------------
    // Event Handlers
    // ----------------------------
    const handleFormSubmit = async (e) => {
        e.preventDefault();
        const input = $('#journal-input');
        const text = input.value.trim();
        if (!text) return;
        // UI: show user message
        renderUserMessage(text);
        input.value = '';
        // Show routing status bar
        $('#routing-status-bar').classList.remove('hidden');
        try {
            const payload = await api.postCheckin(text);
            // Hide status bar
            $('#routing-status-bar').classList.add('hidden');
            // Render agent response based on route
            const { route, response, resources } = payload;
            // Update quick summary cards
            updateQuickMood(payload.trend_result.trend, payload.trend_result.reason);
            updateQuickThemes(payload.entry_analysis.themes);
            // Add entry to history state and UI
            state.history.push({
                timestamp: new Date().toISOString(),
                text,
                mood_score: payload.entry_analysis.mood_score,
                themes: payload.entry_analysis.themes
            });
            refreshHistoryUI();
            // Update chart data
            state.chartData.labels.push(formatDate(new Date().toISOString()));
            state.chartData.scores.push(payload.entry_analysis.mood_score);
            if (state.chartData.labels.length > 30) {
                state.chartData.labels.shift();
                state.chartData.scores.shift();
            }
            updateChart();
            // Render response based on routing
            if (route === 'crisis') {
                // Red background card for crisis
                renderMessage(response, 'crisis');
                renderResources(resources);
            } else if (route === 'elevated') {
                renderMessage(response, 'elevated');
                renderResources(resources);
            } else {
                renderMessage(response, 'system');
            }
            // Update debug drawer
            updateDebugDrawer(payload);
        } catch (err) {
            console.error(err);
            $('#routing-status-bar').classList.add('hidden');
            renderMessage('Oops! Something went wrong while processing your entry.', 'system');
        }
    };

    const handleNavClick = (e) => {
        const targetId = e.currentTarget.id;
        // Update active nav
        $$('.nav-item').forEach(btn => btn.classList.toggle('active', btn.id === targetId));
        // Show corresponding section
        $$('.content-section').forEach(sec => {
            const show = sec.id === `section-${targetId.split('-')[1]}`;
            sec.classList.toggle('active', show);
        });
    };

    const handleEvalRun = async () => {
        // Disable button while running
        const btn = $('#btn-run-eval');
        btn.disabled = true;
        btn.textContent = 'Running...';
        try {
            const summary = await api.runEvaluation();
            renderEvalMetrics(summary);
        } catch (err) {
            console.error(err);
            alert('Failed to execute evaluation suite. Check console for details.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="play"></i> <span>Execute Test Suite</span>';
        }
    };

    const toggleDebugDrawer = () => {
        const drawer = $('#debug-drawer');
        drawer.classList.toggle('open');
        // Rotate chevron handled via CSS class
    };

    // -------------------------------------------------
    // Initialization
    // -------------------------------------------------
    const init = async () => {
        // Activate Lucide icons
        lucide.createIcons();
        // Navigation wiring
        $$('#nav-journal, #nav-trends, #nav-evals').forEach(btn => btn.addEventListener('click', handleNavClick));
        // Form handling
        $('#journal-form').addEventListener('submit', handleFormSubmit);
        // Debug drawer toggle
        $('#debug-drawer-toggle').addEventListener('click', toggleDebugDrawer);
        // Eval run button
        $('#btn-run-eval').addEventListener('click', handleEvalRun);
        // Load initial history from backend
        try {
            const data = await api.getHistory();
            state.history = data.history || [];
            // Populate quick cards based on latest entry if exists
            if (state.history.length) {
                const last = state.history[state.history.length - 1];
                // We'll fetch the latest trend via a temporary re‑run (or simply use stored entry data)
                // Since the backend already stored mood_score, we can set quick mood & chart directly.
                updateQuickMood('routine', 'Showing latest mood from history.'); // placeholder; actual trend will be re‑computed later.
                updateQuickThemes(last.themes);
                // Chart data preparation
                state.chartData.labels = state.history.map(e => formatDate(e.timestamp));
                state.chartData.scores = state.history.map(e => e.mood_score);
            }
            refreshHistoryUI();
            initChart();
            updateChart();
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    };

    // Run init on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
