// Euno - Focus Data Loading & Utilities

// ============== Agent Pause Status ==============

let agentPauseStatus = {};  // Cache: { agentId: { isPaused, reason, timestamp, tokenUsage, budgetReset } }

async function loadAgentPauseStatus(agentId) {
    // Default state - also used as fallback on error
    const defaultState = {
        state: 'enabled',
        isPaused: false,
        isDisabled: false,
        isEnabled: true,
        reason: null,
        timestamp: null,
        tokenUsage: null,
        budgetReset: null
    };

    try {
        const response = await fetch(`/api/agents/${agentId}/state`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const data = await response.json();
            const pauseInfo = data.pause_info || {};
            agentPauseStatus[agentId] = {
                state: data.state || 'enabled',
                isPaused: data.state === 'paused',
                isDisabled: data.state === 'disabled',
                isEnabled: data.state === 'enabled',
                reason: pauseInfo.reason || null,
                timestamp: pauseInfo.timestamp || null,
                tokenUsage: data.token_usage || null,
                budgetReset: data.budget_reset || null
            };
            return agentPauseStatus[agentId];
        }
    } catch (error) {
        console.error('Failed to load agent pause status:', error);
    }
    // Always set cache to prevent infinite reload loop
    agentPauseStatus[agentId] = defaultState;
    return defaultState;
}

async function setAgentState(agentId, state, reason = null) {
    try {
        const body = { state };
        if (reason) body.reason = reason;

        const response = await fetch(`/api/agents/${agentId}/state`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(body)
        });
        if (response.ok) {
            // Clear cache entry to force reload
            delete agentPauseStatus[agentId];
            // Clear agent data cache to refresh config
            delete agentDataCache[agentId];
            // Clear agents cache to refresh list
            agentsCache = null;
            // Re-render the view
            renderFocusTab();
            return true;
        }
    } catch (error) {
        console.error('Failed to set agent state:', error);
    }
    return false;
}

async function resumeAgent(agentId) {
    return setAgentState(agentId, 'enabled');
}

async function pauseAgent(agentId) {
    return setAgentState(agentId, 'paused', 'Manual pause');
}

async function enableAgent(agentId) {
    return setAgentState(agentId, 'enabled');
}

async function disableAgent(agentId) {
    return setAgentState(agentId, 'disabled');
}

async function resetAgentTokenUsage(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/reset-usage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin'
        });
        if (response.ok) {
            // Clear cache entry to force reload
            delete agentPauseStatus[agentId];
            // Re-render the view
            renderFocusTab();
            return true;
        }
    } catch (error) {
        console.error('Failed to reset agent token usage:', error);
    }
    return false;
}

function handleReflectionProgress(data) {
    // Progress tracking removed - consolidation topic in topics list serves as indicator
}

function handleReflectionComplete(data) {
    // Invalidate caches when consolidation completes
    if (data.agent_id) {
        // Clear agent data cache (identity, config) to force reload
        delete agentDataCache[data.agent_id];

        // Clear memory caches for this agent
        if (typeof memoryListCache !== 'undefined') {
            delete memoryListCache[data.agent_id];
        }
        if (typeof longTermMemoryListCache !== 'undefined') {
            delete longTermMemoryListCache[data.agent_id];
        }
        if (typeof longTermMemoryDetailCache !== 'undefined') {
            // Clear all long-term memory detail entries for this agent
            for (const key of Object.keys(longTermMemoryDetailCache)) {
                if (key.startsWith(data.agent_id + '-')) {
                    delete longTermMemoryDetailCache[key];
                }
            }
        }

        // Clear monitoring cache and loading flag to force reload
        delete monitoringCache[data.agent_id];
        if (typeof monitoringLoading !== 'undefined') {
            delete monitoringLoading[data.agent_id];
        }
        // Reset pagination to first page
        if (typeof monitoringPagination !== 'undefined') {
            monitoringPagination[data.agent_id] = { offset: 0, limit: 20 };
        }

        // Re-render if viewing any view related to this agent
        if (focusView) {
            const agentId = data.agent_id;
            // Check if viewing agent's topic detail page
            const agentTopic = topicsData.find(j => j.agent_id === agentId);
            if ((agentTopic && focusView === `topic-${agentTopic.id}`) ||
                focusView === `identity-${agentId}` ||
                focusView === `config-${agentId}` ||
                focusView === `monitoring-${agentId}` ||
                focusView === `memory-list-${agentId}` ||
                focusView.startsWith(`memory-item-${agentId}-`) ||
                focusView === `long-term-memory-${agentId}` ||
                focusView.startsWith(`long-term-memory-detail-${agentId}-`)) {
                renderFocusTab();
            }
        }
    }
}

