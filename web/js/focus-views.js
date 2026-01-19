// Euno - Focus View Renderers

// ============== Collapsible Sections ==============

function isSectionOpen(sectionId) {
    // Default to closed
    return sessionStorage.getItem(`focus-section-${sectionId}`) === 'open';
}

function toggleSection(sectionId) {
    const isOpen = isSectionOpen(sectionId);
    sessionStorage.setItem(`focus-section-${sectionId}`, isOpen ? 'closed' : 'open');
    renderFocusTab();
}

function togglePersonaSection(header, event) {
    // Don't toggle if clicking on the Save action
    if (event.target.classList.contains('job-section-action')) return;

    header.classList.toggle('open');
    const content = header.nextElementSibling;
    if (content && content.classList.contains('collapsible-content')) {
        content.classList.toggle('open');
    }
}

async function toggleAgentSection(header, event, sectionType, agentId) {
    // Don't toggle if clicking on actions
    if (event.target.classList.contains('job-section-action')) return;

    header.classList.toggle('open');
    const content = header.nextElementSibling;
    if (content && content.classList.contains('collapsible-content')) {
        content.classList.toggle('open');

        // Lazy load data on first expand
        if (content.classList.contains('open')) {
            const isLoaded = content.dataset.loaded === 'true';
            if (!isLoaded) {
                content.innerHTML = '<div class="section-loading">Loading...</div>';

                if (sectionType === 'completed-by-agent') {
                    const jobs = await loadAgentCompletedJobs(agentId);
                    content.innerHTML = renderAgentCompletedJobsContent(jobs);
                } else if (sectionType === 'monitoring') {
                    const data = await loadAgentMonitoring(agentId);
                    content.innerHTML = renderMonitoringContent(data);
                } else if (sectionType === 'job-api-calls') {
                    const data = await loadJobApiCalls(agentId);  // agentId is actually jobId here
                    content.innerHTML = renderJobApiCallsContent(data);
                } else if (sectionType === 'rate-limit-events') {
                    const data = await loadRateLimitEvents(agentId);
                    content.innerHTML = renderRateLimitEventsContent(data, agentId);
                } else if (sectionType === 'short-term-memory') {
                    const items = await loadShortTermMemory(agentId);
                    content.innerHTML = renderShortTermMemoryContent(items, agentId);
                } else if (sectionType === 'long-term-memory') {
                    const dates = await loadLongTermMemoryDates(agentId);
                    if (dates.length > 0) {
                        const contentData = await loadLongTermMemoryContent(agentId, dates[0]);
                        content.innerHTML = renderLongTermMemoryContent(dates, dates[0], contentData, agentId);
                    } else {
                        content.innerHTML = '<div class="focus-empty">No long-term memory entries.</div>';
                    }
                } else if (sectionType === 'reflection') {
                    const data = await loadReflectionLogs(agentId);
                    content.innerHTML = renderReflectionContent(data, agentId);
                } else if (sectionType === 'exploration') {
                    content.innerHTML = renderExplorationContent(agentId);
                }
                content.dataset.loaded = 'true';
            }
        }
    }
}

function renderAgentCompletedJobsContent(jobs) {
    if (!jobs || jobs.length === 0) {
        return '<div class="focus-empty">No jobs completed by this agent yet.</div>';
    }
    return jobs.map(job => renderCompletedJobCardWithTrace(job)).join('');
}

function renderCompletedJobCardWithTrace(job) {
    const name = job.name || 'Untitled';
    const completedDate = job.completed_at ? formatFriendlyPastDate(job.completed_at.split('T')[0]) : '';

    return `
        <div class="job-card completed-job-card">
            <div class="job-card-content" onclick="navigateToTrace('${job.id}')">
                <span class="job-icon">${icon('check-circle')}</span>
                <span class="job-name">${escapeHtml(name)}</span>
                ${completedDate ? `<span class="job-completed-date">${completedDate}</span>` : ''}
            </div>
            <button class="trace-btn" onclick="event.stopPropagation(); navigateToTrace('${job.id}')" title="View Trace">
                ${icon('chart-bar')}
            </button>
        </div>
    `;
}

