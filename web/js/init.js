// Euno - Initialization, SSE, Drag & Drop

// ============== SSE ==============

let eventSource = null;
let reconnectAttempts = 0;

function connectSSE() {
    if (eventSource) eventSource.close();

    eventSource = new EventSource('/api/events');

    eventSource.addEventListener('init', (e) => {
        const data = JSON.parse(e.data);
        const allJobs = data.jobs || [];
        // Split jobs into active and completed (filter out archived)
        jobsData = allJobs.filter(j => j.status !== 'completed' && j.status !== 'archived');
        completedJobsData = allJobs.filter(j => j.status === 'completed')
            .sort((a, b) => (b.completed_at || '').localeCompare(a.completed_at || ''))
            .slice(0, 20);
        updateTasksBadge();
        if (activeTab === 'focus') {
            renderFocusTab();
        }
        reconnectAttempts = 0;
    });

    eventSource.addEventListener('jobs_update', (e) => {
        const data = JSON.parse(e.data);
        const allJobs = data.jobs || [];
        // Split jobs into active and completed (filter out archived)
        jobsData = allJobs.filter(j => j.status !== 'completed' && j.status !== 'archived');
        completedJobsData = allJobs.filter(j => j.status === 'completed')
            .sort((a, b) => (b.completed_at || '').localeCompare(a.completed_at || ''))
            .slice(0, 20);
        if (activeTab === 'focus') {
            renderFocusTab();
        }
        updateTasksBadge();
    });

    eventSource.addEventListener('ping', () => {});

    // Handle agent messages (proactive notifications from Curator, etc.)
    eventSource.addEventListener('agent_message', (e) => {
        const data = JSON.parse(e.data);
        // Add message to chat as if from the agent
        addInlineMessage(data.message, 'friend');
        // Show notification if not on chat tab
        showChatNotification();
    });

    // Handle TTS audio from agent tool calls
    eventSource.addEventListener('tts_audio', (e) => {
        const data = JSON.parse(e.data);
        if (data.audio_base64 && typeof playTTSAudio === 'function') {
            playTTSAudio(data.audio_base64);
        }
    });

    // Handle reflection progress events (for live monitoring)
    eventSource.addEventListener('reflection:progress', (e) => {
        const data = JSON.parse(e.data);
        if (typeof handleReflectionProgress === 'function') {
            handleReflectionProgress(data);
        }
    });

    eventSource.addEventListener('reflection:llm_complete', (e) => {
        const data = JSON.parse(e.data);
        if (typeof handleReflectionProgress === 'function') {
            handleReflectionProgress({
                ...data,
                step: 'llm_complete',
                message: `LLM complete (${data.input_tokens} in / ${data.output_tokens} out)`
            });
        }
    });

    eventSource.addEventListener('reflection:complete', (e) => {
        const data = JSON.parse(e.data);
        if (typeof handleReflectionComplete === 'function') {
            handleReflectionComplete(data);
        }
    });

    eventSource.addEventListener('reflection:error', (e) => {
        const data = JSON.parse(e.data);
        if (typeof handleReflectionError === 'function') {
            handleReflectionError(data);
        }
    });

    // Handle agent pause/resume events (for real-time UI updates)
    eventSource.addEventListener('agent:paused', (e) => {
        const data = JSON.parse(e.data);
        if (typeof agentPauseStatus !== 'undefined') {
            agentPauseStatus[data.agent_id] = {
                isPaused: true,
                reason: data.reason || 'Agent paused',
                timestamp: data.timestamp
            };
            // Re-render if viewing this agent's manage page
            if (typeof focusView !== 'undefined' && focusView === `manage-agent-${data.agent_id}`) {
                renderFocusTab();
            }
        }
    });

    eventSource.addEventListener('agent:resumed', (e) => {
        const data = JSON.parse(e.data);
        if (typeof agentPauseStatus !== 'undefined') {
            delete agentPauseStatus[data.agent_id];
            // Re-render if viewing this agent's manage page
            if (typeof focusView !== 'undefined' && focusView === `manage-agent-${data.agent_id}`) {
                renderFocusTab();
            }
        }
    });

    // Handle new LLM calls (for real-time monitoring updates)
    eventSource.addEventListener('monitoring:llm_call', (e) => {
        const data = JSON.parse(e.data);
        const agentId = data.agent_id;

        // Update stats in cache if we have it
        if (typeof monitoringCache !== 'undefined' && monitoringCache[agentId]) {
            const cached = monitoringCache[agentId];

            // Update call counts
            if (cached.stats) {
                if (cached.stats.hour) cached.stats.hour.calls = (cached.stats.hour.calls || 0) + 1;
                if (cached.stats.today) cached.stats.today.calls = (cached.stats.today.calls || 0) + 1;
                if (cached.stats.week) cached.stats.week.calls = (cached.stats.week.calls || 0) + 1;

                // Update token counts
                const tokens = (data.input_tokens || 0) + (data.output_tokens || 0);
                if (cached.stats.hour) cached.stats.hour.tokens = (cached.stats.hour.tokens || 0) + tokens;
                if (cached.stats.today) cached.stats.today.tokens = (cached.stats.today.tokens || 0) + tokens;
                if (cached.stats.week) cached.stats.week.tokens = (cached.stats.week.tokens || 0) + tokens;

                // Update costs
                if (cached.stats.hour) cached.stats.hour.cost = (cached.stats.hour.cost || 0) + (data.cost || 0);
                if (cached.stats.today) cached.stats.today.cost = (cached.stats.today.cost || 0) + (data.cost || 0);
                if (cached.stats.week) cached.stats.week.cost = (cached.stats.week.cost || 0) + (data.cost || 0);
            }

            // If viewing page 1 (offset 0), prepend the new call to the list
            if (typeof monitoringPagination !== 'undefined') {
                const pagination = monitoringPagination[agentId] || { offset: 0, limit: 20 };
                if (pagination.offset === 0) {
                    // Prepend new entry and update pagination total
                    const promptsList = cached.prompts || cached.recent_prompts || [];
                    promptsList.unshift({
                        timestamp: data.timestamp,
                        input_tokens: data.input_tokens || 0,
                        output_tokens: data.output_tokens || 0,
                        model: data.model,
                        cost: data.cost || 0,
                        duration_ms: data.duration_ms
                    });

                    // Remove excess if over limit
                    if (promptsList.length > pagination.limit) {
                        promptsList.pop();
                    }

                    // Update total count
                    if (cached.pagination) {
                        cached.pagination.total = (cached.pagination.total || 0) + 1;
                        cached.pagination.has_more = promptsList.length >= pagination.limit;
                    }

                    cached.prompts = promptsList;
                }
            }
        }

        // Re-render if viewing this agent's monitoring page
        if (typeof focusView !== 'undefined' && focusView === `monitoring-${agentId}`) {
            renderFocusTab();
        }
    });

    eventSource.onerror = () => {
        eventSource.close();
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        reconnectAttempts++;
        setTimeout(connectSSE, delay);
    };
}

