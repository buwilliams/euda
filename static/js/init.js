// Euno - Initialization, SSE, Drag & Drop

// ============== SSE ==============

let eventSource = null;
let reconnectAttempts = 0;

function connectSSE() {
    if (eventSource) eventSource.close();

    eventSource = new EventSource('/api/events');

    eventSource.addEventListener('init', (e) => {
        const data = JSON.parse(e.data);
        const allTasks = data.tasks || [];
        // Split tasks into active and completed (filter out archived)
        tasksData = allTasks.filter(t => t.status !== 'completed' && t.status !== 'archived');
        completedTasksData = allTasks.filter(t => t.status === 'completed')
            .sort((a, b) => (b.completed_at || '').localeCompare(a.completed_at || ''))
            .slice(0, 20);
        projectsData = data.projects || [];
        updateTasksBadge();
        if (activeTab === 'focus') {
            renderFocusTab();
        }
        reconnectAttempts = 0;
    });

    eventSource.addEventListener('tasks_update', (e) => {
        const data = JSON.parse(e.data);
        const allTasks = data.tasks || [];
        // Split tasks into active and completed (filter out archived)
        tasksData = allTasks.filter(t => t.status !== 'completed' && t.status !== 'archived');
        completedTasksData = allTasks.filter(t => t.status === 'completed')
            .sort((a, b) => (b.completed_at || '').localeCompare(a.completed_at || ''))
            .slice(0, 20);
        if (activeTab === 'focus') {
            renderFocusTab();
        }
        updateTasksBadge();
    });

    eventSource.addEventListener('projects_update', (e) => {
        const data = JSON.parse(e.data);
        projectsData = data.projects || [];
        if (activeTab === 'focus') {
            renderFocusTab();
        }
    });

    eventSource.addEventListener('ping', () => {});

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
