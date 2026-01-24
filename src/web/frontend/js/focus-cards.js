// Euno - Focus Card Rendering

// ============== Swipeable Detection ==============

function isSwipeable(job) {
    // System containers are not swipeable
    if (job.tags && (job.tags.includes('system:agents') || job.tags.includes('system:projects'))) {
        return false;
    }
    // Agent inbox jobs are not swipeable
    if (job.tags && job.tags.includes('agent-inbox')) {
        return false;
    }
    if (job.agent_id) {
        return false;
    }
    return true;
}

// ============== Job Cards ==============

function renderJobCard(job, swipeable = false) {
    const isExpanded = expandedCards.has(`job-${job.id}`);
    const cardHtml = isExpanded ? renderFullJobCard(job) : renderMinimalJobCard(job);

    // Wrap in swipe container if enabled
    if (swipeable && !isExpanded) {
        return wrapCardForSwipe(cardHtml, job.id, false);
    }
    return cardHtml;
}

function renderMinimalJobCard(job) {
    const displayName = job.name || 'Untitled';
    const dueDate = job.due_date;
    const dueDateLabel = dueDate ? `<span class="card-due-date">${formatFriendlyDueDate(dueDate)}</span>` : '';
    // Use context-aware descendant count (all descendants matching timeline)
    const childCount = getDescendantCountForContext(job.id);
    const childBadge = childCount > 0 ? `<span class="card-badge">${childCount}</span>` : '';
    const assignee = job.assignee;

    // Status indicator based on job state
    let statusIndicator = '';
    if (job.status === 'working') {
        statusIndicator = '<span class="card-status-indicator card-working-indicator" title="Agent working">' + icon('bolt') + '</span>';
    } else if (job.status === 'error') {
        statusIndicator = '<span class="card-status-indicator card-error-indicator" title="Error">' + icon('exclamation-triangle') + '</span>';
    } else if (job.status === 'archived') {
        statusIndicator = '<span class="card-status-indicator card-archived-indicator" title="Archived">' + icon('archive-box') + '</span>';
    } else if (job.status === 'done') {
        statusIndicator = '<span class="card-status-indicator card-done-indicator" title="Completed">' + icon('check') + '</span>';
    } else if (assignee) {
        statusIndicator = '<span class="card-status-indicator card-assigned-indicator" title="Assigned to ' + escapeHtml(assignee) + '">' + icon('user') + '</span>';
    }

    return `
        <div class="card card-minimal${job.status === 'done' ? ' card-completed' : ''}${job.status === 'archived' ? ' card-archived' : ''}${job.status === 'error' ? ' card-error' : ''}" data-job-id="${job.id}" data-testid="job-card" onclick="navigateFocus('job-${job.id}')">
            ${statusIndicator}
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
    // Use context-aware descendant count (all descendants matching timeline)
    const childCount = getDescendantCountForContext(job.id);

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = allJobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    return `
        <div class="card card-full" data-job-id="${job.id}" data-testid="job-card">
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
                <button class="card-action" data-testid="action-complete" onclick="completeJob(event, '${job.id}')">Complete</button>
                <button class="card-action" data-testid="action-archive" onclick="showArchiveInput(event, '${job.id}')">${isArchiving ? 'Cancel' : 'Archive'}</button>
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
    const today = getLocalDateString();
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

function renderCompletedJobCard(job, childCount = 0, swipeable = false) {
    const displayName = job.name || 'Untitled';
    const completedDateLabel = job.completed_at ? `<span class="card-due-date">${formatFriendlyPastDate(job.completed_at)}</span>` : '';
    const childBadge = childCount > 0 ? `<span class="card-badge">${childCount}</span>` : '';

    const cardHtml = `
        <div class="card card-minimal" data-job-id="${job.id}" onclick="navigateFocus('completed-${job.id}')">
            <span class="card-title" style="text-decoration: line-through; color: #888;">${escapeHtml(displayName)}</span>
            ${childBadge}
            ${completedDateLabel}
            <button class="card-restore-btn" onclick="restoreJob(event, '${job.id}')" title="Restore to todo">${icon('arrow-uturn-left')}</button>
            <span class="card-arrow">›</span>
        </div>
    `;

    // Wrap in swipe container if enabled
    if (swipeable) {
        return wrapCardForSwipe(cardHtml, job.id, true);
    }
    return cardHtml;
}
