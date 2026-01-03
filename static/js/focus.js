// Euno - Focus Tab (Jobs with infinite nesting)

// ============== State ==============

let jobsData = [];           // All active jobs
let completedJobsData = [];  // Recently completed jobs
let jobAssetsCache = {};     // Cache of assets per job
let editingJobField = null;  // Which field is being edited: {jobId, field}
let currentAssetData = null; // Currently viewed asset
let editingAssetFilename = null; // Track if we're editing an asset
let agentsCache = null;      // Cache of available agents

// ============== Icons ==============

function icon(name, className = '') {
    const cls = className ? ` class="${className}"` : '';
    return `<img src="/static/icons/${name}.svg" alt="${name}"${cls}>`;
}

// ============== Data Loading ==============

async function loadJobsData() {
    try {
        const fetchOpts = { credentials: 'same-origin' };
        const [activeRes, completedRes] = await Promise.all([
            fetch('/api/jobs?status=todo', fetchOpts),
            fetch('/api/jobs?status=completed', fetchOpts)
        ]);

        if (activeRes.status === 401 || completedRes.status === 401) {
            console.error('Focus tab: Authentication required');
            window.location.reload();
            return;
        }

        const activeJobs = await activeRes.json();
        const completedJobs = await completedRes.json();

        // Active jobs (not completed, not archived)
        jobsData = Array.isArray(activeJobs) ? activeJobs : [];
        // Recently completed jobs (limit to 20)
        completedJobsData = Array.isArray(completedJobs) ? completedJobs.slice(0, 20) : [];

        renderFocusTab();
        updateTasksBadge();
    } catch (error) {
        console.error('Failed to load jobs data:', error);
    }
}

// Alias for backwards compatibility
async function loadTasksData() {
    return loadJobsData();
}

