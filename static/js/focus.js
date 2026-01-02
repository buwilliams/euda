// Euno - Focus Tab (Jobs with infinite nesting)

// ============== State ==============

let jobsData = [];           // All active jobs
let completedJobsData = [];  // Recently completed jobs
let jobAssetsCache = {};     // Cache of assets per job
let jobNotesCache = {};      // Cache of notes per job
let editingJobField = null;  // Which field is being edited: {jobId, field}
let currentNoteData = null;  // Currently viewed note

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
    const counts = { today: 0, upcoming: 0, anytime: 0, someday: 0, logbook: 0, toplevel: 0 };

    jobsData.forEach(job => {
        const category = getJobCategory(job);
        if (category !== 'logbook') {
            counts[category]++;
        }
        if (!job.parent_id) {
            counts.toplevel++;
        }
    });

    counts.logbook = completedJobsData.length;
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
    } else if (focusView === 'logbook') {
        content = renderLogbookView();
    } else if (focusView.startsWith('note-')) {
        // note-{jobId}-{noteId}
        const parts = focusView.substring(5).split('-');
        const jobId = parts[0];
        const noteId = parts.slice(1).join('-');
        content = renderNoteView(jobId, noteId);
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

    return `
        <div class="focus-menu">
            <div class="focus-menu-item" onclick="navigateFocus('today')">
                <span class="focus-menu-icon">☀️</span>
                <span class="focus-menu-label">Today</span>
                <span class="focus-menu-count">${counts.today}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('upcoming')">
                <span class="focus-menu-icon">📅</span>
                <span class="focus-menu-label">Upcoming</span>
                <span class="focus-menu-count">${counts.upcoming}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('anytime')">
                <span class="focus-menu-icon">⏳</span>
                <span class="focus-menu-label">Anytime</span>
                <span class="focus-menu-count">${counts.anytime}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('someday')">
                <span class="focus-menu-icon">💭</span>
                <span class="focus-menu-label">Someday</span>
                <span class="focus-menu-count">${counts.someday}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('logbook')">
                <span class="focus-menu-icon">📖</span>
                <span class="focus-menu-label">Logbook</span>
                <span class="focus-menu-count">${counts.logbook}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            ${topLevelJobs.map(job => {
                const childCount = jobsData.filter(j => j.parent_id === job.id).length;
                return `
                <div class="focus-menu-item" onclick="navigateFocus('job-${job.id}')">
                    <span class="focus-menu-icon">📁</span>
                    <span class="focus-menu-label">${escapeHtml(job.name)}</span>
                    <span class="focus-menu-count">${childCount}</span>
                    <button class="card-trash-btn" onclick="quickDeleteJob(event, '${job.id}')" title="Delete job">🗑</button>
                    <span class="focus-menu-arrow">›</span>
                </div>
            `}).join('')}
        </div>
        <div class="quick-add-section">
            <input type="text" id="quick-add-root" class="quick-add-input" placeholder="Add new job..." onkeypress="handleQuickAddKeypress(event, 'quick-add-root')">
            <button class="quick-add-btn" onclick="quickAddJob('quick-add-root')">+</button>
        </div>
    `;
}

function getTimelineIcon(category) {
    const icons = { today: '☀️', upcoming: '📅', anytime: '⏳', someday: '💭' };
    return icons[category] || '';
}

