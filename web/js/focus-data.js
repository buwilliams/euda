// Euno - Focus Data Loading & Utilities

// ============== Live Execution State ==============

let activeExecution = null;

// ============== Agent Pause Status ==============

let agentPauseStatus = {};  // Cache: { agentId: { isPaused, reason, timestamp } }

async function loadAgentPauseStatus(agentId) {
    try {
        const response = await fetch(`/api/rate-limiting/agents/${agentId}/stats`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const data = await response.json();
            agentPauseStatus[agentId] = {
                isPaused: data.is_paused || false,
                reason: data.pause_reason || null,
                timestamp: data.pause_timestamp || null
            };
            return agentPauseStatus[agentId];
        }
    } catch (error) {
        console.error('Failed to load agent pause status:', error);
    }
    return { isPaused: false, reason: null, timestamp: null };
}

async function resumeAgent(agentId) {
    try {
        const response = await fetch(`/api/rate-limiting/agents/${agentId}/resume`, {
            method: 'POST',
            credentials: 'same-origin'
        });
        if (response.ok) {
            // Clear cache entry
            delete agentPauseStatus[agentId];
            // Re-render the view
            renderFocusTab();
            return true;
        }
    } catch (error) {
        console.error('Failed to resume agent:', error);
    }
    return false;
}

