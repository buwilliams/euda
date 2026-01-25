// Euno - Focus Feature Screens (Child Topics, Attach)

// ============== New Child Topic Screen ==============

function renderNewTopicScreen(parentTopicId) {
    const parentTopic = allTopicsData.find(j => j.id === parentTopicId);
    const parentName = parentTopic ? parentTopic.name : 'Topic';
    const childTopics = allTopicsData.filter(j => j.parent_id === parentTopicId);

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Add Topics</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="topic-section">
                <div class="topic-section-header">Add to: ${escapeHtml(parentName)}</div>
                <div class="quick-add-section" style="margin-top: 0; padding-top: 0; border-top: none;">
                    <input type="text" id="quick-add-child-${parentTopicId}" class="quick-add-input" placeholder="New topic name..." onkeypress="handleQuickAddChildKeypress(event, '${parentTopicId}')">
                    <button class="quick-add-btn" onclick="quickAddChildTopic('${parentTopicId}')">${icon('plus')}</button>
                </div>
            </div>
            ${childTopics.length > 0 ? `
            <div class="topic-section">
                <div class="topic-section-header">Child Topics (${childTopics.length})</div>
                ${childTopics.map(topic => renderTopicCard(topic, true)).join('')}
            </div>
            ` : ''}
        </div>
    `;
}

function handleQuickAddChildKeypress(event, parentTopicId) {
    if (event.key === 'Enter') {
        quickAddChildTopic(parentTopicId);
    }
}

async function quickAddChildTopic(parentTopicId) {
    const input = document.getElementById(`quick-add-child-${parentTopicId}`);
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    try {
        const response = await fetch('/api/topics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent_id: parentTopicId, assignee: 'user' })
        });

        if (response.ok) {
            input.value = '';
            await loadTopicsData();
            // Re-focus the input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById(`quick-add-child-${parentTopicId}`);
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create topic:', error);
    }
}

// ============== Attach Screen ==============

function renderAttachScreen(topicId) {
    const topic = allTopicsData.find(j => j.id === topicId);
    const topicName = topic ? topic.name : 'Topic';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Add Assets</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="topic-section">
                <div class="topic-section-header">Add to: ${escapeHtml(topicName)}</div>

                <div class="attach-option" onclick="showNewFileForm('${topicId}')">
                    <span class="attach-option-icon">${icon('pencil')}</span>
                    <span class="attach-option-label">Create new file</span>
                </div>

                <label class="attach-option">
                    <span class="attach-option-icon">${icon('folder')}</span>
                    <span class="attach-option-label">Upload files</span>
                    <input type="file" multiple style="display: none;" onchange="handleMultiFileUpload(event, '${topicId}')">
                </label>
            </div>

            <div id="new-file-form" class="topic-section" style="display: none;">
                <div class="topic-section-header">New File</div>
                <textarea class="topic-description-input" id="new-file-content" placeholder="Start writing..." style="min-height: 150px;"></textarea>
                <div class="screen-actions" style="margin-top: 0.5rem;">
                    <button class="screen-action-btn" onclick="hideNewFileForm()">Cancel</button>
                    <button class="screen-action-btn primary" onclick="createNewFileWithContent('${topicId}')">Save</button>
                </div>
            </div>
        </div>
    `;
}

function showNewFileForm(topicId) {
    document.getElementById('new-file-form').style.display = 'block';
    document.getElementById('new-file-content').focus();
}

function hideNewFileForm() {
    document.getElementById('new-file-form').style.display = 'none';
    document.getElementById('new-file-content').value = '';
}

function generateFilenameFromContent(content) {
    // Get first line
    let firstLine = content.split('\n')[0].trim();
    // Strip markdown heading characters and other common prefixes
    firstLine = firstLine.replace(/^[#*\->\s]+/, '').trim();
    // Take first 5 words max
    const words = firstLine.split(/\s+/).slice(0, 5).join('_');
    // Remove special characters, keep alphanumeric and underscores
    let filename = words.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase();
    // Remove leading/trailing underscores
    filename = filename.replace(/^_+|_+$/g, '');
    // Fallback if empty
    if (!filename) {
        filename = 'note_' + Date.now();
    }
    // Limit length
    if (filename.length > 40) {
        filename = filename.substring(0, 40);
    }
    return filename + '.md';
}

async function createNewFileWithContent(topicId) {
    const content = document.getElementById('new-file-content').value;

    if (!content.trim()) {
        return;
    }

    const filename = generateFilenameFromContent(content);

    try {
        const response = await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            // Clear cache to force reload
            delete topicAssetsCache[topicId];
            // Navigate back to topic detail (will trigger fresh asset load)
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to create file:', error);
    }
}

async function handleMultiFileUpload(event, topicId) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
        try {
            const content = await file.text();
            await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(file.name)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        } catch (error) {
            console.error('Failed to upload file:', error);
        }
    }

    // Clear cache to force reload
    delete topicAssetsCache[topicId];
    navigateFocusBack();
}
