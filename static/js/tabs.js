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

// ============== More Menu Screen Navigation ==============

function openMoreMenuScreen(tabName) {
    // Remember which tab to return to
    moreMenuReturnTab = activeTab;

    // Show the target tab pane but keep More button active
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active', 'slide-left', 'slide-right');
        if (pane.id === `tab-${tabName}`) {
            pane.classList.add('active');
        } else {
            pane.classList.add('slide-left');
        }
    });

    // Activate the More button
    const overflowBtn = document.getElementById('overflow-btn');
    if (overflowBtn) overflowBtn.classList.add('active');

    // Load data for the screen
    if (tabName === 'history') {
        historyView = 'list';
        historyViewHistory = [];
        loadHistoryData();
    }
    if (tabName === 'about') loadAboutData();
    if (tabName === 'settings') loadSettingsData();
}

function navigateMoreMenuBack() {
    if (moreMenuReturnTab) {
        const returnTab = moreMenuReturnTab;
        moreMenuReturnTab = null;
        switchTab(returnTab);
    } else {
        switchTab('focus');
    }
}

// ============== Tab Functions ==============

function switchTab(tabName) {
    // Determine slide direction based on tab order
    const prevIndex = TAB_ORDER.indexOf(previousTab);
    const newIndex = TAB_ORDER.indexOf(tabName);
    const slideRight = newIndex > prevIndex; // New tab is to the right, slide left to reveal

    // Deactivate all buttons
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    // Update pane positions for slide animation
    document.querySelectorAll('.tab-pane').forEach(pane => {
        const paneTab = pane.id.replace('tab-', '');
        const paneIndex = TAB_ORDER.indexOf(paneTab);

        pane.classList.remove('active', 'slide-left', 'slide-right');

        if (paneTab === tabName) {
            pane.classList.add('active');
        } else if (paneIndex < newIndex) {
            pane.classList.add('slide-left');
        } else {
            pane.classList.add('slide-right');
        }
    });

    // Activate button
    const btn = document.querySelector(`.tab-menu > [data-tab="${tabName}"]`);
    if (btn) btn.classList.add('active');

    // If tab is in overflow menu, highlight the "More" button
    const overflowTabs = ['history', 'about', 'settings'];
    const overflowBtn = document.getElementById('overflow-btn');
    if (overflowTabs.includes(tabName) && overflowBtn) {
        overflowBtn.classList.add('active');
    }

    previousTab = tabName;
    activeTab = tabName;

    // Load data for tab
    if (tabName === 'chat') {
        // Clear notification when switching to chat
        clearChatNotification();
    }
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