async function loadAgents() {
    if (agentsCache) return agentsCache;
    try {
        const response = await fetch('/api/agents', { credentials: 'same-origin' });
        if (response.ok) {
            agentsCache = await response.json();
            return agentsCache;
        }
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
    return [];
}

// ============== Job Categories (Timeline Views) ==============

function getJobCategory(job) {
    const today = new Date().toISOString().split('T')[0];
    const dueDate = job.due_date;
    const someday = job.someday;

    if (job.status === 'completed') return 'logbook';
    if (dueDate === today) return 'today';
    if (dueDate && dueDate > today) return 'upcoming';
    if (!dueDate && someday) return 'someday';
    return 'anytime';
}

function formatFriendlyDueDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const nextWeek = new Date(today);
    nextWeek.setDate(nextWeek.getDate() + 7);

    if (date.getTime() === today.getTime()) {
        return 'Today';
    } else if (date.getTime() === tomorrow.getTime()) {
        return 'Tomorrow';
    } else if (date < nextWeek) {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function formatFriendlyPastDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    date.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    if (date.getTime() === today.getTime()) {
        return 'Today';
    } else if (date.getTime() === yesterday.getTime()) {
        return 'Yesterday';
    } else if (date > lastWeek) {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function getFocusCounts() {
    const counts = { today: 0, upcoming: 0, anytime: 0, someday: 0, toplevel: 0 };

    jobsData.forEach(job => {
        const category = getJobCategory(job);
        counts[category]++;
        if (!job.parent_id) {
            counts.toplevel++;
        }
    });

    return counts;
}

// ============== Focus Tab Navigation ==============

let focusSlideDirection = null;

function renderFocusTab() {
    const container = document.getElementById('focus-content');
    if (!container) return;

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
    }, 300);
}

function renderFocusMenu() {
    const counts = getFocusCounts();
    const topLevelJobs = jobsData.filter(j => !j.parent_id);
    // Root completed jobs: no parent OR parent is not in completed list (parent still active/archived)
    const completedJobIds = new Set(completedJobsData.map(j => j.id));
    const topLevelCompletedJobs = completedJobsData.filter(j => !j.parent_id || !completedJobIds.has(j.parent_id));

    return `
        <div class="focus-menu">
            <div class="focus-menu-item" onclick="navigateFocus('today')">
                <span class="focus-menu-icon">${icon('sun')}</span>
                <span class="focus-menu-label">Today</span>
                <span class="focus-menu-count">${counts.today}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('upcoming')">
                <span class="focus-menu-icon">${icon('calendar')}</span>
                <span class="focus-menu-label">Upcoming</span>
                <span class="focus-menu-count">${counts.upcoming}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('anytime')">
                <span class="focus-menu-icon">${icon('clock')}</span>
                <span class="focus-menu-label">Anytime</span>
                <span class="focus-menu-count">${counts.anytime}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('someday')">
                <span class="focus-menu-icon">${icon('cloud')}</span>
                <span class="focus-menu-label">Someday</span>
                <span class="focus-menu-count">${counts.someday}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('completed')">
                <span class="focus-menu-icon">${icon('check')}</span>
                <span class="focus-menu-label">Completed</span>
                <span class="focus-menu-count">${topLevelCompletedJobs.length}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            ${topLevelJobs.map(job => {
                const childCount = jobsData.filter(j => j.parent_id === job.id).length;
                const assignees = job.assignees || [];
                const workingBadge = job.in_progress_by ? '<span class="menu-working-badge" title="Agent working">' + icon('bolt') + '</span>' : '';
                const assignedBadge = !job.in_progress_by && assignees.length > 0 ? '<span class="menu-assigned-badge" title="Assigned">' + icon('user') + '</span>' : '';
                return `
                <div class="focus-menu-item" onclick="navigateFocus('job-${job.id}')">
                    <span class="focus-menu-icon">${icon('folder')}</span>
                    <span class="focus-menu-label">${escapeHtml(job.name)}</span>
                    ${workingBadge}${assignedBadge}
                    <span class="focus-menu-count">${childCount}</span>
                    <button class="card-trash-btn" onclick="quickDeleteJob(event, '${job.id}')" title="Delete job">${icon('trash')}</button>
                    <span class="focus-menu-arrow">›</span>
                </div>
            `}).join('')}
        </div>
        <div class="quick-add-section">
            <input type="text" id="quick-add-root" class="quick-add-input" placeholder="Add new job..." onkeypress="handleQuickAddKeypress(event, 'quick-add-root')">
            <button class="quick-add-btn" onclick="quickAddJob('quick-add-root')">${icon('plus')}</button>
        </div>
    `;
}

function getTimelineIcon(category) {
    const iconNames = { today: 'sun', upcoming: 'calendar', anytime: 'clock', someday: 'cloud' };
    return iconNames[category] ? icon(iconNames[category]) : '';
}

function renderTimelineView(category, title) {
    const jobs = jobsData.filter(j => getJobCategory(j) === category);
    const categoryIcon = getTimelineIcon(category);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${categoryIcon} ${title}</span>
        </div>
        <div class="focus-view-content">
            ${jobs.length === 0
                ? '<div class="focus-empty">No jobs</div>'
                : jobs.map(job => renderJobCard(job)).join('')
            }
        </div>
    `;
}

function renderCompletedJobsView() {
    // Root completed jobs: no parent OR parent is not in completed list
    const completedJobIds = new Set(completedJobsData.map(j => j.id));
    const rootCompletedJobs = completedJobsData.filter(j => !j.parent_id || !completedJobIds.has(j.parent_id));
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${icon('check')} Completed Jobs</span>
        </div>
        <div class="focus-view-content">
            ${rootCompletedJobs.length === 0
                ? '<div class="focus-empty">No completed jobs</div>'
                : rootCompletedJobs.map(job => {
                    const childCount = completedJobsData.filter(j => j.parent_id === job.id).length;
                    return renderCompletedJobCard(job, childCount);
                }).join('')
            }
        </div>
    `;
}

function navigateFocus(view) {
    focusViewHistory.push(focusView);
    focusView = view;
    focusSlideDirection = 'forward';
    renderFocusTab();
}

function navigateFocusBack() {
    if (focusViewHistory.length > 0) {
        focusView = focusViewHistory.pop();
    } else {
        focusView = 'menu';
    }
    focusSlideDirection = 'back';
    renderFocusTab();
}

// ============== Job Cards ==============

function renderJobCard(job) {
    const isExpanded = expandedCards.has(`job-${job.id}`);
    return isExpanded ? renderFullJobCard(job) : renderMinimalJobCard(job);
}

function renderMinimalJobCard(job) {
    const displayName = job.name || 'Untitled';
    const dueDate = job.due_date;
    const dueDateLabel = dueDate ? `<span class="card-due-date">${formatFriendlyDueDate(dueDate)}</span>` : '';
    const childCount = jobsData.filter(j => j.parent_id === job.id).length;
    const childBadge = childCount > 0 ? `<span class="card-badge">${childCount}</span>` : '';
    const assignees = job.assignees || [];
    const workingIndicator = job.in_progress_by ? '<span class="card-working-indicator" title="Agent working">' + icon('bolt') + '</span>' : '';
    const assignedIndicator = !job.in_progress_by && assignees.length > 0 ? '<span class="card-assigned-indicator" title="Assigned to ' + assignees.join(', ') + '">' + icon('user') + '</span>' : '';

    return `
        <div class="card card-minimal" data-job-id="${job.id}" onclick="navigateFocus('job-${job.id}')">
            ${workingIndicator}${assignedIndicator}
            <span class="card-title">${escapeHtml(displayName)}</span>
            ${childBadge}
            ${dueDateLabel}
            <button class="card-trash-btn" onclick="quickDeleteJob(event, '${job.id}')" title="Delete job">${icon('trash')}</button>
            <span class="card-arrow">›</span>
        </div>
    `;
}

function renderFullJobCard(job) {
    const whenLabel = getWhenLabel(job);
    const isArchiving = archivingTaskId === job.id;
    const displayName = job.name || 'Untitled';
    const hasDescription = job.description && job.description.length > 0;
    const childCount = jobsData.filter(j => j.parent_id === job.id).length;

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = jobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    return `
        <div class="card card-full" data-job-id="${job.id}">
            <div class="card-header">
                <span class="card-title" onclick="toggleJobCard('${job.id}')">${escapeHtml(displayName)}</span>
                <button class="card-collapse" onclick="event.stopPropagation(); toggleJobCard('${job.id}')">−</button>
            </div>
            <div class="card-body">
                ${hasDescription ? `<div class="card-description">${marked.parse(job.description)}</div>` : ''}
                ${parentName ? `<div class="card-meta">Parent: <span class="card-project-link" onclick="event.stopPropagation(); navigateFocus('job-${job.parent_id}')">${escapeHtml(parentName)}</span></div>` : ''}
                ${childCount > 0 ? `<div class="card-meta">${childCount} child job${childCount !== 1 ? 's' : ''}</div>` : ''}
            </div>
            <div class="card-actions">
                <button class="card-action" onclick="event.stopPropagation(); openWhenPicker('job', '${job.id}')">${icon('calendar')} ${escapeHtml(whenLabel)}</button>
                <button class="card-action" onclick="completeJob(event, '${job.id}')">Complete</button>
                <button class="card-action" onclick="showArchiveInput(event, '${job.id}')">${isArchiving ? 'Cancel' : 'Archive'}</button>
                <button class="card-action danger" onclick="deleteJob(event, '${job.id}')">Delete</button>
            </div>
            ${isArchiving ? `
            <div class="card-archive-form">
                <input type="text" class="card-archive-input" id="archive-reason-${job.id}" placeholder="Reason (optional)..." onkeypress="if(event.key==='Enter')confirmArchiveJob('${job.id}')">
                <button class="card-archive-btn confirm" onclick="confirmArchiveJob('${job.id}')">Archive</button>
            </div>
            ` : ''}
        </div>
    `;
}

function getWhenLabel(job) {
    const today = new Date().toISOString().split('T')[0];
    const dueDate = job.due_date;
    const someday = job.someday;

    if (dueDate === today) return 'Today';
    if (dueDate) return dueDate;
    if (someday) return 'Someday';
    return 'Anytime';
}

function renderJobDetailView(jobId) {
    const job = jobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">Job Not Found</span>
            </div>
            <div class="focus-empty">This job no longer exists.</div>
        `;
    }

    const whenLabel = getWhenLabel(job);
    const isArchiving = archivingTaskId === job.id;
    const displayName = job.name || 'Untitled';
    const hasDescription = job.description && job.description.length > 0;
    const childJobs = jobsData.filter(j => j.parent_id === job.id);
    const completedChildJobs = completedJobsData.filter(j => j.parent_id === job.id);
    const assets = jobAssetsCache[jobId] || [];

    // Check if we're editing this job
    const isEditingName = editingJobField?.jobId === jobId && editingJobField?.field === 'name';
    const isEditingDesc = editingJobField?.jobId === jobId && editingJobField?.field === 'description';

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = jobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('job', '${job.id}')">${icon('calendar')} ${escapeHtml(whenLabel)}</button>
                <button class="task-detail-action" onclick="openAssigneesPicker('${job.id}')">${getAssigneesLabel(job)}</button>
                <button class="task-detail-action" onclick="openAddPicker('${job.id}')">+ Add</button>
                <button class="task-detail-action" onclick="openMorePicker('${job.id}')">••• More</button>
            </div>

            <!-- Name Section -->
            <div class="job-section">
                <div class="job-section-header">Name</div>
                ${isEditingName ? `
                    <input type="text" class="job-name-input" id="edit-name-${job.id}" value="${escapeHtml(displayName)}"
                        onkeydown="handleEditKeypress(event, '${job.id}', 'name')"
                        onblur="saveJobField('${job.id}', 'name', this.value)">
                ` : `
                    <div class="job-name-display" onclick="startEditingField('${job.id}', 'name')">${escapeHtml(displayName)}</div>
                `}
            </div>

            <!-- Description Section -->
            <div class="job-section">
                <div class="job-section-header">
                    Description
                    ${isEditingDesc ? `<span class="job-section-action" onclick="saveJobField('${job.id}', 'description', document.getElementById('edit-description-${job.id}').value)">Save</span>` : ''}
                </div>
                ${isEditingDesc ? `
                    <textarea class="job-description-input" id="edit-description-${job.id}"
                        onkeydown="handleDescriptionKeypress(event, '${job.id}')"
                        placeholder="Add a description...">${escapeHtml(job.description || '')}</textarea>
                ` : `
                    <div class="job-description-display ${hasDescription ? '' : 'empty'}" onclick="startEditingField('${job.id}', 'description')">
                        ${hasDescription ? marked.parse(job.description) : 'Click to add description...'}
                    </div>
                `}
            </div>

            <!-- Child Jobs Section -->
            ${childJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Child Jobs (${childJobs.length})</div>
                ${childJobs.map(child => renderJobCard(child)).join('')}
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Completed (${completedChildJobs.length})</div>
                ${completedChildJobs.map(child => {
                    const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                    return renderCompletedJobCard(child, grandchildCount);
                }).join('')}
            </div>
            ` : ''}

            <!-- Parent Link -->
            ${parentName ? `
            <div class="job-section">
                <div class="job-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('job-${job.parent_id}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

            <!-- Assets Section -->
            ${assets.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Assets (${assets.length})</div>
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${job.id}-${asset.filename}')" style="cursor: pointer;">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="event.stopPropagation(); deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">x</button>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">x</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

function renderCompletedJobDetailView(jobId) {
    const job = completedJobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">Job Not Found</span>
            </div>
            <div class="focus-empty">This job no longer exists.</div>
        `;
    }

    const displayName = job.name || 'Untitled';
    const hasDescription = job.description && job.description.length > 0;
    const completedDate = job.completed_at ? formatFriendlyPastDate(job.completed_at) : 'Unknown';
    const completedChildJobs = completedJobsData.filter(j => j.parent_id === job.id);
    const activeChildJobs = jobsData.filter(j => j.parent_id === job.id);
    const assets = jobAssetsCache[jobId] || [];

    // Check if we're editing this job
    const isEditingName = editingJobField?.jobId === jobId && editingJobField?.field === 'name';
    const isEditingDesc = editingJobField?.jobId === jobId && editingJobField?.field === 'description';

    // Get parent job name for context (could be active or completed)
    let parentName = null;
    let parentIsCompleted = false;
    if (job.parent_id) {
        let parent = jobsData.find(j => j.id === job.parent_id);
        if (!parent) {
            parent = completedJobsData.find(j => j.id === job.parent_id);
            parentIsCompleted = true;
        }
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="restoreJob(event, '${job.id}')">${icon('arrow-uturn-left')} Restore</button>
                <button class="task-detail-action danger" onclick="deleteJob(event, '${job.id}')">${icon('trash')} Delete</button>
            </div>

            <!-- Completed Badge -->
            <div class="job-section" style="background: #f0f8f0; border-radius: 6px; padding: 0.5rem 1rem;">
                <span style="color: #4a8; font-weight: 500;">${icon('check')} Completed ${escapeHtml(completedDate)}</span>
            </div>

            <!-- Name Section -->
            <div class="job-section">
                <div class="job-section-header">Name</div>
                ${isEditingName ? `
                    <input type="text" class="job-name-input" id="edit-name-${job.id}" value="${escapeHtml(displayName)}"
                        onkeydown="handleEditKeypress(event, '${job.id}', 'name')"
                        onblur="saveCompletedJobField('${job.id}', 'name', this.value)">
                ` : `
                    <div class="job-name-display" onclick="startEditingField('${job.id}', 'name')">${escapeHtml(displayName)}</div>
                `}
            </div>

            <!-- Description Section -->
            <div class="job-section">
                <div class="job-section-header">
                    Description
                    ${isEditingDesc ? `<span class="job-section-action" onclick="saveCompletedJobField('${job.id}', 'description', document.getElementById('edit-description-${job.id}').value)">Save</span>` : ''}
                </div>
                ${isEditingDesc ? `
                    <textarea class="job-description-input" id="edit-description-${job.id}"
                        onkeydown="handleCompletedDescriptionKeypress(event, '${job.id}')"
                        placeholder="Add a description...">${escapeHtml(job.description || '')}</textarea>
                ` : `
                    <div class="job-description-display ${hasDescription ? '' : 'empty'}" onclick="startEditingField('${job.id}', 'description')">
                        ${hasDescription ? marked.parse(job.description) : 'Click to add description...'}
                    </div>
                `}
            </div>

            <!-- Active Child Jobs Section (rare but possible) -->
            ${activeChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Active Children (${activeChildJobs.length})</div>
                ${activeChildJobs.map(child => renderJobCard(child)).join('')}
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Completed Children (${completedChildJobs.length})</div>
                ${completedChildJobs.map(child => {
                    const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                    return renderCompletedJobCard(child, grandchildCount);
                }).join('')}
            </div>
            ` : ''}

            <!-- Parent Link -->
            ${parentName ? `
            <div class="job-section">
                <div class="job-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('${parentIsCompleted ? 'completed' : 'job'}-${job.parent_id}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

            <!-- Assets Section -->
            ${assets.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Assets (${assets.length})</div>
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${job.id}-${asset.filename}')" style="cursor: pointer;">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="event.stopPropagation(); deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">x</button>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">x</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

function toggleJobCard(jobId) {
    const key = `job-${jobId}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderFocusTab();
}

function renderCompletedJobCard(job, childCount = 0) {
    const displayName = job.name || 'Untitled';
    const completedDateLabel = job.completed_at ? `<span class="card-due-date">${formatFriendlyPastDate(job.completed_at)}</span>` : '';
    const childBadge = childCount > 0 ? `<span class="card-badge">${childCount}</span>` : '';

    return `
        <div class="card card-minimal" data-job-id="${job.id}" onclick="navigateFocus('completed-${job.id}')">
            <span class="card-title" style="text-decoration: line-through; color: #888;">${escapeHtml(displayName)}</span>
            ${childBadge}
            ${completedDateLabel}
            <span class="card-arrow">›</span>
        </div>
    `;
}

function isTextAsset(asset) {
    const textTypes = ['text/', 'application/json', 'application/xml', 'application/javascript'];
    const textExtensions = ['.md', '.txt', '.json', '.xml', '.html', '.css', '.js', '.py', '.sh', '.yaml', '.yml'];

    if (asset.mime_type) {
        for (const type of textTypes) {
            if (asset.mime_type.startsWith(type)) return true;
        }
    }

    const filename = asset.filename.toLowerCase();
    for (const ext of textExtensions) {
        if (filename.endsWith(ext)) return true;
    }

    return false;
}

function startEditingAsset(filename) {
    editingAssetFilename = filename;
    renderFocusTab();
    setTimeout(() => {
        const textarea = document.getElementById(`asset-content-edit`);
        if (textarea) textarea.focus();
    }, 50);
}

function cancelEditingAsset() {
    editingAssetFilename = null;
    renderFocusTab();
}

function renderAssetView(jobId, filename) {
    // Get job name for header (check both active and completed)
    let job = jobsData.find(j => j.id === jobId);
    let isCompleted = false;
    if (!job) {
        job = completedJobsData.find(j => j.id === jobId);
        isCompleted = true;
    }
    const jobName = job ? job.name : 'Job';

    // Load asset if not already loaded
    if (!currentAssetData || currentAssetData.filename !== filename || currentAssetData.jobId !== jobId) {
        loadAssetContent(jobId, filename).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">Loading...</span>
            </div>
            <div class="focus-view-content">
                <div class="empty-section">Loading asset...</div>
            </div>
        `;
    }

    const asset = currentAssetData;
    const isEditing = editingAssetFilename === filename;
    const hasContent = asset.content && asset.content.trim().length > 0;
    const isMarkdown = filename.toLowerCase().endsWith('.md');

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${escapeHtml(filename)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                ${isEditing ? `
                    <button class="task-detail-action" onclick="saveAssetContent('${jobId}', '${escapeHtml(filename)}'); cancelEditingAsset();">${icon('arrow-down-tray')} Save</button>
                    <button class="task-detail-action" onclick="cancelEditingAsset()">Cancel</button>
                ` : `
                    <button class="task-detail-action" onclick="startEditingAsset('${escapeHtml(filename)}')">${icon('pencil')} Edit</button>
                `}
                <button class="task-detail-action danger" onclick="deleteAsset('${jobId}', '${escapeHtml(filename)}'); navigateFocusBack();">${icon('trash')} Delete</button>
            </div>

            <!-- Asset Content -->
            <div class="job-section">
                <div class="job-section-header">Content</div>
                ${isEditing ? `
                    <textarea class="job-description-input" id="asset-content-edit" style="min-height: 300px;"
                        placeholder="Write content here...">${escapeHtml(asset.content || '')}</textarea>
                ` : `
                    <div class="job-description-display ${hasContent ? '' : 'empty'}" onclick="startEditingAsset('${escapeHtml(filename)}')">
                        ${hasContent ? (isMarkdown ? marked.parse(asset.content) : `<pre>${escapeHtml(asset.content)}</pre>`) : 'Click to add content...'}
                    </div>
                `}
            </div>

            <!-- Back Link -->
            <div class="job-section">
                <div class="job-section-header">Job</div>
                <div class="card-project-link" onclick="navigateFocus('${isCompleted ? 'completed' : 'job'}-${jobId}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(jobName)}</div>
            </div>
        </div>
    `;
}

function renderAssetsListView(jobId) {
    // Check both active and completed jobs
    let job = jobsData.find(j => j.id === jobId);
    let isCompleted = false;
    if (!job) {
        job = completedJobsData.find(j => j.id === jobId);
        isCompleted = true;
    }
    const jobName = job ? job.name : 'Job';
    const assets = jobAssetsCache[jobId] || [];

    // Load assets if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">Assets</span>
        </div>
        <div class="focus-view-content">
            <div class="job-section">
                <div class="job-section-header">Job</div>
                <div class="card-project-link" onclick="navigateFocus('${isCompleted ? 'completed' : 'job'}-${jobId}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(jobName)}</div>
            </div>

            <div class="task-detail-actions">
                <label class="task-detail-action" style="cursor: pointer;">
                    Upload File
                    <input type="file" style="display: none;" onchange="handleAssetUpload(event, '${jobId}')">
                </label>
            </div>

            ${assets.length > 0 ? `
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${jobId}-${asset.filename}')" style="cursor: pointer;">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="event.stopPropagation(); deleteAsset('${jobId}', '${escapeHtml(asset.filename)}')" title="Delete">x</button>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${jobId}', '${escapeHtml(asset.filename)}')" title="Delete">x</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            ` : ''}

            <div class="asset-add-row">
                <input type="text" class="asset-add-input" id="new-asset-${jobId}" placeholder="New asset name..." onkeypress="handleNewAssetKeypress(event, '${jobId}')">
                <button class="asset-add-btn" onclick="createNewAsset('${jobId}')">${icon('plus')}</button>
                <label class="asset-upload-btn">
                    Upload
                    <input type="file" style="display: none;" onchange="handleAssetUpload(event, '${jobId}')">
                </label>
            </div>
        </div>
    `;
}

// ============== New Job Screen ==============

function renderNewJobScreen(parentJobId) {
    const parentJob = jobsData.find(j => j.id === parentJobId);
    const parentName = parentJob ? parentJob.name : 'Job';
    const childJobs = jobsData.filter(j => j.parent_id === parentJobId);

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">Add Jobs</span>
        </div>
        <div class="focus-view-content">
            <div class="job-section">
                <div class="job-section-header">Add to: ${escapeHtml(parentName)}</div>
                <div class="quick-add-section" style="margin-top: 0; padding-top: 0; border-top: none;">
                    <input type="text" id="quick-add-child-${parentJobId}" class="quick-add-input" placeholder="New job name..." onkeypress="handleQuickAddChildKeypress(event, '${parentJobId}')">
                    <button class="quick-add-btn" onclick="quickAddChildJob('${parentJobId}')">${icon('plus')}</button>
                </div>
            </div>
            ${childJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Child Jobs (${childJobs.length})</div>
                ${childJobs.map(job => renderJobCard(job)).join('')}
            </div>
            ` : ''}
        </div>
    `;
}

function handleQuickAddChildKeypress(event, parentJobId) {
    if (event.key === 'Enter') {
        quickAddChildJob(parentJobId);
    }
}

async function quickAddChildJob(parentJobId) {
    const input = document.getElementById(`quick-add-child-${parentJobId}`);
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    try {
        const response = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent_id: parentJobId })
        });

        if (response.ok) {
            input.value = '';
            await loadJobsData();
            // Re-focus the input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById(`quick-add-child-${parentJobId}`);
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create job:', error);
    }
}

// ============== Attach Screen ==============

function renderAttachScreen(jobId) {
    const job = jobsData.find(j => j.id === jobId);
    const jobName = job ? job.name : 'Job';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">Add Assets</span>
        </div>
        <div class="focus-view-content">
            <div class="job-section">
                <div class="job-section-header">Add to: ${escapeHtml(jobName)}</div>

                <div class="attach-option" onclick="showNewFileForm('${jobId}')">
                    <span class="attach-option-icon">${icon('pencil')}</span>
                    <span class="attach-option-label">Create new file</span>
                </div>

                <label class="attach-option">
                    <span class="attach-option-icon">${icon('folder')}</span>
                    <span class="attach-option-label">Upload files</span>
                    <input type="file" multiple style="display: none;" onchange="handleMultiFileUpload(event, '${jobId}')">
                </label>
            </div>

            <div id="new-file-form" class="job-section" style="display: none;">
                <div class="job-section-header">New File</div>
                <input type="text" class="multi-input" id="new-file-name" placeholder="Filename (e.g., notes.md)..." style="margin-bottom: 0.5rem;">
                <textarea class="job-description-input" id="new-file-content" placeholder="Content..." style="min-height: 150px;"></textarea>
                <div class="screen-actions" style="margin-top: 0.5rem;">
                    <button class="screen-action-btn" onclick="hideNewFileForm()">Cancel</button>
                    <button class="screen-action-btn primary" onclick="createNewFileWithContent('${jobId}')">Create</button>
                </div>
            </div>
        </div>
    `;
}

function showNewFileForm(jobId) {
    document.getElementById('new-file-form').style.display = 'block';
    document.getElementById('new-file-name').focus();
}

function hideNewFileForm() {
    document.getElementById('new-file-form').style.display = 'none';
    document.getElementById('new-file-name').value = '';
    document.getElementById('new-file-content').value = '';
}

async function createNewFileWithContent(jobId) {
    let filename = document.getElementById('new-file-name').value.trim();
    const content = document.getElementById('new-file-content').value;

    if (!filename) {
        return;
    }

    // Add .md extension if no extension provided
    if (!filename.includes('.')) {
        filename = filename + '.md';
    }

    try {
        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            // Clear cache to force reload
            delete jobAssetsCache[jobId];
            // Navigate back to job detail (will trigger fresh asset load)
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to create file:', error);
    }
}

async function handleMultiFileUpload(event, jobId) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
        try {
            const content = await file.text();
            await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(file.name)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        } catch (error) {
            console.error('Failed to upload file:', error);
        }
    }

    // Clear cache to force reload
    delete jobAssetsCache[jobId];
    navigateFocusBack();
}

