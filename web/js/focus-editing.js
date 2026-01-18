// Euno - Focus Inline Field Editing

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

// ============== Completed Job Editing ==============

async function saveCompletedJobField(jobId, field, value) {
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
        console.error('Failed to save completed job field:', error);
    }
}

function handleCompletedDescriptionKeypress(event, jobId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveCompletedJobField(jobId, 'description', event.target.value);
    }
}

// ============== Agent Editing ==============

async function toggleAgentEnabled(agentId, enabled) {
    const success = await saveAgentConfig(agentId, { enabled });
    if (success) {
        renderFocusTab();
    }
}

async function saveAgentPersonaField(agentId, jobId) {
    const textarea = document.getElementById(`edit-persona-${jobId}`);
    if (!textarea) return;

    const success = await saveAgentPersona(agentId, textarea.value);
    if (success) {
        editingJobField = null;
        renderFocusTab();
    }
}

async function saveAgentProfileField(agentId, jobId) {
    const textarea = document.getElementById(`edit-profile-${jobId}`);
    if (!textarea) return;

    const success = await saveAgentPersona(agentId, textarea.value);
    if (success) {
        editingJobField = null;
        renderFocusTab();
    }
}

async function saveAgentConfigField(agentId, jobId) {
    const triggersInput = document.getElementById(`edit-triggers-${jobId}`);
    const toolsInput = document.getElementById(`edit-tools-${jobId}`);

    if (!triggersInput || !toolsInput) return;

    // Parse comma-separated values into arrays
    const triggers = triggersInput.value.split(',').map(s => s.trim()).filter(s => s);
    const tools = toolsInput.value.split(',').map(s => s.trim()).filter(s => s);

    // Build update object
    const updates = { triggers, tools };

    // Get reflection settings
    const reflectionEnabledInput = document.getElementById(`edit-reflection-enabled-${jobId}`);
    const reflectionTriggerInput = document.getElementById(`edit-reflection-trigger-${jobId}`);
    if (reflectionEnabledInput && reflectionTriggerInput) {
        updates.reflection = {
            enabled: reflectionEnabledInput.checked,
            trigger: reflectionTriggerInput.value.trim() || 'time:evening'
        };
    }

    // Get exploration settings
    const explorationEnabledInput = document.getElementById(`edit-exploration-enabled-${jobId}`);
    const explorationTriggerInput = document.getElementById(`edit-exploration-trigger-${jobId}`);
    if (explorationEnabledInput && explorationTriggerInput) {
        updates.exploration = {
            enabled: explorationEnabledInput.checked,
            trigger: explorationTriggerInput.value.trim() || 'time:hour_04'
        };
    }

    const success = await saveAgentConfig(agentId, updates);
    if (success) {
        editingJobField = null;
        renderFocusTab();
    }
}

function handleAgentPersonaKeypress(event, agentId, jobId) {
    if (event.key === 'Escape') {
        cancelEditing();
    }
    // Ctrl+Enter or Cmd+Enter to save
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        saveAgentPersonaField(agentId, jobId);
    }
}
