// Euno - Authentication & Settings

// ============== Authentication ==============

async function checkAuth() {
    try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Auth check failed:', error);
        return { authenticated: true, password_required: false };
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');
    const error = document.getElementById('login-error');

    btn.disabled = true;
    btn.textContent = 'Signing in...';
    error.textContent = '';

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });

        if (response.ok) {
            const loginOverlay = document.getElementById('login-overlay');
            const appContainer = document.getElementById('app-container');

            // Crossfade: login out, app in
            // Trigger reflow to ensure transitions work
            appContainer.offsetHeight;

            loginOverlay.classList.remove('visible');
            appContainer.classList.add('visible');

            // Clean up login overlay after fade
            setTimeout(() => {
                loginOverlay.classList.add('hidden');
            }, 400);

            initApp();
        } else {
            const data = await response.json();
            error.textContent = data.detail || 'Invalid password';
        }
    } catch (err) {
        error.textContent = 'Connection error. Please try again.';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (err) {
        console.error('Logout failed:', err);
    }
    window.location.reload();
}

function initApp() {
    // Reset scroll positions to top (mobile browsers try to restore previous scroll)
    resetScrollPositions();

    // Initialize with default tab (focus)
    switchTab(activeTab);

    // Load daily quote for Focus tab
    loadDailyQuote();

    // Load quote and show empty state for Chat tab
    loadChatQuote();
    showChatEmptyState();

    // Initialize swipe gesture handlers
    initSwipeHandlers();

    // Connect SSE
    connectSSE();

    // Load tasks data for badge
    loadTasksData();

    // Load settings data (needed for voice button visibility)
    loadSettingsData();
}

function resetScrollPositions() {
    // Scroll window to top
    window.scrollTo(0, 0);

    // Scroll all tab panes to top
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.scrollTop = 0;
    });

    // Scroll chat messages to top
    const chatMessages = document.getElementById('inline-messages');
    if (chatMessages) chatMessages.scrollTop = 0;
}

// ============== Settings ==============

let costsData = null;

