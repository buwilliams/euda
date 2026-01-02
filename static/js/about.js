// Euno - About Tab

// ============== About ==============

let aboutContent = null;

async function loadAboutData() {
    try {
        const response = await fetch('/api/about');
        const data = await response.json();
        aboutContent = data.content || '';
        renderAbout();
    } catch (error) {
        console.error('Failed to load about:', error);
        document.getElementById('about-content').innerHTML =
            '<div class="focus-empty">Failed to load about content</div>';
    }
}

function renderAbout() {
    const container = document.getElementById('about-content');
    if (!aboutContent) {
        container.innerHTML = '<div class="focus-empty">No content available</div>';
        return;
    }
    // Use marked to convert markdown to HTML
    container.innerHTML = marked.parse(aboutContent);
}

function discussTask(description) {
    contextInput.value = `Tell me about the task: ${description}`;
    switchTab('chat');
    sendContextMessage();
}

function showFullContent(title, content, type = 'task') {
    // Show full content in chat area as a system message (not logged to lifelog)
    switchTab('chat');

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-system';
    messageDiv.innerHTML = `
        <div class="message-system-header">
            <span class="message-system-title">${escapeHtml(title)}</span>
            <button class="message-system-close" onclick="this.closest('.message-system').remove()">×</button>
        </div>
        <div class="message-system-body">${type === 'notes' ? marked.parse(content) : escapeHtml(content)}</div>
    `;

    inlineMessages.appendChild(messageDiv);
    scrollChatToBottom();
}

function scrollChatToBottom() {
    const chatPane = document.getElementById('tab-chat');
    if (chatPane) chatPane.scrollTop = chatPane.scrollHeight;
}

function showTaskById(taskId) {
    // Look up task in tasksData or completedTasksData and show in chat
    const task = tasksData.find(t => t.id === taskId) || completedTasksData.find(t => t.id === taskId);
    if (!task) return;
    const displayName = task.name || task.description || 'Untitled';
    const description = task.description || '';
    showTaskFullContent(displayName, description, task.project_title || 'General');
}

function showTaskFullContent(taskName, description, projectName) {
    // Show task with project name in chat area, rendering markdown
    switchTab('chat');

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-system';
    messageDiv.innerHTML = `
        <div class="message-system-header">
            <span class="message-system-title">${escapeHtml(projectName)}: ${escapeHtml(taskName)}</span>
            <button class="message-system-close" onclick="this.closest('.message-system').remove()">×</button>
        </div>
        ${description ? `<div class="message-system-body">${marked.parse(description)}</div>` : ''}
    `;

    inlineMessages.appendChild(messageDiv);
    scrollChatToBottom();
}

function bringNoteToChat(projectName, noteTitle, notePreview) {
    // Quote note and ask what user wants to do
    const message = `Regarding this note from "${projectName}":\n\n> **${noteTitle}**\n> ${notePreview}\n\nWhat would you like to do with this?`;
    contextInput.value = message;
    contextInput.focus();
    // Auto-expand textarea
    contextInput.style.height = 'auto';
    contextInput.style.height = Math.min(contextInput.scrollHeight, 200) + 'px';
}

async function deleteProjectNote(projectId, filename) {
    if (!confirm('Delete this note?')) return;

    try {
        const response = await fetch(`/api/projects/${projectId}/notes/${filename}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Clear the expanded state for this note
            expandedCards.delete(`note-${filename}`);
            // Reload data to refresh notes list
            await loadTasksData();
        }
    } catch (error) {
        console.error('Failed to delete note:', error);
    }
}

async function addTaskToProject(projectId, inputEl) {
    const description = inputEl.value.trim();
    if (!description) return;

    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: description,
                project_id: projectId,
                priority: 'medium'
            })
        });

        if (response.ok) {
            inputEl.value = '';
            await loadTasksData();
        }
    } catch (error) {
        console.error('Failed to add task:', error);
    }
}

function updateTasksBadge() {
    const badge = document.getElementById('tasks-badge');
    // Count jobs due today
    const count = jobsData.filter(j => getJobCategory(j) === 'today').length;
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline' : 'none';
}