async function loadActiveExecutions(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/active-executions`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const executions = await response.json();
            // Restore activeExecution if there's an active trigger job
            if (executions.length > 0) {
                const exec = executions[0];  // Take the first (most recent)
                activeExecution = {
                    executionId: exec.execution_id,
                    agentId: agentId,
                    phase: exec.phase,
                    step: 'running',
                    message: 'In progress...'
                };
            }
            return executions;
        }
    } catch (error) {
        console.error('Failed to load active executions:', error);
    }
    return [];
}

function handleReflectionProgress(data) {
    // Match by execution_id if we have one, otherwise match by agent_id
    if (activeExecution &&
        (activeExecution.executionId === data.execution_id ||
         (!activeExecution.executionId && activeExecution.agentId === data.agent_id))) {
        activeExecution.executionId = data.execution_id; // Update if we didn't have it
        activeExecution.step = data.step;
        activeExecution.message = data.message;
        if (data.input_tokens) {
            activeExecution.tokens = {
                input: data.input_tokens,
                output: data.output_tokens
            };
        }
        updateExecutionUI();
    }
}

function handleReflectionComplete(data) {
    if (activeExecution &&
        (activeExecution.executionId === data.execution_id ||
         activeExecution.agentId === data.agent_id)) {
        activeExecution = null;
        updateExecutionUI();
        // Refresh monitoring data after completion
        if (data.agent_id) {
            // Clear cache and loading flag to force reload
            delete monitoringCache[data.agent_id];
            if (typeof monitoringLoading !== 'undefined') {
                delete monitoringLoading[data.agent_id];
            }
            // Reset pagination to first page
            if (typeof monitoringPagination !== 'undefined') {
                monitoringPagination[data.agent_id] = { offset: 0, limit: 20 };
            }
            loadAgentMonitoring(data.agent_id, 0, 20);
        }
    }
}

function handleReflectionError(data) {
    if (activeExecution &&
        (activeExecution.executionId === data.execution_id ||
         activeExecution.agentId === data.agent_id)) {
        activeExecution.error = data.error;
        activeExecution.step = 'error';
        activeExecution.message = `Error: ${data.error}`;
        updateExecutionUI();
        // Clear after showing error
        setTimeout(() => {
            if (activeExecution?.executionId === data.execution_id) {
                activeExecution = null;
                updateExecutionUI();
            }
        }, 5000);
    }
}

function updateExecutionUI() {
    // Re-render if we're on a monitoring or manage view for this agent
    if (focusView && (focusView.startsWith('monitoring-') || focusView.startsWith('manage-agent-'))) {
        renderFocusTab();
    }
}

function getActiveExecutionHtml(agentId) {
    if (!activeExecution || activeExecution.agentId !== agentId) {
        return '';
    }

    const phaseLabel = activeExecution.phase === 'append' ? 'Append' :
                       activeExecution.phase === 'consolidate' ? 'Consolidate' :
                       activeExecution.phase === 'exploration' ? 'Explore' : activeExecution.phase;

    const isError = activeExecution.step === 'error';
    const statusClass = isError ? 'reflection-progress error' : 'reflection-progress';

    return `
        <div class="${statusClass}">
            <div class="reflection-progress-header">
                ${isError ? icon('exclamation-triangle') : icon('arrow-path', 'spinning')}
                <span>${isError ? 'Error' : 'Running'} ${phaseLabel}...</span>
            </div>
            <div class="reflection-progress-body">
                <div class="progress-message">${escapeHtml(activeExecution.message || 'Processing...')}</div>
                ${activeExecution.tokens ? `
                    <div class="progress-tokens">
                        ${activeExecution.tokens.input} in / ${activeExecution.tokens.output} out
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

// ============== Data Loading ==============

async function loadJobsData() {
    try {
        const fetchOpts = { credentials: 'same-origin' };
        const [activeRes, completedRes] = await Promise.all([
            fetch('/api/jobs?status=todo', fetchOpts),
            fetch('/api/jobs?status=completed', fetchOpts)
        ]);

        if (activeRes.status === 401 || completedRes.status === 401) {
            console.error('Focus tab: Authentication required');
            window.location.reload();
            return;
        }

        const activeJobs = await activeRes.json();
        const completedJobs = await completedRes.json();

        // Active jobs (not completed, not archived)
        jobsData = Array.isArray(activeJobs) ? activeJobs : [];
        // Recently completed jobs (limit to 20)
        completedJobsData = Array.isArray(completedJobs) ? completedJobs.slice(0, 20) : [];

        renderFocusTab();
        updateTasksBadge();
        // Load daily quote when showing the focus menu
        if (focusView === 'menu') {
            loadDailyQuote();
        }
    } catch (error) {
        console.error('Failed to load jobs data:', error);
    }
}

// Alias for backwards compatibility
async function loadTasksData() {
    return loadJobsData();
}

async function loadAgents() {
    if (agentsCache) return agentsCache;
    try {
        const response = await fetch('/api/agents', { credentials: 'same-origin' });
        if (response.ok) {
            agentsCache = await response.json();
            return agentsCache;
        }
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
    return [];
}

async function loadAgentData(agentId) {
    try {
        const [personaRes, configRes] = await Promise.all([
            fetch(`/api/agents/${agentId}/persona`, { credentials: 'same-origin' }),
            fetch(`/api/agents/${agentId}/config`, { credentials: 'same-origin' })
        ]);

        const data = { agentId };

        if (personaRes.ok) {
            const personaData = await personaRes.json();
            data.persona = personaData.persona;
        }

        if (configRes.ok) {
            data.config = await configRes.json();
        }

        agentDataCache[agentId] = data;
        return data;
    } catch (error) {
        console.error('Failed to load agent data:', error);
    }
    return null;
}

async function saveAgentPersona(agentId, persona) {
    try {
        const response = await fetch(`/api/agents/${agentId}/persona`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ persona })
        });

        if (response.ok) {
            // Update cache
            if (agentDataCache[agentId]) {
                agentDataCache[agentId].persona = persona;
            }
            return true;
        }
    } catch (error) {
        console.error('Failed to save agent persona:', error);
    }
    return false;
}

async function saveAgentConfig(agentId, updates) {
    try {
        const response = await fetch(`/api/agents/${agentId}/config`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });

        if (response.ok) {
            const result = await response.json();
            // Update cache
            if (agentDataCache[agentId]) {
                agentDataCache[agentId].config = result.config;
            }
            return true;
        }
    } catch (error) {
        console.error('Failed to save agent config:', error);
    }
    return false;
}

async function loadAgentCompletedJobs(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/completed-jobs`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const jobs = await response.json();
            // Update cache
            if (agentDataCache[agentId]) {
                agentDataCache[agentId].completedByAgent = jobs;
            }
            return jobs;
        }
    } catch (error) {
        console.error('Failed to load agent completed jobs:', error);
    }
    return [];
}