async function loadSettingsData() {
    try {
        const response = await fetch('/api/settings');
        settingsData = await response.json();
        renderSettings();
        loadCostsData();
        loadRateLimitingData();

        // Update voice button visibility based on provider capabilities
        if (typeof updateVoiceButtonVisibility === 'function') {
            updateVoiceButtonVisibility();
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function loadCostsData() {
    try {
        const response = await fetch('/api/costs');
        costsData = await response.json();
        renderCosts();
    } catch (error) {
        console.error('Failed to load costs:', error);
    }
}

function renderCostRow(elementId, periodData) {
    const row = document.getElementById(elementId);
    if (!row || !periodData) return;

    const amountEl = row.querySelector('.costs-amount');
    const callsEl = row.querySelector('.costs-calls');

    const cost = periodData.cost || 0;
    const calls = periodData.calls || 0;

    amountEl.textContent = `$${cost.toFixed(2)}`;
    callsEl.textContent = `${calls.toLocaleString()} call${calls !== 1 ? 's' : ''}`;
}

function renderCosts() {
    if (!costsData) return;

    // Render all three periods
    renderCostRow('costs-session', costsData.session);
    renderCostRow('costs-seven-days', costsData.seven_days);
    renderCostRow('costs-month', costsData.month);

    // Show budget info if set
    const budgetEl = document.getElementById('costs-budget');
    if (costsData.budget) {
        const remaining = costsData.budget - (costsData.session?.cost || 0);
        budgetEl.textContent = `Budget: $${costsData.budget.toFixed(2)} ($${remaining.toFixed(2)} remaining)`;
    } else {
        budgetEl.textContent = '';
    }
}

function renderSettings() {
    if (!settingsData) return;

    // Populate and set provider dropdown
    const providerSelect = document.getElementById('default-provider');
    if (providerSelect && settingsData.llm?.providers) {
        // Build options from API data
        providerSelect.innerHTML = '';
        for (const [id, config] of Object.entries(settingsData.llm.providers)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = config.display_name || id;
            providerSelect.appendChild(option);
        }
        // Set current value
        providerSelect.value = settingsData.llm.provider || 'anthropic';
    }

    // Set budget limit
    const budgetInput = document.getElementById('budget-limit');
    if (budgetInput && settingsData.llm?.budget_limit !== undefined) {
        budgetInput.value = settingsData.llm.budget_limit || '';
    }

    // Render schedules
    renderSchedules();
}

function renderSchedules() {
    const container = document.getElementById('schedules-table');
    if (!container) return;

    if (!settingsData?.schedules || Object.keys(settingsData.schedules).length === 0) {
        container.innerHTML = '<div class="schedule-row"><span class="schedule-name" style="color: var(--color-text-muted);">No schedules configured</span></div>';
        return;
    }

    const schedules = settingsData.schedules;
    container.innerHTML = '';

    for (const [name, time] of Object.entries(schedules)) {
        // Skip special schedule types like 'every_hour'
        if (time === 'every_hour') continue;

        const row = document.createElement('div');
        row.className = 'schedule-row';
        row.innerHTML = `
            <span class="schedule-name">${name}</span>
            <input type="time" class="schedule-time" value="${time}" data-schedule="${name}" onchange="handleScheduleChange('${name}', this.value)">
        `;
        container.appendChild(row);
    }

    // Show message if all schedules were filtered out
    if (container.children.length === 0) {
        container.innerHTML = '<div class="schedule-row"><span class="schedule-name" style="color: var(--color-text-muted);">No editable schedules</span></div>';
    }
}

async function handleBudgetChange() {
    const budgetInput = document.getElementById('budget-limit');
    const messageEl = document.getElementById('ai-message');
    const value = budgetInput.value ? parseFloat(budgetInput.value) : null;

    try {
        const response = await fetch('/api/settings/llm', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budget_limit: value })
        });

        if (response.ok) {
            messageEl.textContent = 'Budget limit saved';
            messageEl.className = 'settings-message success';
            // Reload to update costs display
            await loadCostsData();
        } else {
            const data = await response.json();
            messageEl.textContent = data.detail || 'Failed to save';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        messageEl.textContent = 'Connection error';
        messageEl.className = 'settings-message error';
    }

    setTimeout(() => { messageEl.textContent = ''; }, 2000);
}

async function handleScheduleChange(name, value) {
    const messageEl = document.getElementById('ai-message');

    try {
        const response = await fetch('/api/settings/schedules', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [name]: value })
        });

        if (response.ok) {
            messageEl.textContent = `Schedule "${name}" updated`;
            messageEl.className = 'settings-message success';
        } else {
            const data = await response.json();
            messageEl.textContent = data.detail || 'Failed to save';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        messageEl.textContent = 'Connection error';
        messageEl.className = 'settings-message error';
    }

    setTimeout(() => { messageEl.textContent = ''; }, 2000);
}

async function handleProviderChange() {
    const providerSelect = document.getElementById('default-provider');
    const messageEl = document.getElementById('ai-message');
    const newProvider = providerSelect.value;

    try {
        const response = await fetch('/api/settings/llm', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ default_provider: newProvider })
        });

        if (response.ok) {
            messageEl.textContent = 'Provider changed';
            messageEl.className = 'settings-message success';

            // Reload settings to get updated speech capabilities
            await loadSettingsData();
        } else {
            const data = await response.json();
            messageEl.textContent = data.detail || 'Failed to save';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        messageEl.textContent = 'Connection error';
        messageEl.className = 'settings-message error';
    }

    setTimeout(() => { messageEl.textContent = ''; }, 2000);
}

