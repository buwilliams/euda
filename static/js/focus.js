// Euno - Focus Tab (Tasks, Projects, When Picker)

// ============== Tasks ==============

async function loadTasksData() {
    try {
        const fetchOpts = { credentials: 'same-origin' };
        const [tasksRes, projectsRes, completedRes] = await Promise.all([
            fetch('/api/tasks', fetchOpts),
            fetch('/api/projects', fetchOpts),
            fetch('/api/tasks/completed?days=30&limit=20', fetchOpts)
        ]);

        // Check for auth errors - if any request returns 401, redirect to login
        if (tasksRes.status === 401 || projectsRes.status === 401 || completedRes.status === 401) {
            console.error('Focus tab: Authentication required');
            window.location.reload();
            return;
        }

        const tasksJson = await tasksRes.json();
        const projectsJson = await projectsRes.json();
        const completedJson = await completedRes.json();

        // Filter out archived and completed tasks from main list
        const allTasks = tasksJson.tasks || [];
        tasksData = allTasks.filter(t => t.status !== 'completed' && t.status !== 'archived');
        projectsData = projectsJson.projects || [];
        completedTasksData = completedJson.tasks || [];

        // Load notes for each active project (full list for inline display)
        const activeProjects = projectsData.filter(p => p.status === 'active');
        const notesPromises = activeProjects.map(async (p) => {
            try {
                const res = await fetch(`/api/projects/${p.id}/notes/list`, fetchOpts);
                const data = await res.json();
                projectNotesData[p.id] = {
                    count: data.count || 0,
                    notes: data.notes || []
                };
            } catch (e) {
                projectNotesData[p.id] = { count: 0, notes: [] };
            }
        });
        await Promise.all(notesPromises);

        renderFocusTab();
        updateTasksBadge();
    } catch (error) {
        console.error('Failed to load tasks data:', error);
    }
}

// ============== Focus Tab - Things-like Navigation ==============

// System project IDs that should be filtered from timeline views
const SYSTEM_PROJECT_IDS = ['project-notifications', 'project-recommendations'];

function isSystemProjectTask(task) {
    return SYSTEM_PROJECT_IDS.includes(task.project_id);
}

function shouldShowInTimeline(task) {
    // Non-system project tasks always show in timeline
    if (!isSystemProjectTask(task)) return true;
    // System project tasks only show if user explicitly set a When value
    const dueDate = task.scheduling?.due_date;
    const someday = task.scheduling?.someday;
    return dueDate || someday;
}

function getTaskCategory(task) {
    const today = new Date().toISOString().split('T')[0];
    const dueDate = task.scheduling?.due_date;
    const someday = task.scheduling?.someday;

    if (task.status === 'completed') return 'logbook';
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
    const today = new Date().toISOString().split('T')[0];
    const counts = { today: 0, upcoming: 0, anytime: 0, someday: 0, logbook: 0, projects: 0 };

    // Only count tasks that should show in timeline
    tasksData.filter(shouldShowInTimeline).forEach(task => {
        const category = getTaskCategory(task);
        if (category === 'logbook') return; // Don't count in logbook badge
        counts[category]++;
    });

    counts.logbook = completedTasksData.filter(shouldShowInTimeline).length;
    counts.projects = projectsData.filter(p => p.status === 'active').length;

    return counts;
}

function renderFocusTab() {
    const container = document.getElementById('focus-content');
    if (!container) return;

    if (focusView === 'menu') {
        container.innerHTML = renderFocusMenu();
    } else if (focusView === 'today') {
        container.innerHTML = renderTimelineView('today', 'Today');
    } else if (focusView === 'upcoming') {
        container.innerHTML = renderTimelineView('upcoming', 'Upcoming');
    } else if (focusView === 'anytime') {
        container.innerHTML = renderTimelineView('anytime', 'Anytime');
    } else if (focusView === 'someday') {
        container.innerHTML = renderTimelineView('someday', 'Someday');
    } else if (focusView === 'logbook') {
        container.innerHTML = renderLogbookView();
    } else if (focusView.startsWith('task-')) {
        const taskId = focusView.substring(5);
        container.innerHTML = renderTaskDetailView(taskId);
    } else if (focusView.startsWith('completed-')) {
        const taskId = focusView.substring(10);
        container.innerHTML = renderCompletedTaskDetailView(taskId);
    } else if (focusView.startsWith('note-')) {
        const noteKey = focusView.substring(5); // format: projectId:filename
        container.innerHTML = renderNoteDetailView(noteKey);
    } else if (focusView.startsWith('project-')) {
        const projectId = focusView;
        container.innerHTML = renderSingleProjectView(projectId);
    }
}