async function loadAgentMonitoring(agentId, offset = 0, limit = 20) {
    try {
        const response = await fetch(`/api/agents/${agentId}/monitoring?offset=${offset}&limit=${limit}`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const data = await response.json();
            // Update cache
            if (agentDataCache[agentId]) {
                agentDataCache[agentId].monitoring = data;
            }
            return data;
        }
    } catch (error) {
        console.error('Failed to load agent monitoring:', error);
    }
    return null;
}

// ============== Job Categories ==============

function isContainerJob(job) {
    // Agent inbox jobs have agent_id set
    if (job.agent_id) return true;
    // System containers have system:agents, system:projects, or system:system tags
    const tags = job.tags || [];
    if (tags.includes('system:agents') || tags.includes('system:projects') || tags.includes('system:system')) return true;
    return false;
}

function isAgentOrSystemJob(job) {
    // Check if job itself is an agent inbox or has system:agents/system:system tags
    if (job.agent_id) return true;
    const tags = job.tags || [];
    if (tags.includes('system:agents') || tags.includes('system:system')) return true;
    if (tags.includes('agent-inbox')) return true;
    return false;
}

function hasAgentOrSystemAncestor(job, allJobs) {
    // Walk up the parent chain to check if any ancestor is under Agents or System
    // allJobs should include both active and completed jobs for full traversal
    let parentId = job.parent_id;
    while (parentId) {
        const parent = allJobs.find(j => j.id === parentId);
        if (!parent) break;
        if (isAgentOrSystemJob(parent)) return true;
        parentId = parent.parent_id;
    }
    return false;
}

function isProjectsDescendant(job, allJobs) {
    // A job is a Projects descendant if it's NOT under Agents or System containers
    // This includes jobs with no container parent (user-created root jobs)
    if (isAgentOrSystemJob(job)) return false;
    if (hasAgentOrSystemAncestor(job, allJobs)) return false;
    return true;
}

function getJobCategory(job) {
    // Container jobs don't belong in timeline categories
    if (isContainerJob(job)) return 'container';

    const today = new Date().toISOString().split('T')[0];
    const dueDate = job.due_date;
    const someday = job.someday;

    if (job.status === 'completed') return 'logbook';
    if (dueDate && dueDate <= today) return 'today';  // Includes past due
    if (dueDate && dueDate > today) return 'upcoming';
    if (!dueDate && someday) return 'someday';
    return 'anytime';
}

// ============== Job Hierarchy Helpers ==============

function getJobById(id) {
    return jobsData.find(j => j.id === id);
}

function getTimelineContext() {
    // Look through navigation history to find the timeline context we came from
    // Returns 'today', 'upcoming', 'anytime', 'someday', or null if not in timeline context
    const timelineViews = ['today', 'upcoming', 'anytime', 'someday'];

    // Check current view first
    if (timelineViews.includes(focusView)) {
        return focusView;
    }

    // Look back through history (most recent first)
    for (let i = focusViewHistory.length - 1; i >= 0; i--) {
        if (timelineViews.includes(focusViewHistory[i])) {
            return focusViewHistory[i];
        }
    }

    return null; // Not in a timeline context (e.g., navigated from Projects)
}

function getChildJobsForContext(parentId) {
    // Get child jobs filtered by timeline context (if any)
    const allChildren = jobsData.filter(j => j.parent_id === parentId);
    const context = getTimelineContext();

    if (!context) {
        // No timeline context - show all children
        return allChildren;
    }

    // Filter to only children (or descendants) that match the timeline context
    return allChildren.filter(child => {
        // Check if this child or any of its descendants match the context
        if (child.status !== 'completed' && getJobCategory(child) === context) {
            return true;
        }
        // Check descendants
        const descendants = getAllDescendants(child.id);
        return descendants.some(d => d.status !== 'completed' && getJobCategory(d) === context);
    });
}

