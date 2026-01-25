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
        const response = await fetch(`/api/topics/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            closeWhenPicker();
            await loadTopicsData();
        } else {
            console.error('Failed to update when:', await response.text());
        }
    } catch (error) {
        console.error('Failed to update when:', error);
    }
}

// ============== Assignees Picker ==============

function getAssigneesLabel(topic) {
    const assignee = topic.assignee;
    if (topic.status === 'working') {
        return `${icon('bolt')} ${assignee || 'Working'}`;
    }
    if (!assignee) {
        return `${icon('user')} Assign`;
    }
    return `${icon('user')} ${assignee}`;
}

async function openAssigneesPicker(topicId) {
    const topic = allTopicsData.find(j => j.id === topicId);
    if (!topic) return;

    const agents = await loadAgents();
    const currentAssignee = topic.assignee;

    const picker = document.createElement('div');
    picker.className = 'assignees-picker';
    picker.id = 'assignees-picker';
    picker.innerHTML = `
        <div class="assignees-picker-backdrop" onclick="closeAssigneesPicker()"></div>
        <div class="assignees-picker-content">
            <div class="assignees-picker-header">Assign Agent</div>
            ${topic.status === 'working' ? `
                <div class="assignees-picker-working">
                    <span class="assignees-picker-working-icon">${icon('bolt')}</span>
                    <span>Currently working: <strong>${escapeHtml(currentAssignee || 'unknown')}</strong></span>
                </div>
            ` : ''}
            ${agents.map(agent => {
                const isAssigned = currentAssignee === agent.id;
                return `
                    <div class="assignees-option ${isAssigned ? 'assigned' : ''}" onclick="toggleAgentAssignment('${topicId}', '${agent.id}', ${isAssigned})">
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

async function toggleAgentAssignment(topicId, agentId, isCurrentlyAssigned) {
    try {
        const endpoint = isCurrentlyAssigned ? 'unassign' : 'assign';
        const response = await fetch(`/api/topics/${topicId}/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agentId })
        });

        if (response.ok) {
            // Backend handles resetting status to 'todo' if topic was 'working'
            await loadTopicsData();
            closeAssigneesPicker();
            // Reopen picker to show updated state
            openAssigneesPicker(topicId);
        } else {
            const error = await response.json();
            console.error(`Failed to ${endpoint} agent:`, error);
        }
    } catch (error) {
        console.error('Failed to toggle assignment:', error);
    }
}

// ============== Add Picker ==============