// ============== Drag and Drop ==============

const appEl = document.querySelector('.app');

appEl.addEventListener('dragover', (e) => {
    e.preventDefault();
    appEl.classList.add('drag-over');
});

appEl.addEventListener('dragleave', (e) => {
    e.preventDefault();
    appEl.classList.remove('drag-over');
});

appEl.addEventListener('drop', (e) => {
    e.preventDefault();
    appEl.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        queueUploads(Array.from(e.dataTransfer.files));
    }
});

// ============== Initialize ==============

async function init() {
    // Run splash animation and auth check in parallel
    const [_, auth] = await Promise.all([
        runSplashAnimation(),
        checkAuth()
    ]);

    const splashScreen = document.getElementById('splash-screen');
    const loginOverlay = document.getElementById('login-overlay');
    const appContainer = document.getElementById('app-container');

    if (auth.password_required && !auth.authenticated) {
        // Crossfade: splash out, login in
        loginOverlay.classList.remove('hidden');
        // Trigger reflow to ensure transition works
        loginOverlay.offsetHeight;

        splashScreen.classList.add('fade-out');
        loginOverlay.classList.add('visible');

        // Clean up splash after fade
        setTimeout(() => {
            splashScreen.classList.add('hidden');
            document.getElementById('login-password').focus();
        }, 400);
    } else {
        // Crossfade: splash out, app in
        splashScreen.classList.add('fade-out');
        appContainer.classList.add('visible');

        // Clean up splash after fade and init app
        setTimeout(() => {
            splashScreen.classList.add('hidden');
        }, 400);

        initApp();
    }
}

// Start the app
init();
