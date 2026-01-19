// Euno - Asters Tab
// Asters are nebulous goals that can be fulfilled but never completed.
// They are stored as jobs with tags: ["aster"]

// Track which asters are expanded
let expandedAsters = new Set();

// Get all aster jobs from jobsData
function getAsterJobs() {
    return jobsData.filter(job => job.tags && job.tags.includes('aster') && job.status !== 'archived');
}

// Get fulfilled (archived) asters
function getFulfilledAsters() {
    // Need to check completedJobsData and also filter archived from all jobs
    return completedJobsData.filter(job => job.tags && job.tags.includes('aster'));
}

// Check if any aster jobs exist (for tab visibility)
function hasAsterJobs() {
    return getAsterJobs().length > 0;
}

// Update asters button visibility
function updateAstersVisibility() {
    const btn = document.getElementById('asters-btn');
    if (!btn) return;

    if (hasAsterJobs()) {
        btn.style.display = 'flex';
    } else {
        btn.style.display = 'none';
        // If currently viewing asters tab but no asters exist, switch to focus
        if (activeTab === 'asters') {
            switchTab('focus');
        }
    }
}

// Load and render asters tab
function loadAstersData() {
    renderAstersTab();
}

// Render the asters tab content
function renderAstersTab() {
    const content = document.getElementById('asters-content');
    if (!content) return;

    const asterJobs = getAsterJobs();

    if (asterJobs.length === 0) {
        content.innerHTML = `
            <div class="focus-empty">
                <p>No asters yet.</p>
                <p class="focus-empty-hint">Asters are big, open-ended aspirations—goals that can be fulfilled but never truly completed.</p>
            </div>
        `;
        return;
    }

    // Render aster cards
    const cardsHtml = asterJobs.map(job => renderAsterCard(job)).join('');

    content.innerHTML = `
        <div class="asters-header">
            <h2>Asters</h2>
            <p class="asters-subtitle">Aspirations you're cultivating</p>
        </div>
        <div class="asters-list">
            ${cardsHtml}
        </div>
    `;
}

// Toggle aster card expansion
function toggleAsterExpand(jobId, event) {
    event.stopPropagation();
    if (expandedAsters.has(jobId)) {
        expandedAsters.delete(jobId);
    } else {
        expandedAsters.add(jobId);
    }
    renderAstersTab();
}

// Render a single aster card
function renderAsterCard(job) {
    const description = job.description || '';
    const isExpanded = expandedAsters.has(job.id);
    const needsTruncation = description.length > 200;

    // Show truncated or full description based on state
    const displayDesc = isExpanded || !needsTruncation
        ? description
        : description.substring(0, 200) + '...';

    // Get log entries - show last 3 when collapsed, all when expanded
    const allLogs = job.log || [];
    const displayLogs = isExpanded ? allLogs : allLogs.slice(-3);
    const hasMoreLogs = !isExpanded && allLogs.length > 3;

    const logsHtml = displayLogs.length > 0
        ? `<div class="aster-logs">
            ${displayLogs.map(log => `
                <div class="aster-log-entry">
                    <span class="aster-log-date">${formatRelativeDate(log.timestamp)}</span>
                    <span class="aster-log-text">${escapeHtml(log.action)}</span>
                </div>
            `).join('')}
            ${hasMoreLogs ? `<div class="aster-logs-more">+ ${allLogs.length - 3} more entries</div>` : ''}
           </div>`
        : '';

    // Expand/collapse indicator
    const expandIndicator = (needsTruncation || allLogs.length > 3)
        ? `<span class="aster-expand-hint">${isExpanded ? 'tap to collapse' : 'tap to expand'}</span>`
        : '';

    return `
        <div class="aster-card ${isExpanded ? 'expanded' : ''}" onclick="toggleAsterExpand('${job.id}', event)">
            <div class="aster-card-header">
                <h3 class="aster-name">${escapeHtml(job.name)}</h3>
                <button class="aster-detail-btn" onclick="event.stopPropagation(); navigateToJob('${job.id}')" title="View details">
                    ${typeof icon === 'function' ? icon('chevron-right') : '→'}
                </button>
            </div>
            ${displayDesc ? `<div class="aster-description">${isExpanded ? marked.parse(displayDesc) : escapeHtml(displayDesc)}</div>` : ''}
            ${logsHtml}
            ${expandIndicator}
        </div>
    `;
}

// Format date as relative (e.g., "2 days ago")
function formatRelativeDate(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
}

// Navigate to job detail view (reuse Focus tab's job view)
function navigateToAsterDetail(jobId) {
    // Switch to focus tab and navigate to the job
    switchTab('focus');
    navigateToJob(jobId);
}
