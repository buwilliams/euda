// Euno - Focus Tab (Jobs with infinite nesting)

// ============== State ==============

let jobsData = [];           // All active jobs
let completedJobsData = [];  // Recently completed jobs

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
                    <span class="focus-menu-arrow">›</span>
                </div>
            `}).join('')}
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

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = jobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <div class="task-detail">
                ${hasDescription ? `<div class="task-detail-description">${marked.parse(job.description)}</div>` : ''}
                ${parentName ? `
                <div class="task-detail-meta">
                    <span class="task-detail-label">Parent:</span>
                    <span class="task-detail-value card-project-link" onclick="navigateFocus('job-${job.parent_id}')">${escapeHtml(parentName)}</span>
                </div>
                ` : ''}
                <div class="task-detail-meta">
                    <span class="task-detail-label">When:</span>
                    <span class="task-detail-value">${escapeHtml(whenLabel)}</span>
                </div>
                ${job.tags && job.tags.length > 0 ? `
                <div class="task-detail-meta">
                    <span class="task-detail-label">Tags:</span>
                    <span class="task-detail-value">${job.tags.map(t => escapeHtml(t)).join(', ')}</span>
                </div>
                ` : ''}
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('job', '${job.id}')">📅 Change When</button>
                <button class="task-detail-action" onclick="completeJob(event, '${job.id}')">✓ Complete</button>
                <button class="task-detail-action" onclick="showArchiveInput(event, '${job.id}')">${isArchiving ? 'Cancel' : '📦 Archive'}</button>
                <button class="task-detail-action danger" onclick="deleteJob(event, '${job.id}')">🗑 Delete</button>
            </div>
            ${isArchiving ? `
            <div class="card-archive-form">
                <input type="text" class="card-archive-input" id="archive-reason-${job.id}" placeholder="Reason (optional)..." onkeypress="if(event.key==='Enter')confirmArchiveJob('${job.id}')">
                <button class="card-archive-btn confirm" onclick="confirmArchiveJob('${job.id}')">Archive</button>
            </div>
            ` : ''}
            ${childJobs.length > 0 ? `
            <div class="section-header">CHILD JOBS (${childJobs.length})</div>
            ${childJobs.map(child => renderJobCard(child)).join('')}
            ` : ''}
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
        payload = { due_date: null, someday: true };
    } else if (whenType === 'clear') {
        payload = { due_date: null, someday: false };
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
