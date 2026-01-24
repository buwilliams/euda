// Euno - Focus View Job Renderers
// Job views, navigation menus, and timelines

// ============== Global Caches ==============

let traceDataCache = {};

// ============== Job Trace View ==============

function renderJobTraceView(jobId) {
    const traceData = traceDataCache[jobId];

    // Load data if not cached
    if (!traceData) {
        loadJobTrace(jobId).then(data => {
            traceDataCache[jobId] = data || { job_id: jobId, job_name: 'Unknown', entries: [], summary: {} };
            renderFocusTab();
        });
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Job Trace</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading trace data...</div>
            </div>
        `;
    }

    const { job_name, summary, entries } = traceData;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('chart-bar')} Trace: ${escapeHtml(job_name || 'Job')}</span>
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

function navigateToTrace(jobId) {
    navigateFocusTo(`trace-${jobId}`);
}

function formatPromptTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// ============== Menu & Timeline Views ==============

function renderFocusMenu() {
    const counts = getFocusCounts();
    const todayJobs = getRootJobsForCategory('today');

    // For completed count, only show Projects descendants (exclude Agents and System)
    const allJobs = [...jobsData, ...completedJobsData];
    const projectsCompletedJobs = completedJobsData.filter(j => isProjectsDescendant(j, allJobs));
    const completedJobIds = new Set(projectsCompletedJobs.map(j => j.id));
    const topLevelCompletedJobs = projectsCompletedJobs.filter(j => !j.parent_id || !completedJobIds.has(j.parent_id));

    // Find system containers
    const agentsContainer = jobsData.find(j => j.tags && j.tags.includes('system:agents') && !j.parent_id);
    const projectsContainer = jobsData.find(j => j.tags && j.tags.includes('system:projects') && !j.parent_id);

    // Count children of each container
    const agentsCount = agentsContainer ? jobsData.filter(j => j.parent_id === agentsContainer.id).length : 0;
    const projectsCount = projectsContainer ? jobsData.filter(j => j.parent_id === projectsContainer.id).length : 0;

    // Check collapsed states
    const timelinesOpen = isSectionOpen('timelines');
    const collectionsOpen = isSectionOpen('collections');

    // Build today section using same format as other menu sections
    let todaySection = '';
    if (todayJobs.length > 0) {
        todaySection = `
            <div class="focus-menu-section" data-testid="today-section">
                <div class="focus-menu-section-label">Today</div>
                <div class="focus-today-jobs">
                    ${todayJobs.map(job => renderJobCard(job, isSwipeable(job))).join('')}
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
                <div class="focus-menu-item" onclick="navigateFocus('job-${agentsContainer.id}')">
                    <span class="focus-menu-icon">${icon('bolt')}</span>
                    <span class="focus-menu-label">Agents</span>
                    <span class="focus-menu-count">${agentsCount}</span>
                    <span class="focus-menu-arrow">›</span>
                </div>
                ` : ''}
                ${projectsContainer ? `
                <div class="focus-menu-item" onclick="navigateFocus('job-${projectsContainer.id}')">
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
                    <span class="focus-menu-count">${topLevelCompletedJobs.length}</span>
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
    // Get only root jobs that have descendants matching this category
    let jobs = getRootJobsForCategory(category);

    // Sort upcoming jobs by due date ascending (nearest first)
    if (category === 'upcoming') {
        jobs = jobs.slice().sort((a, b) => {
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
            ${jobs.length === 0
                ? '<div class="focus-empty">No jobs</div>'
                : jobs.map(job => renderJobCard(job, isSwipeable(job))).join('')
            }
        </div>
    `;
}

function renderCompletedJobsView() {
    // Combine active and completed jobs for ancestor traversal
    const allJobs = [...jobsData, ...completedJobsData];

    // Filter to only Projects descendants (exclude Agents and System jobs)
    const projectsCompletedJobs = completedJobsData.filter(j => isProjectsDescendant(j, allJobs));

    // Root completed jobs: no parent OR parent is not in completed list
    const completedJobIds = new Set(projectsCompletedJobs.map(j => j.id));
    const rootCompletedJobs = projectsCompletedJobs.filter(j => !j.parent_id || !completedJobIds.has(j.parent_id));

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${icon('check')} Completed</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${rootCompletedJobs.length === 0
                ? '<div class="focus-empty">No completed jobs</div>'
                : rootCompletedJobs.map(job => {
                    const childCount = projectsCompletedJobs.filter(j => j.parent_id === job.id).length;
                    return renderCompletedJobCard(job, childCount, true);
                }).join('')
            }
        </div>
    `;
}

// ============== System Container Views ==============

function renderSystemContainerView(job, isAgentsContainer) {
    const childJobs = jobsData.filter(j => j.parent_id === job.id);

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

    // For Projects containers, render children as swipeable job cards
    // For Agents container, render children as non-swipeable agent cards
    const renderChildJobs = () => {
        if (childJobs.length === 0) {
            return `<div class="focus-empty">${emptyMessage}</div>`;
        }

        if (isAgentsContainer) {
            // Agent inboxes - not swipeable, custom rendering
            return `
                <div class="child-jobs-list">
                    ${childJobs.map(child => {
                        const grandchildCount = jobsData.filter(j => j.parent_id === child.id).length;
                        const childIcon = icon('bolt');
                        return `
                            <div class="child-job-card" data-testid="agent-card" onclick="navigateFocus('job-${child.id}')">
                                <span class="child-job-icon">${childIcon}</span>
                                <span class="child-job-name">${escapeHtml(child.name)}</span>
                                <span class="child-job-count">${grandchildCount}</span>
                                <span class="child-job-arrow">${icon('chevron-right')}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } else {
            // Projects - swipeable job cards
            return `
                <div class="child-jobs-list">
                    ${childJobs.map(child => renderJobCard(child, true)).join('')}
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
            <!-- Child Jobs -->
            <div class="job-section">
                ${renderChildJobs()}
            </div>
        </div>
    `;
}

// ============== Job Detail View ==============

function renderJobDetailView(jobId) {
    // Use allJobsData to find jobs regardless of status
    const job = allJobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Job Not Found</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-empty">This job no longer exists.</div>
        `;
    }

    // Check if this is a system container
    const isAgentsContainer = job.tags && job.tags.includes('system:agents');
    const isProjectsContainer = job.tags && job.tags.includes('system:projects');
    const isSystemContainer = isAgentsContainer || isProjectsContainer;

    // For system containers, render a simplified view
    if (isSystemContainer) {
        return renderSystemContainerView(job, isAgentsContainer);
    }

    // For agent inbox jobs, render the agent detail view
    if (job.agent_id) {
        return renderAgentDetailView(job);
    }

    const whenLabel = getWhenLabel(job);
    const isArchiving = archivingTaskId === job.id;
    const displayName = job.name || 'Untitled';
    const hasDescription = job.description && job.description.length > 0;
    // Get ALL child jobs sorted by status priority (working > todo > error > done > archived)
    const allChildJobs = getAllChildJobsSorted(job.id);
    const assets = jobAssetsCache[jobId] || [];
    const isAgentJob = !!job.agent_id;
    const titleIcon = isAgentJob ? icon('bolt') : '';

    // Check if we're editing this job
    const isEditingName = editingJobField?.jobId === jobId && editingJobField?.field === 'name';
    const isEditingDesc = editingJobField?.jobId === jobId && editingJobField?.field === 'description';

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = allJobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title${isAgentJob ? ' agent-job-title' : ''}">${titleIcon}${escapeHtml(displayName)}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content" data-testid="job-detail">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('job', '${job.id}')">${icon('calendar')} ${escapeHtml(whenLabel)}</button>
                <button class="task-detail-action" onclick="openStatePicker('${job.id}')">${getJobStatusIcon(job)} ${getJobStatusLabel(job)}</button>
                <button class="task-detail-action" onclick="openAssigneesPicker('${job.id}')">${getAssigneesLabel(job)}</button>
                <button class="task-detail-action" onclick="openReassignPicker('${job.id}')">${icon('arrow-path')} Reassign</button>
                <button class="task-detail-action" onclick="openAddPicker('${job.id}')">+ Add</button>
                ${isAgentJob ? '' : `<button class="task-detail-action" onclick="openMorePicker('${job.id}')">Actions</button>`}
            </div>

            <!-- Name Section -->
            <div class="job-section" data-testid="job-name">
                <div class="job-section-header">Name</div>
                ${isEditingName ? `
                    <input type="text" class="job-name-input" id="edit-name-${job.id}" value="${escapeHtml(displayName)}"
                        onkeydown="handleEditKeypress(event, '${job.id}', 'name')"
                        onblur="saveJobField('${job.id}', 'name', this.value)">
                ` : `
                    <div class="job-name-display" onclick="startEditingField('${job.id}', 'name')">${escapeHtml(displayName)}</div>
                `}
            </div>

            <!-- Description Section -->
            <div class="job-section" data-testid="job-description">
                <div class="job-section-header">
                    Description
                    ${isEditingDesc ? `<span class="job-section-action" onclick="saveJobField('${job.id}', 'description', document.getElementById('edit-description-${job.id}').value)">Save</span>` : ''}
                </div>
                ${isEditingDesc ? `
                    <textarea class="job-description-input" id="edit-description-${job.id}"
                        onkeydown="handleDescriptionKeypress(event, '${job.id}')"
                        placeholder="Add a description...">${escapeHtml(job.description || '')}</textarea>
                ` : `
                    <div class="job-description-display ${hasDescription ? '' : 'empty'}" onclick="startEditingField('${job.id}', 'description')">
                        ${hasDescription ? marked.parse(job.description) : 'Click to add description...'}
                    </div>
                `}
            </div>

            <!-- Child Jobs Section - shows all jobs sorted by status -->
            ${allChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Jobs (${allChildJobs.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content open">
                    ${allChildJobs.map(child => renderJobCard(child, true)).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Parent Link -->
            ${parentName ? `
            <div class="job-section">
                <div class="job-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('job-${job.parent_id}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

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

            <!-- API Calls Section -->
            <div class="job-section">
                <div class="job-section-header collapsible" onclick="toggleAgentSection(this, event, 'job-api-calls', '${job.id}')">
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

// ============== Completed Job Detail View ==============

function renderCompletedJobDetailView(jobId) {
    const job = completedJobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Job Not Found</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-empty">This job no longer exists.</div>
        `;
    }

    const displayName = job.name || 'Untitled';
    const hasDescription = job.description && job.description.length > 0;
    const completedDate = job.completed_at ? formatFriendlyPastDate(job.completed_at) : 'Unknown';
    const completedChildJobs = completedJobsData.filter(j => j.parent_id === job.id);
    const activeChildJobs = jobsData.filter(j => j.parent_id === job.id);
    const assets = jobAssetsCache[jobId] || [];

    // Check if we're editing this job
    const isEditingName = editingJobField?.jobId === jobId && editingJobField?.field === 'name';
    const isEditingDesc = editingJobField?.jobId === jobId && editingJobField?.field === 'description';

    // Get parent job name for context (could be active or completed)
    let parentName = null;
    let parentIsCompleted = false;
    if (job.parent_id) {
        let parent = jobsData.find(j => j.id === job.parent_id);
        if (!parent) {
            parent = completedJobsData.find(j => j.id === job.parent_id);
            parentIsCompleted = true;
        }
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
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
                <button class="task-detail-action" onclick="restoreJob(event, '${job.id}')">${icon('arrow-uturn-left')} Restore</button>
                <button class="task-detail-action danger" onclick="deleteJob(event, '${job.id}')">${icon('trash')} Delete</button>
            </div>

            <!-- Completed Badge -->
            <div class="job-section" style="background: #f0f8f0; border-radius: 6px; padding: 0.5rem 1rem;">
                <span style="color: #4a8; font-weight: 500;">${icon('check')} Completed ${escapeHtml(completedDate)}</span>
            </div>

            <!-- Name Section -->
            <div class="job-section">
                <div class="job-section-header">Name</div>
                ${isEditingName ? `
                    <input type="text" class="job-name-input" id="edit-name-${job.id}" value="${escapeHtml(displayName)}"
                        onkeydown="handleEditKeypress(event, '${job.id}', 'name')"
                        onblur="saveCompletedJobField('${job.id}', 'name', this.value)">
                ` : `
                    <div class="job-name-display" onclick="startEditingField('${job.id}', 'name')">${escapeHtml(displayName)}</div>
                `}
            </div>

            <!-- Description Section -->
            <div class="job-section">
                <div class="job-section-header">
                    Description
                    ${isEditingDesc ? `<span class="job-section-action" onclick="saveCompletedJobField('${job.id}', 'description', document.getElementById('edit-description-${job.id}').value)">Save</span>` : ''}
                </div>
                ${isEditingDesc ? `
                    <textarea class="job-description-input" id="edit-description-${job.id}"
                        onkeydown="handleCompletedDescriptionKeypress(event, '${job.id}')"
                        placeholder="Add a description...">${escapeHtml(job.description || '')}</textarea>
                ` : `
                    <div class="job-description-display ${hasDescription ? '' : 'empty'}" onclick="startEditingField('${job.id}', 'description')">
                        ${hasDescription ? marked.parse(job.description) : 'Click to add description...'}
                    </div>
                `}
            </div>

            <!-- Active Child Jobs Section (rare but possible) - open by default -->
            ${activeChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Active Children (${activeChildJobs.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content open">
                    ${activeChildJobs.map(child => renderJobCard(child, true)).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section - collapsed by default -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Completed Children (${completedChildJobs.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content">
                    ${completedChildJobs.map(child => {
                        const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                        return renderCompletedJobCard(child, grandchildCount, true);
                    }).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Parent Link -->
            ${parentName ? `
            <div class="job-section">
                <div class="job-section-header">Parent</div>
                <div class="card-project-link" onclick="navigateFocus('${parentIsCompleted ? 'completed' : 'job'}-${job.parent_id}')" style="padding: 0.5rem; cursor: pointer;">${icon('folder')} ${escapeHtml(parentName)}</div>
            </div>
            ` : ''}

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
