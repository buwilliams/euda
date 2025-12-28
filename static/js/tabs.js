// Euno - Tab Navigation

// ============== Overflow Menu ==============

function toggleOverflowMenu() {
    const menu = document.getElementById('overflow-menu');
    const btn = document.getElementById('overflow-btn');
    menu.classList.toggle('open');
    btn.classList.toggle('menu-open');

    // Update active state on overflow items
    if (menu.classList.contains('open')) {
        updateOverflowActiveState();
    }
}

function closeOverflowMenu() {
    const menu = document.getElementById('overflow-menu');
    const btn = document.getElementById('overflow-btn');
    menu.classList.remove('open');
    btn.classList.remove('menu-open');
}

function updateOverflowActiveState() {
    // Mark the currently active tab in overflow menu
    document.querySelectorAll('.overflow-item').forEach(item => {
        const tabName = item.getAttribute('data-tab');
        if (tabName === activeTab) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// Close overflow menu when clicking outside
document.addEventListener('click', (e) => {
    const overflow = document.querySelector('.tab-overflow');
    if (overflow && !overflow.contains(e.target)) {
        closeOverflowMenu();
    }
});

// ============== Tab Functions ==============

function switchTab(tabName, saveState = true) {
    // Hide all panes and deactivate all buttons
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    // Show selected pane and activate button
    const pane = document.getElementById(`tab-${tabName}`);
    const btn = document.querySelector(`.tab-menu > [data-tab="${tabName}"]`);
    if (pane) pane.classList.add('active');
    if (btn) btn.classList.add('active');

    // If tab is in overflow menu, highlight the "More" button
    const overflowTabs = ['history', 'about', 'settings'];
    const overflowBtn = document.getElementById('overflow-btn');
    if (overflowTabs.includes(tabName) && overflowBtn) {
        overflowBtn.classList.add('active');
    }

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
    if (tabName === 'history') {
        // Reset history view to list when clicking tab
        historyView = 'list';
        historyViewHistory = [];
        loadHistoryData();
    }
    if (tabName === 'about') loadAboutData();
    if (tabName === 'settings') loadSettingsData();
}

