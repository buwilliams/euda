// Euno - Focus View Agent Renderers
// All agent-related views and management screens

// ============== Global Caches ==============

let memoryListCache = {};
let memoryItemCache = {};
let longTermMemoryListCache = {};
let longTermMemoryDetailCache = {};
let monitoringCache = {};
let monitoringPagination = {};  // { agentId: { offset: 0, limit: 20 } }
let monitoringLoading = {};     // { agentId: true } - prevents duplicate requests
let rateLimitViewCache = {};

// ============== Agent Detail View ==============

function renderAgentDetailView(job) {
    const agentId = job.agent_id;
    const displayName = job.name || 'Untitled';
    const childJobs = jobsData.filter(j => j.parent_id === job.id);
    const completedChildJobs = completedJobsData.filter(j => j.parent_id === job.id);
    // Merge and sort: open jobs first, then completed
    const allChildJobs = [...childJobs, ...completedChildJobs].sort((a, b) => {
        const aCompleted = a.status === 'completed' ? 1 : 0;
        const bCompleted = b.status === 'completed' ? 1 : 0;
        return aCompleted - bCompleted;
    });
    const assets = jobAssetsCache[job.id] || [];

    // Load agent data if not cached
    const agentData = agentDataCache[agentId];
    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">${icon('bolt')}${escapeHtml(displayName)}</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading agent data...</div>
            </div>
        `;
    }

    // Load assets if not cached
    if (!jobAssetsCache[job.id]) {
        loadJobAssets(job.id).then(() => renderFocusTab());
    }

    const config = agentData.config || {};
    const isEnabled = config.enabled !== false;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('bolt')}${escapeHtml(displayName)}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="toggleAgentEnabled('${agentId}', ${!isEnabled})">${isEnabled ? icon('x-mark') + ' Disable' : icon('check') + ' Enable'}</button>
                <button class="task-detail-action" onclick="openAddPicker('${job.id}')">+ Add</button>
            </div>

            <!-- Jobs Section (merged pending + completed child jobs, open first) -->
            <div class="job-section">
                <div class="job-section-header collapsible ${allChildJobs.length > 0 ? 'open' : ''}" onclick="togglePersonaSection(this, event)">
                    <span>Jobs${allChildJobs.length > 0 ? ` (${allChildJobs.length})` : ''}</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content ${allChildJobs.length > 0 ? 'open' : ''}">
                    ${allChildJobs.length === 0 ? '<div class="focus-empty">No jobs assigned to this agent.</div>' :
                      allChildJobs.map(child => {
                          const isCompleted = child.status === 'completed';
                          if (isCompleted) {
                              const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                              return renderCompletedJobCard(child, grandchildCount, true);
                          } else {
                              return renderJobCard(child, true);
                          }
                      }).join('')
                    }
                </div>
            </div>

            <!-- Manage Navigation -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('manage-agent-${agentId}')">
                    <span>Manage</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Assets Section -->
            ${assets.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Assets (${assets.length})</div>
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${job.id}-${asset.filename}')" style="cursor: pointer;">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="event.stopPropagation(); deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">${icon('trash')}</button>
                                <span class="asset-item-arrow">${icon('chevron-right')}</span>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${job.id}', '${escapeHtml(asset.filename)}')" title="Delete">${icon('trash')}</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

// ============== Agent Pause Banner ==============

function renderPauseBanner(agentId, pauseStatus) {
    const reason = pauseStatus.reason || 'Agent paused by rate limiting';
    const timestamp = pauseStatus.timestamp;
    const timeAgo = timestamp ? formatPauseTimestamp(timestamp) : '';

    return `
        <div class="agent-paused-banner">
            <div class="pause-banner-content">
                ${icon('exclamation-triangle')}
                <div class="pause-banner-text">
                    <strong>Agent Paused</strong>
                    <span class="pause-reason">${escapeHtml(reason)}</span>
                    ${timeAgo ? `<span class="pause-time">${timeAgo}</span>` : ''}
                </div>
            </div>
            <button class="pause-resume-btn" onclick="resumeAgent('${agentId}')">
                ${icon('play')} Resume
            </button>
        </div>
    `;
}

function formatPauseTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============== Agent Manage View ==============

function renderAgentManageView(agentId) {
    const agent = agentsCache?.find(a => a.id === agentId);
    // Also try agentDataCache
    const agentData = agentDataCache[agentId];

    // Load agent data if not cached
    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Manage</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading agent data...</div>
            </div>
        `;
    }

    // Load pause status if not cached
    if (!(agentId in agentPauseStatus)) {
        loadAgentPauseStatus(agentId).then(() => renderFocusTab());
    }

    // Check active executions on initial load to restore button state after page refresh
    // Only check if we don't already have an active execution for this agent
    if (!activeExecution || activeExecution.agentId !== agentId) {
        // Check if we've already loaded active executions for this agent
        if (!agentDataCache[agentId]?._activeExecutionsLoaded) {
            loadActiveExecutions(agentId).then(() => {
                if (agentDataCache[agentId]) {
                    agentDataCache[agentId]._activeExecutionsLoaded = true;
                }
                renderFocusTab();
            });
        }
    }

    const displayName = agent?.name || agentData?.config?.name || agentId;
    const pauseStatus = agentPauseStatus[agentId] || { isPaused: false };

    // Check if any execution is running for this agent
    const isRunning = activeExecution && activeExecution.agentId === agentId;
    const runningPhase = isRunning ? activeExecution.phase : null;

    // Helper to render action button with running state
    const actionButton = (phase, iconName, label, onclick) => {
        const isThisRunning = runningPhase === phase;
        const classes = `task-detail-action${isThisRunning ? ' running' : ''}`;
        const disabled = isRunning || pauseStatus.isPaused ? 'disabled' : '';
        const displayIcon = isThisRunning ? icon('arrow-path', 'spinning') : icon(iconName);
        const displayLabel = isThisRunning ? `${label}...` : label;
        return `<button class="${classes}" onclick="${onclick}" ${disabled}>${displayIcon} ${displayLabel}</button>`;
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Manage</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${pauseStatus.isPaused ? renderPauseBanner(agentId, pauseStatus) : ''}

            <!-- Live Execution Progress -->
            ${getActiveExecutionHtml(agentId)}

            <!-- Action Menu -->
            <div class="task-detail-actions">
                ${actionButton('append', 'arrow-path', 'Append', `triggerReflection('${agentId}', 'append')`)}
                ${actionButton('consolidate', 'archive-box', 'Consolidate', `triggerReflection('${agentId}', 'consolidate')`)}
                ${actionButton('exploration', 'sparkles', 'Explore', `triggerExploration('${agentId}')`)}
            </div>

            <!-- Identity Section - navigates to identity view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('identity-${agentId}')">
                    <span>Identity</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Configuration Section - navigates to config view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('config-${agentId}')">
                    <span>Configuration</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Short-term Memory Section - navigates to memory list view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('memory-list-${agentId}')">
                    <span>Short-term Memory</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Long-term Memory Section - navigates to memory dates view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('long-term-memory-${agentId}')">
                    <span>Long-term Memory</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Monitoring Section - navigates to prompts list view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('monitoring-${agentId}')">
                    <span>Monitoring</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Rate Limit Events Section - navigates to events view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('rate-limits-${agentId}')">
                    <span>Rate Limit Events</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>
        </div>
    `;
}

// ============== Memory List View ==============

function renderMemoryListView(agentId) {
    const agentData = agentDataCache[agentId];
    const displayName = agentData?.config?.name || agentId;

    // Check cache
    const cached = memoryListCache[agentId];
    if (!cached) {
        loadShortTermMemory(agentId).then(items => {
            memoryListCache[agentId] = items || [];
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Short-term Memory</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading memory...</div>
            </div>
        `;
    }

    const items = cached;
    const typeColors = {
        person: 'type-person',
        place: 'type-place',
        thing: 'type-thing',
        goal: 'type-goal',
        concern: 'type-concern',
        idea: 'type-idea',
        learning: 'type-learning',
        behavior: 'type-behavior'
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Short-term Memory</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Action Menu -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="addMemoryItem('${agentId}')">+ Add Memory</button>
            </div>

            <!-- Memory Items -->
            ${items.length === 0 ? '<div class="focus-empty">No short-term memory items.</div>' :
              items.map(item => `
                <div class="memory-list-item" onclick="navigateFocus('memory-item-${agentId}-${item.id}')">
                    <span class="memory-type-badge ${typeColors[item.type] || 'type-thing'}">${escapeHtml(item.type)}</span>
                    <span class="memory-item-content">${escapeHtml(item.short_description)}</span>
                    <span class="memory-item-arrow">${icon('chevron-right')}</span>
                </div>
              `).join('')
            }
        </div>
    `;
}

// ============== Memory Item Detail View ==============

function renderMemoryItemView(agentId, entryId) {
    const cacheKey = `${agentId}-${entryId}`;

    // Try to get from list cache first
    const listItems = memoryListCache[agentId];
    let item = listItems?.find(i => i.id === entryId);

    if (!item) {
        item = memoryItemCache[cacheKey];
    }

    if (!item) {
        // Load from API
        loadMemoryItem(agentId, entryId).then(data => {
            memoryItemCache[cacheKey] = data;
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Memory Item</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    const typeColors = {
        person: 'type-person',
        place: 'type-place',
        thing: 'type-thing',
        goal: 'type-goal',
        concern: 'type-concern',
        idea: 'type-idea',
        learning: 'type-learning',
        behavior: 'type-behavior'
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Memory Item</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Action Menu -->
            <div class="task-detail-actions">
                <button class="task-detail-action danger" onclick="deleteMemoryItemAndGoBack('${agentId}', '${entryId}')">
                    ${icon('trash')} Delete
                </button>
            </div>

            <!-- Type Badge -->
            <div class="job-section">
                <div class="job-section-header">Type</div>
                <div class="memory-type-badge ${typeColors[item.type] || 'type-thing'}" style="display: inline-block; margin: 0.5rem 0;">
                    ${escapeHtml(item.type)}
                </div>
            </div>

            <!-- Content -->
            <div class="job-section">
                <div class="job-section-header">Content</div>
                <div class="memory-item-full-content">${escapeHtml(item.short_description)}</div>
            </div>

            <!-- Details -->
            ${item.details ? `
            <div class="job-section">
                <div class="job-section-header">Details</div>
                <div class="memory-item-details">${escapeHtml(item.details)}</div>
            </div>
            ` : ''}

            <!-- Created -->
            <div class="job-section">
                <div class="job-section-header">Created</div>
                <div class="memory-item-date">${item.created_at ? formatFriendlyPastDate(item.created_at) : 'Unknown'}</div>
            </div>

            <!-- Expires -->
            ${item.expires_at ? `
            <div class="job-section">
                <div class="job-section-header">Expires</div>
                <div class="memory-item-date">${formatFriendlyPastDate(item.expires_at)}</div>
            </div>
            ` : ''}
        </div>
    `;
}

