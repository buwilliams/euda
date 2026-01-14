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

        // Show browser notification if appropriate
        if (typeof shouldShowBrowserNotification === 'function' &&
            shouldShowBrowserNotification()) {
            // Request permission if first time
            if (typeof maybeRequestNotificationPermission === 'function') {
                maybeRequestNotificationPermission();
            }
            // Show browser notification
            if (typeof showBrowserNotification === 'function') {
                showBrowserNotification(data.message, data.agent || 'Euno');
            }
        }
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
