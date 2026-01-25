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

function renderAgentDetailView(topic) {
    const agentId = topic.agent_id;
    const displayName = topic.name || 'Untitled';
    // Get ALL child topics sorted by status priority (working > todo > error > done > archived)
    const allChildTopics = getAllChildTopicsSorted(topic.id);
    const assets = topicAssetsCache[topic.id] || [];

    // Load agent data if not cached
    const agentData = agentDataCache[agentId];
    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
    if (!topicAssetsCache[topic.id]) {
        loadTopicAssets(topic.id).then(() => renderFocusTab());
    }

    // Load pause status if not cached or missing token usage data
    if (!(agentId in agentPauseStatus) || !agentPauseStatus[agentId]?.tokenUsage) {
        loadAgentPauseStatus(agentId).then(() => renderFocusTab());
    }

    const config = agentData.config || {};
    const triggers = config.triggers || [];
    const pauseStatus = agentPauseStatus[agentId] || { state: 'enabled', isPaused: false, isDisabled: false, isEnabled: true };
    const agentState = pauseStatus.state || 'enabled';

    // Get trigger topic names to check for active tasks
    const triggerTopicNames = triggers.map(t => t.topic_name || t);

    // Find which triggers have active tasks (todo or working)
    const activeTriggerTopics = allChildTopics
        .filter(j => triggerTopicNames.includes(j.name) && (j.status === 'todo' || j.status === 'working'))
        .map(j => j.name);

    // Render trigger button with picker
    const renderTriggerButton = () => {
        if (triggers.length === 0) return '';
        const disabled = pauseStatus.isPaused || pauseStatus.isDisabled ? 'disabled' : '';
        // Store trigger data in a global cache for the picker to access
        window._triggerPickerData = window._triggerPickerData || {};
        window._triggerPickerData[agentId] = { triggers, disabledTriggers: activeTriggerTopics };
        return `<button class="task-detail-action" onclick="openTriggerPickerFromCache('${agentId}')" ${disabled}>${icon('play')} Trigger</button>`;
    };

    // Status badge color class
    const statusBadgeClass = agentState === 'enabled' ? 'status-enabled' :
                             agentState === 'paused' ? 'status-paused' :
                             agentState === 'disabled' ? 'status-disabled' : '';

    // Render controls button that opens a picker
    const renderControlsButton = () => {
        // Store control state in cache for the picker
        window._agentControlsData = window._agentControlsData || {};
        window._agentControlsData[agentId] = { state: agentState };
        return `<button class="task-detail-action" onclick="openAgentControlsPicker('${agentId}')">${icon('cog-6-tooth')} Controls</button>`;
    };

    // Token budget info
    const tokenUsage = pauseStatus.tokenUsage;
    const budgetReset = pauseStatus.budgetReset;

    // Render token budget section (collapsible, collapsed by default)
    const renderTokenBudgetSection = () => {
        if (!tokenUsage) return '';

        const inputPercent = tokenUsage.input_percent || 0;
        const outputPercent = tokenUsage.output_percent || 0;
        const frequency = tokenUsage.frequency || 'daily';
        const resetTime = budgetReset?.time_until || '';
        const periodStart = tokenUsage.period_start;
        const hourlyData = tokenUsage.hourly || {};

        // Extract projected percentage from pause reason if threshold exceeded
        let projectedInputPercent = null;
        let projectedOutputPercent = null;
        if (pauseStatus.isPaused && pauseStatus.reason) {
            const inputMatch = pauseStatus.reason.match(/input token threshold exceeded \((\d+)%\)/);
            const outputMatch = pauseStatus.reason.match(/output token threshold exceeded \((\d+)%\)/);
            if (inputMatch) projectedInputPercent = parseInt(inputMatch[1]);
            if (outputMatch) projectedOutputPercent = parseInt(outputMatch[1]);
        }

        // Determine bar color based on percentage
        const getBarColor = (percent) => {
            if (percent >= 100) return 'var(--color-danger)';
            if (percent >= 80) return 'var(--color-warning)';
            return 'var(--color-success)';
        };

        // Format period start time
        const formatPeriodStart = (isoString) => {
            if (!isoString) return null;
            const date = new Date(isoString);
            const now = new Date();
            const isToday = date.toDateString() === now.toDateString();
            const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            if (isToday) {
                return `today at ${time}`;
            }
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ` at ${time}`;
        };

        // Render usage breakdown based on frequency
        const renderUsageBreakdown = () => {
            const buckets = Object.keys(hourlyData);
            if (buckets.length === 0) return '';

            // For hourly frequency, no breakdown needed
            if (frequency === 'hourly') return '';

            const getOrdinalSuffix = (n) => {
                const s = ['th', 'st', 'nd', 'rd'];
                const v = n % 100;
                return s[(v - 20) % 10] || s[v] || s[0];
            };

            // For daily frequency: show by hour
            // For weekly/monthly: aggregate by day and show by day
            if (frequency === 'daily') {
                // Show hourly breakdown
                const hours = buckets.sort();
                const rows = hours.map(hour => {
                    const data = hourlyData[hour];
                    return `<div class="hourly-row">
                        <span class="hourly-label">${hour}:00</span>
                        <span class="hourly-value">${formatTokenCount(data.input)} in / ${formatTokenCount(data.output)} out</span>
                    </div>`;
                }).join('');

                return `
                    <div class="hourly-breakdown">
                        <div class="hourly-header">Usage by hour</div>
                        ${rows}
                    </div>
                `;
            } else {
                // Weekly or monthly: aggregate by day
                // Bucket keys are like "23T14" (day 23, hour 14)
                const dailyTotals = {};
                buckets.forEach(key => {
                    const data = hourlyData[key];
                    let dayKey;
                    if (key.includes('T')) {
                        dayKey = key.split('T')[0]; // Extract day part
                    } else {
                        // Fallback for unexpected format
                        dayKey = key;
                    }
                    if (!dailyTotals[dayKey]) {
                        dailyTotals[dayKey] = { input: 0, output: 0 };
                    }
                    dailyTotals[dayKey].input += data.input || 0;
                    dailyTotals[dayKey].output += data.output || 0;
                });

                const days = Object.keys(dailyTotals).sort();
                const rows = days.map(day => {
                    const data = dailyTotals[day];
                    const dayNum = parseInt(day);
                    const label = `${dayNum}${getOrdinalSuffix(dayNum)}`;
                    return `<div class="hourly-row">
                        <span class="hourly-label">${label}</span>
                        <span class="hourly-value">${formatTokenCount(data.input)} in / ${formatTokenCount(data.output)} out</span>
                    </div>`;
                }).join('');

                return `
                    <div class="hourly-breakdown">
                        <div class="hourly-header">Usage by day</div>
                        ${rows}
                    </div>
                `;
            }
        };

        const periodStartFormatted = formatPeriodStart(periodStart);
        const consumesTokens = tokenUsage.consumes_tokens !== false;

        // Show different content for agents that don't consume tokens
        const renderBudgetContent = () => {
            if (!consumesTokens) {
                return `
                    <div class="token-budget-no-consume">
                        This agent doesn't consume API tokens.
                    </div>
                `;
            }

            return `
                ${periodStartFormatted ? `
                    <div class="token-budget-period-start">
                        Active since ${periodStartFormatted}
                    </div>
                ` : ''}
                <div class="token-budget-row">
                    <span class="token-budget-label">Input</span>
                    <div class="token-budget-bar-container">
                        <div class="token-budget-bar" style="width: ${Math.min(inputPercent, 100)}%; background: ${getBarColor(projectedInputPercent || inputPercent)};"></div>
                        ${projectedInputPercent ? `<div class="token-budget-projected-marker" style="left: ${Math.min(projectedInputPercent, 100)}%;"></div>` : ''}
                    </div>
                    <span class="token-budget-value">${inputPercent.toFixed(1)}%${projectedInputPercent ? ` <span class="projected-percent">(${projectedInputPercent}% projected)</span>` : ''}</span>
                </div>
                <div class="token-budget-detail">
                    ${formatTokenCount(tokenUsage.input_tokens || 0)} / ${formatTokenCount(tokenUsage.input_budget || 0)} tokens
                </div>
                <div class="token-budget-row">
                    <span class="token-budget-label">Output</span>
                    <div class="token-budget-bar-container">
                        <div class="token-budget-bar" style="width: ${Math.min(outputPercent, 100)}%; background: ${getBarColor(projectedOutputPercent || outputPercent)};"></div>
                        ${projectedOutputPercent ? `<div class="token-budget-projected-marker" style="left: ${Math.min(projectedOutputPercent, 100)}%;"></div>` : ''}
                    </div>
                    <span class="token-budget-value">${outputPercent.toFixed(1)}%${projectedOutputPercent ? ` <span class="projected-percent">(${projectedOutputPercent}% projected)</span>` : ''}</span>
                </div>
                <div class="token-budget-detail">
                    ${formatTokenCount(tokenUsage.output_tokens || 0)} / ${formatTokenCount(tokenUsage.output_budget || 0)} tokens
                </div>
                ${resetTime ? `
                    <div class="token-budget-reset">
                        Resets in ${resetTime}
                    </div>
                ` : ''}
                ${renderUsageBreakdown()}
            `;
        };

        return `
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Token Budget${consumesTokens ? ` (${frequency})` : ''}</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    <div class="token-budget-content">
                        ${renderBudgetContent()}
                    </div>
                </div>
            </div>
        `;
    };

    // Render pause reason notice if paused
    const renderPauseNotice = () => {
        if (!pauseStatus.isPaused) return '';
        // Show simple message - the detailed reason may contain stale percentage data
        const timeAgo = pauseStatus.timestamp ? formatPauseTimestamp(pauseStatus.timestamp) : '';
        return `
            <div class="pause-notice">
                ${icon('exclamation-triangle')} Agent paused due to token budget${timeAgo ? ` (${timeAgo})` : ''}
            </div>
        `;
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('bolt')}${escapeHtml(displayName)}</span>
                ${renderBreadcrumbs()}
            </div>
            <span class="agent-status-badge ${statusBadgeClass}">${agentState}</span>
        </div>
        <div class="focus-view-content" data-testid="agent-detail">
            <!-- Pause Notice (if paused) -->
            ${renderPauseNotice()}

            <!-- Action Menu - all controls in one row -->
            <div class="task-detail-actions">
                ${renderControlsButton()}
                ${renderTriggerButton()}
                <button class="task-detail-action" onclick="openAddPicker('${topic.id}')">+ Add</button>
            </div>

            <!-- Topics Section (all topics sorted by status: working > todo > error > done > archived) -->
            <div class="topic-section">
                <div class="topic-section-header collapsible ${allChildTopics.length > 0 ? 'open' : ''}" onclick="togglePersonaSection(this, event)">
                    <span>Topics${allChildTopics.length > 0 ? ` (${allChildTopics.length})` : ''}</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content ${allChildTopics.length > 0 ? 'open' : ''}">
                    ${allChildTopics.length === 0 ? '<div class="focus-empty">No topics assigned to this agent.</div>' :
                      allChildTopics.map(child => renderTopicCard(child, true)).join('')
                    }
                </div>
            </div>

            <!-- Token Budget Section (collapsible, collapsed by default) -->
            ${renderTokenBudgetSection()}

            <!-- Identity Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible clickable" onclick="navigateFocus('identity-${agentId}')">
                    <span>Identity</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Configuration Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible clickable" onclick="navigateFocus('config-${agentId}')">
                    <span>Configuration</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Short-term Memory Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible clickable" onclick="navigateFocus('memory-list-${agentId}')">
                    <span>Short-term Memory</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Long-term Memory Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible clickable" onclick="navigateFocus('long-term-memory-${agentId}')">
                    <span>Long-term Memory</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Monitoring Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible clickable" onclick="navigateFocus('monitoring-${agentId}')">
                    <span>Monitoring</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Incidents Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible clickable" onclick="navigateFocus('rate-limits-${agentId}')">
                    <span>Incidents</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
            </div>

            <!-- Assets Section -->
            ${assets.length > 0 ? `
            <div class="topic-section">
                <div class="topic-section-header">Assets (${assets.length})</div>
                <div class="asset-list">
                    ${assets.map(asset => {
                        const isText = isTextAsset(asset);
                        const assetIcon = asset.filename.endsWith('.md') ? icon('pencil') : icon('document');
                        return isText ? `
                            <div class="asset-item clickable" onclick="navigateFocus('asset-${topic.id}-${asset.filename}')" style="cursor: pointer;">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="event.stopPropagation(); deleteAsset('${topic.id}', '${escapeHtml(asset.filename)}')" title="Delete">${icon('trash')}</button>
                                <span class="asset-item-arrow">${icon('chevron-right')}</span>
                            </div>
                        ` : `
                            <div class="asset-item">
                                <span class="asset-item-name">${assetIcon} ${escapeHtml(asset.filename)}</span>
                                <span class="asset-item-size">${formatFileSize(asset.size)}</span>
                                <button class="asset-item-delete" onclick="deleteAsset('${topic.id}', '${escapeHtml(asset.filename)}')" title="Delete">${icon('trash')}</button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

// ============== Agent Pause Helpers ==============

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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <div data-testid="memory-list">
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <div class="topic-section">
                <div class="topic-section-header">Type</div>
                <div class="memory-type-badge ${typeColors[item.type] || 'type-thing'}" style="display: inline-block; margin: 0.5rem 0;">
                    ${escapeHtml(item.type)}
                </div>
            </div>

            <!-- Content -->
            <div class="topic-section">
                <div class="topic-section-header">Content</div>
                <div class="memory-item-full-content">${escapeHtml(item.short_description)}</div>
            </div>

            <!-- Details -->
            ${item.details ? `
            <div class="topic-section">
                <div class="topic-section-header">Details</div>
                <div class="memory-item-details">${escapeHtml(item.details)}</div>
            </div>
            ` : ''}

            <!-- Created -->
            <div class="topic-section">
                <div class="topic-section-header">Created</div>
                <div class="memory-item-date">${item.created_at ? formatFriendlyPastDate(item.created_at) : 'Unknown'}</div>
            </div>

            <!-- Expires -->
            ${item.expires_at ? `
            <div class="topic-section">
                <div class="topic-section-header">Expires</div>
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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

    // Calculate pagination display info
    const currentPage = Math.floor(paginationInfo.offset / paginationInfo.limit) + 1;
    const totalPages = Math.ceil(paginationInfo.total / paginationInfo.limit);
    const hasPrev = paginationInfo.offset > 0;
    const hasNext = paginationInfo.has_more;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Monitoring</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
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
            <div class="topic-section">
                <div class="topic-section-header">Recent Prompts${paginationInfo.total > 0 ? ` (${paginationInfo.total} total)` : ''}</div>
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Prompt</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Summary -->
            <div class="topic-section">
                <div class="topic-section-header">Summary</div>
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
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="togglePersonaSection(this, event)">
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
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Messages</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    <div class="prompt-messages-list">${renderMessages(prompt.messages)}</div>
                </div>
            </div>
            ` : ''}

            <!-- Response (if available) -->
            ${prompt.response ? `
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Response</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    <div class="prompt-rendered-content">${renderResponse(prompt.response)}</div>
                </div>
            </div>
            ` : ''}

            <!-- Tools (if available) -->
            ${prompt.tools && prompt.tools.length > 0 ? `
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="togglePersonaSection(this, event)">
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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

    const identity = agentData.identity || '';
    const hasIdentity = identity.length > 0;

    // Find the topic for this agent (for editing state)
    const agentTopic = topicsData.find(j => j.agent_id === agentId);
    const topicId = agentTopic?.id || agentId;

    const isEditingIdentity = editingTopicField?.topicId === topicId && editingTopicField?.field === 'identity';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Identity</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${isEditingIdentity ? `
                <!-- Edit Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="saveAgentIdentityField('${agentId}', '${topicId}')">
                        ${icon('check')} Save
                    </button>
                    <button class="task-detail-action" onclick="cancelEditing()">
                        ${icon('x-mark')} Cancel
                    </button>
                </div>

                <div class="identity-edit">
                    <textarea class="topic-description-input" id="edit-identity-${topicId}"
                        placeholder="Define the agent's identity and behavioral rules..."
                        style="min-height: 300px;">${escapeHtml(identity)}</textarea>
                </div>
            ` : `
                <!-- View Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="startEditingField('${topicId}', 'identity')">
                        ${icon('pencil')} Edit
                    </button>
                </div>

                <div class="identity-content ${hasIdentity ? '' : 'empty'}" data-testid="identity-content">
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
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
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

    // Find the topic for this agent (for editing state)
    const agentTopic = topicsData.find(j => j.agent_id === agentId);
    const topicId = agentTopic?.id || agentId;

    const isEditingConfig = editingTopicField?.topicId === topicId && editingTopicField?.field === 'config';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Configuration</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${isEditingConfig ? `
                <!-- Edit Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="saveAgentConfigField('${agentId}', '${topicId}')">
                        ${icon('check')} Save
                    </button>
                    <button class="task-detail-action" onclick="cancelEditing()">
                        ${icon('x-mark')} Cancel
                    </button>
                </div>

                <div class="agent-config-edit">
                    <label class="agent-config-label">
                        <span>Triggers (comma-separated)</span>
                        <input type="text" class="agent-config-input" id="edit-triggers-${topicId}"
                            value="${escapeHtml(triggers.join(', '))}"
                            placeholder="Object triggers (edit config.json directly)">
                    </label>
                    <label class="agent-config-label">
                        <span>Tools (comma-separated)</span>
                        <input type="text" class="agent-config-input" id="edit-tools-${topicId}"
                            value="${escapeHtml(tools.join(', '))}"
                            placeholder="e.g., list_topics, create_topic">
                    </label>
                    <div class="agent-config-group">
                        <div class="agent-config-group-title">Consolidation</div>
                        <label class="agent-config-checkbox">
                            <input type="checkbox" id="edit-consolidation-enabled-${topicId}"
                                ${config.consolidation?.enabled !== false ? 'checked' : ''}>
                            <span>Enabled</span>
                        </label>
                        <label class="agent-config-label">
                            <span>Trigger</span>
                            <input type="text" class="agent-config-input" id="edit-consolidation-trigger-${topicId}"
                                value="${escapeHtml(config.consolidation?.trigger || 'time:evening')}"
                                placeholder="e.g., time:evening">
                        </label>
                    </div>
                </div>
            ` : `
                <!-- View Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="startEditingField('${topicId}', 'config')">
                        ${icon('pencil')} Edit
                    </button>
                </div>

                <div class="topic-section">
                    <div class="topic-section-header">Triggers</div>
                    <div class="config-value">${triggers.length > 0 ? escapeHtml(triggers.join(', ')) : '<em class="text-muted">None configured</em>'}</div>
                </div>

                <div class="topic-section">
                    <div class="topic-section-header">Tools</div>
                    <div class="config-value">${tools.length > 0 ? escapeHtml(tools.join(', ')) : '<em class="text-muted">None configured</em>'}</div>
                </div>

                <div class="topic-section">
                    <div class="topic-section-header">Consolidation</div>
                    <div class="config-value">
                        <span class="config-status ${config.consolidation?.enabled !== false ? 'enabled' : 'disabled'}">
                            ${config.consolidation?.enabled !== false ? 'Enabled' : 'Disabled'}
                        </span>
                        <span class="config-trigger">${escapeHtml(config.consolidation?.trigger || 'time:evening')}</span>
                    </div>
                </div>
            `}
        </div>
    `;
}

// ============== Incidents View ==============

function renderRateLimitEventsView(agentId) {
    const cached = rateLimitViewCache[agentId];

    if (!cached) {
        loadRateLimitEvents(agentId).then(data => {
            rateLimitViewCache[agentId] = data || [];
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Incidents</span>
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
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Incidents</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${agentEvents.length === 0 ? '<div class="focus-empty">No incidents for this agent.</div>' :
              agentEvents.slice(0, 50).map(e => {
                  const eventClass = e.severity === 'critical' ? 'event-paused' :
                                     e.severity === 'warning' ? 'event-limited' : '';
                  return `
                    <div class="rate-limit-event ${eventClass}">
                        <span class="event-time">${formatPromptTime(e.timestamp)}</span>
                        <span class="event-type">${escapeHtml(e.incident_type || '')}</span>
                        <span class="event-detail">${escapeHtml(e.reason || '')}</span>
                    </div>
                  `;
              }).join('')
            }
        </div>
    `;
}
