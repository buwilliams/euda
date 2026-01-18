// Euno - Focus Tab Core (State, Icons, Navigation)

// ============== State ==============

let jobsData = [];           // All active jobs
let completedJobsData = [];  // Recently completed jobs
let jobAssetsCache = {};     // Cache of assets per job
let editingJobField = null;  // Which field is being edited: {jobId, field}
let currentAssetData = null; // Currently viewed asset
let editingAssetFilename = null; // Track if we're editing an asset
let agentsCache = null;      // Cache of available agents
let agentDataCache = {};     // Cache of agent persona and config
let isViewAnimating = false; // Track if view animation is in progress
let pendingRender = false;   // Track if a render is pending after animation

// ============== Icons ==============

function icon(name, className = '') {
    const cls = className ? ` class="${className}"` : '';
    return `<img src="/web/icons/${name}.svg" alt="${name}"${cls}>`;
}

// ============== Focus Tab Navigation ==============

let focusSlideDirection = null;

function renderFocusTab() {
    const container = document.getElementById('focus-content');
    if (!container) return;

    // Defer render if animation is in progress
    if (isViewAnimating) {
        pendingRender = true;
        return;
    }

    let content;
    if (focusView === 'menu') {
        content = renderFocusMenu();
    } else if (focusView === 'today') {
        content = renderTimelineView('today', 'Today');
    } else if (focusView === 'upcoming') {
        content = renderTimelineView('upcoming', 'Upcoming');
    } else if (focusView === 'anytime') {
        content = renderTimelineView('anytime', 'Anytime');
    } else if (focusView === 'someday') {
        content = renderTimelineView('someday', 'Someday');
    } else if (focusView === 'completed') {
        content = renderCompletedJobsView();
    } else if (focusView.startsWith('assets-')) {
        // assets-{jobId} - list of assets for a job
        const jobId = focusView.substring(7);
        content = renderAssetsListView(jobId);
    } else if (focusView.startsWith('asset-')) {
        // asset-{jobId}-{filename} where jobId is like "job-xxxxxxxx"
        const rest = focusView.substring(6); // remove "asset-"
        // Job IDs are "job-" + 8 hex chars, so extract first 12 chars
        const jobId = rest.substring(0, 12);
        const filename = rest.substring(13); // skip jobId + "-"
        content = renderAssetView(jobId, filename);
    } else if (focusView === 'newjob') {
        // Standalone new job creator screen
        content = renderNewJobCreatorScreen();
    } else if (focusView.startsWith('newjob-')) {
        // newjob-{jobId} - create new child jobs
        const jobId = focusView.substring(7);
        content = renderNewJobScreen(jobId);
    } else if (focusView.startsWith('attach-')) {
        // attach-{jobId} - attach assets to a job
        const jobId = focusView.substring(7);
        content = renderAttachScreen(jobId);
    } else if (focusView.startsWith('job-')) {
        const jobId = focusView.substring(4);
        content = renderJobDetailView(jobId);
    } else if (focusView.startsWith('completed-')) {
        const jobId = focusView.substring(10);
        content = renderCompletedJobDetailView(jobId);
    } else if (focusView.startsWith('trace-')) {
        const jobId = focusView.substring(6);
        content = renderJobTraceView(jobId);
    } else if (focusView.startsWith('manage-agent-')) {
        const agentId = focusView.substring(13);
        content = renderAgentManageView(agentId);
    } else if (focusView.startsWith('memory-list-')) {
        const agentId = focusView.substring(12);
        content = renderMemoryListView(agentId);
    } else if (focusView.startsWith('memory-item-')) {
        // memory-item-{agentId}-{entryId}
        const rest = focusView.substring(12);
        const dashIndex = rest.indexOf('-');
        const agentId = rest.substring(0, dashIndex);
        const entryId = rest.substring(dashIndex + 1);
        content = renderMemoryItemView(agentId, entryId);
    } else if (focusView.startsWith('monitoring-')) {
        const agentId = focusView.substring(11);
        content = renderMonitoringView(agentId);
    } else if (focusView.startsWith('prompt-')) {
        // prompt-{agentId}-{index}
        const rest = focusView.substring(7);
        const dashIndex = rest.indexOf('-');
        const agentId = rest.substring(0, dashIndex);
        const promptIndex = rest.substring(dashIndex + 1);
        content = renderPromptDetailView(agentId, promptIndex);
    } else if (focusView.startsWith('long-term-memory-detail-')) {
        // long-term-memory-detail-{agentId}-{date}
        const rest = focusView.substring(24);
        const dashIndex = rest.indexOf('-');
        const agentId = rest.substring(0, dashIndex);
        const date = rest.substring(dashIndex + 1);
        content = renderLongTermMemoryDetailView(agentId, date);
    } else if (focusView.startsWith('long-term-memory-')) {
        const agentId = focusView.substring(17);
        content = renderLongTermMemoryListView(agentId);
    } else if (focusView.startsWith('profile-')) {
        const agentId = focusView.substring(8);
        content = renderProfileView(agentId);
    } else if (focusView.startsWith('config-')) {
        const agentId = focusView.substring(7);
        content = renderConfigurationView(agentId);
    } else if (focusView.startsWith('rate-limits-')) {
        const agentId = focusView.substring(12);
        content = renderRateLimitEventsView(agentId);
    }

    if (focusSlideDirection && container.querySelector('.view-slide-container')) {
        animateViewTransition(container, content, focusSlideDirection);
        focusSlideDirection = null;
    } else {
        container.innerHTML = `<div class="view-slide-container current">${content}</div>`;
    }
}