function handleReflectionError(data) {
    // Error handling via topic status - topic will show error status in topics list
    console.error('Consolidation error:', data.error);
}

// ============== Data Loading ==============

async function loadTopicsData() {
    try {
        const fetchOpts = { credentials: 'same-origin' };
        const [activeRes, completedRes] = await Promise.all([
            fetch('/api/topics?status=todo', fetchOpts),
            fetch('/api/topics?status=done', fetchOpts)
        ]);

        if (activeRes.status === 401 || completedRes.status === 401) {
            console.error('Focus tab: Authentication required');
            window.location.reload();
            return;
        }

        const activeTopics = await activeRes.json();
        const completedTopics = await completedRes.json();

        // Active topics (not completed, not archived)
        topicsData = Array.isArray(activeTopics) ? activeTopics : [];
        // Recently completed topics (limit to 20)
        completedTopicsData = Array.isArray(completedTopics) ? completedTopics.slice(0, 20) : [];

        renderFocusTab();
        updateTopicsBadge();
        // Load daily quote when showing the focus menu
        if (focusView === 'menu') {
            loadDailyQuote();
        }
    } catch (error) {
        console.error('Failed to load topics data:', error);
    }
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
    // Always set cache to prevent infinite reload loop
    agentsCache = [];
    return [];
}

async function loadAgentData(agentId) {
    try {
        const [identityRes, configRes] = await Promise.all([
            fetch(`/api/agents/${agentId}/identity`, { credentials: 'same-origin' }),
            fetch(`/api/agents/${agentId}/config`, { credentials: 'same-origin' })
        ]);

        const data = { agentId };

        if (identityRes.ok) {
            const identityData = await identityRes.json();
            data.identity = identityData.identity;
        }

        if (configRes.ok) {
            data.config = await configRes.json();
        }

        agentDataCache[agentId] = data;
        return data;
    } catch (error) {
        console.error('Failed to load agent data:', error);
    }
    // Always set cache to prevent infinite reload loop
    agentDataCache[agentId] = { agentId };
    return null;
}

