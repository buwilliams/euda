// Euno - Focus Card Rendering

// ============== Swipeable Detection ==============

function isSwipeable(topic) {
    // System containers are not swipeable
    if (topic.tags && (topic.tags.includes('system:agents') || topic.tags.includes('system:projects') || topic.tags.includes('system:assets'))) {
        return false;
    }
    // Agent inbox topics are not swipeable
    if (topic.tags && topic.tags.includes('agent-inbox')) {
        return false;
    }
    if (topic.agent_id) {
        return false;
    }
    return true;
}

// ============== Topic Cards ==============

function renderTopicCard(topic, swipeable = false) {
    const isExpanded = expandedCards.has(`topic-${topic.id}`);
    const cardHtml = isExpanded ? renderFullTopicCard(topic) : renderMinimalTopicCard(topic);

    // Wrap in swipe container if enabled
    if (swipeable && !isExpanded) {
        return wrapCardForSwipe(cardHtml, topic.id, false);
    }
    return cardHtml;
}

function renderMinimalTopicCard(topic) {
    const displayName = topic.name || 'Untitled';
    const dueDate = topic.due_date;
    const dueDateLabel = dueDate ? `<span class="card-due-date">${formatFriendlyDueDate(dueDate)}</span>` : '';
    // Use context-aware descendant count (all descendants matching timeline)
    const childCount = getDescendantCountForContext(topic.id);
    const childBadge = childCount > 0 ? `<span class="card-badge">${childCount}</span>` : '';
    const assignee = topic.assignee;

    // Status indicator based on topic state
    let statusIndicator = '';
    if (topic.status === 'working') {
        statusIndicator = '<span class="card-status-indicator card-working-indicator" title="Agent working">' + icon('bolt') + '</span>';
    } else if (topic.status === 'error') {
        statusIndicator = '<span class="card-status-indicator card-error-indicator" title="Error">' + icon('exclamation-triangle') + '</span>';
    } else if (topic.status === 'archived') {
        statusIndicator = '<span class="card-status-indicator card-archived-indicator" title="Archived">' + icon('archive-box') + '</span>';
    } else if (topic.status === 'done') {
        statusIndicator = '<span class="card-status-indicator card-done-indicator" title="Completed">' + icon('check') + '</span>';
    } else if (assignee) {
        statusIndicator = '<span class="card-status-indicator card-assigned-indicator" title="Assigned to ' + escapeHtml(assignee) + '">' + icon('user') + '</span>';
    }

    // Assignee label shown before the arrow (only when assigned to an agent)
    const assigneeLabel = assignee
        ? `<span class="card-assignee-label">${escapeHtml(assignee)}</span>`
        : '';

    return `
        <div class="card card-minimal${topic.status === 'done' ? ' card-completed' : ''}${topic.status === 'archived' ? ' card-archived' : ''}${topic.status === 'error' ? ' card-error' : ''}" data-topic-id="${topic.id}" data-testid="topic-card" onclick="navigateFocus('topic-${topic.id}')">
            ${statusIndicator}
            <span class="card-title">${escapeHtml(displayName)}</span>
            ${assigneeLabel}
            ${dueDateLabel}
            <button class="card-trash-btn" onclick="quickDeleteTopic(event, '${topic.id}')" title="Delete topic">${icon('trash')}</button>
            ${childBadge}
            <span class="card-arrow">›</span>
        </div>
    `;
}

function renderFullTopicCard(topic) {
    const whenLabel = getWhenLabel(topic);
    const isArchiving = archivingTopicId === topic.id;
    const displayName = topic.name || 'Untitled';
    const hasDescription = topic.description && topic.description.length > 0;
    // Use context-aware descendant count (all descendants matching timeline)
    const childCount = getDescendantCountForContext(topic.id);

    // Get parent topic name for context
    let parentName = null;
    if (topic.parent_id) {
        const parent = allTopicsData.find(j => j.id === topic.parent_id);
        parentName = parent ? parent.name : null;
    }

    return `
        <div class="card card-full" data-topic-id="${topic.id}" data-testid="topic-card">
            <div class="card-header">
                <span class="card-title" onclick="toggleTopicCard('${topic.id}')">${escapeHtml(displayName)}</span>
                <button class="card-collapse" onclick="event.stopPropagation(); toggleTopicCard('${topic.id}')">−</button>
            </div>
            <div class="card-body">
                ${hasDescription ? `<div class="card-description">${marked.parse(topic.description)}</div>` : ''}
                ${parentName ? `<div class="card-meta">Parent: <span class="card-project-link" onclick="event.stopPropagation(); navigateFocus('topic-${topic.parent_id}')">${escapeHtml(parentName)}</span></div>` : ''}
                ${childCount > 0 ? `<div class="card-meta">${childCount} child topic${childCount !== 1 ? 's' : ''}</div>` : ''}
            </div>
            <div class="card-actions">
                <button class="card-action" onclick="event.stopPropagation(); openWhenPicker('topic', '${topic.id}')">${icon('calendar')} ${escapeHtml(whenLabel)}</button>
                <button class="card-action" data-testid="action-complete" onclick="completeTopic(event, '${topic.id}')">Complete</button>
                <button class="card-action" data-testid="action-archive" onclick="showArchiveInput(event, '${topic.id}')">${isArchiving ? 'Cancel' : 'Archive'}</button>
                <button class="card-action danger" onclick="deleteTopic(event, '${topic.id}')">Delete</button>
            </div>
            ${isArchiving ? `
            <div class="card-archive-form">
                <input type="text" class="card-archive-input" id="archive-reason-${topic.id}" placeholder="Reason (optional)..." onkeypress="if(event.key==='Enter')confirmArchiveTopic('${topic.id}')">
                <button class="card-archive-btn confirm" onclick="confirmArchiveTopic('${topic.id}')">Archive</button>
            </div>
            ` : ''}
        </div>
    `;
}

function getWhenLabel(topic) {
    const today = getLocalDateString();
    const dueDate = topic.due_date;
    const someday = topic.someday;

    if (dueDate === today) return 'Today';
    if (dueDate) return dueDate;
    if (someday) return 'Someday';
    return 'Anytime';
}

function toggleTopicCard(topicId) {
    const key = `topic-${topicId}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderFocusTab();
}

function renderCompletedTopicCard(topic, childCount = 0, swipeable = false) {
    const displayName = topic.name || 'Untitled';
    const completedDateLabel = topic.completed_at ? `<span class="card-due-date">${formatFriendlyPastDate(topic.completed_at)}</span>` : '';
    const childBadge = childCount > 0 ? `<span class="card-badge">${childCount}</span>` : '';

    const cardHtml = `
        <div class="card card-minimal" data-topic-id="${topic.id}" onclick="navigateFocus('completed-${topic.id}')">
            <span class="card-title" style="text-decoration: line-through; color: #888;">${escapeHtml(displayName)}</span>
            ${childBadge}
            ${completedDateLabel}
            <button class="card-restore-btn" onclick="restoreTopic(event, '${topic.id}')" title="Restore to todo">${icon('arrow-uturn-left')}</button>
            <span class="card-arrow">›</span>
        </div>
    `;

    // Wrap in swipe container if enabled
    if (swipeable) {
        return wrapCardForSwipe(cardHtml, topic.id, true);
    }
    return cardHtml;
}