function renderMonitoringContent(data) {
    if (!data) {
        return '<div class="focus-empty">No monitoring data available.</div>';
    }

    const { stats, recent_prompts } = data;

    return `
        <div class="monitoring-stats">
            <div class="monitoring-stat">
                <span class="stat-label">This Week</span>
                <span class="stat-value">${stats.week.calls} calls</span>
                <span class="stat-detail">${formatTokenCount(stats.week.tokens)} tokens, $${stats.week.cost.toFixed(4)}</span>
            </div>
            <div class="monitoring-stat">
                <span class="stat-label">Today</span>
                <span class="stat-value">${stats.today.calls} calls</span>
                <span class="stat-detail">${formatTokenCount(stats.today.tokens)} tokens, $${stats.today.cost.toFixed(4)}</span>
            </div>
            <div class="monitoring-stat">
                <span class="stat-label">Last Hour</span>
                <span class="stat-value">${stats.hour.calls} calls</span>
                <span class="stat-detail">${formatTokenCount(stats.hour.tokens)} tokens, $${stats.hour.cost.toFixed(4)}</span>
            </div>
        </div>

        <div class="monitoring-prompts">
            <div class="monitoring-section-title">Recent Prompts</div>
            ${recent_prompts.length === 0 ? '<div class="focus-empty">No recent prompts</div>' :
              recent_prompts.map(p => `
                <div class="monitoring-prompt">
                    <span class="prompt-time">${formatPromptTime(p.timestamp)}</span>
                    <span class="prompt-tokens">${p.input_tokens}/${p.output_tokens}</span>
                    <span class="prompt-model">${p.model || 'unknown'}</span>
                    ${p.duration_ms ? `<span class="prompt-duration">${p.duration_ms}ms</span>` : ''}
                </div>
              `).join('')
            }
        </div>
    `;
}

