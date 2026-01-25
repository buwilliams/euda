// Euno - Focus View Topic Renderers
// Topic views, navigation menus, and timelines

// ============== Global Caches ==============

let traceDataCache = {};

// ============== Topic Trace View ==============

function renderTopicTraceView(topicId) {
    const traceData = traceDataCache[topicId];

    // Load data if not cached
    if (!traceData) {
        loadTopicTrace(topicId).then(data => {
            traceDataCache[topicId] = data || { topic_id: topicId, topic_name: 'Unknown', entries: [], summary: {} };
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Topic Trace</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading trace data...</div>
            </div>
        `;
    }

    const { topic_name, summary, entries } = traceData;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('chart-bar')} Trace: ${escapeHtml(topic_name || 'Topic')}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Summary Stats -->
            <div class="trace-summary">
                <div class="trace-stat">
                    <span class="stat-label">Actions</span>
                    <span class="stat-value">${summary.actions || 0}</span>
                </div>
                <div class="trace-stat">
                    <span class="stat-label">LLM Calls</span>
                    <span class="stat-value">${summary.llm_calls || 0}</span>
                </div>
                <div class="trace-stat">
                    <span class="stat-label">Total Cost</span>
                    <span class="stat-value">$${(summary.total_cost || 0).toFixed(4)}</span>
                </div>
            </div>

            <!-- Timeline -->
            <div class="trace-timeline">
                ${entries.length === 0 ? '<div class="focus-empty">No trace entries recorded.</div>' :
                  entries.map(entry => {
                      const eventType = entry.event || 'unknown';
                      const eventClass = eventType === 'action' ? 'trace-event-action' :
                                        eventType === 'llm_call' ? 'trace-event-llm' :
                                        eventType === 'error' ? 'trace-event-error' : '';

                      let details = '';
                      if (entry.details) {
                          if (eventType === 'action') {
                              details = escapeHtml(entry.details.action || '');
                          } else if (eventType === 'llm_call') {
                              const d = entry.details;
                              details = `${escapeHtml(d.model || 'unknown')} | ${d.input_tokens || 0}/${d.output_tokens || 0} tokens | $${(d.cost || 0).toFixed(4)}`;
                          }
                      }

                      return `
                          <div class="trace-entry ${eventClass}">
                              <span class="trace-time">${formatPromptTime(entry.timestamp)}</span>
                              <span class="trace-event-type">${escapeHtml(eventType)}</span>
                              <span class="trace-agent">${escapeHtml(entry.agent || '')}</span>
                              <span class="trace-details">${details}</span>
                          </div>
                      `;
                  }).join('')
                }
            </div>
        </div>
    `;
}

function navigateToTrace(topicId) {
    navigateFocusTo(`trace-${topicId}`);
}

function formatPromptTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// ============== Menu & Timeline Views ==============

function renderFocusMenu() {
    const counts = getFocusCounts();
    const todayTopics = getRootTopicsForCategory('today');

    // For completed count, only show Projects descendants (exclude Agents and System)
    const allTopics = [...topicsData, ...completedTopicsData];
    const projectsCompletedTopics = completedTopicsData.filter(j => isProjectsDescendant(j, allTopics));
    const completedTopicIds = new Set(projectsCompletedTopics.map(j => j.id));
    const topLevelCompletedTopics = projectsCompletedTopics.filter(j => !j.parent_id || !completedTopicIds.has(j.parent_id));

    // Find system containers
    const agentsContainer = topicsData.find(j => j.tags && j.tags.includes('system:agents') && !j.parent_id);
    const projectsContainer = topicsData.find(j => j.tags && j.tags.includes('system:projects') && !j.parent_id);

    // Count children of each container
    const agentsCount = agentsContainer ? topicsData.filter(j => j.parent_id === agentsContainer.id).length : 0;
    const projectsCount = projectsContainer ? topicsData.filter(j => j.parent_id === projectsContainer.id).length : 0;

    // Check collapsed states
    const timelinesOpen = isSectionOpen('timelines');
    const collectionsOpen = isSectionOpen('collections');

    // Build today section using same format as other menu sections
    let todaySection = '';
    if (todayTopics.length > 0) {
        todaySection = `
            <div class="focus-menu-section" data-testid="today-section">
                <div class="focus-menu-section-label">Today</div>
                <div class="focus-today-topics">
                    ${todayTopics.map(topic => renderTopicCard(topic, isSwipeable(topic))).join('')}
                </div>
            </div>
        `;
    } else {
        todaySection = `
            <div class="focus-menu-section" data-testid="today-section">
                <div class="focus-menu-section-label">Today</div>
                <div class="focus-free-message">
                    <span class="focus-free-text">Your day is free.</span>
                </div>
            </div>
        `;
    }

    // Build system section (Agents + Projects) if any exist
    const hasSystemSection = agentsContainer || projectsContainer;
    const systemSection = hasSystemSection ? `
        <div class="focus-menu-section">
            <div class="focus-menu-section-label collapsible ${collectionsOpen ? 'open' : ''}" onclick="toggleSection('collections')">
                <span>Collections</span>
                <span class="section-toggle">${icon('chevron-right')}</span>
            </div>
            <div class="focus-menu collapsible-content ${collectionsOpen ? 'open' : ''}">
                ${agentsContainer ? `
                <div class="focus-menu-item" onclick="navigateFocus('topic-${agentsContainer.id}')">
                    <span class="focus-menu-icon">${icon('bolt')}</span>
                    <span class="focus-menu-label">Agents</span>
                    <span class="focus-menu-count">${agentsCount}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
                ` : ''}
                ${projectsContainer ? `
                <div class="focus-menu-item" onclick="navigateFocus('topic-${projectsContainer.id}')">
                    <span class="focus-menu-icon">${icon('folder')}</span>
                    <span class="focus-menu-label">Projects</span>
                    <span class="focus-menu-count">${projectsCount}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
                ` : ''}
            </div>
        </div>
    ` : '';

    return `
        <div id="daily-quote-container"></div>
        ${todaySection}
        <div class="focus-menu-section">
            <div class="focus-menu-section-label collapsible ${timelinesOpen ? 'open' : ''}" data-testid="section-timelines" onclick="toggleSection('timelines')">
                <span>Timelines</span>
                <span class="section-toggle">${icon('chevron-right')}</span>
            </div>
            <div class="focus-menu collapsible-content ${timelinesOpen ? 'open' : ''}">
                <div class="focus-menu-item" data-testid="menu-upcoming" onclick="navigateFocus('upcoming')">
                    <span class="focus-menu-icon">${icon('calendar')}</span>
                    <span class="focus-menu-label">Upcoming</span>
                    <span class="focus-menu-count">${counts.upcoming}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
                <div class="focus-menu-item" data-testid="menu-anytime" onclick="navigateFocus('anytime')">
                    <span class="focus-menu-icon">${icon('clock')}</span>
                    <span class="focus-menu-label">Anytime</span>
                    <span class="focus-menu-count">${counts.anytime}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
                <div class="focus-menu-item" data-testid="menu-someday" onclick="navigateFocus('someday')">
                    <span class="focus-menu-icon">${icon('cloud')}</span>
                    <span class="focus-menu-label">Someday</span>
                    <span class="focus-menu-count">${counts.someday}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
                <div class="focus-menu-item" data-testid="menu-completed" onclick="navigateFocus('completed')">
                    <span class="focus-menu-icon">${icon('check')}</span>
                    <span class="focus-menu-label">Completed</span>
                    <span class="focus-menu-count">${topLevelCompletedTopics.length}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
            </div>
        </div>
        ${systemSection}
    `;
}

function getTimelineIcon(category) {
    const iconNames = { today: 'sun', upcoming: 'calendar', anytime: 'clock', someday: 'cloud' };
    return iconNames[category] ? icon(iconNames[category]) : '';
}

function renderTimelineView(category, title) {
    // Get only root topics that have descendants matching this category
    let topics = getRootTopicsForCategory(category);

    // Sort upcoming topics by due date ascending (nearest first)
    if (category === 'upcoming') {
        topics = topics.slice().sort((a, b) => {
            const dateA = a.due_date || '9999-12-31';
            const dateB = b.due_date || '9999-12-31';
            return dateA.localeCompare(dateB);
        });
    }

    const categoryIcon = getTimelineIcon(category);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${categoryIcon} ${title}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${topics.length === 0
                ? '<div class="focus-empty">No topics</div>'
                : topics.map(topic => renderTopicCard(topic, isSwipeable(topic))).join('')
            }
        </div>
    `;
}

function renderCompletedTopicsView() {
    // Combine active and completed topics for ancestor traversal
    const allTopics = [...topicsData, ...completedTopicsData];

    // Filter to only Projects descendants (exclude Agents and System topics)
    const projectsCompletedTopics = completedTopicsData.filter(j => isProjectsDescendant(j, allTopics));

    // Root completed topics: no parent OR parent is not in completed list
    const completedTopicIds = new Set(projectsCompletedTopics.map(j => j.id));
    const rootCompletedTopics = projectsCompletedTopics.filter(j => !j.parent_id || !completedTopicIds.has(j.parent_id));

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('check')} Completed</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${rootCompletedTopics.length === 0
                ? '<div class="focus-empty">No completed topics</div>'
                : rootCompletedTopics.map(topic => {
                    const childCount = projectsCompletedTopics.filter(j => j.parent_id === topic.id).length;
                    return renderCompletedTopicCard(topic, childCount, true);
                }).join('')
            }
        </div>
    `;
}

// ============== System Container Views ==============

function renderSystemContainerView(topic, isAgentsContainer) {
    const childTopics = topicsData.filter(j => j.parent_id === topic.id);

    // Determine container type and styling
    let titleIcon, containerName, emptyMessage;
    if (isAgentsContainer) {
        titleIcon = icon('bolt');
        containerName = 'Agents';
        emptyMessage = 'No agent inboxes yet.';
    } else {
        titleIcon = icon('folder');
        containerName = 'Projects';
        emptyMessage = 'No projects yet.';
    }

    // For Projects containers, render children as swipeable topic cards
    // For Agents container, render children as non-swipeable agent cards
    const renderChildTopics = () => {
        if (childTopics.length === 0) {
            return `<div class="focus-empty">${emptyMessage}</div>`;
        }

        if (isAgentsContainer) {
            // Agent inboxes - not swipeable, custom rendering
            return `
                <div class="child-topics-list">
                    ${childTopics.map(child => {
                        const grandchildCount = topicsData.filter(j => j.parent_id === child.id).length;
                        const childIcon = icon('bolt');
                        return `
                            <div class="child-topic-card" data-testid="agent-card" onclick="navigateFocus('topic-${child.id}')">
                                <span class="child-topic-icon">${childIcon}</span>
                                <span class="child-topic-name">${escapeHtml(child.name)}</span>
                                <span class="child-topic-count">${grandchildCount}</span>
                                <span class="child-topic-arrow">${icon('chevron-right')}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } else {
            // Projects - swipeable topic cards
            return `
                <div class="child-topics-list">
                    ${childTopics.map(child => renderTopicCard(child, true)).join('')}
                </div>
            `;
        }
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${titleIcon}${containerName}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content" data-testid="agents-container">
            <!-- Child Topics -->
            <div class="topic-section">
                ${renderChildTopics()}
            </div>
        </div>
    `;
}

// ============== Topic Detail View ==============

function renderTopicDetailView(topicId) {
    // Use allTopicsData to find topics regardless of status
    const topic = allTopicsData.find(j => j.id === topicId);
    if (!topic) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Topic Not Found</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-empty">This topic no longer exists.</div>
        `;
    }

    // Check if this is a system container
    const isAgentsContainer = topic.tags && topic.tags.includes('system:agents');
    const isProjectsContainer = topic.tags && topic.tags.includes('system:projects');
    const isSystemContainer = isAgentsContainer || isProjectsContainer;

    // For system containers, render a simplified view
    if (isSystemContainer) {
        return renderSystemContainerView(topic, isAgentsContainer);
    }

    // For agent inbox topics, render the agent detail view
    if (topic.agent_id) {
        return renderAgentDetailView(topic);
    }

    const whenLabel = getWhenLabel(topic);
    const isArchiving = archivingTopicId === topic.id;
    const displayName = topic.name || 'Untitled';
    const hasDescription = topic.description && topic.description.length > 0;
    // Get ALL child topics sorted by status priority (working > todo > error > done > archived)
    const allChildTopics = getAllChildTopicsSorted(topic.id);
    const assets = topicAssetsCache[topicId] || [];
    const isAgentTopic = !!topic.agent_id;
    const titleIcon = isAgentTopic ? icon('bolt') : '';

    // Check if we're editing this topic
    const isEditingName = editingTopicField?.topicId === topicId && editingTopicField?.field === 'name';
    const isEditingDesc = editingTopicField?.topicId === topicId && editingTopicField?.field === 'description';

    // Get parent topic name for context
    let parentName = null;
    if (topic.parent_id) {
        const parent = allTopicsData.find(j => j.id === topic.parent_id);
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!topicAssetsCache[topicId]) {
        loadTopicAssets(topicId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title${isAgentTopic ? ' agent-topic-title' : ''}">${titleIcon}${escapeHtml(displayName)}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content" data-testid="topic-detail">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('topic', '${topic.id}')">${icon('calendar')} ${escapeHtml(whenLabel)}</button>
                <button class="task-detail-action" onclick="openStatePicker('${topic.id}')">${getTopicStatusIcon(topic)} ${getTopicStatusLabel(topic)}</button>
                <button class="task-detail-action" onclick="openAssigneesPicker('${topic.id}')">${getAssigneesLabel(topic)}</button>
                <button class="task-detail-action" onclick="openAddPicker('${topic.id}')">+ Add</button>
                ${isAgentTopic ? '' : `<button class="task-detail-action" onclick="openMorePicker('${topic.id}')">Actions</button>`}
            </div>

            <!-- Name Section -->
            <div class="topic-section" data-testid="topic-name">
                <div class="topic-section-header">Name</div>
                ${isEditingName ? `
                    <input type="text" class="topic-name-input" id="edit-name-${topic.id}" value="${escapeHtml(displayName)}"
                        onkeydown="handleEditKeypress(event, '${topic.id}', 'name')"
                        onblur="saveTopicField('${topic.id}', 'name', this.value)">
                ` : `
                    <div class="topic-name-display" onclick="startEditingField('${topic.id}', 'name')">${escapeHtml(displayName)}</div>
                `}
            </div>

            <!-- Description Section -->
            <div class="topic-section" data-testid="topic-description">
                <div class="topic-section-header">
                    Description
                    ${isEditingDesc ? `<span class="topic-section-action" onclick="saveTopicField('${topic.id}', 'description', document.getElementById('edit-description-${topic.id}').value)">Save</span>` : ''}
                </div>
                ${isEditingDesc ? `
                    <textarea class="topic-description-input" id="edit-description-${topic.id}"
                        onkeydown="handleDescriptionKeypress(event, '${topic.id}')"
                        placeholder="Add a description...">${escapeHtml(topic.description || '')}</textarea>
                ` : `
                    <div class="topic-description-display ${hasDescription ? '' : 'empty'}" onclick="startEditingField('${topic.id}', 'description')">
                        ${hasDescription ? marked.parse(topic.description) : 'Click to add description...'}
                    </div>
                `}
            </div>

            <!-- Child Topics Section - shows all topics sorted by status -->
            ${allChildTopics.length > 0 ? `
            <div class="topic-section">
                <div class="topic-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Topics (${allChildTopics.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content open">
                    ${allChildTopics.map(child => renderTopicCard(child, true)).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Parent Link -->
            ${parentName ? `
            <div class="topic-section">
                <div class="topic-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('topic-${topic.parent_id}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

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

            <!-- API Calls Section -->
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="toggleAgentSection(this, event, 'topic-api-calls', '${topic.id}')">
                    <span>API Calls</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content" data-loaded="false">
                    <div class="section-loading">Loading...</div>
                </div>
            </div>
        </div>
    `;
}

// ============== Completed Topic Detail View ==============

function renderCompletedTopicDetailView(topicId) {
    const topic = completedTopicsData.find(j => j.id === topicId);
    if (!topic) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Topic Not Found</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-empty">This topic no longer exists.</div>
        `;
    }

    const displayName = topic.name || 'Untitled';
    const hasDescription = topic.description && topic.description.length > 0;
    const completedDate = topic.completed_at ? formatFriendlyPastDate(topic.completed_at) : 'Unknown';
    const completedChildTopics = completedTopicsData.filter(j => j.parent_id === topic.id);
    const activeChildTopics = topicsData.filter(j => j.parent_id === topic.id);
    const assets = topicAssetsCache[topicId] || [];

    // Check if we're editing this topic
    const isEditingName = editingTopicField?.topicId === topicId && editingTopicField?.field === 'name';
    const isEditingDesc = editingTopicField?.topicId === topicId && editingTopicField?.field === 'description';

    // Get parent topic name for context (could be active or completed)
    let parentName = null;
    let parentIsCompleted = false;
    if (topic.parent_id) {
        let parent = topicsData.find(j => j.id === topic.parent_id);
        if (!parent) {
            parent = completedTopicsData.find(j => j.id === topic.parent_id);
            parentIsCompleted = true;
        }
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!topicAssetsCache[topicId]) {
        loadTopicAssets(topicId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${escapeHtml(displayName)}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="restoreTopic(event, '${topic.id}')">${icon('arrow-uturn-left')} Restore</button>
                <button class="task-detail-action danger" onclick="deleteTopic(event, '${topic.id}')">${icon('trash')} Delete</button>
            </div>

            <!-- Completed Badge -->
            <div class="topic-section" style="background: #f0f8f0; border-radius: 6px; padding: 0.5rem 1rem;">
                <span style="color: #4a8; font-weight: 500;">${icon('check')} Completed ${escapeHtml(completedDate)}</span>
            </div>

            <!-- Name Section -->
            <div class="topic-section">
                <div class="topic-section-header">Name</div>
                ${isEditingName ? `
                    <input type="text" class="topic-name-input" id="edit-name-${topic.id}" value="${escapeHtml(displayName)}"
                        onkeydown="handleEditKeypress(event, '${topic.id}', 'name')"
                        onblur="saveCompletedTopicField('${topic.id}', 'name', this.value)">
                ` : `
                    <div class="topic-name-display" onclick="startEditingField('${topic.id}', 'name')">${escapeHtml(displayName)}</div>
                `}
            </div>

            <!-- Description Section -->
            <div class="topic-section">
                <div class="topic-section-header">
                    Description
                    ${isEditingDesc ? `<span class="topic-section-action" onclick="saveCompletedTopicField('${topic.id}', 'description', document.getElementById('edit-description-${topic.id}').value)">Save</span>` : ''}
                </div>
                ${isEditingDesc ? `
                    <textarea class="topic-description-input" id="edit-description-${topic.id}"
                        onkeydown="handleCompletedDescriptionKeypress(event, '${topic.id}')"
                        placeholder="Add a description...">${escapeHtml(topic.description || '')}</textarea>
                ` : `
                    <div class="topic-description-display ${hasDescription ? '' : 'empty'}" onclick="startEditingField('${topic.id}', 'description')">
                        ${hasDescription ? marked.parse(topic.description) : 'Click to add description...'}
                    </div>
                `}
            </div>

            <!-- Active Child Topics Section (rare but possible) - open by default -->
            ${activeChildTopics.length > 0 ? `
            <div class="topic-section">
                <div class="topic-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Active Children (${activeChildTopics.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content open">
                    ${activeChildTopics.map(child => renderTopicCard(child, true)).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Completed Child Topics Section - collapsed by default -->
            ${completedChildTopics.length > 0 ? `
            <div class="topic-section">
                <div class="topic-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Completed Children (${completedChildTopics.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    ${completedChildTopics.map(child => {
                        const grandchildCount = completedTopicsData.filter(j => j.parent_id === child.id).length;
                        return renderCompletedTopicCard(child, grandchildCount, true);
                    }).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Parent Link -->
            ${parentName ? `
            <div class="topic-section">
                <div class="topic-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('${parentIsCompleted ? 'completed' : 'topic'}-${topic.parent_id}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

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
