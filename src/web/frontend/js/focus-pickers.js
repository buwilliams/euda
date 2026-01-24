// Euno - Focus Pickers (When, Assignees, Add, More)

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
        payload = { due_date: getLocalDateString(), someday: false };
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

// ============== Assignees Picker ==============

function getAssigneesLabel(job) {
    const assignee = job.assignee;
    if (job.status === 'working') {
        return `${icon('bolt')} ${assignee || 'Working'}`;
    }
    if (!assignee) {
        return `${icon('user')} Assign`;
    }
    return `${icon('user')} ${assignee}`;
}

async function openAssigneesPicker(jobId) {
    const job = jobsData.find(j => j.id === jobId) || completedJobsData.find(j => j.id === jobId);
    if (!job) return;

    const agents = await loadAgents();
    const currentAssignee = job.assignee;

    const picker = document.createElement('div');
    picker.className = 'assignees-picker';
    picker.id = 'assignees-picker';
    picker.innerHTML = `
        <div class="assignees-picker-backdrop" onclick="closeAssigneesPicker()"></div>
        <div class="assignees-picker-content">
            <div class="assignees-picker-header">Assign Agent</div>
            ${job.status === 'working' ? `
                <div class="assignees-picker-working">
                    <span class="assignees-picker-working-icon">${icon('bolt')}</span>
                    <span>Currently working: <strong>${escapeHtml(currentAssignee || 'unknown')}</strong></span>
                </div>
            ` : ''}
            ${agents.map(agent => {
                const isAssigned = currentAssignee === agent.id;
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

// ============== State Picker ==============

function openStatePicker(jobId) {
    const job = jobsData.find(j => j.id === jobId) || completedJobsData.find(j => j.id === jobId);
    const currentStatus = job?.status || 'todo';

    const statuses = [
        { value: 'todo', label: 'To Do', icon: 'queue-list' },
        { value: 'working', label: 'Working', icon: 'bolt' },
        { value: 'done', label: 'Done', icon: 'check' },
        { value: 'error', label: 'Error', icon: 'exclamation-triangle' },
        { value: 'archived', label: 'Archived', icon: 'archive-box' }
    ];

    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'state-picker';
    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeStatePicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Status</div>
            ${statuses.map(s => `
                <div class="picker-option ${s.value === currentStatus ? 'selected' : ''}" onclick="selectJobState('${jobId}', '${s.value}')">
                    <span class="picker-option-icon">${icon(s.icon)}</span>
                    <span class="picker-option-label">${s.label}</span>
                    ${s.value === currentStatus ? `<span class="picker-option-check">${icon('check')}</span>` : ''}
                </div>
            `).join('')}
        </div>
    `;
    document.body.appendChild(picker);
}

function closeStatePicker() {
    const picker = document.getElementById('state-picker');
    if (picker) picker.remove();
}

async function selectJobState(jobId, status) {
    closeStatePicker();
    await setJobStatus(jobId, status);
}

// ============== Reassign Picker ==============

async function openReassignPicker(jobId) {
    const agents = await loadAgents();

    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'reassign-picker';
    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeReassignPicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Reassign To</div>
            <div class="picker-description">Assigns agent and sets status to "todo"</div>
            ${agents.map(agent => `
                <div class="picker-option" onclick="selectReassignAgent('${jobId}', '${agent.id}')">
                    <span class="picker-option-icon">${icon('bolt')}</span>
                    <span class="picker-option-label">${escapeHtml(agent.name || agent.id)}</span>
                </div>
            `).join('')}
            ${agents.length === 0 ? '<div class="picker-empty">No agents available</div>' : ''}
        </div>
    `;
    document.body.appendChild(picker);
}

function closeReassignPicker() {
    const picker = document.getElementById('reassign-picker');
    if (picker) picker.remove();
}

async function selectReassignAgent(jobId, agentId) {
    closeReassignPicker();
    await reassignJob(jobId, agentId);
}

// ============== Job Status Label ==============

function getJobStatusLabel(job) {
    const status = job?.status || 'todo';
    const labels = {
        'todo': 'To Do',
        'working': 'Working',
        'done': 'Done',
        'error': 'Error',
        'archived': 'Archived'
    };
    return labels[status] || status;
}

function getJobStatusIcon(job) {
    const status = job?.status || 'todo';
    const icons = {
        'todo': 'queue-list',
        'working': 'bolt',
        'done': 'check',
        'error': 'exclamation-triangle',
        'archived': 'archive-box'
    };
    return icon(icons[status] || 'queue-list');
}