async function loadJobApiCalls(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/api-calls`);
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        console.error('Failed to load job API calls:', error);
        return null;
    }
}

function renderJobApiCallsContent(data) {
    if (!data || data.calls === 0) {
        return '<div class="focus-empty">No API calls recorded for this job.</div>';
    }

    const { calls, cost, input_tokens, output_tokens } = data;
    const callList = data.calls && Array.isArray(data.calls) ? data.calls : [];

    return `
        <div class="monitoring-stats">
            <div class="monitoring-stat">
                <span class="stat-label">Total Calls</span>
                <span class="stat-value">${calls}</span>
            </div>
            <div class="monitoring-stat">
                <span class="stat-label">Total Cost</span>
                <span class="stat-value">$${cost.toFixed(4)}</span>
            </div>
            <div class="monitoring-stat">
                <span class="stat-label">Tokens</span>
                <span class="stat-value">${formatTokenCount(input_tokens + output_tokens)}</span>
                <span class="stat-detail">in: ${formatTokenCount(input_tokens)}, out: ${formatTokenCount(output_tokens)}</span>
            </div>
        </div>

        ${callList.length > 0 ? `
        <div class="monitoring-prompts">
            <div class="monitoring-section-title">Recent API Calls</div>
            ${callList.slice(0, 20).map(call => `
                <div class="monitoring-prompt">
                    <span class="prompt-time">${formatPromptTime(call.timestamp)}</span>
                    <span class="prompt-tokens">${call.input_tokens}/${call.output_tokens}</span>
                    <span class="prompt-model">${call.model || 'unknown'}</span>
                    <span class="prompt-cost">$${call.cost.toFixed(4)}</span>
                </div>
            `).join('')}
        </div>
        ` : ''}
    `;
}

async function loadRateLimitEvents(agentId) {
    try {
        const response = await fetch('/api/rate-limiting/events?days=7');
        if (!response.ok) return null;
        const events = await response.json();
        // Filter events for this agent
        return events.filter(e => e.agent_id === agentId || !e.agent_id);
    } catch (error) {
        console.error('Failed to load rate limit events:', error);
        return null;
    }
}

function renderRateLimitEventsContent(events, agentId) {
    if (!events || events.length === 0) {
        return '<div class="focus-empty">No rate limit events for this agent.</div>';
    }

    // Filter to agent-specific events (exclude global events for now)
    const agentEvents = events.filter(e => e.agent_id === agentId);

    if (agentEvents.length === 0) {
        return '<div class="focus-empty">No rate limit events for this agent.</div>';
    }

    return `
        <div class="rate-limit-events">
            ${agentEvents.slice(0, 50).map(e => {
                const eventClass = e.event === 'agent_paused' ? 'event-paused' :
                                   e.event === 'agent_resumed' ? 'event-resumed' :
                                   e.event === 'rate_limit_hit' ? 'event-limited' : '';
                return `
                    <div class="rate-limit-event ${eventClass}">
                        <span class="event-time">${formatPromptTime(e.timestamp)}</span>
                        <span class="event-type">${escapeHtml(e.event)}</span>
                        <span class="event-detail">${e.reason || e.details?.reason || ''}</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function formatTokenCount(count) {
    if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M';
    if (count >= 1000) return (count / 1000).toFixed(1) + 'K';
    return count.toString();
}

// ============== Memory Render Functions ==============

function renderShortTermMemoryContent(items, agentId) {
    if (!items || items.length === 0) {
        return `
            <div class="focus-empty">No short-term memory items.</div>
            <div class="memory-actions">
                <button class="btn-secondary memory-add" onclick="addMemoryItem('${agentId}')">+ Add Memory</button>
            </div>
        `;
    }

    const state = memoryPageState[agentId] || { page: 0, pageSize: 10 };
    const start = state.page * state.pageSize;
    const end = start + state.pageSize;
    const pageItems = items.slice(start, end);
    const totalPages = Math.ceil(items.length / state.pageSize);

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
        <div class="memory-list">
            ${pageItems.map(item => `
                <div class="memory-item">
                    <span class="memory-type-badge ${typeColors[item.type] || 'type-thing'}">${escapeHtml(item.type)}</span>
                    <span class="memory-description">${escapeHtml(item.short_description)}</span>
                    <button class="memory-delete" onclick="deleteMemoryItem('${agentId}', '${item.id}')" title="Delete">&times;</button>
                </div>
            `).join('')}
        </div>
        ${totalPages > 1 ? `
        <div class="memory-pagination">
            <button class="memory-page-btn" onclick="pageMemory('${agentId}', 'prev')" ${state.page === 0 ? 'disabled' : ''}>Prev</button>
            <span class="memory-page-info">${state.page + 1} / ${totalPages}</span>
            <button class="memory-page-btn" onclick="pageMemory('${agentId}', 'next')" ${end >= items.length ? 'disabled' : ''}>Next</button>
        </div>
        ` : ''}
        <div class="memory-actions">
            <button class="btn-secondary memory-add" onclick="addMemoryItem('${agentId}')">+ Add Memory</button>
        </div>
    `;
}

function renderLongTermMemoryContent(dates, currentDate, content, agentId) {
    if (!dates || dates.length === 0) {
        return '<div class="focus-empty">No long-term memory entries.</div>';
    }

    const currentIndex = dates.indexOf(currentDate);
    const hasPrev = currentIndex < dates.length - 1;
    const hasNext = currentIndex > 0;

    const memoryContent = content?.content || content?.entries?.join('\n\n') || 'No content for this date.';

    return `
        <div class="long-term-memory">
            <div class="memory-date-nav">
                <button class="memory-page-btn" onclick="loadLongTermMemoryDate('${agentId}', '${dates[currentIndex + 1] || currentDate}')" ${!hasPrev ? 'disabled' : ''}>Older</button>
                <span class="memory-date-current">${currentDate}</span>
                <button class="memory-page-btn" onclick="loadLongTermMemoryDate('${agentId}', '${dates[currentIndex - 1] || currentDate}')" ${!hasNext ? 'disabled' : ''}>Newer</button>
            </div>
            <div class="long-term-content">${escapeHtml(memoryContent)}</div>
        </div>
    `;
}

// ============== Reflection Render Functions ==============

function renderReflectionContent(data, agentId) {
    const logs = data?.logs || [];

    return `
        <div class="reflection-section">
            <div class="reflection-actions">
                <button class="btn-secondary" onclick="triggerReflection('${agentId}', 'append')">Run Append</button>
                <button class="btn-secondary" onclick="triggerReflection('${agentId}', 'consolidate')">Run Consolidate</button>
                <button class="btn-primary" onclick="triggerReflection('${agentId}', 'both')">Run Both</button>
            </div>
            <div class="reflection-logs">
                <div class="monitoring-section-title">Recent Activity (7 days)</div>
                ${logs.length === 0 ? '<div class="focus-empty">No reflection activity recorded.</div>' :
                  logs.slice(0, 20).map(log => {
                      const eventType = log.phase || log.event || 'unknown';
                      const eventClass = eventType === 'append' ? 'log-event-append' :
                                        eventType === 'consolidate' ? 'log-event-consolidate' :
                                        eventType === 'error' ? 'log-event-error' : '';
                      return `
                          <div class="reflection-log-entry">
                              <span class="log-time">${formatPromptTime(log.timestamp)}</span>
                              <span class="log-event ${eventClass}">${escapeHtml(eventType)}</span>
                              <span class="log-detail">${escapeHtml(log.message || log.details || '')}</span>
                          </div>
                      `;
                  }).join('')
                }
            </div>
        </div>
    `;
}

// ============== Exploration Render Functions ==============

function renderExplorationContent(agentId) {
    return `
        <div class="exploration-section">
            <div class="exploration-info">
                <p>Exploration runs scheduled discovery where the agent researches opportunities and ideas for you.</p>
            </div>
            <div class="exploration-actions">
                <button class="btn-primary" onclick="triggerExploration('${agentId}')">Run Exploration</button>
            </div>
            <div class="exploration-status">
                <span class="status-label">Status:</span>
                <span class="status-value">Ready to explore</span>
            </div>
        </div>
    `;
}

// ============== Job Trace View ==============

// Cache for trace data
let traceDataCache = {};

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
                <span class="focus-back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn">${icon('chevron-left')}</span>
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
    const systemContainer = jobsData.find(j => j.tags && j.tags.includes('system:system') && !j.parent_id);

    // Count children of each container
    const agentsCount = agentsContainer ? jobsData.filter(j => j.parent_id === agentsContainer.id).length : 0;
    const projectsCount = projectsContainer ? jobsData.filter(j => j.parent_id === projectsContainer.id).length : 0;
    const systemCount = systemContainer ? jobsData.filter(j => j.parent_id === systemContainer.id).length : 0;

    // Check collapsed states
    const timelinesOpen = isSectionOpen('timelines');
    const collectionsOpen = isSectionOpen('collections');

    // Build today section using same format as other menu sections
    let todaySection = '';
    if (todayJobs.length > 0) {
        todaySection = `
            <div class="focus-menu-section">
                <div class="focus-menu-section-label">Today</div>
                <div class="focus-today-jobs">
                    ${todayJobs.map(job => renderJobCard(job, isSwipeable(job))).join('')}
                </div>
            </div>
        `;
    } else {
        todaySection = `
            <div class="focus-menu-section">
                <div class="focus-menu-section-label">Today</div>
                <div class="focus-free-message">
                    <span class="focus-free-text">Your day is free.</span>
                </div>
            </div>
        `;
    }

    // Build system section (Agents + Projects + System) if any exist
    const hasSystemSection = agentsContainer || projectsContainer || systemContainer;
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
                ${systemContainer ? `
                <div class="focus-menu-item" onclick="navigateFocus('job-${systemContainer.id}')">
                    <span class="focus-menu-icon">${icon('cog-6-tooth')}</span>
                    <span class="focus-menu-label">System</span>
                    <span class="focus-menu-count">${systemCount}</span>
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
            <div class="focus-menu-section-label collapsible ${timelinesOpen ? 'open' : ''}" onclick="toggleSection('timelines')">
                <span>Timelines</span>
                <span class="section-toggle">${icon('chevron-right')}</span>
            </div>
            <div class="focus-menu collapsible-content ${timelinesOpen ? 'open' : ''}">
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
            <span class="focus-back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn">${icon('chevron-left')}</span>
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

function renderSystemContainerView(job, isAgentsContainer, isSystemJobsContainer = false) {
    const childJobs = jobsData.filter(j => j.parent_id === job.id);

    // Determine container type and styling
    let titleIcon, containerName, emptyMessage;
    if (isAgentsContainer) {
        titleIcon = icon('bolt');
        containerName = 'Agents';
        emptyMessage = 'No agent inboxes yet.';
    } else if (isSystemJobsContainer) {
        titleIcon = icon('cog-6-tooth');
        containerName = 'System';
        emptyMessage = 'No system jobs.';
    } else {
        titleIcon = icon('folder');
        containerName = 'Projects';
        emptyMessage = 'No projects yet.';
    }

    // For Projects and System containers, render children as swipeable job cards
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
                            <div class="child-job-card" onclick="navigateFocus('job-${child.id}')">
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
            // Projects and System - swipeable job cards
            return `
                <div class="child-jobs-list">
                    ${childJobs.map(child => renderJobCard(child, true)).join('')}
                </div>
            `;
        }
    };

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${titleIcon}${containerName}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <!-- Child Jobs -->
            <div class="job-section">
                ${renderChildJobs()}
            </div>
        </div>
    `;
}

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

            <!-- Profile Section - navigates to profile view -->
            <div class="job-section">
                <div class="job-section-header collapsible clickable" onclick="navigateFocus('profile-${agentId}')">
                    <span>Profile</span>
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

let memoryListCache = {};

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

let memoryItemCache = {};

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

let longTermMemoryListCache = {};

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

let longTermMemoryDetailCache = {};

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

let monitoringCache = {};
let monitoringPagination = {};  // { agentId: { offset: 0, limit: 20 } }
let monitoringLoading = {};     // { agentId: true } - prevents duplicate requests

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

// ============== Profile View ==============

function renderProfileView(agentId) {
    const agentData = agentDataCache[agentId];

    if (!agentData) {
        loadAgentData(agentId).then(() => renderFocusTab());
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
                <div class="focus-view-header-content">
                    <span class="focus-view-title">Profile</span>
                    ${renderBreadcrumbs()}
                </div>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">Loading...</div>
            </div>
        `;
    }

    const profile = agentData.persona || '';
    const hasProfile = profile.length > 0;

    // Find the job for this agent (for editing state)
    const agentJob = jobsData.find(j => j.agent_id === agentId);
    const jobId = agentJob?.id || agentId;

    const isEditingProfile = editingJobField?.jobId === jobId && editingJobField?.field === 'profile';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Profile</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            ${isEditingProfile ? `
                <!-- Edit Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="saveAgentProfileField('${agentId}', '${jobId}')">
                        ${icon('check')} Save
                    </button>
                    <button class="task-detail-action" onclick="cancelEditing()">
                        ${icon('x-mark')} Cancel
                    </button>
                </div>

                <div class="profile-edit">
                    <textarea class="job-description-input" id="edit-profile-${jobId}"
                        placeholder="Define the agent's identity and behavioral rules..."
                        style="min-height: 300px;">${escapeHtml(profile)}</textarea>
                </div>
            ` : `
                <!-- View Mode -->
                <div class="task-detail-actions">
                    <button class="task-detail-action" onclick="startEditingField('${jobId}', 'profile')">
                        ${icon('pencil')} Edit
                    </button>
                </div>

                <div class="profile-content ${hasProfile ? '' : 'empty'}">
                    ${hasProfile ? marked.parse(profile) : '<em class="text-muted">No profile defined. Click Edit to define the agent\'s identity and behavioral rules.</em>'}
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

let rateLimitViewCache = {};

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

// ============== Job Detail View ==============

function renderJobDetailView(jobId) {
    const job = jobsData.find(j => j.id === jobId);
    if (!job) {
        return `
            <div class="focus-view-header" onclick="navigateFocusBack()">
                <span class="focus-back-btn">${icon('chevron-left')}</span>
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
    const isSystemJobsContainer = job.tags && job.tags.includes('system:system');
    const isSystemContainer = isAgentsContainer || isProjectsContainer || isSystemJobsContainer;

    // For system containers, render a simplified view
    if (isSystemContainer) {
        return renderSystemContainerView(job, isAgentsContainer, isSystemJobsContainer);
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
    // Get completed children - filter by timeline context if we're in one
    const timelineContext = getTimelineContext();
    const completedChildJobs = completedJobsData.filter(j => {
        if (j.parent_id !== job.id) return false;
        // If in timeline context, only show completed jobs that matched that context
        if (timelineContext) {
            return getJobCategory({ ...j, status: 'todo' }) === timelineContext;
        }
        return true;
    });
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
            <div class="focus-view-header-content">
                <span class="focus-view-title${isAgentJob ? ' agent-job-title' : ''}">${titleIcon}${escapeHtml(displayName)}</span>
                ${renderBreadcrumbs()}
            </div>
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

            <!-- Child Jobs Section - open by default -->
            ${childJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header collapsible open" onclick="togglePersonaSection(this, event)">
                    <span>Child Jobs (${childJobs.length})</span>
                    <span class="section-toggle">${icon('chevron-right')}</span>
                </div>
                <div class="collapsible-content open">
                    ${childJobs.map(child => renderJobCard(child, true)).join('')}
                </div>
            </div>
            ` : ''}

            <!-- Completed Child Jobs Section - collapsed by default -->
            ${completedChildJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header collapsible" onclick="togglePersonaSection(this, event)">
                    <span>Completed (${completedChildJobs.length})</span>
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
                <span class="focus-back-btn">${icon('chevron-left')}</span>
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
            <span class="focus-back-btn">${icon('chevron-left')}</span>
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
