// Euno - Focus View Renderers

// ============== Menu & Timeline Views ==============

function renderFocusMenu() {
    const counts = getFocusCounts();
    // Root completed jobs: no parent OR parent is not in completed list (parent still active/archived)
    const completedJobIds = new Set(completedJobsData.map(j => j.id));
    const topLevelCompletedJobs = completedJobsData.filter(j => !j.parent_id || !completedJobIds.has(j.parent_id));

    // Find system containers
    const agentsContainer = jobsData.find(j => j.tags && j.tags.includes('system:agents') && !j.parent_id);
    const projectsContainer = jobsData.find(j => j.tags && j.tags.includes('system:projects') && !j.parent_id);

    // Count children of each container
    const agentsCount = agentsContainer ? jobsData.filter(j => j.parent_id === agentsContainer.id).length : 0;
    const projectsCount = projectsContainer ? jobsData.filter(j => j.parent_id === projectsContainer.id).length : 0;

    return `
        <div class="focus-menu">
            <div class="focus-menu-item" onclick="navigateFocus('today')">
                <span class="focus-menu-icon">${icon('sun')}</span>
                <span class="focus-menu-label">Today</span>
                <span class="focus-menu-count">${counts.today}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('upcoming')">
                <span class="focus-menu-icon">${icon('calendar')}</span>
                <span class="focus-menu-label">Upcoming</span>
                <span class="focus-menu-count">${counts.upcoming}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('anytime')">
                <span class="focus-menu-icon">${icon('clock')}</span>
                <span class="focus-menu-label">Anytime</span>
                <span class="focus-menu-count">${counts.anytime}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('someday')">
                <span class="focus-menu-icon">${icon('cloud')}</span>
                <span class="focus-menu-label">Someday</span>
                <span class="focus-menu-count">${counts.someday}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
            <div class="focus-menu-item" onclick="navigateFocus('completed')">
                <span class="focus-menu-icon">${icon('check')}</span>
                <span class="focus-menu-label">Completed</span>
                <span class="focus-menu-count">${topLevelCompletedJobs.length}</span>
                <span class="focus-menu-arrow">›</span>
            </div>
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
        <div id="daily-quote-container"></div>
    `;
}

function getTimelineIcon(category) {
    const iconNames = { today: 'sun', upcoming: 'calendar', anytime: 'clock', someday: 'cloud' };
    return iconNames[category] ? icon(iconNames[category]) : '';
}

function renderTimelineView(category, title) {
    // Get only root jobs that have descendants matching this category
    const jobs = getRootJobsForCategory(category);
    const categoryIcon = getTimelineIcon(category);
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${categoryIcon} ${title}</span>
        </div>
        <div class="focus-view-content">
            ${jobs.length === 0
                ? '<div class="focus-empty">No jobs</div>'
                : jobs.map(job => renderJobCard(job)).join('')
            }
        </div>
    `;
}

function renderCompletedJobsView() {
    // Root completed jobs: no parent OR parent is not in completed list
    const completedJobIds = new Set(completedJobsData.map(j => j.id));
    const rootCompletedJobs = completedJobsData.filter(j => !j.parent_id || !completedJobIds.has(j.parent_id));
    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${icon('check')} Completed Jobs</span>
        </div>
        <div class="focus-view-content">
            ${rootCompletedJobs.length === 0
                ? '<div class="focus-empty">No completed jobs</div>'
                : rootCompletedJobs.map(job => {
                    const childCount = completedJobsData.filter(j => j.parent_id === job.id).length;
                    return renderCompletedJobCard(job, childCount);
                }).join('')
            }
        </div>
    `;
}

// ============== System Container Views ==============

