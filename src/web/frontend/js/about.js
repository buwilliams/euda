// Euno - Docs Explorer

// ============== Docs Navigation ==============

let docsHistory = [];  // Stack of {path, title} objects
let currentDoc = null;
let docsSlideDirection = null;  // 'forward' or 'back'

async function loadDocsData() {
    // Start on README.md
    docsSlideDirection = null;  // No animation for initial load
    await navigateToDoc('README.md');
}

async function navigateToDoc(path, direction = 'forward') {
    try {
        const response = await fetch(`/api/docs?path=${encodeURIComponent(path)}`);
        const data = await response.json();

        if (data.error) {
            document.getElementById('about-content').innerHTML =
                `<div class="view-slide-container current"><div class="focus-empty">Error: ${data.error}</div></div>`;
            return;
        }

        // Add current doc to history before navigating (if we have one)
        if (currentDoc && currentDoc.path !== path) {
            docsHistory.push(currentDoc);
            docsSlideDirection = direction;
        }

        // Extract title from first heading or filename
        const title = extractTitle(data.content, path);

        currentDoc = { path: path, title: title, content: data.content };
        renderDoc();
    } catch (error) {
        console.error('Failed to load doc:', error);
        document.getElementById('about-content').innerHTML =
            '<div class="view-slide-container current"><div class="focus-empty">Failed to load documentation</div></div>';
    }
}

function extractTitle(content, path) {
    // Try to extract title from first # heading
    const match = content.match(/^#\s+(.+)$/m);
    if (match) {
        return match[1];
    }
    // Fall back to filename without extension
    return path.split('/').pop().replace('.md', '');
}

function renderDoc() {
    if (!currentDoc) return;

    const container = document.getElementById('about-content');
    const titleEl = document.getElementById('docs-title');
    const breadcrumbsEl = document.getElementById('docs-breadcrumbs');

    // Update header
    titleEl.textContent = currentDoc.title;

    // Build breadcrumbs
    const pathParts = currentDoc.path.split('/');
    let breadcrumbHtml = '<span>More</span><img src="/web/icons/chevron-right.svg" alt=">">';
    breadcrumbHtml += '<span>About</span>';
    if (currentDoc.path !== 'README.md') {
        breadcrumbHtml += '<img src="/web/icons/chevron-right.svg" alt=">">';
        breadcrumbHtml += `<span>${pathParts[pathParts.length - 1].replace('.md', '')}</span>`;
    }
    breadcrumbsEl.innerHTML = breadcrumbHtml;

    // Render markdown content
    const html = marked.parse(currentDoc.content);
    const content = `<div class="docs-markdown-content">${html}</div>`;

    // Apply slide animation if we have a direction and existing view
    if (docsSlideDirection && container.querySelector('.view-slide-container')) {
        animateSlideTransition(container, content, docsSlideDirection, processDocsContent);
        docsSlideDirection = null;
    } else {
        container.innerHTML = `<div class="view-slide-container current">${content}</div>`;
        processDocsContent(container.querySelector('.view-slide-container'));
    }

    // Scroll to top
    container.scrollTop = 0;
}

function processDocsContent(viewContainer) {
    const innerContainer = viewContainer.querySelector('.docs-markdown-content');
    if (innerContainer) {
        rewriteImagePaths(innerContainer);
        interceptDocLinks(innerContainer);
    }
}

// Generic slide transition animation (reusable)
function animateSlideTransition(container, newContent, direction, onNewViewReady) {
    const oldView = container.querySelector('.view-slide-container');
    if (!oldView) {
        container.innerHTML = `<div class="view-slide-container current">${newContent}</div>`;
        if (onNewViewReady) onNewViewReady(container.querySelector('.view-slide-container'));
        return;
    }

    const newView = document.createElement('div');
    newView.className = 'view-slide-container';
    newView.innerHTML = newContent;

    if (direction === 'forward') {
        newView.classList.add('slide-in-right');
    } else {
        newView.classList.add('slide-in-left');
    }

    container.appendChild(newView);

    // Process new content before animation completes
    if (onNewViewReady) onNewViewReady(newView);

    newView.offsetHeight; // Trigger reflow

    if (direction === 'forward') {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-left');
    } else {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-right');
    }

    newView.classList.remove('slide-in-left', 'slide-in-right');
    newView.classList.add('current');

    setTimeout(() => {
        if (oldView.parentNode) oldView.remove();
    }, 300);
}

function rewriteImagePaths(container) {
    const images = container.querySelectorAll('img');
    images.forEach(img => {
        const src = img.getAttribute('src');
        if (!src) return;

        // Rewrite src/web/frontend/images/ to /web/images/
        if (src.startsWith('src/web/frontend/images/')) {
            img.setAttribute('src', src.replace('src/web/frontend/images/', '/web/images/'));
        }
        // Rewrite src/web/frontend/ to /web/
        else if (src.startsWith('src/web/frontend/')) {
            img.setAttribute('src', src.replace('src/web/frontend/', '/web/'));
        }
    });
}

function interceptDocLinks(container) {
    const links = container.querySelectorAll('a');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;

        // Check if it's a local markdown link
        if (isLocalDocLink(href)) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const resolvedPath = resolveDocPath(href);
                navigateToDoc(resolvedPath);
            });
            // Style as internal link
            link.classList.add('doc-internal-link');
        } else if (href.startsWith('http://') || href.startsWith('https://')) {
            // External link - open in new tab
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        }
    });
}