function openAddPicker(topicId) {
    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'add-picker';
    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeAddPicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Add</div>
            <div class="picker-option" onclick="closeAddPicker(); navigateFocus('newtopic-${topicId}')">
                <span class="picker-option-icon">${icon('queue-list')}</span>
                <span class="picker-option-label">Topics</span>
            </div>
            <div class="picker-option" onclick="closeAddPicker(); navigateFocus('attach-${topicId}')">
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

function openMorePicker(topicId) {
    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'more-picker';
    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeMorePicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Actions</div>
            <div class="picker-option" onclick="closeMorePicker(); completeTopicDirect('${topicId}')">
                <span class="picker-option-icon">${icon('check')}</span>
                <span class="picker-option-label">Complete</span>
            </div>
            <div class="picker-option" onclick="closeMorePicker(); archiveTopicDirect('${topicId}')">
                <span class="picker-option-icon">${icon('archive-box')}</span>
                <span class="picker-option-label">Archive</span>
            </div>
            <div class="picker-option danger" onclick="closeMorePicker(); deleteTopicDirect('${topicId}')">
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

async function completeTopicDirect(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/complete`, { method: 'POST' });
        if (response.ok) {
            await loadTopicsData();
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to complete topic:', error);
    }
}

async function archiveTopicDirect(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/archive`, { method: 'POST' });
        if (response.ok) {
            await loadTopicsData();
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to archive topic:', error);
    }
}

async function deleteTopicDirect(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}`, { method: 'DELETE' });
        if (response.ok) {
            await loadTopicsData();
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to delete topic:', error);
    }
}

// ============== State Picker ==============

function openStatePicker(topicId) {
    const topic = allTopicsData.find(j => j.id === topicId);
    const currentStatus = topic?.status || 'todo';

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
                <div class="picker-option ${s.value === currentStatus ? 'selected' : ''}" onclick="selectTopicState('${topicId}', '${s.value}')">
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

async function selectTopicState(topicId, status) {
    closeStatePicker();
    await setTopicStatus(topicId, status);
}


// ============== Agent Controls Picker ==============

function openAgentControlsPicker(agentId) {
    const data = window._agentControlsData?.[agentId];
    const agentState = data?.state || 'enabled';

    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'agent-controls-picker';

    // Build options based on current state
    let options = '';

    if (agentState === 'enabled') {
        options = `
            <div class="picker-option" onclick="closeAgentControlsPicker(); pauseAgent('${agentId}')">
                <span class="picker-option-icon">${icon('pause')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Pause</span>
                    <span class="picker-option-description">Temporarily stop agent from working</span>
                </div>
            </div>
            <div class="picker-option" onclick="closeAgentControlsPicker(); disableAgent('${agentId}')">
                <span class="picker-option-icon">${icon('x-mark')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Disable</span>
                    <span class="picker-option-description">Turn off agent completely</span>
                </div>
            </div>
            <div class="picker-option" onclick="closeAgentControlsPicker(); resetAgentTokenUsage('${agentId}')">
                <span class="picker-option-icon">${icon('arrow-path')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Reset Tokens</span>
                    <span class="picker-option-description">Reset token usage for current period</span>
                </div>
            </div>
        `;
    } else if (agentState === 'paused') {
        options = `
            <div class="picker-option" onclick="closeAgentControlsPicker(); enableAgent('${agentId}')">
                <span class="picker-option-icon">${icon('play')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Resume</span>
                    <span class="picker-option-description">Resume agent operations</span>
                </div>
            </div>
            <div class="picker-option" onclick="closeAgentControlsPicker(); resetAgentTokenUsage('${agentId}')">
                <span class="picker-option-icon">${icon('arrow-path')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Reset Tokens</span>
                    <span class="picker-option-description">Reset token usage for current period</span>
                </div>
            </div>
        `;
    } else if (agentState === 'disabled') {
        options = `
            <div class="picker-option" onclick="closeAgentControlsPicker(); enableAgent('${agentId}')">
                <span class="picker-option-icon">${icon('check')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Enable</span>
                    <span class="picker-option-description">Turn on agent</span>
                </div>
            </div>
            <div class="picker-option" onclick="closeAgentControlsPicker(); resetAgentTokenUsage('${agentId}')">
                <span class="picker-option-icon">${icon('arrow-path')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">Reset Tokens</span>
                    <span class="picker-option-description">Reset token usage for current period</span>
                </div>
            </div>
        `;
    }

    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeAgentControlsPicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Controls</div>
            ${options}
        </div>
    `;
    document.body.appendChild(picker);
}

function closeAgentControlsPicker() {
    const picker = document.getElementById('agent-controls-picker');
    if (picker) picker.remove();
}


// ============== Trigger Picker ==============

function openTriggerPickerFromCache(agentId) {
    const data = window._triggerPickerData?.[agentId];
    if (!data) {
        console.warn('No trigger data found for agent:', agentId);
        return;
    }
    openTriggerPicker(agentId, data.triggers, data.disabledTriggers || []);
}

function openTriggerPicker(agentId, triggers, disabledTriggers = []) {
    if (!triggers || triggers.length === 0) {
        console.warn('No triggers configured for agent');
        return;
    }

    const picker = document.createElement('div');
    picker.className = 'picker-modal';
    picker.id = 'trigger-picker';

    const triggerOptions = triggers.map(trigger => {
        const topicName = trigger.topic_name || trigger;
        const description = trigger.topic_description || '';
        const schedule = trigger.schedule || '';
        const isDisabled = disabledTriggers.includes(topicName);
        const disabledAttr = isDisabled ? 'disabled' : '';
        const disabledClass = isDisabled ? 'disabled' : '';

        // Format display name (e.g., "euno:consolidate" -> "Consolidate")
        const displayName = topicName.includes(':')
            ? topicName.split(':').pop().replace(/^\w/, c => c.toUpperCase())
            : topicName;

        return `
            <div class="picker-option ${disabledClass}" onclick="${isDisabled ? '' : `triggerEvent('${agentId}', '${topicName}', '${escapeHtml(description)}')`}" ${disabledAttr}>
                <span class="picker-option-icon">${icon('play')}</span>
                <div class="picker-option-content">
                    <span class="picker-option-label">${escapeHtml(displayName)}</span>
                    ${description ? `<span class="picker-option-description">${escapeHtml(description)}</span>` : ''}
                </div>
                ${schedule ? `<span class="picker-option-badge">${escapeHtml(schedule)}</span>` : ''}
            </div>
        `;
    }).join('');

    picker.innerHTML = `
        <div class="picker-backdrop" onclick="closeTriggerPicker()"></div>
        <div class="picker-content">
            <div class="picker-header">Trigger</div>
            ${triggerOptions}
        </div>
    `;
    document.body.appendChild(picker);
}

function closeTriggerPicker() {
    const picker = document.getElementById('trigger-picker');
    if (picker) picker.remove();
}

async function triggerEvent(agentId, topicName, topicDescription) {
    closeTriggerPicker();

    try {
        const response = await fetch(`/api/agents/${agentId}/trigger`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({
                topic_name: topicName,
                topic_description: topicDescription || undefined
            })
        });

        if (!response.ok) {
            console.error('Failed to trigger event:', await response.text());
        }
        // Topic created - SSE will update the topics list
    } catch (error) {
        console.error('Failed to trigger event:', error);
    }
}


// ============== Topic Status Label ==============

function getTopicStatusLabel(topic) {
    const status = topic?.status || 'todo';
    const labels = {
        'todo': 'To Do',
        'working': 'Working',
        'done': 'Done',
        'error': 'Error',
        'archived': 'Archived'
    };
    return labels[status] || status;
}

function getTopicStatusIcon(topic) {
    const status = topic?.status || 'todo';
    const icons = {
        'todo': 'queue-list',
        'working': 'bolt',
        'done': 'check',
        'error': 'exclamation-triangle',
        'archived': 'archive-box'
    };
    return icon(icons[status] || 'queue-list');
}