function renderTimelineView(category, title) {
    const jobs = jobsData.filter(j => getJobCategory(j) === category);
    const icon = getTimelineIcon(category);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${icon} ${title}</span>
        </div>
        <div class="focus-view-content">
            ${jobs.length === 0
                ? '<div class="focus-empty">No jobs</div>'
                : jobs.map(job => renderJobCard(job)).join('')
            }
        </div>
    `;
}

function renderLogbookView() {
    const jobs = completedJobsData.slice(0, 20);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">📖 Logbook</span>
        </div>
        <div class="focus-view-content">
            ${jobs.length === 0
                ? '<div class="focus-empty">No completed jobs</div>'
                : jobs.map(job => renderCompletedJobCard(job)).join('')
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

    return `
        <div class="card card-minimal" data-job-id="${job.id}" onclick="navigateFocus('job-${job.id}')">
            <span class="card-title">${escapeHtml(displayName)}</span>
            ${childBadge}
            ${dueDateLabel}
            <button class="card-trash-btn" onclick="quickDeleteJob(event, '${job.id}')" title="Delete job">🗑</button>
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
                <button class="card-action" onclick="event.stopPropagation(); openWhenPicker('job', '${job.id}')">📅 ${escapeHtml(whenLabel)}</button>
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
                <span class="focus-back-btn">←</span>
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
    const assets = jobAssetsCache[jobId] || [];
    const notes = jobNotesCache[jobId] || [];

    // Check if we're editing this job
    const isEditingName = editingJobField?.jobId === jobId && editingJobField?.field === 'name';
    const isEditingDesc = editingJobField?.jobId === jobId && editingJobField?.field === 'description';

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = jobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    // Load assets and notes if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
    }
    if (!jobNotesCache[jobId]) {
        loadJobNotes(jobId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('job', '${job.id}')">📅 ${escapeHtml(whenLabel)}</button>
                <button class="task-detail-action" onclick="completeJob(event, '${job.id}')">✓ Complete</button>
                <button class="task-detail-action" onclick="showArchiveInput(event, '${job.id}')">${isArchiving ? 'Cancel' : '📦 Archive'}</button>
                <label class="task-detail-action" style="cursor: pointer;">
                    📎 Upload
                    <input type="file" style="display: none;" onchange="handleAssetUpload(event, '${job.id}')">
                </label>
                <button class="task-detail-action danger" onclick="deleteJob(event, '${job.id}')">🗑 Delete</button>
            </div>
            ${isArchiving ? `
            <div class="card-archive-form">
                <input type="text" class="card-archive-input" id="archive-reason-${job.id}" placeholder="Reason (optional)..." onkeypress="if(event.key==='Enter')confirmArchiveJob('${job.id}')">
                <button class="card-archive-btn confirm" onclick="confirmArchiveJob('${job.id}')">Archive</button>
            </div>
            ` : ''}

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

            <!-- Parent Link -->
            ${parentName ? `
            <div class="job-section">
                <div class="job-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('job-${job.parent_id}')" style="padding: 0.5rem; cursor: pointer;">📁 ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

            <!-- Assets Section -->
            <div class="job-section">
                <div class="job-section-header">Assets${assets.length > 0 ? ` (${assets.length})` : ''}</div>
                ${assets.length > 0 ? `
                    <div class="asset-list">
                        ${assets.map(asset => `
                            <div class="asset-item">
                                <span class="asset-item-name">📎 ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">✕</button>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="empty-section">No assets attached</div>
                `}
            </div>

            <!-- Notes Section -->
            <div class="job-section">
                <div class="job-section-header">Notes${notes.length > 0 ? ` (${notes.length})` : ''}</div>
                ${notes.length > 0 ? `
                    <div class="notes-list">
                        ${notes.map(note => `
                            <div class="note-item" onclick="navigateFocus('note-${job.id}-${note.id}')" style="cursor: pointer;">
                                <div class="note-item-header">
                                    <span class="note-item-agent">📝 ${escapeHtml(note.title)}</span>
                                    <span class="note-item-time">${formatNoteTime(note.modified_at)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="empty-section">No notes yet</div>
                `}
                <div class="note-add">
                    <input type="text" class="note-add-input" id="note-title-${job.id}" placeholder="New note title..." onkeypress="handleNoteCreateKeypress(event, '${job.id}')">
                    <button class="note-add-btn" onclick="createNote('${job.id}')">+ Note</button>
                </div>
            </div>

            <!-- Child Jobs Section -->
            <div class="job-section">
                <div class="job-section-header">Child Jobs${childJobs.length > 0 ? ` (${childJobs.length})` : ''}</div>
                ${childJobs.map(child => renderJobCard(child)).join('')}
                <div class="quick-add-section" style="border-top: none; margin-top: 0;">
                    <input type="text" id="quick-add-${job.id}" class="quick-add-input" placeholder="Add child job..." onkeypress="handleQuickAddKeypress(event, 'quick-add-${job.id}', '${job.id}')">
                    <button class="quick-add-btn" onclick="quickAddJob('quick-add-${job.id}', '${job.id}')">+</button>
                </div>
            </div>
        </div>
    `;
}

function renderCompletedJobDetailView(jobId) {
    const job = completedJobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">←</span>
                <span class="focus-view-title">Job Not Found</span>
            </div>
            <div class="focus-empty">This job no longer exists.</div>
        `;
    }

    const displayName = job.name || 'Untitled';
    const hasDescription = job.description && job.description.length > 0;
    const completedDate = job.completed_at ? new Date(job.completed_at).toLocaleDateString() : 'Unknown';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <div class="task-detail">
                ${hasDescription ? `<div class="task-detail-description">${marked.parse(job.description)}</div>` : ''}
                <div class="task-detail-meta">
                    <span class="task-detail-label">Completed:</span>
                    <span class="task-detail-value">${escapeHtml(completedDate)}</span>
                </div>
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="restoreJob(event, '${job.id}')">↩ Restore</button>
                <button class="task-detail-action danger" onclick="deleteJob(event, '${job.id}')">🗑 Delete</button>
            </div>
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

function renderCompletedJobCard(job) {
    const displayName = job.name || 'Untitled';
    const completedDateLabel = job.completed_at ? `<span class="card-due-date">${formatFriendlyPastDate(job.completed_at)}</span>` : '';

    return `
        <div class="card card-minimal" data-job-id="${job.id}" style="opacity: 0.7;" onclick="navigateFocus('completed-${job.id}')">
            <span class="card-title" style="text-decoration: line-through; color: #888;">${escapeHtml(displayName)}</span>
            ${completedDateLabel}
            <span class="card-arrow">›</span>
        </div>
    `;
}

function renderNoteView(jobId, noteId) {
    // Get job name for header
    const job = jobsData.find(j => j.id === jobId);
    const jobName = job ? job.name : 'Job';

    // Load note if not already loaded
    if (!currentNoteData || currentNoteData.id !== noteId) {
        loadNoteContent(jobId, noteId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocus('job-${jobId}')">
                <span class="focus-back-btn">←</span>
                <span class="focus-view-title">Loading...</span>
            </div>
            <div class="focus-view-content">
                <div class="empty-section">Loading note...</div>
            </div>
        `;
    }

    const note = currentNoteData;

    return `
        <div class="focus-view-header" onclick="navigateFocus('job-${jobId}')">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${escapeHtml(note.title)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="saveNoteContent('${jobId}', '${noteId}')">💾 Save</button>
                <button class="task-detail-action danger" onclick="deleteNote('${jobId}', '${noteId}')">🗑 Delete</button>
            </div>

            <!-- Note Content -->
            <div class="job-section">
                <div class="job-section-header">
                    Content
                    <span class="note-item-time">Last modified: ${formatNoteTime(note.modified_at)}</span>
                </div>
                <textarea class="job-description-input" id="note-content-${noteId}" style="min-height: 300px;"
                    placeholder="Write your note here...">${escapeHtml(note.content || '')}</textarea>
            </div>

            <!-- Back Link -->
            <div class="job-section">
                <div class="job-section-header">Job</div>
                <div class="card-project-link" onclick="navigateFocus('job-${jobId}')" style="padding: 0.5rem; cursor: pointer;">📁 ${escapeHtml(jobName)}</div>
            </div>
        </div>
    `;
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
                <span class="when-option-icon">☀️</span>
                <span class="when-option-label">Today</span>
            </div>
            <div class="when-option" onclick="toggleInlineCalendar()">
                <span class="when-option-icon">📅</span>
                <span class="when-option-label">Pick a date...</span>
            </div>
            <div id="inline-calendar-container"></div>
            <div class="when-option" onclick="setWhen('${type}', '${id}', 'someday')">
                <span class="when-option-icon">💭</span>
                <span class="when-option-label">Someday</span>
            </div>
            <div class="when-option" onclick="setWhen('${type}', '${id}', 'clear')">
                <span class="when-option-icon">✕</span>
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

// ============== Notes Management ==============

async function loadJobNotes(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/notes`);
        if (response.ok) {
            const notes = await response.json();
            jobNotesCache[jobId] = notes;
            return notes;
        }
    } catch (error) {
        console.error('Failed to load notes:', error);
    }
    return [];
}

async function createNote(jobId) {
    const titleInput = document.getElementById(`note-title-${jobId}`);
    if (!titleInput) return;

    const title = titleInput.value.trim();
    if (!title) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content: '', agent: 'user' })
        });

        if (response.ok) {
            const note = await response.json();
            titleInput.value = '';
            await loadJobNotes(jobId);
            // Navigate to the new note
            navigateFocus(`note-${jobId}-${note.id}`);
        }
    } catch (error) {
        console.error('Failed to create note:', error);
    }
}

function handleNoteCreateKeypress(event, jobId) {
    if (event.key === 'Enter') {
        createNote(jobId);
    }
}

async function loadNoteContent(jobId, noteId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/notes/${noteId}`);
        if (response.ok) {
            currentNoteData = await response.json();
            currentNoteData.jobId = jobId;
            return currentNoteData;
        }
    } catch (error) {
        console.error('Failed to load note:', error);
    }
    return null;
}

async function saveNoteContent(jobId, noteId) {
    const textarea = document.getElementById(`note-content-${noteId}`);
    if (!textarea) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}/notes/${noteId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: textarea.value })
        });

        if (response.ok) {
            // Refresh cache
            await loadJobNotes(jobId);
        }
    } catch (error) {
        console.error('Failed to save note:', error);
    }
}

async function deleteNote(jobId, noteId) {
    if (!confirm('Delete this note?')) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}/notes/${noteId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadJobNotes(jobId);
            // Navigate back to job
            navigateFocus(`job-${jobId}`);
        }
    } catch (error) {
        console.error('Failed to delete note:', error);
    }
}

function formatNoteTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

// ============== Legacy Aliases ==============

// These maintain backwards compatibility with other parts of the UI

async function toggleTask(event, taskId) {
    // In the old system this toggled between pending/completed
    // For jobs, just complete it
    return completeJob(event, taskId);
}

async function deleteTask(event, taskId) {
    return deleteJob(event, taskId);
}

function renderTaskCard(task) {
    return renderJobCard(task);
}

function renderCompletedTaskCard(task) {
    return renderCompletedJobCard(task);
}