function isLocalDocLink(href) {
    // Local doc links are relative .md files or docs/specs paths
    if (href.startsWith('http://') || href.startsWith('https://')) {
        return false;
    }
    if (href.startsWith('#')) {
        return false;  // Anchor link
    }
    if (href.endsWith('.md')) {
        return true;
    }
    if (href.startsWith('docs/') || href.startsWith('specs/')) {
        return true;
    }
    return false;
}

function resolveDocPath(href) {
    // Resolve relative path based on current doc location
    if (!currentDoc) return href;

    // If already absolute-ish (starts with docs/ or specs/ or is README.md)
    if (href.startsWith('docs/') || href.startsWith('specs/') || href === 'README.md') {
        return href;
    }

    // Get current directory
    const currentDir = currentDoc.path.includes('/')
        ? currentDoc.path.substring(0, currentDoc.path.lastIndexOf('/'))
        : '';

    // Handle relative paths
    if (href.startsWith('./')) {
        href = href.substring(2);
    }

    // Handle parent directory references
    let targetDir = currentDir;
    while (href.startsWith('../')) {
        href = href.substring(3);
        targetDir = targetDir.includes('/')
            ? targetDir.substring(0, targetDir.lastIndexOf('/'))
            : '';
    }

    // Combine
    if (targetDir) {
        return `${targetDir}/${href}`;
    }
    return href;
}

function docsNavigateBack() {
    if (docsHistory.length > 0) {
        // Pop from history and navigate with back animation
        const prev = docsHistory.pop();
        currentDoc = prev;
        docsSlideDirection = 'back';
        renderDoc();
    } else {
        // No history, go back to More menu
        navigateMoreMenuBack();
    }
}

// Reset docs state when opening the tab
function resetDocsExplorer() {
    docsHistory = [];
    currentDoc = null;
}

// ============== Legacy functions kept for compatibility ==============

function discussTask(description) {
    contextInput.value = `Tell me about the task: ${description}`;
    switchTab('chat');
    sendContextMessage();
}

function showFullContent(title, content, type = 'task') {
    // Show full content in chat area as a system message (not logged to memory)
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
    const messages = document.getElementById('inline-messages');
    if (messages) messages.scrollTop = messages.scrollHeight;
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
    try {
        const response = await fetch(`/api/projects/${projectId}/notes/${filename}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Clear the expanded state for this note
            expandedCards.delete(`note-${filename}`);
            // Reload data to refresh notes list
            await loadTopicsData();
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
            await loadTopicsData();
        }
    } catch (error) {
        console.error('Failed to add task:', error);
    }
}

function updateTopicsBadge() {
    const badge = document.getElementById('tasks-badge');
    // Count topics due today
    const count = topicsData.filter(j => getTopicCategory(j) === 'today').length;
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline' : 'none';
}
