// Euno - Focus Asset Management

// ============== Asset Utilities ==============

function isTextAsset(asset) {
    const textTypes = ['text/', 'application/json', 'application/xml', 'application/javascript'];
    const textExtensions = ['.md', '.txt', '.json', '.xml', '.html', '.css', '.js', '.py', '.sh', '.yaml', '.yml'];

    if (asset.mime_type) {
        for (const type of textTypes) {
            if (asset.mime_type.startsWith(type)) return true;
        }
    }

    const filename = asset.filename.toLowerCase();
    for (const ext of textExtensions) {
        if (filename.endsWith(ext)) return true;
    }

    return false;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function startEditingAsset(filename) {
    editingAssetFilename = filename;
    renderFocusTab();
    setTimeout(() => {
        const textarea = document.getElementById(`asset-content-edit`);
        if (textarea) textarea.focus();
    }, 50);
}

function cancelEditingAsset() {
    editingAssetFilename = null;
    renderFocusTab();
}

// ============== Asset API Functions ==============

async function loadTopicAssets(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/assets`);
        if (response.ok) {
            const assets = await response.json();
            topicAssetsCache[topicId] = assets;
            return assets;
        }
    } catch (error) {
        console.error('Failed to load assets:', error);
    }
    // Always set cache to prevent infinite reload loop
    topicAssetsCache[topicId] = [];
    return [];
}

async function deleteAsset(topicId, filename) {
    try {
        const response = await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTopicAssets(topicId);
            renderFocusTab();
        }
    } catch (error) {
        console.error('Failed to delete asset:', error);
    }
}

async function uploadAsset(topicId, file) {
    try {
        // Read file as text (for now, only supporting text files)
        const content = await file.text();

        const response = await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(file.name)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            await loadTopicAssets(topicId);
            renderFocusTab();
        }
    } catch (error) {
        console.error('Failed to upload asset:', error);
    }
}

function handleAssetUpload(event, topicId) {
    const file = event.target.files[0];
    if (file) {
        uploadAsset(topicId, file);
        event.target.value = ''; // Reset input
    }
}

async function loadAssetContent(topicId, filename) {
    try {
        const response = await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(filename)}`);
        if (response.ok) {
            currentAssetData = await response.json();
            currentAssetData.topicId = topicId;
            return currentAssetData;
        }
    } catch (error) {
        console.error('Failed to load asset:', error);
    }
    // Always set currentAssetData to prevent infinite reload loop
    currentAssetData = { topicId, filename, content: '', error: true };
    return null;
}

async function saveAssetContent(topicId, filename) {
    const textarea = document.getElementById('asset-content-edit');
    if (!textarea) return;

    try {
        const response = await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: textarea.value })
        });

        if (response.ok) {
            // Update current data and refresh cache
            currentAssetData.content = textarea.value;
            await loadTopicAssets(topicId);
        }
    } catch (error) {
        console.error('Failed to save asset:', error);
    }
}