function getDescendantCountForContext(jobId) {
    // Count ALL descendants (not just direct children) that match the timeline context
    const context = getTimelineContext();
    const allDescendants = getAllDescendants(jobId);

    if (!context) {
        // No timeline context - count all descendants
        return allDescendants.length;
    }

    // Count only descendants that match the context and are incomplete
    return allDescendants.filter(d =>
        d.status !== 'completed' && getJobCategory(d) === context
    ).length;
}

function hasCompletedAncestor(job) {
    // Check if any ancestor of this job is completed
    let parentId = job.parent_id;
    while (parentId) {
        // Check if parent is in completed jobs
        const completedParent = completedJobsData.find(j => j.id === parentId);
        if (completedParent) return true;

        // Check if parent is in active jobs and continue walking up
        const activeParent = getJobById(parentId);
        if (!activeParent) break; // Parent not found anywhere
        if (isContainerJob(activeParent)) break; // Stop at containers
        parentId = activeParent.parent_id;
    }
    return false;
}

function getRootAncestor(job) {
    // Walk up the parent chain to find the root job
    // Stop at containers (system jobs, agent inboxes) - job under container is the effective root
    let current = job;
    while (current.parent_id) {
        const parent = getJobById(current.parent_id);
        if (!parent) break; // Parent not in active jobs, current is effectively root
        if (isContainerJob(parent)) break; // Don't walk into containers
        current = parent;
    }
    return current;
}

function getAllDescendants(jobId) {
    // Get all descendants recursively (children, grandchildren, etc.)
    const descendants = [];
    const children = jobsData.filter(j => j.parent_id === jobId);

    for (const child of children) {
        descendants.push(child);
        descendants.push(...getAllDescendants(child.id));
    }

    return descendants;
}

function getJobWithDescendants(jobId) {
    // Get a job and all its descendants
    const job = getJobById(jobId);
    if (!job) return [];
    return [job, ...getAllDescendants(jobId)];
}

function hasMatchingIncompleteDescendant(job, category) {
    // Check if this job or any of its descendants:
    // 1. Matches the category
    // 2. Is not completed

    // Check the job itself (only if it's a leaf or has the category set)
    if (job.status !== 'completed' && getJobCategory(job) === category) {
        return true;
    }

    // Check all descendants
    const descendants = getAllDescendants(job.id);
    for (const descendant of descendants) {
        if (descendant.status !== 'completed' && getJobCategory(descendant) === category) {
            return true;
        }
    }

    return false;
}

function getRootJobsForCategory(category) {
    // Get root jobs that have at least one incomplete descendant matching the category
    // A "root" job is one with no parent, or whose parent is not in jobsData (e.g., system container)

    const rootJobs = new Map(); // Use Map to deduplicate by job ID

    for (const job of jobsData) {
        // Skip containers
        if (isContainerJob(job)) continue;

        // Skip jobs with completed ancestors (orphaned children of completed projects)
        if (hasCompletedAncestor(job)) continue;

        // Check if this job matches the category and is incomplete
        if (job.status !== 'completed' && getJobCategory(job) === category) {
            // Find its root ancestor
            const root = getRootAncestor(job);

            // Skip if root is a container (system jobs, agent inboxes)
            if (isContainerJob(root)) continue;

            rootJobs.set(root.id, root);
        }
    }

    return Array.from(rootJobs.values());
}

// ============== Date Formatting ==============

function formatFriendlyDueDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const nextWeek = new Date(today);
    nextWeek.setDate(nextWeek.getDate() + 7);

    if (date.getTime() === today.getTime()) {
        return 'Today';
    } else if (date.getTime() === tomorrow.getTime()) {
        return 'Tomorrow';
    } else if (date < nextWeek) {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function formatFriendlyPastDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    date.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    if (date.getTime() === today.getTime()) {
        return 'Today';
    } else if (date.getTime() === yesterday.getTime()) {
        return 'Yesterday';
    } else if (date > lastWeek) {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function getFocusCounts() {
    // Temporal filters (today, upcoming, someday): count ALL matching jobs
    // Anytime: count root jobs only
    const counts = { today: 0, upcoming: 0, anytime: 0, someday: 0 };

    jobsData.forEach(job => {
        // Skip containers
        if (isContainerJob(job)) return;
        // Skip completed
        if (job.status === 'completed') return;
        // Skip jobs with completed ancestors (orphaned children)
        if (hasCompletedAncestor(job)) return;

        const category = getJobCategory(job);
        // For temporal categories, count all jobs
        if (category === 'today' || category === 'upcoming' || category === 'someday') {
            counts[category]++;
        }
    });

    // For anytime, count root jobs only
    counts.anytime = getRootJobsForCategory('anytime').length;

    return counts;
}

// ============== Memory Data Loading ==============

// Cache for memory pagination state
const memoryPageState = {};
const longTermMemoryCache = {};

async function loadShortTermMemory(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/memory/short-term`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const items = await response.json();
            // Initialize pagination state
            if (!memoryPageState[agentId]) {
                memoryPageState[agentId] = { page: 0, pageSize: 10 };
            }
            return items;
        }
    } catch (error) {
        console.error('Failed to load short-term memory:', error);
    }
    return [];
}

async function loadMemoryItem(agentId, entryId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/memory/short-term/${entryId}`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to load memory item:', error);
    }
    return null;
}

async function loadLongTermMemoryDates(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/memory/long-term/dates`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const dates = await response.json();
            // Cache the dates list
            if (!longTermMemoryCache[agentId]) {
                longTermMemoryCache[agentId] = {};
            }
            longTermMemoryCache[agentId].dates = dates;
            return dates;
        }
    } catch (error) {
        console.error('Failed to load long-term memory dates:', error);
    }
    return [];
}

async function loadLongTermMemoryContent(agentId, date) {
    try {
        const response = await fetch(`/api/agents/${agentId}/memory/long-term?date=${date}`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const data = await response.json();
            // Cache the content
            if (!longTermMemoryCache[agentId]) {
                longTermMemoryCache[agentId] = {};
            }
            longTermMemoryCache[agentId][date] = data;
            return data;
        }
    } catch (error) {
        console.error('Failed to load long-term memory content:', error);
    }
    return null;
}

async function loadLongTermMemoryWithPreviews(agentId) {
    try {
        // First get the list of dates
        const datesResponse = await fetch(`/api/agents/${agentId}/memory/long-term/dates`, {
            credentials: 'same-origin'
        });
        if (!datesResponse.ok) return [];

        const dates = await datesResponse.json();
        if (!dates || dates.length === 0) return [];

        // Load content for each date to get previews
        const entries = await Promise.all(dates.map(async (date) => {
            try {
                const contentResponse = await fetch(`/api/agents/${agentId}/memory/long-term?date=${date}`, {
                    credentials: 'same-origin'
                });
                if (contentResponse.ok) {
                    const data = await contentResponse.json();
                    const content = data.content || '';
                    // Get first 100 chars as preview, strip markdown
                    const preview = content
                        .replace(/^#+\s+/gm, '')  // Remove headers
                        .replace(/\*\*/g, '')     // Remove bold
                        .replace(/\n+/g, ' ')     // Replace newlines with spaces
                        .trim()
                        .substring(0, 100);
                    return {
                        date: date,
                        preview: preview + (content.length > 100 ? '...' : ''),
                        content: content
                    };
                }
            } catch (error) {
                console.error(`Failed to load content for ${date}:`, error);
            }
            return { date: date, preview: '', content: '' };
        }));

        return entries;
    } catch (error) {
        console.error('Failed to load long-term memory with previews:', error);
    }
    return [];
}

async function loadReflectionLogs(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/logs/reflection?days=7`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to load reflection logs:', error);
    }
    return { agent_id: agentId, logs: [] };
}

