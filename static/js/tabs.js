// Euno - Tab Navigation

// ============== Tab Functions ==============

function switchTab(tabName, saveState = true) {
    // Hide all panes and deactivate all buttons
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    // Show selected pane and activate button
    const pane = document.getElementById(`tab-${tabName}`);
    const btn = document.querySelector(`[data-tab="${tabName}"]`);
    if (pane) pane.classList.add('active');
    if (btn) btn.classList.add('active');

    activeTab = tabName;
    if (saveState) {
        localStorage.setItem('activeTab', tabName);
    }

    // Load data for tab
    if (tabName === 'focus') {
        // Reset focus view to menu when clicking tab
        focusView = 'menu';
        focusViewHistory = [];
        loadTasksData();
    }
    if (tabName === 'history') loadHistoryData();
    if (tabName === 'about') loadAboutData();
    if (tabName === 'settings') loadSettingsData();
}

