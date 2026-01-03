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
    if (dueDate === today) return 'today';
    if (dueDate && dueDate > today) return 'upcoming';
    if (!dueDate && someday) return 'someday';
    return 'anytime';
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
    const counts = { today: 0, upcoming: 0, anytime: 0, someday: 0, toplevel: 0 };

    jobsData.forEach(job => {
        const category = getJobCategory(job);
        counts[category]++;
        if (!job.parent_id) {
            counts.toplevel++;
        }
    });

    return counts;
}
