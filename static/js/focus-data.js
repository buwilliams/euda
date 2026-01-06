// Euno - Focus Data Loading & Utilities

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

// ============== Job Categories ==============

function isContainerJob(job) {
    // Agent inbox jobs have agent_id set
    if (job.agent_id) return true;
    // System containers have system:agents or system:projects tags
    const tags = job.tags || [];
    if (tags.includes('system:agents') || tags.includes('system:projects')) return true;
    return false;
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