async function saveAgentIdentity(agentId, identity) {
    try {
        const response = await fetch(`/api/agents/${agentId}/identity`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: identity })
        });

        if (response.ok) {
            // Update cache
            if (agentDataCache[agentId]) {
                agentDataCache[agentId].identity = identity;
            }
            return true;
        }
    } catch (error) {
        console.error('Failed to save agent identity:', error);
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

async function loadAgentCompletedTopics(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/completed-topics`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const topics = await response.json();
            // Update cache
            if (agentDataCache[agentId]) {
                agentDataCache[agentId].completedByAgent = topics;
            }
            return topics;
        }
    } catch (error) {
        console.error('Failed to load agent completed topics:', error);
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

// ============== Topic Categories ==============

function isContainerTopic(topic) {
    // Agent inbox topics have agent_id set
    if (topic.agent_id) return true;
    // System containers have system:agents or system:projects tags
    const tags = topic.tags || [];
    if (tags.includes('system:agents') || tags.includes('system:projects')) return true;
    return false;
}

function isAgentOrSystemTopic(topic) {
    // Check if topic itself is an agent inbox or has system:agents tags
    if (topic.agent_id) return true;
    const tags = topic.tags || [];
    if (tags.includes('system:agents')) return true;
    if (tags.includes('agent-inbox')) return true;
    return false;
}

function hasAgentOrSystemAncestor(topic, allTopics) {
    // Walk up the parent chain to check if any ancestor is under Agents or System
    // allTopics should include both active and completed topics for full traversal
    let parentId = topic.parent_id;
    while (parentId) {
        const parent = allTopics.find(j => j.id === parentId);
        if (!parent) break;
        if (isAgentOrSystemTopic(parent)) return true;
        parentId = parent.parent_id;
    }
    return false;
}

function isProjectsDescendant(topic, allTopics) {
    // A topic is a Projects descendant if it's NOT under Agents or System containers
    // This includes topics with no container parent (user-created root topics)
    if (isAgentOrSystemTopic(topic)) return false;
    if (hasAgentOrSystemAncestor(topic, allTopics)) return false;
    return true;
}

function getTopicCategory(topic) {
    // Container topics don't belong in timeline categories
    if (isContainerTopic(topic)) return 'container';

    const today = getLocalDateString();
    const dueDate = topic.due_date;
    const someday = topic.someday;

    if (topic.status === 'done') return 'logbook';
    if (dueDate && dueDate <= today) return 'today';  // Includes past due
    if (dueDate && dueDate > today) return 'upcoming';
    if (!dueDate && someday) return 'someday';
    return 'anytime';
}

// ============== Topic Hierarchy Helpers ==============

function getTopicById(id) {
    // Use allTopicsData to find topics regardless of status
    return allTopicsData.find(j => j.id === id);
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

function getChildTopicsForContext(parentId) {
    // Get child topics filtered by timeline context (if any)
    const allChildren = topicsData.filter(j => j.parent_id === parentId);
    const context = getTimelineContext();

    if (!context) {
        // No timeline context - show all children
        return allChildren;
    }

    // Filter to only children (or descendants) that match the timeline context
    return allChildren.filter(child => {
        // Check if this child or any of its descendants match the context
        if (child.status !== 'done' && getTopicCategory(child) === context) {
            return true;
        }
        // Check descendants
        const descendants = getAllDescendants(child.id);
        return descendants.some(d => d.status !== 'done' && getTopicCategory(d) === context);
    });
}

function getAllChildTopicsSorted(parentId) {
    // Get all child topics (including archived, error, etc.) from allTopicsData
    // Sort by status priority: working > todo > error > done > archived, then by created_at desc
    const statusPriority = {
        'working': 0,
        'todo': 1,
        'error': 2,
        'done': 3,
        'archived': 4
    };

    return allTopicsData
        .filter(j => j.parent_id === parentId)
        .sort((a, b) => {
            const aPriority = statusPriority[a.status] ?? 5;
            const bPriority = statusPriority[b.status] ?? 5;
            if (aPriority !== bPriority) {
                return aPriority - bPriority;
            }
            // Same status - sort by created_at descending
            return (b.created_at || '').localeCompare(a.created_at || '');
        });
}

function getDescendantCountForContext(topicId) {
    // Count ALL descendants (not just direct children) that match the timeline context
    const context = getTimelineContext();
    const allDescendants = getAllDescendants(topicId);

    if (!context) {
        // No timeline context - count all descendants
        return allDescendants.length;
    }

    // Count only descendants that match the context and are incomplete
    return allDescendants.filter(d =>
        d.status !== 'done' && getTopicCategory(d) === context
    ).length;
}

function hasCompletedAncestor(topic) {
    // Check if any ancestor of this topic is completed
    let parentId = topic.parent_id;
    while (parentId) {
        // Check if parent is in completed topics
        const completedParent = completedTopicsData.find(j => j.id === parentId);
        if (completedParent) return true;

        // Check if parent is in active topics and continue walking up
        const activeParent = getTopicById(parentId);
        if (!activeParent) break; // Parent not found anywhere
        if (isContainerTopic(activeParent)) break; // Stop at containers
        parentId = activeParent.parent_id;
    }
    return false;
}

function getRootAncestor(topic) {
    // Walk up the parent chain to find the root topic
    // Stop at containers (system topics, agent inboxes) - topic under container is the effective root
    let current = topic;
    while (current.parent_id) {
        const parent = getTopicById(current.parent_id);
        if (!parent) break; // Parent not in active topics, current is effectively root
        if (isContainerTopic(parent)) break; // Don't walk into containers
        current = parent;
    }
    return current;
}

function getAllDescendants(topicId) {
    // Get all descendants recursively (children, grandchildren, etc.)
    const descendants = [];
    const children = topicsData.filter(j => j.parent_id === topicId);

    for (const child of children) {
        descendants.push(child);
        descendants.push(...getAllDescendants(child.id));
    }

    return descendants;
}

function getTopicWithDescendants(topicId) {
    // Get a topic and all its descendants
    const topic = getTopicById(topicId);
    if (!topic) return [];
    return [topic, ...getAllDescendants(topicId)];
}

function hasMatchingIncompleteDescendant(topic, category) {
    // Check if this topic or any of its descendants:
    // 1. Matches the category
    // 2. Is not completed

    // Check the topic itself (only if it's a leaf or has the category set)
    if (topic.status !== 'done' && getTopicCategory(topic) === category) {
        return true;
    }

    // Check all descendants
    const descendants = getAllDescendants(topic.id);
    for (const descendant of descendants) {
        if (descendant.status !== 'done' && getTopicCategory(descendant) === category) {
            return true;
        }
    }

    return false;
}

function getRootTopicsForCategory(category) {
    // Get root topics that have at least one incomplete descendant matching the category
    // A "root" topic is one with no parent, or whose parent is not in topicsData (e.g., system container)

    const rootTopics = new Map(); // Use Map to deduplicate by topic ID

    for (const topic of topicsData) {
        // Skip containers
        if (isContainerTopic(topic)) continue;

        // Skip topics with completed ancestors (orphaned children of completed projects)
        if (hasCompletedAncestor(topic)) continue;

        // Check if this topic matches the category and is incomplete
        if (topic.status !== 'done' && getTopicCategory(topic) === category) {
            // Find its root ancestor
            const root = getRootAncestor(topic);

            // Skip if root is a container (system topics, agent inboxes)
            if (isContainerTopic(root)) continue;

            rootTopics.set(root.id, root);
        }
    }

    return Array.from(rootTopics.values());
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
    // Temporal filters (today, upcoming, someday): count ALL matching topics
    // Anytime: count root topics only
    const counts = { today: 0, upcoming: 0, anytime: 0, someday: 0 };

    topicsData.forEach(topic => {
        // Skip containers
        if (isContainerTopic(topic)) return;
        // Skip completed
        if (topic.status === 'done') return;
        // Skip topics with completed ancestors (orphaned children)
        if (hasCompletedAncestor(topic)) return;

        const category = getTopicCategory(topic);
        // For temporal categories, count all topics
        if (category === 'today' || category === 'upcoming' || category === 'someday') {
            counts[category]++;
        }
    });

    // For anytime, count root topics only
    counts.anytime = getRootTopicsForCategory('anytime').length;

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

async function loadConsolidationLogs(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/logs/consolidation?days=7`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to load consolidation logs:', error);
    }
    return { agent_id: agentId, logs: [] };
}

