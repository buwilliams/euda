// Euno - Focus Card Rendering

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