// ============== When Picker ==============

let whenPickerState = {
    type: null,
    id: null,
    viewDate: new Date(),
    selectedDate: null
};

function openWhenPicker(type, id) {
    whenPickerState = {
        type,
        id,
        viewDate: new Date(),
        selectedDate: null
    };

    const picker = document.createElement('div');
    picker.className = 'when-picker';
    picker.id = 'when-picker';
    picker.innerHTML = `
        <div class="when-picker-backdrop" onclick="closeWhenPicker()"></div>
        <div class="when-picker-content">
            <div class="when-picker-header">When?</div>
            <div class="when-option" onclick="setWhen('${type}', '${id}', 'today')">
                <span class="when-option-icon">${icon('sun')}</span>
                <span class="when-option-label">Today</span>
            </div>
            <div class="when-option" onclick="toggleInlineCalendar()">
                <span class="when-option-icon">${icon('calendar')}</span>
                <span class="when-option-label">Pick a date...</span>
            </div>
            <div id="inline-calendar-container"></div>
            <div class="when-option" onclick="setWhen('${type}', '${id}', 'someday')">
                <span class="when-option-icon">${icon('cloud')}</span>
                <span class="when-option-label">Someday</span>
            </div>
            <div class="when-option" onclick="setWhen('${type}', '${id}', 'clear')">
                <span class="when-option-icon">${icon('x-mark')}</span>
                <span class="when-option-label">Clear (Anytime)</span>
            </div>
        </div>
    `;
    document.body.appendChild(picker);
}