async function createNewAsset(topicId) {
    const input = document.getElementById(`new-asset-${topicId}`);
    if (!input) return;

    let filename = input.value.trim();
    if (!filename) return;

    // Add .md extension if no extension provided
    if (!filename.includes('.')) {
        filename = filename + '.md';
    }

    try {
        const response = await fetch(`/api/topics/${topicId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: '' })
        });

        if (response.ok) {
            input.value = '';
            await loadTopicAssets(topicId);
            // Navigate to the new asset
            navigateFocus(`asset-${topicId}-${filename}`);
        }
    } catch (error) {
        console.error('Failed to create asset:', error);
    }
}

function handleNewAssetKeypress(event, topicId) {
    if (event.key === 'Enter') {
        createNewAsset(topicId);
    }
}

// ============== Asset Views ==============

function renderAssetView(topicId, filename) {
    // Get topic name for header (use allTopicsData to find any topic regardless of status)
    const topic = allTopicsData.find(j => j.id === topicId);
    const isCompleted = topic?.status === 'done';
    const topicName = topic ? topic.name : 'Topic';

    // Load asset if not already loaded
    if (!currentAssetData || currentAssetData.filename !== filename || currentAssetData.topicId !== topicId) {
        loadAssetContent(topicId, filename).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Loading...</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="empty-section">Loading asset...</div>
            </div>
        `;
    }

    const asset = currentAssetData;
    const isEditing = editingAssetFilename === filename;
    const hasContent = asset.content && asset.content.trim().length > 0;
    const isMarkdown = filename.toLowerCase().endsWith('.md');

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${escapeHtml(filename)}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                ${isEditing ? `
                    <button class="task-detail-action" onclick="saveAssetContent('${topicId}', '${escapeHtml(filename)}'); cancelEditingAsset();">${icon('arrow-down-tray')} Save</button>
                    <button class="task-detail-action" onclick="cancelEditingAsset()">Cancel</button>
                ` : `
                    <button class="task-detail-action" onclick="startEditingAsset('${escapeHtml(filename)}')">${icon('pencil')} Edit</button>
                `}
                <button class="task-detail-action danger" onclick="deleteAsset('${topicId}', '${escapeHtml(filename)}'); navigateFocusBack();">${icon('trash')} Delete</button>
            </div>

            <!-- Asset Content -->
            <div class="topic-section">
                <div class="topic-section-header">Content</div>
                ${isEditing ? `
                    <textarea class="topic-description-input" id="asset-content-edit" style="min-height: 300px;"
                        placeholder="Write content here...">${escapeHtml(asset.content || '')}</textarea>
                ` : `
                    <div class="topic-description-display ${hasContent ? '' : 'empty'}" onclick="startEditingAsset('${escapeHtml(filename)}')">
                        ${hasContent ? (isMarkdown ? marked.parse(asset.content) : `<pre>${escapeHtml(asset.content)}</pre>`) : 'Click to add content...'}
                    </div>
                `}
            </div>

            <!-- Back Link -->
            <div class="topic-section">
                <div class="topic-section-header">Topic</div>
                <div class="asset-back-link" onclick="navigateFocus('${isCompleted ? 'completed' : 'topic'}-${topicId}')">
                    ${icon('folder')}
                    <span>${escapeHtml(topicName)}</span>
                    ${icon('chevron-right')}
                </div>
            </div>
        </div>
    `;
}

function renderAssetsListView(topicId) {
    // Use allTopicsData to find any topic regardless of status
    const topic = allTopicsData.find(j => j.id === topicId);
    const isCompleted = topic?.status === 'done';
    const topicName = topic ? topic.name : 'Topic';
    const assets = topicAssetsCache[topicId] || [];

    // Load assets if not cached
    if (!topicAssetsCache[topicId]) {
        loadTopicAssets(topicId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Assets</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="topic-section">
                <div class="topic-section-header">Topic</div>
                <div class="card-project-link" onclick="navigateFocus('${isCompleted ? 'completed' : 'topic'}-${topicId}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(topicName)}</div>
            </div>

            <div class="task-detail-actions">
                <label class="task-detail-action" style="cursor: pointer;">
                    Upload File
                    <input type="file" style="display: none;" onchange="handleAssetUpload(event, '${topicId}')">
                </label>
            </div>

            ${assets.length > 0 ? `
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${topicId}-${asset.filename}')" style="cursor: pointer;">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="event.stopPropagation(); deleteAsset('${topicId}', '${escapeHtml(asset.filename)}')" title="Delete">${icon('trash')}</button>
                                <span class="asset-item-arrow">${icon('chevron-right')}</span>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${topicId}', '${escapeHtml(asset.filename)}')" title="Delete">${icon('trash')}</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            ` : ''}

            <div class="asset-add-row">
                <input type="text" class="asset-add-input" id="new-asset-${topicId}" placeholder="New asset name..." onkeypress="handleNewAssetKeypress(event, '${topicId}')">
                <button class="asset-add-btn" onclick="createNewAsset('${topicId}')">${icon('plus')}</button>
                <label class="asset-upload-btn">
                    Upload
                    <input type="file" style="display: none;" onchange="handleAssetUpload(event, '${topicId}')">
                </label>
            </div>
        </div>
    `;
}

function renderRecentAssetsView() {
    // Load recent assets if not cached
    if (recentAssetsCache === null) {
        loadRecentAssets().then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">${icon('document')} Assets</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading assets...</div>
            </div>
        `;
    }

    const assets = recentAssetsCache || [];

    // Helper to get topic name
    const getTopicName = (topicId) => {
        const topic = allTopicsData.find(t => t.id === topicId);
        return topic ? topic.name : topicId;
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('document')} Assets</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${assets.length > 0 ? `
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        const topicName = getTopicName(asset.topic_id);
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${asset.topic_id}-${asset.filename}')" style="cursor: pointer;">
                                <div class="asset-item-info">
                                    <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                    <span class="asset-item-topic">${escapeHtml(topicName)}</span>
                                </div>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <span class="asset-item-arrow">${icon('chevron-right')}</span>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <div class="asset-item-info">
                                    <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                    <span class="asset-item-topic">${escapeHtml(topicName)}</span>
                                </div>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            ` : '<div class="focus-empty">No assets yet</div>'}
        </div>
    `;
}