async function handleChangePassword(event) {
    event.preventDefault();

    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const messageEl = document.getElementById('password-message');

    // Validate
    if (!currentPassword || !newPassword || !confirmPassword) {
        messageEl.textContent = 'All fields are required';
        messageEl.className = 'settings-message error';
        return;
    }

    if (newPassword !== confirmPassword) {
        messageEl.textContent = 'New passwords do not match';
        messageEl.className = 'settings-message error';
        return;
    }

    if (newPassword.length < 4) {
        messageEl.textContent = 'Password must be at least 4 characters';
        messageEl.className = 'settings-message error';
        return;
    }

    try {
        const response = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        if (response.ok) {
            messageEl.textContent = 'Password changed successfully';
            messageEl.className = 'settings-message success';
            // Clear form
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            const data = await response.json();
            messageEl.textContent = data.detail || 'Failed to change password';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        messageEl.textContent = 'Connection error';
        messageEl.className = 'settings-message error';
    }

    setTimeout(() => { messageEl.textContent = ''; }, 3000);
}

// ============== Rate Limiting ==============

let rateLimitData = null;

async function loadRateLimitingData() {
    try {
        const [statusRes, configRes] = await Promise.all([
            fetch('/api/rate-limiting/status'),
            fetch('/api/rate-limiting/config')
        ]);

        if (statusRes.ok && configRes.ok) {
            const status = await statusRes.json();
            const config = await configRes.json();
            rateLimitData = { status, config };
            renderRateLimitingSettings();
        }
    } catch (error) {
        console.error('Failed to load rate limiting data:', error);
    }
}

function renderRateLimitingSettings() {
    if (!rateLimitData) return;

    const { status, config } = rateLimitData;

    // Update status display
    const callsInWindow = status.rolling_window?.current_calls || 0;
    const maxCalls = status.rolling_window?.max_calls || 30;
    const pausedAgents = status.paused_agents || [];

    document.getElementById('rl-calls-in-window').textContent = callsInWindow;
    document.getElementById('rl-window-limit').textContent = `of ${maxCalls} max`;
    document.getElementById('rl-paused-count').textContent = pausedAgents.length;
    document.getElementById('rl-paused-list').textContent = pausedAgents.length > 0
        ? pausedAgents.join(', ')
        : 'none';

    // Update form fields
    document.getElementById('rl-enabled').checked = config.enabled !== false;
    document.getElementById('rl-max-calls').value = config.rolling_window?.max_calls || 30;
    document.getElementById('rl-window-seconds').value = config.rolling_window?.window_seconds || 60;

    document.getElementById('rl-throttle-enabled').checked = config.throttle?.enabled || false;
    document.getElementById('rl-throttle-rate').value = config.throttle?.calls_per_minute || 10;

    document.getElementById('rl-runaway-enabled').checked = config.runaway_detection?.enabled !== false;
    document.getElementById('rl-spike-multiplier').value = config.runaway_detection?.spike_multiplier || 5;
}

async function handleRateLimitChange() {
    const messageEl = document.getElementById('rate-limit-message');

    const config = {
        enabled: document.getElementById('rl-enabled').checked,
        rolling_window: {
            max_calls: parseInt(document.getElementById('rl-max-calls').value) || 30,
            window_seconds: parseInt(document.getElementById('rl-window-seconds').value) || 60
        },
        throttle: {
            enabled: document.getElementById('rl-throttle-enabled').checked,
            calls_per_minute: parseInt(document.getElementById('rl-throttle-rate').value) || 10
        },
        runaway_detection: {
            enabled: document.getElementById('rl-runaway-enabled').checked,
            spike_multiplier: parseFloat(document.getElementById('rl-spike-multiplier').value) || 5
        }
    };

    try {
        const response = await fetch('/api/rate-limiting/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            messageEl.textContent = 'Settings saved';
            messageEl.className = 'settings-message success';
            // Reload to update status display
            await loadRateLimitingData();
        } else {
            const data = await response.json();
            messageEl.textContent = data.error || 'Failed to save';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        messageEl.textContent = 'Connection error';
        messageEl.className = 'settings-message error';
    }

    setTimeout(() => { messageEl.textContent = ''; }, 2000);
}

async function resumePausedAgent(agentId) {
    try {
        const response = await fetch(`/api/rate-limiting/agents/${agentId}/resume`, {
            method: 'POST'
        });

        if (response.ok) {
            await loadRateLimitingData();
        }
    } catch (error) {
        console.error('Failed to resume agent:', error);
    }
}