async function loadJobTrace(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/trace`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to load job trace:', error);
    }
    return null;
}

// ============== Memory Actions ==============

async function addMemoryItem(agentId) {
    const description = prompt('Memory description:');
    if (!description) return;

    const type = prompt('Type (person, place, thing, goal, concern, idea, learning, behavior):') || 'thing';

    try {
        const response = await fetch(`/api/agents/${agentId}/memory/short-term`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({
                short_description: description,
                type: type
            })
        });

        if (response.ok) {
            await refreshMemorySection(agentId, 'short-term-memory');
        }
    } catch (error) {
        console.error('Failed to add memory item:', error);
    }
}

async function deleteMemoryItem(agentId, entryId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/memory/short-term/${entryId}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });

        if (response.ok) {
            await refreshMemorySection(agentId, 'short-term-memory');
        }
    } catch (error) {
        console.error('Failed to delete memory item:', error);
    }
}

async function refreshMemorySection(agentId, sectionType) {
    // Find and refresh the memory section content
    const sections = document.querySelectorAll('.job-section');
    for (const section of sections) {
        const header = section.querySelector('.job-section-header');
        if (header && header.textContent.includes('Short-term Memory') && sectionType === 'short-term-memory') {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('collapsible-content')) {
                content.dataset.loaded = 'false';
                const items = await loadShortTermMemory(agentId);
                content.innerHTML = renderShortTermMemoryContent(items, agentId);
                content.dataset.loaded = 'true';
            }
            break;
        }
    }
}

function pageMemory(agentId, direction) {
    if (!memoryPageState[agentId]) {
        memoryPageState[agentId] = { page: 0, pageSize: 10 };
    }

    const state = memoryPageState[agentId];
    if (direction === 'next') {
        state.page++;
    } else if (direction === 'prev' && state.page > 0) {
        state.page--;
    }

    // Re-render the section
    refreshMemorySection(agentId, 'short-term-memory');
}

async function loadLongTermMemoryDate(agentId, date) {
    const content = await loadLongTermMemoryContent(agentId, date);
    const dates = longTermMemoryCache[agentId]?.dates || [];

    // Find and update the long-term memory section
    const sections = document.querySelectorAll('.job-section');
    for (const section of sections) {
        const header = section.querySelector('.job-section-header');
        if (header && header.textContent.includes('Long-term Memory')) {
            const contentDiv = header.nextElementSibling;
            if (contentDiv && contentDiv.classList.contains('collapsible-content')) {
                contentDiv.innerHTML = renderLongTermMemoryContent(dates, date, content, agentId);
            }
            break;
        }
    }
}

// ============== Trigger Actions ==============

async function triggerReflection(agentId, phase) {
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = 'Triggering...';
    button.disabled = true;

    try {
        const response = await fetch(`/api/agents/${agentId}/reflection/trigger`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ phase: phase })
        });

        if (response.ok) {
            const result = await response.json();

            // Set up active execution for SSE tracking
            activeExecution = {
                executionId: result.execution_id,
                agentId: agentId,
                phase: phase,
                step: 'triggered',
                message: 'Starting...'
            };
            updateExecutionUI();

            button.textContent = originalText;
            button.disabled = false;
        } else {
            button.textContent = 'Failed';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 2000);
        }
    } catch (error) {
        console.error('Failed to trigger reflection:', error);
        button.textContent = originalText;
        button.disabled = false;
    }
}

async function triggerExploration(agentId) {
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = 'Triggering...';
    button.disabled = true;

    try {
        const response = await fetch(`/api/agents/${agentId}/exploration/trigger`, {
            method: 'POST',
            credentials: 'same-origin'
        });

        if (response.ok) {
            const result = await response.json();

            // Set up active execution for SSE tracking
            activeExecution = {
                executionId: result.execution_id,
                agentId: agentId,
                phase: 'exploration',
                step: 'triggered',
                message: 'Starting exploration...'
            };
            updateExecutionUI();

            button.textContent = originalText;
            button.disabled = false;
        } else {
            button.textContent = 'Failed';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 2000);
        }
    } catch (error) {
        console.error('Failed to trigger exploration:', error);
        button.textContent = originalText;
        button.disabled = false;
    }
}

async function refreshReflectionSection(agentId) {
    const sections = document.querySelectorAll('.job-section');
    for (const section of sections) {
        const header = section.querySelector('.job-section-header');
        if (header && header.textContent.includes('Reflection')) {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('collapsible-content') && content.classList.contains('open')) {
                const data = await loadReflectionLogs(agentId);
                content.innerHTML = renderReflectionContent(data, agentId);
            }
            break;
        }
    }
}