async function deleteMemoryItemAndGoBack(agentId, entryId) {
    await deleteMemoryItem(agentId, entryId);
    // Clear caches
    delete memoryListCache[agentId];
    delete memoryItemCache[`${agentId}-${entryId}`];
    navigateFocusBack();
}

// ============== Long-term Memory List View ==============

function renderLongTermMemoryListView(agentId) {
    // Check cache for dates and previews
    const cached = longTermMemoryListCache[agentId];
    if (!cached) {
        loadLongTermMemoryWithPreviews(agentId).then(data => {
            longTermMemoryListCache[agentId] = data || [];
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Long-term Memory</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading memory...</div>
            </div>
        `;
    }

    const entries = cached;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Long-term Memory</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${entries.length === 0 ? '<div class="focus-empty">No long-term memory entries.</div>' :
              entries.map(entry => `
                <div class="memory-list-item" onclick="navigateFocus('long-term-memory-detail-${agentId}-${entry.date}')">
                    <span class="memory-date-badge">${formatMemoryDate(entry.date)}</span>
                    <span class="memory-item-content">${escapeHtml(entry.preview || 'No content')}</span>
                    <span class="memory-item-arrow">${icon('chevron-right')}</span>
                </div>
              `).join('')
            }
        </div>
    `;
}

function formatMemoryDate(dateStr) {
    // Format YYYY-MM-DD to more readable format
    const date = new Date(dateStr + 'T00:00:00');
    const options = { month: 'short', day: 'numeric', year: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// ============== Long-term Memory Detail View ==============

function renderLongTermMemoryDetailView(agentId, date) {
    const cacheKey = `${agentId}-${date}`;

    // Check cache
    let entry = longTermMemoryDetailCache[cacheKey];

    if (!entry) {
        // Try to get from list cache
        const listCache = longTermMemoryListCache[agentId];
        const listEntry = listCache?.find(e => e.date === date);
        if (listEntry?.content) {
            entry = listEntry;
        }
    }

    if (!entry || !entry.content) {
        loadLongTermMemoryContent(agentId, date).then(data => {
            longTermMemoryDetailCache[cacheKey] = data;
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">${formatMemoryDate(date)}</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${formatMemoryDate(date)}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="long-term-memory-content">
                ${marked.parse(entry.content || '')}
            </div>
        </div>
    `;
}

// ============== Monitoring View ==============

function renderMonitoringView(agentId) {
    const agentData = agentDataCache[agentId];
    const displayName = agentData?.config?.name || agentId;

    // Initialize pagination state if not set
    if (!monitoringPagination[agentId]) {
        monitoringPagination[agentId] = { offset: 0, limit: 20 };
    }
    const { offset, limit } = monitoringPagination[agentId];

    // Check cache - only use cache if offset matches
    const cached = monitoringCache[agentId];
    const cacheValid = cached && cached.pagination?.offset === offset;

    if (!cacheValid && !monitoringLoading[agentId]) {
        monitoringLoading[agentId] = true;
        loadAgentMonitoring(agentId, offset, limit).then(data => {
            monitoringCache[agentId] = data || { stats: {}, prompts: [], pagination: { offset: 0, limit: 20, total: 0, has_more: false } };
            monitoringLoading[agentId] = false;
            renderFocusTab();
        }).catch(() => {
            monitoringLoading[agentId] = false;
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Monitoring</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading monitoring data...</div>
            </div>
        `;
    }

    // Support both old (recent_prompts) and new (prompts) format
    const { stats, prompts, recent_prompts, pagination } = cached;
    const promptsList = prompts || recent_prompts || [];
    const paginationInfo = pagination || { offset: 0, limit: 20, total: promptsList.length, has_more: false };

    // Get active execution progress HTML if any
    const progressHtml = getActiveExecutionHtml(agentId);

    // Calculate pagination display info
    const currentPage = Math.floor(paginationInfo.offset / paginationInfo.limit) + 1;
    const totalPages = Math.ceil(paginationInfo.total / paginationInfo.limit);
    const hasPrev = paginationInfo.offset > 0;
    const hasNext = paginationInfo.has_more;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Monitoring</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Live Progress (if running) -->
            ${progressHtml}

            <!-- Stats -->
            <div class="monitoring-stats">
                <div class="monitoring-stat">
                    <span class="stat-label">This Week</span>
                    <span class="stat-value">${stats.week?.calls || 0} calls</span>
                    <span class="stat-detail">${formatTokenCount(stats.week?.tokens || 0)} tokens, $${(stats.week?.cost || 0).toFixed(4)}</span>
                </div>
                <div class="monitoring-stat">
                    <span class="stat-label">Today</span>
                    <span class="stat-value">${stats.today?.calls || 0} calls</span>
                    <span class="stat-detail">${formatTokenCount(stats.today?.tokens || 0)} tokens, $${(stats.today?.cost || 0).toFixed(4)}</span>
                </div>
                <div class="monitoring-stat">
                    <span class="stat-label">Last Hour</span>
                    <span class="stat-value">${stats.hour?.calls || 0} calls</span>
                    <span class="stat-detail">${formatTokenCount(stats.hour?.tokens || 0)} tokens, $${(stats.hour?.cost || 0).toFixed(4)}</span>
                </div>
            </div>

            <!-- Recent Prompts Header -->
            <div class="job-section">
                <div class="job-section-header">Recent Prompts${paginationInfo.total > 0 ? ` (${paginationInfo.total} total)` : ''}</div>
            </div>

            <!-- Prompts List -->
            ${promptsList.length === 0 ? '<div class="focus-empty">No recent prompts</div>' :
              promptsList.map((p, index) => `
                <div class="prompt-list-item" onclick="navigateFocus('prompt-${agentId}-${index}')">
                    <span class="prompt-time">${formatPromptTime(p.timestamp)}</span>
                    <span class="prompt-tokens">${p.input_tokens}/${p.output_tokens}</span>
                    <span class="prompt-model">${escapeHtml(p.model || 'unknown')}</span>
                    <span class="prompt-item-arrow">${icon('chevron-right')}</span>
                </div>
              `).join('')
            }

            <!-- Pagination Controls -->
            ${totalPages > 1 ? `
                <div class="memory-pagination" style="margin-top: var(--spacing-md); padding-top: var(--spacing-md); border-top: 1px solid var(--color-border-light); border-bottom: none; margin-bottom: 0; padding-bottom: 0;">
                    <button class="memory-page-btn" onclick="monitoringPagePrev('${agentId}')" ${!hasPrev ? 'disabled' : ''}>Newer</button>
                    <span class="memory-page-info">Page ${currentPage} of ${totalPages}</span>
                    <button class="memory-page-btn" onclick="monitoringPageNext('${agentId}')" ${!hasNext ? 'disabled' : ''}>Older</button>
                </div>
            ` : ''}
        </div>
    `;
}

// Pagination functions for monitoring view
function monitoringPagePrev(agentId) {
    if (!monitoringPagination[agentId]) return;
    const { offset, limit } = monitoringPagination[agentId];
    const newOffset = Math.max(0, offset - limit);
    monitoringPagination[agentId].offset = newOffset;
    delete monitoringCache[agentId];  // Clear cache to force reload
    delete monitoringLoading[agentId];  // Clear loading flag
    renderFocusTab();
}

function monitoringPageNext(agentId) {
    if (!monitoringPagination[agentId]) return;
    const cached = monitoringCache[agentId];
    if (!cached?.pagination?.has_more) return;
    const { offset, limit } = monitoringPagination[agentId];
    monitoringPagination[agentId].offset = offset + limit;
    delete monitoringCache[agentId];  // Clear cache to force reload
    delete monitoringLoading[agentId];  // Clear loading flag
    renderFocusTab();
}

// ============== Prompt Detail View ==============

function renderPromptDetailView(agentId, promptIndex) {
    const cached = monitoringCache[agentId];
    // Support both old (recent_prompts) and new (prompts) format
    const promptsList = cached?.prompts || cached?.recent_prompts;
    if (!cached || !promptsList) {
        // Need to load monitoring data first
        const pagination = monitoringPagination[agentId] || { offset: 0, limit: 20 };
        loadAgentMonitoring(agentId, pagination.offset, pagination.limit).then(data => {
            monitoringCache[agentId] = data || { stats: {}, prompts: [], pagination: { offset: 0, limit: 20, total: 0, has_more: false } };
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Prompt</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    const prompt = promptsList[parseInt(promptIndex)];
    if (!prompt) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Prompt</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Prompt not found</div>
            </div>
        `;
    }

    // Helper to render messages nicely
    const renderMessages = (messages) => {
        if (!Array.isArray(messages)) {
            return `<pre class="prompt-content">${escapeHtml(JSON.stringify(messages, null, 2))}</pre>`;
        }
        return messages.map(msg => {
            const role = msg.role || 'unknown';
            const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2);
            return `
                <div class="prompt-message">
                    <div class="prompt-message-role">${escapeHtml(role)}</div>
                    <div class="prompt-message-content">${marked.parse(content)}</div>
                </div>
            `;
        }).join('');
    };

    // Helper to render response
    const renderResponse = (response) => {
        if (typeof response === 'string') {
            return marked.parse(response);
        }
        // Handle structured response with content array
        if (response && typeof response === 'object') {
            if (Array.isArray(response.content)) {
                // New format: content is an array of blocks
                return response.content.map(block => {
                    if (block.type === 'text') {
                        return `<div class="response-text">${marked.parse(block.text || '')}</div>`;
                    } else if (block.type === 'tool_use') {
                        return `
                            <div class="response-tool-use">
                                <div class="tool-use-header">Tool: ${escapeHtml(block.name || 'unknown')}</div>
                                <pre class="tool-use-input">${escapeHtml(JSON.stringify(block.input, null, 2))}</pre>
                            </div>
                        `;
                    }
                    return `<pre class="prompt-content">${escapeHtml(JSON.stringify(block, null, 2))}</pre>`;
                }).join('');
            }
            if (typeof response.content === 'string') {
                return marked.parse(response.content);
            }
            return `<pre class="prompt-content">${escapeHtml(JSON.stringify(response, null, 2))}</pre>`;
        }
        return '';
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Prompt</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Summary -->
            <div class="job-section">
                <div class="job-section-header">Summary</div>
                <div class="prompt-summary">
                    <div class="prompt-summary-row">
                        <span class="prompt-summary-label">Time:</span>
                        <span class="prompt-summary-value">${prompt.timestamp ? new Date(prompt.timestamp).toLocaleString() : 'Unknown'}</span>
                    </div>
                    <div class="prompt-summary-row">
                        <span class="prompt-summary-label">Model:</span>
                        <span class="prompt-summary-value">${escapeHtml(prompt.model || 'unknown')}</span>
                    </div>
                    <div class="prompt-summary-row">
                        <span class="prompt-summary-label">Input Tokens:</span>
                        <span class="prompt-summary-value">${prompt.input_tokens || 0}</span>
                    </div>
                    <div class="prompt-summary-row">
                        <span class="prompt-summary-label">Output Tokens:</span>
                        <span class="prompt-summary-value">${prompt.output_tokens || 0}</span>
                    </div>
                    <div class="prompt-summary-row">
                        <span class="prompt-summary-label">Cost:</span>
                        <span class="prompt-summary-value">$${(prompt.cost || 0).toFixed(4)}</span>
                    </div>
                    ${prompt.duration_ms ? `
                    <div class="prompt-summary-row">
                        <span class="prompt-summary-label">Duration:</span>
                        <span class="prompt-summary-value">${prompt.duration_ms}ms</span>
                    </div>
                    ` : ''}
                </div>
            </div>

            <!-- System Prompt (if available) -->
            ${prompt.system ? `
            <div class="job-section">
                <div class="job-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>System Prompt</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    <div class="prompt-rendered-content">${marked.parse(prompt.system)}</div>
                </div>
            </div>
            ` : ''}

            <!-- Messages (if available) -->
            ${prompt.messages ? `
            <div class="job-section">
                <div class="job-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Messages</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content" style="display: block;">
                    <div class="prompt-messages-list">${renderMessages(prompt.messages)}</div>
                </div>
            </div>
            ` : ''}

            <!-- Response (if available) -->
            ${prompt.response ? `
            <div class="job-section">
                <div class="job-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Response</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content" style="display: block;">
                    <div class="prompt-rendered-content">${renderResponse(prompt.response)}</div>
                </div>
            </div>
            ` : ''}

            <!-- Tools (if available) -->
            ${prompt.tools && prompt.tools.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Tools (${prompt.tools.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    <div class="prompt-tools-list">
                        ${prompt.tools.map(t => `<span class="prompt-tool-tag">${escapeHtml(t)}</span>`).join('')}
                    </div>
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

// ============== Identity View ==============

function renderIdentityView(agentId) {
    const agentData = agentDataCache[agentId];

    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Identity</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    const identity = agentData.persona || '';
    const hasIdentity = identity.length > 0;

    // Find the job for this agent (for editing state)
    const agentJob = jobsData.find(j => j.agent_id === agentId);
    const jobId = agentJob?.id || agentId;

    const isEditingIdentity = editingJobField?.jobId === jobId && editingJobField?.field === 'identity';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Identity</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${isEditingIdentity ? `
                <!-- Edit Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="saveAgentIdentityField('${agentId}', '${jobId}')">
                        ${icon('check')} Save
                    </button>
                    <button class="task-detail-action" onclick="cancelEditing()">
                        ${icon('x-mark')} Cancel
                    </button>
                </div>

                <div class="identity-edit">
                    <textarea class="job-description-input" id="edit-identity-${jobId}"
                        placeholder="Define the agent's identity and behavioral rules..."
                        style="min-height: 300px;">${escapeHtml(identity)}</textarea>
                </div>
            ` : `
                <!-- View Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="startEditingField('${jobId}', 'identity')">
                        ${icon('pencil')} Edit
                    </button>
                </div>

                <div class="identity-content ${hasIdentity ? '' : 'empty'}">
                    ${hasIdentity ? marked.parse(identity) : '<em class="text-muted">No identity defined. Click Edit to define the agent\'s identity and behavioral rules.</em>'}
                </div>
            `}
        </div>
    `;
}

// ============== Configuration View ==============

function renderConfigurationView(agentId) {
    const agentData = agentDataCache[agentId];

    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Configuration</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    const config = agentData.config || {};
    const triggers = config.triggers || [];
    const tools = config.tools || [];

    // Find the job for this agent (for editing state)
    const agentJob = jobsData.find(j => j.agent_id === agentId);
    const jobId = agentJob?.id || agentId;

    const isEditingConfig = editingJobField?.jobId === jobId && editingJobField?.field === 'config';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Configuration</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${isEditingConfig ? `
                <!-- Edit Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="saveAgentConfigField('${agentId}', '${jobId}')">
                        ${icon('check')} Save
                    </button>
                    <button class="task-detail-action" onclick="cancelEditing()">
                        ${icon('x-mark')} Cancel
                    </button>
                </div>

                <div class="agent-config-edit">
                    <label class="agent-config-label">
                        <span>Triggers (comma-separated)</span>
                        <input type="text" class="agent-config-input" id="edit-triggers-${jobId}"
                            value="${escapeHtml(triggers.join(', '))}"
                            placeholder="e.g., job:assigned, time:morning">
                    </label>
                    <label class="agent-config-label">
                        <span>Tools (comma-separated)</span>
                        <input type="text" class="agent-config-input" id="edit-tools-${jobId}"
                            value="${escapeHtml(tools.join(', '))}"
                            placeholder="e.g., list_jobs, create_job">
                    </label>
                    <div class="agent-config-group">
                        <div class="agent-config-group-title">Reflection</div>
                        <label class="agent-config-checkbox">
                            <input type="checkbox" id="edit-reflection-enabled-${jobId}"
                                ${config.reflection?.enabled !== false ? 'checked' : ''}>
                            <span>Enabled</span>
                        </label>
                        <label class="agent-config-label">
                            <span>Trigger</span>
                            <input type="text" class="agent-config-input" id="edit-reflection-trigger-${jobId}"
                                value="${escapeHtml(config.reflection?.trigger || 'time:evening')}"
                                placeholder="e.g., time:evening">
                        </label>
                    </div>
                    <div class="agent-config-group">
                        <div class="agent-config-group-title">Exploration</div>
                        <label class="agent-config-checkbox">
                            <input type="checkbox" id="edit-exploration-enabled-${jobId}"
                                ${config.exploration?.enabled ? 'checked' : ''}>
                            <span>Enabled</span>
                        </label>
                        <label class="agent-config-label">
                            <span>Trigger</span>
                            <input type="text" class="agent-config-input" id="edit-exploration-trigger-${jobId}"
                                value="${escapeHtml(config.exploration?.trigger || 'time:hour_04')}"
                                placeholder="e.g., time:hour_04">
                        </label>
                    </div>
                </div>
            ` : `
                <!-- View Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="startEditingField('${jobId}', 'config')">
                        ${icon('pencil')} Edit
                    </button>
                </div>

                <div class="job-section">
                    <div class="job-section-header">Triggers</div>
                    <div class="config-value">${triggers.length > 0 ? escapeHtml(triggers.join(', ')) : '<em class="text-muted">None configured</em>'}</div>
                </div>

                <div class="job-section">
                    <div class="job-section-header">Tools</div>
                    <div class="config-value">${tools.length > 0 ? escapeHtml(tools.join(', ')) : '<em class="text-muted">None configured</em>'}</div>
                </div>

                <div class="job-section">
                    <div class="job-section-header">Reflection</div>
                    <div class="config-value">
                        <span class="config-status ${config.reflection?.enabled !== false ? 'enabled' : 'disabled'}">
                            ${config.reflection?.enabled !== false ? 'Enabled' : 'Disabled'}
                        </span>
                        <span class="config-trigger">${escapeHtml(config.reflection?.trigger || 'time:evening')}</span>
                    </div>
                </div>

                <div class="job-section">
                    <div class="job-section-header">Exploration</div>
                    <div class="config-value">
                        <span class="config-status ${config.exploration?.enabled ? 'enabled' : 'disabled'}">
                            ${config.exploration?.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <span class="config-trigger">${escapeHtml(config.exploration?.trigger || 'time:hour_04')}</span>
                    </div>
                </div>
            `}
        </div>
    `;
}

// ============== Rate Limit Events View ==============

function renderRateLimitEventsView(agentId) {
    const cached = rateLimitViewCache[agentId];

    if (!cached) {
        loadRateLimitEvents(agentId).then(data => {
            rateLimitViewCache[agentId] = data || [];
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Rate Limit Events</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    // Filter to agent-specific events
    const agentEvents = cached.filter(e => e.agent_id === agentId);

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Rate Limit Events</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${agentEvents.length === 0 ? '<div class="focus-empty">No rate limit events for this agent.</div>' :
              agentEvents.slice(0, 50).map(e => {
                  const eventClass = e.event === 'agent_paused' ? 'event-paused' :
                                     e.event === 'agent_resumed' ? 'event-resumed' :
                                     e.event === 'rate_limit_hit' ? 'event-limited' : '';
                  return `
                    <div class="rate-limit-event ${eventClass}">
                        <span class="event-time">${formatPromptTime(e.timestamp)}</span>
                        <span class="event-type">${escapeHtml(e.event || 'unknown')}</span>
                        <span class="event-detail">${escapeHtml(e.reason || e.details?.reason || '')}</span>
                    </div>
                  `;
              }).join('')
            }
        </div>
    `;
}