function animateViewTransition(container, newContent, direction) {
    const oldView = container.querySelector('.view-slide-container');
    if (!oldView) {
        container.innerHTML = `<div class="view-slide-container current">${newContent}</div>`;
        return;
    }

    isViewAnimating = true;

    const newView = document.createElement('div');
    newView.className = 'view-slide-container';
    newView.innerHTML = newContent;

    if (direction === 'forward') {
        newView.classList.add('slide-in-right');
    } else {
        newView.classList.add('slide-in-left');
    }

    container.appendChild(newView);
    newView.offsetHeight;

    if (direction === 'forward') {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-left');
    } else {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-right');
    }

    newView.classList.remove('slide-in-left', 'slide-in-right');
    newView.classList.add('current');

    setTimeout(() => {
        if (oldView.parentNode) {
            oldView.remove();
        }
        isViewAnimating = false;
        if (pendingRender) {
            pendingRender = false;
            renderFocusTab();
        }
    }, 300);
}

function navigateFocus(view) {
    focusViewHistory.push(focusView);
    focusView = view;
    focusSlideDirection = 'forward';

    // Set job context for chat input (context-aware routing)
    if (view.startsWith('job-')) {
        const jobId = view.substring(4);
        if (typeof setJobContext === 'function') {
            setJobContext(jobId);
        }
    } else {
        if (typeof clearJobContext === 'function') {
            clearJobContext();
        }
    }

    renderFocusTab();
}

function navigateFocusBack() {
    if (focusViewHistory.length > 0) {
        focusView = focusViewHistory.pop();
    } else {
        focusView = 'menu';
    }
    focusSlideDirection = 'back';

    // Update job context for chat input
    if (focusView.startsWith('job-')) {
        const jobId = focusView.substring(4);
        if (typeof setJobContext === 'function') {
            setJobContext(jobId);
        }
    } else {
        if (typeof clearJobContext === 'function') {
            clearJobContext();
        }
    }

    // If returning to menu from a More menu screen, go back to the original tab
    if (focusView === 'menu' && moreMenuReturnTab) {
        const returnTab = moreMenuReturnTab;
        moreMenuReturnTab = null;
        switchTab(returnTab);
        return;
    }

    renderFocusTab();
}
