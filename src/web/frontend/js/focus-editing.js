// Euno - Focus Inline Field Editing

// ============== Topic Editing ==============

function startEditingField(topicId, field) {
    editingTopicField = { topicId, field };
    renderFocusTab();

    // Focus the input after render
    setTimeout(() => {
        const input = document.getElementById(`edit-${field}-${topicId}`);
        if (input) {
            input.focus();
            if (input.tagName === 'INPUT') {
                input.select();
            }
        }
    }, 50);
}

function cancelEditing() {
    editingTopicField = null;
    renderFocusTab();
}

async function saveTopicField(topicId, field, value) {
    try {
        const body = {};
        body[field] = value;

        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            editingTopicField = null;
            await loadTopicsData();
        }
    } catch (error) {
        console.error('Failed to save topic field:', error);
    }
}

function handleEditKeypress(event, topicId, field) {
    if (event.key === 'Enter' && field === 'name') {
        saveTopicField(topicId, field, event.target.value);
    } else if (event.key === 'Escape') {
        cancelEditing();
    }
}

function handleDescriptionKeypress(event, topicId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveTopicField(topicId, 'description', event.target.value);
    }
}

// ============== Completed Topic Editing ==============

async function saveCompletedTopicField(topicId, field, value) {
    try {
        const body = {};
        body[field] = value;

        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            editingTopicField = null;
            await loadTopicsData();
        }
    } catch (error) {
        console.error('Failed to save completed topic field:', error);
    }
}

function handleCompletedDescriptionKeypress(event, topicId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveCompletedTopicField(topicId, 'description', event.target.value);
    }
}

// ============== Agent Editing ==============

async function toggleAgentEnabled(agentId, enabled) {
    const newState = enabled ? 'enabled' : 'disabled';
    const success = await setAgentState(agentId, newState);
    if (success) {
        renderFocusTab();
    }
}

// Agent identity/config editing removed; updates handled via Chat.
