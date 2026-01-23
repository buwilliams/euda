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

    // Set budget limit and period
    const budgetInput = document.getElementById('budget-limit');
    if (budgetInput && settingsData.llm?.budget?.limit !== undefined) {
        budgetInput.value = settingsData.llm.budget.limit || '';
    }
    const budgetPeriod = document.getElementById('budget-period');
    if (budgetPeriod && settingsData.llm?.budget?.period) {
        budgetPeriod.value = settingsData.llm.budget.period;
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
            body: JSON.stringify({ budget: { limit: value } })
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

async function handleBudgetPeriodChange() {
    const budgetPeriod = document.getElementById('budget-period');
    const messageEl = document.getElementById('ai-message');
    const value = budgetPeriod.value;

    try {
        const response = await fetch('/api/settings/llm', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budget: { period: value } })
        });

        if (response.ok) {
            messageEl.textContent = 'Budget period saved';
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

// ============== Fresh Start & Backups ==============

async function handleFreshStart() {
    const messageEl = document.getElementById('fresh-start-message');

    // Show processing state
    messageEl.textContent = 'Creating backup and resetting...';
    messageEl.className = 'settings-message';

    try {
        const response = await fetch('/api/fresh-start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            messageEl.textContent = 'Done! Backed up as ' + data.backup_name + '. Reloading...';
            messageEl.className = 'settings-message success';

            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            messageEl.textContent = data.error || 'Failed to reset data';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        console.error('Fresh start failed:', error);
        messageEl.textContent = 'Connection error. Please try again.';
        messageEl.className = 'settings-message error';
    }
}

let backupsData = null;

async function loadBackupsData() {
    const listEl = document.getElementById('backups-list');

    try {
        const response = await fetch('/api/backups');
        backupsData = await response.json();
        renderBackupsList();
    } catch (error) {
        console.error('Failed to load backups:', error);
        listEl.textContent = 'Failed to load backups';
    }
}

function renderBackupsList() {
    const listEl = document.getElementById('backups-list');

    if (!backupsData || backupsData.count === 0) {
        listEl.innerHTML = '<div class="focus-empty">No backups available</div>';
        return;
    }

    const backups = backupsData.backups;
    // Build HTML safely - backup names are filesystem-generated timestamps
    let html = '';
    for (const backup of backups) {
        const ts = backup.timestamp;
        const formatted = ts.length >= 15
            ? ts.slice(0,4) + '-' + ts.slice(4,6) + '-' + ts.slice(6,8) + ' ' + ts.slice(9,11) + ':' + ts.slice(11,13) + ':' + ts.slice(13,15)
            : ts;

        html += '<div class="backup-item">' +
            '<div class="backup-info">' +
            '<span class="backup-name">' + escapeHtml(backup.name) + '</span>' +
            '<span class="backup-date">' + formatted + '</span>' +
            '</div>' +
            '<div class="backup-actions">' +
            '<button class="backup-btn backup-restore" onclick="handleRestoreBackup(\'' + escapeHtml(backup.name) + '\')">Restore</button>' +
            '<button class="backup-btn backup-delete" onclick="handleDeleteBackup(\'' + escapeHtml(backup.name) + '\')">Delete</button>' +
            '</div>' +
            '</div>';
    }
    listEl.innerHTML = html;
}

async function handleRestoreBackup(backupName) {
    const messageEl = document.getElementById('backups-message');
    messageEl.textContent = 'Restoring backup...';
    messageEl.className = 'settings-message';

    try {
        const response = await fetch('/api/backups/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ backup_name: backupName })
        });

        const data = await response.json();

        if (data.success) {
            messageEl.textContent = 'Restored! Current data saved as ' + data.current_backed_up_as + '. Reloading...';
            messageEl.className = 'settings-message success';

            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            messageEl.textContent = data.error || 'Failed to restore backup';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        console.error('Restore failed:', error);
        messageEl.textContent = 'Connection error. Please try again.';
        messageEl.className = 'settings-message error';
    }
}

async function handleDeleteBackup(backupName) {
    const messageEl = document.getElementById('backups-message');
    messageEl.textContent = 'Deleting backup...';
    messageEl.className = 'settings-message';

    try {
        const response = await fetch('/api/backups/' + encodeURIComponent(backupName), {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            messageEl.textContent = 'Backup deleted.';
            messageEl.className = 'settings-message success';
            // Refresh the list
            await loadBackupsData();
            setTimeout(() => { messageEl.textContent = ''; }, 2000);
        } else {
            messageEl.textContent = data.error || 'Failed to delete backup';
            messageEl.className = 'settings-message error';
        }
    } catch (error) {
        console.error('Delete failed:', error);
        messageEl.textContent = 'Connection error. Please try again.';
        messageEl.className = 'settings-message error';
    }
}

