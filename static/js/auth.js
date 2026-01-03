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

    // Load daily quote
    loadDailyQuote();

    // Connect SSE
    connectSSE();

    // Load tasks data for badge
    loadTasksData();
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

async function loadSettingsData() {
    try {
        const response = await fetch('/api/settings');
        settingsData = await response.json();
        renderSettings();
    } catch (error) {
        console.error('Failed to load settings:', error);
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
            if (settingsData?.llm) {
                settingsData.llm.provider = newProvider;
            }
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
