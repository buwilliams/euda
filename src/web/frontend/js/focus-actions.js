// Euno - Focus Topic Actions (CRUD Operations)

// ============== Topic Actions ==============

function showArchiveInput(event, topicId) {
    event.stopPropagation();
    if (archivingTopicId === topicId) {
        archivingTopicId = null;
    } else {
        archivingTopicId = topicId;
    }
    renderFocusTab();
    setTimeout(() => {
        const input = document.getElementById(`archive-reason-${topicId}`);
        if (input) input.focus();
    }, 50);
}

async function confirmArchiveTopic(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/archive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            archivingTopicId = null;
            await loadTopicsData();
            if (focusView === `topic-${topicId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to archive topic:', error);
    }
}

async function completeTopic(event, topicId) {
    if (event) event.stopPropagation();

    try {
        const response = await fetch(`/api/topics/${topicId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            await loadTopicsData();
            if (focusView === `topic-${topicId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to complete topic:', error);
    }
}

async function restoreTopic(event, topicId) {
    if (event) event.stopPropagation();

    try {
        const response = await fetch(`/api/topics/${topicId}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            await loadTopicsData();
            if (focusView === `completed-${topicId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to restore topic:', error);
    }
}

async function deleteTopic(event, topicId) {
    if (event) event.stopPropagation();

    const wasViewingTopic = focusView === `topic-${topicId}` || focusView === `completed-${topicId}`;

    try {
        const response = await fetch(`/api/topics/${topicId}?delete_children=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTopicsData();
            if (wasViewingTopic) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to delete topic:', error);
    }
}

async function quickAddTopic(inputId, parentId = null) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    try {
        const body = { name };
        if (parentId) {
            body.parent_id = parentId;
        }

        const response = await fetch('/api/topics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            input.value = '';
            await loadTopicsData();
            // Re-focus the input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById(inputId);
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create topic:', error);
    }
}

function handleQuickAddKeypress(event, inputId, parentId = null) {
    if (event.key === 'Enter') {
        quickAddTopic(inputId, parentId);
    }
}

async function quickDeleteTopic(event, topicId) {
    event.stopPropagation();

    try {
        const response = await fetch(`/api/topics/${topicId}?delete_children=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTopicsData();
        }
    } catch (error) {
        console.error('Failed to delete topic:', error);
    }
}