function closeWhenPicker() {
    const picker = document.getElementById('when-picker');
    if (picker) {
        picker.remove();
    }
}

function toggleInlineCalendar() {
    const container = document.getElementById('inline-calendar-container');
    if (container.innerHTML) {
        container.innerHTML = '';
    } else {
        renderInlineCalendar();
    }
}

function renderInlineCalendar() {
    const container = document.getElementById('inline-calendar-container');
    const { viewDate } = whenPickerState;
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();

    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    const dayNames = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let daysHtml = '';

    for (let i = 0; i < firstDay; i++) {
        daysHtml += '<div class="calendar-day empty"></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dateStr = formatDateISO(date);
        const isToday = date.getTime() === today.getTime();
        const isPast = date < today;
        const classes = ['calendar-day'];
        if (isToday) classes.push('today');
        if (isPast) classes.push('past');

        daysHtml += `<div class="${classes.join(' ')}" onclick="selectCalendarDate('${dateStr}')">${day}</div>`;
    }

    container.innerHTML = `
        <div class="inline-calendar">
            <div class="calendar-nav">
                <button class="calendar-nav-btn" onclick="changeCalendarMonth(-1)">‹</button>
                <div class="calendar-nav-title">
                    <span class="calendar-month" onclick="showMonthPicker()">${monthNames[month]}</span>
                    <span class="calendar-year" onclick="showYearPicker()">${year}</span>
                </div>
                <button class="calendar-nav-btn" onclick="changeCalendarMonth(1)">›</button>
            </div>
            <div id="calendar-picker-overlay"></div>
            <div class="calendar-weekdays">
                ${dayNames.map(d => `<div class="calendar-weekday">${d}</div>`).join('')}
            </div>
            <div class="calendar-days">
                ${daysHtml}
            </div>
        </div>
    `;
}

