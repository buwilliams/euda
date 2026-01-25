// Euno - Focus Inline Field Editing

// ============== Job Editing ==============

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
        console.error('Failed to save job field:', error);
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

// ============== Completed Job Editing ==============

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
        console.error('Failed to save completed job field:', error);
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

async function saveAgentIdentityField(agentId, topicId) {
    const textarea = document.getElementById(`edit-identity-${topicId}`);
    if (!textarea) return;

    const success = await saveAgentIdentity(agentId, textarea.value);
    if (success) {
        editingTopicField = null;
        renderFocusTab();
    }
}

async function saveAgentConfigField(agentId, topicId) {
    const triggersInput = document.getElementById(`edit-triggers-${topicId}`);
    const toolsInput = document.getElementById(`edit-tools-${topicId}`);

    if (!triggersInput || !toolsInput) return;

    // Parse comma-separated values into arrays
    const triggers = triggersInput.value.split(',').map(s => s.trim()).filter(s => s);
    const tools = toolsInput.value.split(',').map(s => s.trim()).filter(s => s);

    // Build update object
    const updates = { triggers, tools };

    // Get consolidation settings
    const consolidationEnabledInput = document.getElementById(`edit-consolidation-enabled-${topicId}`);
    const consolidationTriggerInput = document.getElementById(`edit-consolidation-trigger-${topicId}`);
    if (consolidationEnabledInput && consolidationTriggerInput) {
        updates.consolidation = {
            enabled: consolidationEnabledInput.checked,
            trigger: consolidationTriggerInput.value.trim() || 'time:evening'
        };
    }

    const success = await saveAgentConfig(agentId, updates);
    if (success) {
        editingTopicField = null;
        renderFocusTab();
    }
}

function handleAgentIdentityKeypress(event, agentId, topicId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveAgentIdentityField(agentId, topicId);
    }
}