async function loadTopicTrace(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/trace`, {
            credentials: 'same-origin'
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to load topic trace:', error);
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
    const sections = document.querySelectorAll('.topic-section');
    for (const section of sections) {
        const header = section.querySelector('.topic-section-header');
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
    const sections = document.querySelectorAll('.topic-section');
    for (const section of sections) {
        const header = section.querySelector('.topic-section-header');
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
            // Topic created - SSE will update the topics list which will show the topic
            // and disable the button via the topic-based check
            button.textContent = originalText;
            button.disabled = true; // Keep disabled until topics update via SSE
        } else {
            button.textContent = 'Failed';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 2000);
        }
    } catch (error) {
        console.error('Failed to trigger consolidation:', error);
        button.textContent = originalText;
        button.disabled = false;
    }
}

async function refreshReflectionSection(agentId) {
    const sections = document.querySelectorAll('.topic-section');
    for (const section of sections) {
        const header = section.querySelector('.topic-section-header');
        if (header && header.textContent.includes('Reflection')) {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('collapsible-content') && content.classList.contains('open')) {
                const data = await loadConsolidationLogs(agentId);
                content.innerHTML = renderReflectionContent(data, agentId);
            }
            break;
        }
    }
}

// ============== Topic State Functions ==============

async function setTopicStatus(topicId, status) {
    try {
        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ status })
        });
        if (response.ok) {
            await loadTopicsData();
            return true;
        }
    } catch (error) {
        console.error('Failed to set topic status:', error);
    }
    return false;
}

async function reassignTopic(topicId, agentId) {
    try {
        // Unassign current assignee if different
        const topic = topicsData.find(j => j.id === topicId) || completedTopicsData.find(j => j.id === topicId);
        if (topic && topic.assignee && topic.assignee !== agentId) {
            await fetch(`/api/topics/${topicId}/unassign`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ agent_id: topic.assignee })
            });
        }

        // Assign the new agent
        const assignResponse = await fetch(`/api/topics/${topicId}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ agent_id: agentId })
        });

        if (!assignResponse.ok) {
            console.error('Failed to assign agent');
            return false;
        }

        // Set status to todo
        const statusResponse = await fetch(`/api/topics/${topicId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ status: 'todo' })
        });

        if (statusResponse.ok) {
            await loadTopicsData();
            return true;
        }
    } catch (error) {
        console.error('Failed to reassign topic:', error);
    }
    return false;
}