function formatDateISO(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function changeCalendarMonth(delta) {
    whenPickerState.viewDate.setMonth(whenPickerState.viewDate.getMonth() + delta);
    renderInlineCalendar();
}

function showMonthPicker() {
    const overlay = document.getElementById('calendar-picker-overlay');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const currentMonth = whenPickerState.viewDate.getMonth();

    overlay.innerHTML = `
        <div class="calendar-picker-grid months">
            ${monthNames.map((m, i) => `
                <div class="calendar-picker-item ${i === currentMonth ? 'selected' : ''}"
                     onclick="selectMonth(${i})">${m}</div>
            `).join('')}
        </div>
    `;
    overlay.style.display = 'block';
}

function selectMonth(month) {
    whenPickerState.viewDate.setMonth(month);
    document.getElementById('calendar-picker-overlay').style.display = 'none';
    renderInlineCalendar();
}

function showYearPicker() {
    const overlay = document.getElementById('calendar-picker-overlay');
    const currentYear = whenPickerState.viewDate.getFullYear();
    const startYear = currentYear - 5;
    const years = [];
    for (let y = startYear; y <= startYear + 11; y++) {
        years.push(y);
    }

    overlay.innerHTML = `
        <div class="calendar-picker-grid years">
            ${years.map(y => `
                <div class="calendar-picker-item ${y === currentYear ? 'selected' : ''}"
                     onclick="selectYear(${y})">${y}</div>
            `).join('')}
        </div>
    `;
    overlay.style.display = 'block';
}

function selectYear(year) {
    whenPickerState.viewDate.setFullYear(year);
    document.getElementById('calendar-picker-overlay').style.display = 'none';
    renderInlineCalendar();
}

function selectCalendarDate(dateStr) {
    setWhen(whenPickerState.type, whenPickerState.id, 'date', dateStr);
}

async function setWhen(type, id, whenType, date = null) {
    // Build the update payload
    let payload = {};

    if (whenType === 'today') {
        payload = { due_date: new Date().toISOString().split('T')[0], someday: false };
    } else if (whenType === 'date') {
        payload = { due_date: date, someday: false };
    } else if (whenType === 'someday') {
        payload = { due_date: '', someday: true };  // Empty string means clear
    } else if (whenType === 'clear') {
        payload = { due_date: '', someday: false };  // Empty string means clear
    }

    try {
        const response = await fetch(`/api/jobs/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            closeWhenPicker();
            await loadJobsData();
        } else {
            console.error('Failed to update when:', await response.text());
        }
    } catch (error) {
        console.error('Failed to update when:', error);
    }
}

// ============== Job Actions ==============

function showArchiveInput(event, jobId) {
    event.stopPropagation();
    if (archivingTaskId === jobId) {
        archivingTaskId = null;
    } else {
        archivingTaskId = jobId;
    }
    renderFocusTab();
    setTimeout(() => {
        const input = document.getElementById(`archive-reason-${jobId}`);
        if (input) input.focus();
    }, 50);
}

async function confirmArchiveJob(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/archive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            archivingTaskId = null;
            await loadJobsData();
            if (focusView === `job-${jobId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to archive job:', error);
    }
}

async function completeJob(event, jobId) {
    event.stopPropagation();

    try {
        const response = await fetch(`/api/jobs/${jobId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            await loadJobsData();
            if (focusView === `job-${jobId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to complete job:', error);
    }
}

async function restoreJob(event, jobId) {
    event.stopPropagation();

    try {
        const response = await fetch(`/api/jobs/${jobId}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            await loadJobsData();
            if (focusView === `completed-${jobId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to restore job:', error);
    }
}

async function deleteJob(event, jobId) {
    event.stopPropagation();
    if (!confirm('Delete this job?')) return;

    const wasViewingJob = focusView === `job-${jobId}` || focusView === `completed-${jobId}`;

    try {
        const response = await fetch(`/api/jobs/${jobId}?delete_children=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadJobsData();
            if (wasViewingJob) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to delete job:', error);
    }
}

async function quickAddJob(inputId, parentId = null) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    try {
        const body = { name };
        if (parentId) {
            body.parent_id = parentId;
        }

        const response = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            input.value = '';
            await loadJobsData();
            // Re-focus the input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById(inputId);
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create job:', error);
    }
}

function handleQuickAddKeypress(event, inputId, parentId = null) {
    if (event.key === 'Enter') {
        quickAddJob(inputId, parentId);
    }
}

async function quickDeleteJob(event, jobId) {
    event.stopPropagation();
    if (!confirm('Delete this job and all children?')) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}?delete_children=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadJobsData();
        }
    } catch (error) {
        console.error('Failed to delete job:', error);
    }
}

// ============== Job Editing ==============

function startEditingField(jobId, field) {
    editingJobField = { jobId, field };
    renderFocusTab();

    // Focus the input after render
    setTimeout(() => {
        const input = document.getElementById(`edit-${field}-${jobId}`);
        if (input) {
            input.focus();
            if (input.tagName === 'INPUT') {
                input.select();
            }
        }
    }, 50);
}

function cancelEditing() {
    editingJobField = null;
    renderFocusTab();
}

async function saveJobField(jobId, field, value) {
    try {
        const body = {};
        body[field] = value;

        const response = await fetch(`/api/jobs/${jobId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            editingJobField = null;
            await loadJobsData();
        }
    } catch (error) {
        console.error('Failed to save job field:', error);
    }
}

function handleEditKeypress(event, jobId, field) {
    if (event.key === 'Enter' && field === 'name') {
        saveJobField(jobId, field, event.target.value);
    } else if (event.key === 'Escape') {
        cancelEditing();
    }
}

function handleDescriptionKeypress(event, jobId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveJobField(jobId, 'description', event.target.value);
    }
}

// Functions for editing completed jobs
async function saveCompletedJobField(jobId, field, value) {
    try {
        const body = {};
        body[field] = value;

        const response = await fetch(`/api/jobs/${jobId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            editingJobField = null;
            await loadJobsData();
        }
    } catch (error) {
        console.error('Failed to save completed job field:', error);
    }
}

function handleCompletedDescriptionKeypress(event, jobId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveCompletedJobField(jobId, 'description', event.target.value);
    }
}

// ============== Assets Management ==============

async function loadJobAssets(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/assets`);
        if (response.ok) {
            const assets = await response.json();
            jobAssetsCache[jobId] = assets;
            return assets;
        }
    } catch (error) {
        console.error('Failed to load assets:', error);
    }
    return [];
}

async function deleteAsset(jobId, filename) {
    if (!confirm(`Delete asset "${filename}"?`)) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadJobAssets(jobId);
            renderFocusTab();
        }
    } catch (error) {
        console.error('Failed to delete asset:', error);
    }
}

async function uploadAsset(jobId, file) {
    try {
        // Read file as text (for now, only supporting text files)
        const content = await file.text();

        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(file.name)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            await loadJobAssets(jobId);
            renderFocusTab();
        }
    } catch (error) {
        console.error('Failed to upload asset:', error);
    }
}

function handleAssetUpload(event, jobId) {
    const file = event.target.files[0];
    if (file) {
        uploadAsset(jobId, file);
        event.target.value = ''; // Reset input
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function loadAssetContent(jobId, filename) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(filename)}`);
        if (response.ok) {
            currentAssetData = await response.json();
            currentAssetData.jobId = jobId;
            return currentAssetData;
        }
    } catch (error) {
        console.error('Failed to load asset:', error);
    }
    return null;
}

async function saveAssetContent(jobId, filename) {
    const textarea = document.getElementById('asset-content-edit');
    if (!textarea) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: textarea.value })
        });

        if (response.ok) {
            // Update current data and refresh cache
            currentAssetData.content = textarea.value;
            await loadJobAssets(jobId);
        }
    } catch (error) {
        console.error('Failed to save asset:', error);
    }
}

async function createNewAsset(jobId) {
    const input = document.getElementById(`new-asset-${jobId}`);
    if (!input) return;

    let filename = input.value.trim();
    if (!filename) return;

    // Add .md extension if no extension provided
    if (!filename.includes('.')) {
        filename = filename + '.md';
    }

    try {
        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: '' })
        });

        if (response.ok) {
            input.value = '';
            await loadJobAssets(jobId);
            // Navigate to the new asset
            navigateFocus(`asset-${jobId}-${filename}`);
        }
    } catch (error) {
        console.error('Failed to create asset:', error);
    }
}

function handleNewAssetKeypress(event, jobId) {
    if (event.key === 'Enter') {
        createNewAsset(jobId);
    }
}

// ============== Assignment Management ==============

function getAssigneesLabel(job) {
    const assignees = job.assignees || [];
    if (job.in_progress_by) {
        return `${icon('bolt')} ${job.in_progress_by}`;
    }
    if (assignees.length === 0) {
        return `${icon('user')} Assign`;
    }
    if (assignees.length === 1) {
        return `${icon('user')} ${assignees[0]}`;
    }
    return `${icon('user')} ${assignees.length} assigned`;
}

async function openAssigneesPicker(jobId) {
    const job = jobsData.find(j => j.id === jobId) || completedJobsData.find(j => j.id === jobId);
    if (!job) return;

    const agents = await loadAgents();
    const currentAssignees = job.assignees || [];

    const picker = document.createElement('div');
    picker.className = 'assignees-picker';
    picker.id = 'assignees-picker';
    picker.innerHTML = `
        <div class="assignees-picker-backdrop" onclick="closeAssigneesPicker()"></div>
        <div class="assignees-picker-content">
            <div class="assignees-picker-header">Assign Agents</div>
            ${job.in_progress_by ? `
                <div class="assignees-picker-working">
                    <span class="assignees-picker-working-icon">${icon('bolt')}</span>
                    <span>Currently working: <strong>${escapeHtml(job.in_progress_by)}</strong></span>
                </div>
            ` : ''}
            ${agents.map(agent => {
                const isAssigned = currentAssignees.includes(agent.id);
                return `
                    <div class="assignees-option ${isAssigned ? 'assigned' : ''}" onclick="toggleAgentAssignment('${jobId}', '${agent.id}', ${isAssigned})">
                        <span class="assignees-option-check">${isAssigned ? icon('check') : ''}</span>
                        <span class="assignees-option-label">${escapeHtml(agent.name || agent.id)}</span>
                    </div>
                `;
            }).join('')}
            ${agents.length === 0 ? '<div class="assignees-empty">No agents available</div>' : ''}
        </div>
    `;
    document.body.appendChild(picker);
}

function closeAssigneesPicker() {
    const picker = document.getElementById('assignees-picker');
    if (picker) {
        picker.remove();
    }
}

async function toggleAgentAssignment(jobId, agentId, isCurrentlyAssigned) {
    try {
        const endpoint = isCurrentlyAssigned ? 'unassign' : 'assign';
        const response = await fetch(`/api/jobs/${jobId}/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agentId })
        });

        if (response.ok) {
            await loadJobsData();
            closeAssigneesPicker();
            // Reopen picker to show updated state
            openAssigneesPicker(jobId);
        } else {
            const error = await response.json();
            console.error(`Failed to ${endpoint} agent:`, error);
        }
    } catch (error) {
        console.error('Failed to toggle assignment:', error);
    }
}

