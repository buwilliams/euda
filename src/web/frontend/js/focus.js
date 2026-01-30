// Euno - Focus Tab Core (State, Icons, Navigation)

// ============== Date Utilities ==============

function getLocalDateString(date = null) {
    // Get date in YYYY-MM-DD format using local timezone
    const d = date || new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// ============== State ==============

let topicsData = [];           // All active topics
let completedTopicsData = [];  // Recently completed topics
let allTopicsData = [];        // All topics including archived (for detail views)
let topicAssetsCache = {};     // Cache of assets per topic
let recentAssetsCache = null;  // Cache of recent assets across all topics
let editingTopicField = null;  // Which field is being edited: {topicId, field}
let currentAssetData = null; // Currently viewed asset
let editingAssetFilename = null; // Track if we're editing an asset
let agentsCache = null;      // Cache of available agents
let agentDataCache = {};     // Cache of agent identity and config
let isViewAnimating = false; // Track if view animation is in progress
let pendingRender = false;   // Track if a render is pending after animation

// ============== SSE Partial Updates ==============

function applyTopicsUpdateToFocusView(prevAllTopics, nextAllTopics) {
    const container = document.getElementById('focus-content');
    if (!container || typeof focusView === 'undefined') return false;

    // Timeline views: update only the list content to avoid full re-render flicker
    if (focusView === 'today' || focusView === 'upcoming' || focusView === 'anytime' || focusView === 'someday') {
        return patchTimelineViewList(container, focusView);
    }

    // Completed view: update only the list content
    if (focusView === 'completed') {
        return patchCompletedViewList(container);
    }

    // Topic detail view: avoid re-render if the active topic itself didn't change
    if (focusView.startsWith('topic-')) {
        const topicId = focusView.substring(6);
        const prev = (prevAllTopics || []).find(t => t.id === topicId);
        const next = (nextAllTopics || []).find(t => t.id === topicId);
        if (!next) return false; // topic removed, let full render show not found
        if (!prev || topicRecordChanged(prev, next)) return false;
        return true;
    }

    return false;
}

function patchTimelineViewList(container, category) {
    const contentEl = container.querySelector('.focus-view-content');
    if (!contentEl) return false;

    let topics = getRootTopicsForCategory(category);
    if (category === 'upcoming') {
        topics = topics.slice().sort((a, b) => {
            const dateA = a.due_date || '9999-12-31';
            const dateB = b.due_date || '9999-12-31';
            return dateA.localeCompare(dateB);
        });
    }

    if (topics.length === 0) {
        contentEl.innerHTML = '<div class="focus-empty">No topics</div>';
        return true;
    }

    contentEl.innerHTML = topics.map(topic => renderTopicCard(topic, isSwipeable(topic))).join('');
    return true;
}

function patchCompletedViewList(container) {
    const contentEl = container.querySelector('.focus-view-content');
    if (!contentEl) return false;

    const allTopics = [...topicsData, ...completedTopicsData];
    const projectsCompletedTopics = completedTopicsData.filter(j => isProjectsDescendant(j, allTopics));
    const completedTopicIds = new Set(projectsCompletedTopics.map(j => j.id));
    const rootCompletedTopics = projectsCompletedTopics.filter(j => !j.parent_id || !completedTopicIds.has(j.parent_id));

    if (rootCompletedTopics.length === 0) {
        contentEl.innerHTML = '<div class="focus-empty">No completed topics</div>';
        return true;
    }

    contentEl.innerHTML = rootCompletedTopics.map(topic => {
        const childCount = projectsCompletedTopics.filter(j => j.parent_id === topic.id).length;
        return renderCompletedTopicCard(topic, childCount, true);
    }).join('');
    return true;
}

function topicRecordChanged(prev, next) {
    if (!prev || !next) return true;
    const keys = [
        'name', 'status', 'due_date', 'someday', 'assignee', 'agent_id', 'description',
        'parent_id', 'completed_at', 'updated_at'
    ];
    for (const key of keys) {
        if ((prev[key] || null) !== (next[key] || null)) return true;
    }
    const prevTags = Array.isArray(prev.tags) ? prev.tags.join(',') : '';
    const nextTags = Array.isArray(next.tags) ? next.tags.join(',') : '';
    return prevTags !== nextTags;
}

// ============== Icons ==============

function icon(name, className = '') {
    const cls = className ? ` class="${className}"` : '';
    return `<img src="/web/icons/${name}.svg" alt="${name}"${cls}>`;
}

// ============== Focus Tab Navigation ==============

let focusSlideDirection = null;

function renderFocusTab() {
    const container = document.getElementById('focus-content');
    if (!container) return;

    // Remove loading skeleton on first render
    document.getElementById('skeleton-loading')?.remove();

    // Defer render if animation is in progress
    if (isViewAnimating) {
        pendingRender = true;
        return;
    }

    let content;
    if (focusView === 'menu') {
        content = renderFocusMenu();
    } else if (focusView === 'today') {
        content = renderTimelineView('today', 'Today');
    } else if (focusView === 'upcoming') {
        content = renderTimelineView('upcoming', 'Upcoming');
    } else if (focusView === 'anytime') {
        content = renderTimelineView('anytime', 'Anytime');
    } else if (focusView === 'someday') {
        content = renderTimelineView('someday', 'Someday');
    } else if (focusView === 'completed') {
        content = renderCompletedTopicsView();
    } else if (focusView === 'recent-assets') {
        content = renderRecentAssetsView();
    } else if (focusView.startsWith('assets-')) {
        // assets-{topicId} - list of assets for a topic
        const topicId = focusView.substring(7);
        content = renderAssetsListView(topicId);
    } else if (focusView.startsWith('asset-')) {
        // asset-{topicId}-{filename} where topicId is like "topic-xxxxxxxx"
        const rest = focusView.substring(6); // remove "asset-"
        // Topic IDs are "topic-" + 8 hex chars = 14 chars total
        const topicId = rest.substring(0, 14);
        const filename = rest.substring(15); // skip topicId + "-"
        content = renderAssetView(topicId, filename);
    } else if (focusView.startsWith('newtopic-')) {
        // newtopic-{topicId} - create new child topics
        const topicId = focusView.substring(9);
        content = renderNewTopicScreen(topicId);
    } else if (focusView.startsWith('attach-')) {
        // attach-{topicId} - attach assets to a topic
        const topicId = focusView.substring(7);
        content = renderAttachScreen(topicId);
    } else if (focusView.startsWith('topic-api-calls-')) {
        // topic-api-calls-{topicId} - API calls for a topic
        const topicId = focusView.substring(16);
        content = renderTopicApiCallsView(topicId);
    } else if (focusView.startsWith('topic-prompt-')) {
        // topic-prompt-{topicId}-{index} - specific API call detail
        const rest = focusView.substring(13);
        const dashIndex = rest.indexOf('-');
        const topicId = rest.substring(0, dashIndex);
        const promptIndex = rest.substring(dashIndex + 1);
        content = renderTopicPromptDetailView(topicId, promptIndex);
    } else if (focusView.startsWith('topic-')) {
        const topicId = focusView.substring(6);
        content = renderTopicDetailView(topicId);
    } else if (focusView.startsWith('completed-')) {
        const topicId = focusView.substring(10);
        content = renderCompletedTopicDetailView(topicId);
    } else if (focusView.startsWith('trace-')) {
        const topicId = focusView.substring(6);
        content = renderTopicTraceView(topicId);
    } else if (focusView.startsWith('memory-list-')) {
        const agentId = focusView.substring(12);
        content = renderMemoryListView(agentId);
    } else if (focusView.startsWith('memory-item-')) {
        // memory-item-{agentId}-{entryId}
        const rest = focusView.substring(12);
        const dashIndex = rest.indexOf('-');
        const agentId = rest.substring(0, dashIndex);
        const entryId = rest.substring(dashIndex + 1);
        content = renderMemoryItemView(agentId, entryId);
    } else if (focusView.startsWith('monitoring-')) {
        const agentId = focusView.substring(11);
        content = renderMonitoringView(agentId);
    } else if (focusView.startsWith('prompt-')) {
        // prompt-{agentId}-{index}
        const rest = focusView.substring(7);
        const dashIndex = rest.indexOf('-');
        const agentId = rest.substring(0, dashIndex);
        const promptIndex = rest.substring(dashIndex + 1);
        content = renderPromptDetailView(agentId, promptIndex);
    } else if (focusView.startsWith('long-term-memory-detail-')) {
        // long-term-memory-detail-{agentId}-{date}
        const rest = focusView.substring(24);
        const dashIndex = rest.indexOf('-');
        const agentId = rest.substring(0, dashIndex);
        const date = rest.substring(dashIndex + 1);
        content = renderLongTermMemoryDetailView(agentId, date);
    } else if (focusView.startsWith('long-term-memory-')) {
        const agentId = focusView.substring(17);
        content = renderLongTermMemoryListView(agentId);
    } else if (focusView.startsWith('identity-')) {
        const agentId = focusView.substring(9);
        content = renderIdentityView(agentId);
    } else if (focusView.startsWith('config-')) {
        const agentId = focusView.substring(7);
        content = renderConfigurationView(agentId);
    } else if (focusView.startsWith('rate-limits-')) {
        const agentId = focusView.substring(12);
        content = renderRateLimitEventsView(agentId);
    }

    if (focusSlideDirection && container.querySelector('.view-slide-container')) {
        animateViewTransition(container, content, focusSlideDirection);
        focusSlideDirection = null;
    } else {
        container.innerHTML = `<div class="view-slide-container current">${content}</div>`;
    }

    if (focusView === 'menu' && typeof maybeRenderDailyQuote === 'function') {
        if (isViewAnimating) {
            setTimeout(() => maybeRenderDailyQuote(), 320);
        } else {
            maybeRenderDailyQuote();
        }
    }
}

function animateViewTransition(container, newContent, direction) {
    const oldView = container.querySelector('.view-slide-container');
    if (!oldView) {
        container.innerHTML = `<div class="view-slide-container current">${newContent}</div>`;
        return;
    }

    isViewAnimating = true;

    const newView = document.createElement('div');
    newView.className = 'view-slide-container';
    newView.innerHTML = newContent;

    if (direction === 'forward') {
        newView.classList.add('slide-in-right');
    } else {
        newView.classList.add('slide-in-left');
    }

    container.appendChild(newView);
    newView.offsetHeight;

    if (direction === 'forward') {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-left');
    } else {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-right');
    }

    newView.classList.remove('slide-in-left', 'slide-in-right');
    newView.classList.add('current');

    setTimeout(() => {
        if (oldView.parentNode) {
            oldView.remove();
        }
        isViewAnimating = false;
        if (pendingRender) {
            pendingRender = false;
            renderFocusTab();
        }
    }, 300);
}

function navigateFocus(view) {
    focusViewHistory.push(focusView);
    focusView = view;
    focusSlideDirection = 'forward';

    // Invalidate assets cache when navigating to assets view to show fresh data
    if (view === 'recent-assets') {
        recentAssetsCache = null;
    }

    // Set topic context for chat input (context-aware routing)
    if (view.startsWith('topic-')) {
        const topicId = view.substring(6);
        if (typeof setTopicContext === 'function') {
            setTopicContext(topicId);
        }
    } else {
        if (typeof clearTopicContext === 'function') {
            clearTopicContext();
        }
    }

    renderFocusTab();
}

function navigateFocusBack() {
    if (focusViewHistory.length > 0) {
        focusView = focusViewHistory.pop();
    } else {
        focusView = 'menu';
    }
    focusSlideDirection = 'back';

    // Update topic context for chat input
    if (focusView.startsWith('topic-')) {
        const topicId = focusView.substring(6);
        if (typeof setTopicContext === 'function') {
            setTopicContext(topicId);
        }
    } else {
        if (typeof clearTopicContext === 'function') {
            clearTopicContext();
        }
    }

    // If returning to menu from a More menu screen, go back to the original tab
    if (focusView === 'menu' && moreMenuReturnTab) {
        const returnTab = moreMenuReturnTab;
        moreMenuReturnTab = null;
        switchTab(returnTab);
        return;
    }

    renderFocusTab();
}

// ============== Breadcrumbs ==============

// Get short display name for a view (used in breadcrumbs)
function getViewDisplayName(view) {
    // Timeline views
    if (view === 'menu') return 'Focus';
    if (view === 'today') return 'Today';
    if (view === 'upcoming') return 'Upcoming';
    if (view === 'anytime') return 'Anytime';
    if (view === 'someday') return 'Someday';
    if (view === 'completed') return 'Completed';

    // Topic views - get topic name from cache
    if (view.startsWith('topic-')) {
        const topicId = view.substring(6);
        const topic = allTopicsData.find(j => j.id === topicId);
        if (topic) {
            // Truncate long names for breadcrumbs
            const name = topic.name || 'Topic';
            return name.length > 20 ? name.substring(0, 18) + '...' : name;
        }
        return 'Topic';
    }

    // Completed topic views
    if (view.startsWith('completed-')) {
        const topicId = view.substring(10);
        const topic = completedTopicsData.find(j => j.id === topicId);
        if (topic) {
            const name = topic.name || 'Topic';
            return name.length > 20 ? name.substring(0, 18) + '...' : name;
        }
        return 'Completed';
    }

    // Agent-related views
    if (view.startsWith('identity-')) {
        return 'Identity';
    }
    if (view.startsWith('config-')) {
        return 'Config';
    }
    if (view.startsWith('memory-list-')) {
        return 'Memory';
    }
    if (view.startsWith('memory-item-')) {
        return 'Item';
    }
    if (view.startsWith('long-term-memory-detail-')) {
        return 'Entry';
    }
    if (view.startsWith('long-term-memory-')) {
        return 'Long-term';
    }
    if (view.startsWith('monitoring-')) {
        return 'Monitoring';
    }
    if (view.startsWith('prompt-')) {
        return 'Prompt';
    }
    if (view.startsWith('rate-limits-')) {
        return 'Incidents';
    }
    if (view.startsWith('topic-api-calls-')) {
        return 'API Calls';
    }
    if (view.startsWith('topic-prompt-')) {
        return 'Prompt';
    }
    if (view.startsWith('trace-')) {
        return 'Trace';
    }

    // Asset views
    if (view.startsWith('assets-')) {
        return 'Assets';
    }
    if (view.startsWith('asset-')) {
        const rest = view.substring(6);
        const filename = rest.substring(15); // skip topicId (14 chars) + "-"
        return filename.length > 15 ? filename.substring(0, 13) + '...' : filename;
    }

    // Child topic creation
    if (view.startsWith('newtopic-')) {
        return 'Add Topics';
    }
    if (view.startsWith('attach-')) {
        return 'Add Assets';
    }

    return 'View';
}

// Build breadcrumb path from navigation history
function getBreadcrumbPath() {
    const path = [];
    for (const view of focusViewHistory) {
        path.push(getViewDisplayName(view));
    }
    return path;
}

// Render just the breadcrumbs HTML (for adding to existing headers)
function renderBreadcrumbs() {
    const breadcrumbs = getBreadcrumbPath();
    if (breadcrumbs.length === 0) return '';
    const arrow = `<img src="/web/icons/chevron-right.svg" alt=">">`;
    const html = breadcrumbs.map(b => `<span>${b}</span>`).join(arrow);
    return `<div class="focus-view-breadcrumbs">${html}</div>`;
}

// Render view header with title and breadcrumbs
function renderViewHeader(title, options = {}) {
    const { iconName = null, iconHtml = null } = options;

    // Build the icon HTML
    let titleIconHtml = '';
    if (iconHtml) {
        titleIconHtml = iconHtml;
    } else if (iconName) {
        titleIconHtml = icon(iconName);
    }

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">${titleIconHtml}${title}</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
    `;
}

// ============== Quick Add (from plus button) ==============

// Get context for quick-add based on current focusView
function getQuickAddContext() {
    const today = getLocalDateString();

    // Only apply context when on Focus tab
    if (activeTab !== 'focus') {
        return { due_date: today, label: 'Today' };
    }

    // Menu or Today view - create topic for today
    if (focusView === 'menu' || focusView === 'today') {
        return { due_date: today, label: 'Today' };
    }

    // Upcoming view - create topic for tomorrow
    if (focusView === 'upcoming') {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        return { due_date: getLocalDateString(tomorrow), label: 'Upcoming' };
    }

    // Anytime view - no due date
    if (focusView === 'anytime') {
        return { due_date: null, label: 'Anytime' };
    }

    // Someday view - far future date (signals someday)
    if (focusView === 'someday') {
        return { due_date: '2099-12-31', label: 'Someday' };
    }

    // Topic detail view - create child topic
    if (focusView.startsWith('topic-')) {
        const topicId = focusView.substring(6);
        const topic = allTopicsData.find(j => j.id === topicId);
        if (topic) {
            return { parent_id: topicId, label: topic.name };
        }
    }

    // Default to today
    return { due_date: today, label: 'Today' };
}

// Quick add topic from chat input (called from plus button)
function quickAddFromInput() {
    const input = document.getElementById('context-input');
    if (!input) return;

    const name = input.value.trim();
    if (!name) {
        // Focus the input if empty
        input.focus();
        return;
    }

    const context = getQuickAddContext();
    const topicData = { name };

    if (context.parent_id) {
        topicData.parent_id = context.parent_id;
    }
    if (context.due_date) {
        topicData.due_date = context.due_date;
    }

    // Clear input immediately for snappy UX
    input.value = '';

    // Create topic in background (don't await)
    fetch('/api/topics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(topicData)
    }).then(response => {
        if (response.ok) {
            loadTopicsData().then(() => {
                // Refresh view if on Focus tab
                if (activeTab === 'focus') {
                    renderFocusTab();
                }
            });
        }
    }).catch(error => {
        console.error('Failed to create topic:', error);
    });

    // Switch to Focus tab immediately
    if (activeTab !== 'focus') {
        switchTab('focus');
    }
}
