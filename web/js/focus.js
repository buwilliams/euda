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

// ============== Breadcrumbs ==============

// Get short display name for a view (used in breadcrumbs)
function getViewDisplayName(view) {
    // Timeline views
    if (view === 'menu') return 'Focus';
    if (view === 'today') return 'Today';
    if (view === 'upcoming') return 'Upcoming';
    if (view === 'anytime') return 'Anytime';
    if (view === 'someday') return 'Someday';
    if (view === 'completed') return 'Completed';
    if (view === 'newjob') return 'New Job';

    // Job views - get job name from cache
    if (view.startsWith('job-')) {
        const jobId = view.substring(4);
        const job = jobsData.find(j => j.id === jobId) || completedJobsData.find(j => j.id === jobId);
        if (job) {
            // Truncate long names for breadcrumbs
            const name = job.name || 'Job';
            return name.length > 20 ? name.substring(0, 18) + '...' : name;
        }
        return 'Job';
    }

    // Completed job views
    if (view.startsWith('completed-')) {
        const jobId = view.substring(10);
        const job = completedJobsData.find(j => j.id === jobId);
        if (job) {
            const name = job.name || 'Job';
            return name.length > 20 ? name.substring(0, 18) + '...' : name;
        }
        return 'Completed';
    }

    // Agent-related views
    if (view.startsWith('manage-agent-')) {
        return 'Manage';
    }
    if (view.startsWith('profile-')) {
        return 'Profile';
    }
    if (view.startsWith('config-')) {
        return 'Config';
    }
    if (view.startsWith('memory-list-')) {
        return 'Memory';
    }
    if (view.startsWith('memory-item-')) {
        return 'Item';
    }
    if (view.startsWith('long-term-memory-detail-')) {
        return 'Entry';
    }
    if (view.startsWith('long-term-memory-')) {
        return 'Long-term';
    }
    if (view.startsWith('monitoring-')) {
        return 'Monitoring';
    }
    if (view.startsWith('prompt-')) {
        return 'Prompt';
    }
    if (view.startsWith('rate-limits-')) {
        return 'Rate Limits';
    }
    if (view.startsWith('trace-')) {
        return 'Trace';
    }

    // Asset views
    if (view.startsWith('assets-')) {
        return 'Assets';
    }
    if (view.startsWith('asset-')) {
        const rest = view.substring(6);
        const filename = rest.substring(13); // skip jobId + "-"
        return filename.length > 15 ? filename.substring(0, 13) + '...' : filename;
    }

    // Child job creation
    if (view.startsWith('newjob-')) {
        return 'Add Jobs';
    }
    if (view.startsWith('attach-')) {
        return 'Add Assets';
    }

    return 'View';
}

// Build breadcrumb path from navigation history
function getBreadcrumbPath() {
    const path = [];
    for (const view of focusViewHistory) {
        path.push(getViewDisplayName(view));
    }
    return path;
}

// Render just the breadcrumbs HTML (for adding to existing headers)
function renderBreadcrumbs() {
    const breadcrumbs = getBreadcrumbPath();
    if (breadcrumbs.length === 0) return '';
    const arrow = `<img src="/web/icons/chevron-right.svg" alt=">">`;
    const html = breadcrumbs.map(b => `<span>${b}</span>`).join(arrow);
    return `<div class="focus-view-breadcrumbs">${html}</div>`;
}

// Render view header with title and breadcrumbs
function renderViewHeader(title, options = {}) {
    const { iconName = null, iconHtml = null } = options;

    // Build the icon HTML
    let titleIconHtml = '';
    if (iconHtml) {
        titleIconHtml = iconHtml;
    } else if (iconName) {
        titleIconHtml = icon(iconName);
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${titleIconHtml}${title}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
    `;
}
