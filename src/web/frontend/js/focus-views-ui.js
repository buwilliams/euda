// Euno - Focus View UI Utilities
// Generic UI utilities and collapsible section handling

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
                    const data = await loadConsolidationLogs(agentId);
                    content.innerHTML = renderReflectionContent(data, agentId);
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