// ============== Add Picker ==============

function openAddPicker(jobId) {
    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'add-picker';
    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeAddPicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Add</div>
            <div class="picker-option" onclick="closeAddPicker(); navigateFocus('newjob-${jobId}')">
                <span class="picker-option-icon">${icon('queue-list')}</span>
                <span class="picker-option-label">Jobs</span>
            </div>
            <div class="picker-option" onclick="closeAddPicker(); navigateFocus('attach-${jobId}')">
                <span class="picker-option-icon">${icon('link')}</span>
                <span class="picker-option-label">Assets</span>
            </div>
        </div>
    `;
    document.body.appendChild(picker);
}

function closeAddPicker() {
    const picker = document.getElementById('add-picker');
    if (picker) picker.remove();
}

// ============== More Picker ==============

function openMorePicker(jobId) {
    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'more-picker';
    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeMorePicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Actions</div>
            <div class="picker-option" onclick="closeMorePicker(); completeJobDirect('${jobId}')">
                <span class="picker-option-icon">${icon('check')}</span>
                <span class="picker-option-label">Complete</span>
            </div>
            <div class="picker-option" onclick="closeMorePicker(); archiveJobDirect('${jobId}')">
                <span class="picker-option-icon">${icon('archive-box')}</span>
                <span class="picker-option-label">Archive</span>
            </div>
            <div class="picker-option danger" onclick="closeMorePicker(); deleteJobDirect('${jobId}')">
                <span class="picker-option-icon">${icon('trash')}</span>
                <span class="picker-option-label">Delete</span>
            </div>
        </div>
    `;
    document.body.appendChild(picker);
}

function closeMorePicker() {
    const picker = document.getElementById('more-picker');
    if (picker) picker.remove();
}

async function completeJobDirect(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/complete`, { method: 'POST' });
        if (response.ok) {
            await loadJobsData();
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to complete job:', error);
    }
}

async function archiveJobDirect(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/archive`, { method: 'POST' });
        if (response.ok) {
            await loadJobsData();
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to archive job:', error);
    }
}

async function deleteJobDirect(jobId) {
    if (!confirm('Delete this job?')) return;
    try {
        const response = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
        if (response.ok) {
            await loadJobsData();
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to delete job:', error);
    }
}