function renderSystemContainerView(job, isAgentsContainer) {
    const childJobs = jobsData.filter(j => j.parent_id === job.id);
    const titleIcon = isAgentsContainer ? icon('bolt') : icon('folder');
    const containerName = isAgentsContainer ? 'Agents' : 'Projects';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${titleIcon}${containerName}</span>
        </div>
        <div class="focus-view-content">
            <!-- Child Jobs -->
            <div class="job-section">
                ${childJobs.length === 0 ? `
                    <div class="focus-empty">No ${isAgentsContainer ? 'agent inboxes' : 'projects'} yet.</div>
                ` : `
                    <div class="child-jobs-list">
                        ${childJobs.map(child => {
                            const grandchildCount = jobsData.filter(j => j.parent_id === child.id).length;
                            const isAgentInbox = !!child.agent_id;
                            const childIcon = isAgentInbox ? icon('bolt') : icon('folder');
                            const trashBtn = isAgentInbox ? '' : `<button class="card-trash-btn" onclick="quickDeleteJob(event, '${child.id}')" title="Delete">${icon('trash')}</button>`;
                            return `
                                <div class="child-job-card" onclick="navigateFocus('job-${child.id}')">
                                    <span class="child-job-icon">${childIcon}</span>
                                    <span class="child-job-name">${escapeHtml(child.name)}</span>
                                    <span class="child-job-count">${grandchildCount}</span>
                                    ${trashBtn}
                                    <span class="child-job-arrow">${icon('chevron-right')}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `}
            </div>
            ${!isAgentsContainer ? `
            <!-- Quick Add for Projects -->
            <div class="quick-add-section">
                <input type="text" id="quick-add-${job.id}" class="quick-add-input" placeholder="Add new project..." onkeypress="handleQuickAddKeypress(event, 'quick-add-${job.id}', '${job.id}')">
                <button class="quick-add-btn" onclick="quickAddJob('quick-add-${job.id}', '${job.id}')">${icon('plus')}</button>
            </div>
            ` : ''}
        </div>
    `;
}

// ============== Agent Detail View ==============

function renderAgentDetailView(job) {
    const agentId = job.agent_id;
    const displayName = job.name || 'Untitled';
    const childJobs = jobsData.filter(j => j.parent_id === job.id);
    const completedChildJobs = completedJobsData.filter(j => j.parent_id === job.id);
    const assets = jobAssetsCache[job.id] || [];

    // Load agent data if not cached
    const agentData = agentDataCache[agentId];
    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">${icon('bolt')}${escapeHtml(displayName)}</span>
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

    const persona = agentData.persona || '';
    const config = agentData.config || {};
    const hasPersona = persona.length > 0;

    // Check if we're editing
    const isEditingPersona = editingJobField?.jobId === job.id && editingJobField?.field === 'persona';
    const isEditingConfig = editingJobField?.jobId === job.id && editingJobField?.field === 'config';

    // Format triggers and tools for display
    const triggers = config.triggers || [];
    const tools = config.tools || [];
    const isEnabled = config.enabled !== false;

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${icon('bolt')}${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="toggleAgentEnabled('${agentId}', ${!isEnabled})">${isEnabled ? icon('x-mark') + ' Disable' : icon('check') + ' Enable'}</button>
                <button class="task-detail-action" onclick="openAddPicker('${job.id}')">+ Add</button>
            </div>

            <!-- Status Section -->
            <div class="job-section" style="background: ${isEnabled ? '#f0f8f0' : '#f8f0f0'}; border-radius: 6px; padding: 0.5rem 1rem;">
                <span style="color: ${isEnabled ? '#4a8' : '#a64'}; font-weight: 500;">
                    ${isEnabled ? icon('check') + ' Agent Enabled' : icon('x-mark') + ' Agent Disabled'}
                </span>
            </div>

            <!-- Persona Section -->
            <div class="job-section">
                <div class="job-section-header">
                    Persona
                    ${isEditingPersona ? `<span class="job-section-action" onclick="saveAgentPersonaField('${agentId}', '${job.id}')">Save</span>` : ''}
                </div>
                ${isEditingPersona ? `
                    <textarea class="job-description-input" id="edit-persona-${job.id}"
                        onkeydown="handleAgentPersonaKeypress(event, '${agentId}', '${job.id}')"
                        placeholder="Define the agent's persona..."
                        style="min-height: 200px;">${escapeHtml(persona)}</textarea>
                ` : `
                    <div class="job-description-display ${hasPersona ? '' : 'empty'}" onclick="startEditingField('${job.id}', 'persona')">
                        ${hasPersona ? marked.parse(persona) : 'Click to define persona...'}
                    </div>
                `}
            </div>

            <!-- Configuration Section -->
            <div class="job-section">
                <div class="job-section-header">
                    Configuration
                    ${isEditingConfig ? `<span class="job-section-action" onclick="saveAgentConfigField('${agentId}', '${job.id}')">Save</span>` : ''}
                </div>
                ${isEditingConfig ? `
                    <div class="agent-config-edit">
                        <label class="agent-config-label">
                            <span>Triggers (comma-separated)</span>
                            <input type="text" class="agent-config-input" id="edit-triggers-${job.id}"
                                value="${escapeHtml(triggers.join(', '))}"
                                placeholder="e.g., job:assigned, time:morning">
                        </label>
                        <label class="agent-config-label">
                            <span>Tools (comma-separated)</span>
                            <input type="text" class="agent-config-input" id="edit-tools-${job.id}"
                                value="${escapeHtml(tools.join(', '))}"
                                placeholder="e.g., list_jobs, create_job">
                        </label>
                        <div class="agent-config-actions">
                            <button class="task-detail-action" onclick="cancelEditing()">Cancel</button>
                        </div>
                    </div>
                ` : `
                    <div class="agent-config-display" onclick="startEditingField('${job.id}', 'config')">
                        <div class="agent-config-row">
                            <span class="agent-config-key">Triggers:</span>
                            <span class="agent-config-value">${triggers.length > 0 ? escapeHtml(triggers.join(', ')) : '<em>None</em>'}</span>
                        </div>
                        <div class="agent-config-row">
                            <span class="agent-config-key">Tools:</span>
                            <span class="agent-config-value">${tools.length > 0 ? escapeHtml(tools.join(', ')) : '<em>None</em>'}</span>
                        </div>
                    </div>
                `}
            </div>

            <!-- Child Jobs Section (Agent's Tasks) -->
            ${childJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Tasks (${childJobs.length})</div>
                ${childJobs.map(child => renderJobCard(child)).join('')}
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Completed (${completedChildJobs.length})</div>
                ${completedChildJobs.map(child => {
                    const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                    return renderCompletedJobCard(child, grandchildCount);
                }).join('')}
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

// ============== Job Detail View ==============

function renderJobDetailView(jobId) {
    const job = jobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">Job Not Found</span>
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
    // Use context-aware filtering for child jobs (respects timeline context)
    const childJobs = getChildJobsForContext(job.id);
    const completedChildJobs = completedJobsData.filter(j => j.parent_id === job.id);
    const assets = jobAssetsCache[jobId] || [];
    const isAgentJob = !!job.agent_id;
    const titleIcon = isAgentJob ? icon('bolt') : '';

    // Check if we're editing this job
    const isEditingName = editingJobField?.jobId === jobId && editingJobField?.field === 'name';
    const isEditingDesc = editingJobField?.jobId === jobId && editingJobField?.field === 'description';

    // Get parent job name for context
    let parentName = null;
    if (job.parent_id) {
        const parent = jobsData.find(j => j.id === job.parent_id);
        parentName = parent ? parent.name : null;
    }

    // Load assets if not cached
    if (!jobAssetsCache[jobId]) {
        loadJobAssets(jobId).then(() => renderFocusTab());
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title${isAgentJob ? ' agent-job-title' : ''}">${titleIcon}${escapeHtml(displayName)}</span>
        </div>
        <div class="focus-view-content">
            <!-- Actions Row -->
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="openWhenPicker('job', '${job.id}')">${icon('calendar')} ${escapeHtml(whenLabel)}</button>
                <button class="task-detail-action" onclick="openAssigneesPicker('${job.id}')">${getAssigneesLabel(job)}</button>
                <button class="task-detail-action" onclick="openAddPicker('${job.id}')">+ Add</button>
                ${isAgentJob ? '' : `<button class="task-detail-action" onclick="openMorePicker('${job.id}')">Actions</button>`}
            </div>

            <!-- Name Section -->
            <div class="job-section">
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
            <div class="job-section">
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

            <!-- Child Jobs Section -->
            ${childJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Child Jobs (${childJobs.length})</div>
                ${childJobs.map(child => renderJobCard(child)).join('')}
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Completed (${completedChildJobs.length})</div>
                ${completedChildJobs.map(child => {
                    const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                    return renderCompletedJobCard(child, grandchildCount);
                }).join('')}
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
        </div>
    `;
}

// ============== Completed Job Detail View ==============

function renderCompletedJobDetailView(jobId) {
    const job = completedJobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">Job Not Found</span>
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
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${escapeHtml(displayName)}</span>
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

            <!-- Active Child Jobs Section (rare but possible) -->
            ${activeChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Active Children (${activeChildJobs.length})</div>
                ${activeChildJobs.map(child => renderJobCard(child)).join('')}
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Completed Children (${completedChildJobs.length})</div>
                ${completedChildJobs.map(child => {
                    const grandchildCount = completedJobsData.filter(j => j.parent_id === child.id).length;
                    return renderCompletedJobCard(child, grandchildCount);
                }).join('')}
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