function renderFocusMenu() {
    const counts = getFocusCounts();
    const activeProjects = projectsData.filter(p => p.status === 'active');

    // Get task counts per project
    const projectTaskCounts = {};
    activeProjects.forEach(p => {
        projectTaskCounts[p.id] = tasksData.filter(t => t.project_id === p.id && t.status !== 'completed').length;
    });

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
            ${activeProjects.map(project => {
                const isSystemProject = project.id === 'project-notifications' || project.id === 'project-recommendations';
                const icon = isSystemProject ? '✨' : '📁';
                const subtitle = isSystemProject ? '<span class="focus-menu-subtitle">from Euno</span>' : '';
                return `
                <div class="focus-menu-item" onclick="navigateFocus('${project.id}')">
                    <span class="focus-menu-icon">${icon}</span>
                    <span class="focus-menu-label">${escapeHtml(project.title)}${subtitle}</span>
                    <span class="focus-menu-count">${projectTaskCounts[project.id] || 0}</span>
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
    // Filter to tasks in this category AND should show in timeline
    const tasks = tasksData.filter(t => shouldShowInTimeline(t) && getTaskCategory(t) === category);
    const icon = getTimelineIcon(category);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${icon} ${title}</span>
        </div>
        <div class="focus-view-content">
            ${tasks.length === 0
                ? '<div class="focus-empty">No tasks</div>'
                : renderTasksSortedByProject(tasks)
            }
        </div>
    `;
}

function renderLogbookView() {
    // Filter completed tasks - only show non-system tasks or system tasks with When value
    const tasks = completedTasksData.filter(shouldShowInTimeline).slice(0, 20);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">📖 Logbook</span>
        </div>
        <div class="focus-view-content">
            ${tasks.length === 0
                ? '<div class="focus-empty">No completed tasks</div>'
                : renderTasksSortedByProject(tasks, true)
            }
        </div>
    `;
}


function renderSingleProjectView(projectId) {
    const project = projectsData.find(p => p.id === projectId);
    if (!project) {
        return `
            <div class="focus-view-header">
                <button class="focus-back-btn" onclick="navigateFocusBack()">←</button>
                <span class="focus-view-title">Project not found</span>
            </div>
        `;
    }

    const projectTasks = tasksData.filter(t => t.project_id === projectId && t.status !== 'completed');
    const noteCount = projectNotesData[projectId]?.count || 0;
    const notes = projectNotesData[projectId]?.notes || [];
    const isSystemProject = projectId === 'project-notifications' || projectId === 'project-recommendations';
    const projectIcon = isSystemProject ? '✨' : '📁';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${projectIcon} ${escapeHtml(project.title)}</span>
        </div>
        <div class="focus-view-content">
            ${project.description ? `<div class="card-description" style="margin-bottom: 0.75rem;">${marked.parse(project.description)}</div>` : ''}
            <div class="section-header">TASKS (${projectTasks.length})</div>
            ${projectTasks.length === 0
                ? '<div class="focus-empty">No pending tasks</div>'
                : projectTasks.map(task => renderTaskCard(task)).join('')
            }
            ${noteCount > 0 ? `
            <div class="notes-section">
                <div class="section-header">NOTES (${noteCount})</div>
                <div class="notes-list-body">
                    ${notes.map(note => renderNoteCard(projectId, project.title, note)).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

function renderTasksSortedByProject(tasks, isCompleted = false) {
    // Sort tasks by project name
    const sortedTasks = [...tasks].sort((a, b) => {
        const projA = a.project_title || 'General';
        const projB = b.project_title || 'General';
        // General goes last
        if (projA === 'General' && projB !== 'General') return 1;
        if (projB === 'General' && projA !== 'General') return -1;
        return projA.localeCompare(projB);
    });

    return sortedTasks.map(task =>
        isCompleted ? renderCompletedTaskCard(task) : renderTaskCard(task)
    ).join('');
}

function navigateFocus(view) {
    focusViewHistory.push(focusView);
    focusView = view;
    renderFocusTab();
}

function navigateFocusBack() {
    if (focusViewHistory.length > 0) {
        focusView = focusViewHistory.pop();
    } else {
        focusView = 'menu';
    }
    renderFocusTab();
}

// ============== Task Cards ==============

function renderTaskCard(task) {
    const isExpanded = expandedCards.has(`task-${task.id}`);
    return isExpanded ? renderFullTaskCard(task) : renderMinimalTaskCard(task);
}

function isEunoTask(task) {
    // Show icon for all system project tasks (notifications, recommendations, legacy euno)
    return SYSTEM_PROJECT_IDS.includes(task.project_id);
}

function renderMinimalTaskCard(task) {
    const eunoIcon = isEunoTask(task) ? '<span class="card-euno-icon">✨</span>' : '';
    const displayName = task.name || task.description || 'Untitled';
    const dueDate = task.scheduling?.due_date;
    const dueDateLabel = dueDate ? `<span class="card-due-date">${formatFriendlyDueDate(dueDate)}</span>` : '';
    return `
        <div class="card card-minimal" data-task-id="${task.id}" onclick="navigateFocus('task-${task.id}')">
            ${eunoIcon}<span class="card-title">${escapeHtml(displayName)}</span>
            ${dueDateLabel}
            <span class="card-arrow">›</span>
        </div>
    `;
}

function renderFullTaskCard(task) {
    const projectName = task.project_title || 'General';
    const projectId = task.project_id || 'project-general';
    const whenLabel = getWhenLabel(task);
    const eunoIcon = isEunoTask(task) ? '<span class="card-euno-icon">✨</span>' : '';
    const isArchiving = archivingTaskId === task.id;
    const displayName = task.name || task.description || 'Untitled';
    const hasDescription = task.description && task.description !== task.name;

    return `
        <div class="card card-full" data-task-id="${task.id}">
            <div class="card-header">
                ${eunoIcon}<span class="card-title" onclick="toggleTaskCard('${task.id}')">${escapeHtml(displayName)}</span>
                <button class="card-collapse" onclick="event.stopPropagation(); toggleTaskCard('${task.id}')">−</button>
            </div>
            <div class="card-body">
                ${hasDescription ? `<div class="card-description">${escapeHtml(task.description)}</div>` : ''}
                <div class="card-meta">Project: <span class="card-project-link" onclick="event.stopPropagation(); navigateFocus('${projectId}')">${escapeHtml(projectName)}</span></div>
            </div>
            <div class="card-actions">
                <button class="card-action" onclick="event.stopPropagation(); openWhenPicker('task', '${task.id}')">📅 ${escapeHtml(whenLabel)}</button>
                <button class="card-action" onclick="toggleTask(event, '${task.id}')">Complete</button>
                <button class="card-action" onclick="showArchiveInput(event, '${task.id}')">${isArchiving ? 'Cancel' : 'Archive'}</button>
                <button class="card-action danger" onclick="deleteTask(event, '${task.id}')">Delete</button>
            </div>
            ${isArchiving ? `
            <div class="card-archive-form">
                <input type="text" class="card-archive-input" id="archive-reason-${task.id}" placeholder="Reason (optional)..." onkeypress="if(event.key==='Enter')confirmArchiveTask('${task.id}')">
                <button class="card-archive-btn confirm" onclick="confirmArchiveTask('${task.id}')">Archive</button>
            </div>
            ` : ''}
        </div>
    `;
}

function getWhenLabel(task) {
    const today = new Date().toISOString().split('T')[0];
    const dueDate = task.scheduling?.due_date;
    const someday = task.scheduling?.someday;

    if (dueDate === today) return 'Today';
    if (dueDate) return dueDate;
    if (someday) return 'Someday';
    return 'Anytime';
}

function renderTaskDetailView(taskId) {
    const task = tasksData.find(t => t.id === taskId);
    if (!task) {
        return `
            <div class="focus-view-header">
                <button class="focus-back-btn" onclick="navigateFocusBack()">←</button>
                <span class="focus-view-title">Task Not Found</span>
            </div>
            <div class="focus-empty">This task no longer exists.</div>
        `;
    }

    const projectName = task.project_title || 'General';
    const projectId = task.project_id || 'project-general';
    const whenLabel = getWhenLabel(task);
    const eunoIcon = isEunoTask(task) ? '<span class="card-euno-icon">✨</span>' : '';
    const isArchiving = archivingTaskId === task.id;
    const displayName = task.name || task.description || 'Untitled';
    const hasDescription = task.description && task.description !== task.name;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${eunoIcon}${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <div class="task-detail">
                ${hasDescription ? `<div class="task-detail-description">${marked.parse(task.description)}</div>` : ''}
                <div class="task-detail-meta">
                    <span class="task-detail-label">Project:</span>
                    <span class="task-detail-value card-project-link" onclick="navigateFocus('${projectId}')">${escapeHtml(projectName)}</span>
                </div>
                <div class="task-detail-meta">
                    <span class="task-detail-label">When:</span>
                    <span class="task-detail-value">${escapeHtml(whenLabel)}</span>
                </div>
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('task', '${task.id}')">📅 Change When</button>
                <button class="task-detail-action" onclick="toggleTask(event, '${task.id}')">✓ Complete</button>
                <button class="task-detail-action" onclick="showArchiveInput(event, '${task.id}')">${isArchiving ? 'Cancel' : '📦 Archive'}</button>
                <button class="task-detail-action danger" onclick="deleteTask(event, '${task.id}')">🗑 Delete</button>
            </div>
            ${isArchiving ? `
            <div class="card-archive-form">
                <input type="text" class="card-archive-input" id="archive-reason-${task.id}" placeholder="Reason (optional)..." onkeypress="if(event.key==='Enter')confirmArchiveTask('${task.id}')">
                <button class="card-archive-btn confirm" onclick="confirmArchiveTask('${task.id}')">Archive</button>
            </div>
            ` : ''}
        </div>
    `;
}

function renderCompletedTaskDetailView(taskId) {
    const task = completedTasksData.find(t => t.id === taskId);
    if (!task) {
        return `
            <div class="focus-view-header">
                <button class="focus-back-btn" onclick="navigateFocusBack()">←</button>
                <span class="focus-view-title">Task Not Found</span>
            </div>
            <div class="focus-empty">This task no longer exists.</div>
        `;
    }

    const displayName = task.name || task.description || 'Untitled';
    const hasDescription = task.description && task.description !== task.name;
    const completedDate = task.completed_at ? new Date(task.completed_at).toLocaleDateString() : 'Unknown';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <div class="task-detail">
                ${hasDescription ? `<div class="task-detail-description">${marked.parse(task.description)}</div>` : ''}
                <div class="task-detail-meta">
                    <span class="task-detail-label">Completed:</span>
                    <span class="task-detail-value">${escapeHtml(completedDate)}</span>
                </div>
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="toggleTask(event, '${task.id}')">↩ Restore</button>
                <button class="task-detail-action danger" onclick="deleteTask(event, '${task.id}')">🗑 Delete</button>
            </div>
        </div>
    `;
}

function toggleTaskCard(taskId) {
    const key = `task-${taskId}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderFocusTab();
}

function expandTaskCard(taskId) {
    expandedCards.add(`task-${taskId}`);
    renderFocusTab();
}

function collapseTaskCard(taskId) {
    expandedCards.delete(`task-${taskId}`);
    renderFocusTab();
}

// ============== Project Cards ==============

function renderProjectCard(project) {
    const isExpanded = expandedCards.has(`project-${project.id}`);
    return isExpanded ? renderFullProjectCard(project) : renderMinimalProjectCard(project);
}

function renderMinimalProjectCard(project) {
    const projectTasks = tasksData.filter(t => t.project_id === project.id && t.status !== 'completed');
    return `
        <div class="card card-minimal" data-project-id="${project.id}" onclick="toggleProjectCard('${project.id}')">
            <span class="card-title">${escapeHtml(project.title)}</span>
            <span class="card-badge">${projectTasks.length} task${projectTasks.length !== 1 ? 's' : ''}</span>
        </div>
    `;
}

function renderFullProjectCard(project) {
    const projectTasks = tasksData.filter(t => t.project_id === project.id && t.status !== 'completed');
    const noteCount = projectNotesData[project.id]?.count || 0;
    const notes = projectNotesData[project.id]?.notes || [];
    const isGeneral = project.id === 'project-general';
    const isNotifications = project.id === 'project-notifications';
    const isRecommendations = project.id === 'project-recommendations';
    const isSystemProject = isGeneral || isNotifications || isRecommendations;
    const whenLabel = getProjectWhenLabel(project);
    const hasDescription = project.description && project.description.length > 0;

    return `
        <div class="card card-full" data-project-id="${project.id}">
            <div class="card-header">
                <span class="card-title" onclick="toggleProjectCard('${project.id}')">${escapeHtml(project.title)}</span>
                <button class="card-collapse" onclick="event.stopPropagation(); toggleProjectCard('${project.id}')">−</button>
            </div>
            <div class="card-body">
                ${hasDescription ? `<div class="card-description">${escapeHtml(project.description)}</div>` : ''}
                ${!isSystemProject ? `
                <div class="card-when" onclick="event.stopPropagation(); openWhenPicker('project', '${project.id}')">
                    <span class="card-when-icon">📅</span>
                    <span class="card-when-label">${escapeHtml(whenLabel)}</span>
                </div>
                ` : ''}
                <div class="card-meta">${projectTasks.length} pending task${projectTasks.length !== 1 ? 's' : ''}</div>
                <button class="card-action" style="margin-top: 0.5rem;" onclick="event.stopPropagation(); navigateFocus('${project.id}')">View tasks →</button>
                ${noteCount > 0 ? `
                <div class="notes-section">
                    <div class="section-header">NOTES (${noteCount})</div>
                    <div class="notes-list-body">
                        ${notes.map(note => renderNoteCard(project.id, project.title, note)).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
            ${!isSystemProject ? `
            <div class="card-actions">
                <button class="card-action" onclick="archiveProject('${project.id}')">Archive</button>
                <button class="card-action danger" onclick="deleteProject('${project.id}')">Delete</button>
            </div>
            ` : ''}
        </div>
    `;
}

function renderNoteCard(projectId, projectTitle, note) {
    const friendlyDate = note.date ? formatFriendlyPastDate(note.date) : '';
    return `
        <div class="card card-minimal" data-note-filename="${note.filename}" onclick="navigateFocus('note-${projectId}:${note.filename}')">
            <span class="card-title">${escapeHtml(note.title)}</span>
            <span class="card-due-date">${escapeHtml(friendlyDate)}</span>
            <span class="card-arrow">›</span>
        </div>
    `;
}

function renderNoteDetailView(noteKey) {
    const [projectId, filename] = noteKey.split(':');
    const projectNotes = projectNotesData[projectId]?.notes || [];
    const note = projectNotes.find(n => n.filename === filename);
    const project = projectsData.find(p => p.id === projectId);
    const projectTitle = project?.title || 'Unknown Project';

    if (!note) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">←</span>
                <span class="focus-view-title">Note Not Found</span>
            </div>
            <div class="focus-empty">This note no longer exists.</div>
        `;
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${escapeHtml(note.title)}</span>
        </div>
        <div class="focus-view-content">
            <div class="note-detail">
                <div class="note-detail-meta">
                    <span class="note-detail-date">${escapeHtml(note.date)}</span>
                    <span class="note-detail-type">${escapeHtml(note.type)}</span>
                </div>
                <div class="note-detail-body">${marked.parse(note.content || '*No content*')}</div>
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="bringNoteToChat('${escapeHtml(projectTitle).replace(/'/g, "\\'")}', '${escapeHtml(note.title).replace(/'/g, "\\'")}', '${escapeHtml(note.preview).replace(/'/g, "\\'")}')">💬 Discuss in Chat</button>
                <button class="task-detail-action danger" onclick="deleteProjectNote('${projectId}', '${note.filename}')">🗑 Delete</button>
            </div>
        </div>
    `;
}

function toggleNoteCard(filename) {
    const key = `note-${filename}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderFocusTab();
}

function getProjectWhenLabel(project) {
    const today = new Date().toISOString().split('T')[0];
    const deadline = project.deadline;
    const someday = project.someday;

    if (deadline === today) return 'Today';
    if (deadline) return deadline;
    if (someday) return 'Someday';
    return 'Anytime';
}

function toggleProjectCard(projectId) {
    const key = `project-${projectId}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderFocusTab();
}

function expandProjectCard(projectId) {
    expandedCards.add(`project-${projectId}`);
    renderFocusTab();
}

function collapseProjectCard(projectId) {
    expandedCards.delete(`project-${projectId}`);
    renderFocusTab();
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

    // Get first day of month and total days
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Build calendar grid
    let daysHtml = '';

    // Empty cells for days before first of month
    for (let i = 0; i < firstDay; i++) {
        daysHtml += '<div class="calendar-day empty"></div>';
    }

    // Days of the month
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
    const endpoint = type === 'task'
        ? `/api/tasks/${id}/when`
        : `/api/projects/${id}/when`;

    try {
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ when_type: whenType, date })
        });

        if (response.ok) {
            closeWhenPicker();
            await loadTasksData();
        } else {
            console.error('Failed to update when:', await response.text());
        }
    } catch (error) {
        console.error('Failed to update when:', error);
    }
}

async function deleteProject(projectId) {
    if (!confirm('Delete this project and all its tasks?')) return;

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTasksData();
        }
    } catch (error) {
        console.error('Failed to delete project:', error);
    }
}

function showArchiveInput(event, taskId) {
    event.stopPropagation();
    // Toggle archive mode - if already archiving this task, cancel
    if (archivingTaskId === taskId) {
        archivingTaskId = null;
    } else {
        archivingTaskId = taskId;
    }
    renderFocusTab();
    // Focus the input after render
    setTimeout(() => {
        const input = document.getElementById(`archive-reason-${taskId}`);
        if (input) input.focus();
    }, 50);
}

async function confirmArchiveTask(taskId) {
    const input = document.getElementById(`archive-reason-${taskId}`);
    const reason = input ? input.value : '';

    try {
        const response = await fetch(`/api/tasks/${taskId}/archive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason, outcome: 'abandoned' })
        });

        if (response.ok) {
            archivingTaskId = null;
            await loadTasksData();
            // Navigate back if viewing this task's detail
            if (focusView === `task-${taskId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to archive task:', error);
    }
}

async function archiveProject(projectId) {
    const reason = prompt('Reason for archiving (optional):');
    if (reason === null) return; // Cancelled

    const outcome = confirm('Was this project completed?') ? 'completed' : 'abandoned';

    try {
        const response = await fetch(`/api/projects/${projectId}/archive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason, outcome })
        });

        if (response.ok) {
            await loadTasksData();
            // Navigate back if viewing this project's detail
            if (focusView === projectId) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to archive project:', error);
    }
}

async function completeProject(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/complete`, {
            method: 'POST'
        });

        if (response.ok) {
            await loadTasksData();
            // Navigate back if viewing this project's detail
            if (focusView === projectId) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to complete project:', error);
    }
}

async function toggleTask(event, taskId) {
    event.stopPropagation();
    const task = tasksData.find(t => t.id === taskId) || completedTasksData.find(t => t.id === taskId);
    if (!task) return;

    const newStatus = task.status === 'completed' ? 'pending' : 'completed';

    try {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            // Reload data to reflect changes
            await loadTasksData();
            // Navigate back if viewing this task's detail
            if (focusView === `task-${taskId}` || focusView === `completed-${taskId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to update task status:', error);
    }
}

async function deleteTask(event, taskId) {
    event.stopPropagation();
    if (!confirm('Delete this task?')) return;

    // Check if viewing this task before deletion
    const wasViewingTask = focusView === `task-${taskId}` || focusView === `completed-${taskId}`;

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTasksData();
            // Navigate back if was viewing this task's detail
            if (wasViewingTask) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to delete task:', error);
    }
}

function renderCompletedTaskCard(task) {
    const isExpanded = expandedCards.has(`completed-${task.id}`);
    const displayName = task.name || task.description || 'Untitled';
    const hasDescription = task.description && task.description !== task.name;

    if (isExpanded) {
        return `
            <div class="card card-full" data-task-id="${task.id}" style="opacity: 0.7;">
                <div class="card-header">
                    <span class="card-title" style="text-decoration: line-through;" onclick="toggleCompletedTaskCard('${task.id}')">${escapeHtml(displayName)}</span>
                    <button class="card-collapse" onclick="event.stopPropagation(); toggleCompletedTaskCard('${task.id}')">−</button>
                </div>
                <div class="card-body">
                    ${hasDescription ? `<div class="card-description" style="text-decoration: line-through;">${escapeHtml(task.description)}</div>` : ''}
                    <div class="card-meta">Completed ${task.completed_at ? new Date(task.completed_at).toLocaleDateString() : 'recently'}</div>
                </div>
                <div class="card-actions">
                    <button class="card-action" onclick="toggleTask(event, '${task.id}')">Restore</button>
                    <button class="card-action danger" onclick="deleteTask(event, '${task.id}')">Delete</button>
                </div>
            </div>
        `;
    } else {
        const completedDateLabel = task.completed_at ? `<span class="card-due-date">${formatFriendlyPastDate(task.completed_at)}</span>` : '';
        return `
            <div class="card card-minimal" data-task-id="${task.id}" style="opacity: 0.7;" onclick="navigateFocus('completed-${task.id}')">
                <span class="card-title" style="text-decoration: line-through; color: #888;">${escapeHtml(displayName)}</span>
                ${completedDateLabel}
                <span class="card-arrow">›</span>
            </div>
        `;
    }
}

function toggleCompletedTaskCard(taskId) {
    const key = `completed-${taskId}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderFocusTab();
}

