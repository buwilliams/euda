// Euno - Focus Feature Screens (New Job, Attach)

// ============== New Job Creator Screen ==============

// Track jobs created in the current new job session
let newJobSessionIds = [];

function openNewJobScreen() {
    // Reset session tracking
    newJobSessionIds = [];

    // Remember which tab to return to
    moreMenuReturnTab = activeTab;

    // Show focus tab pane but keep More button active (since New Job is in More menu)
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active', 'slide-left', 'slide-right');
        if (pane.id === 'tab-focus') {
            pane.classList.add('active');
        } else {
            pane.classList.add('slide-left');
        }
    });

    // Activate the More button
    const overflowBtn = document.getElementById('overflow-btn');
    if (overflowBtn) overflowBtn.classList.add('active');

    // Navigate to new job creator
    previousTab = 'focus';
    activeTab = 'focus';
    navigateFocus('newjob');
}

function getProjectsContainerId() {
    const projectsContainer = jobsData.find(j => j.tags && j.tags.includes('system:projects') && !j.parent_id);
    return projectsContainer ? projectsContainer.id : null;
}

function renderNewJobCreatorScreen() {
    // Get jobs created this session (filter from jobsData)
    const sessionJobs = jobsData.filter(j => newJobSessionIds.includes(j.id));

    // Build hierarchical tree of session jobs
    const rootJobs = sessionJobs.filter(j => {
        // Root if parent is the Projects container or no parent
        const projectsId = getProjectsContainerId();
        return j.parent_id === projectsId || !j.parent_id;
    });

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">New Job</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="quick-add-section" style="margin-top: 0; border-top: none;">
                <input type="text" id="new-job-input" class="quick-add-input" placeholder="What needs to be done?" onkeypress="handleNewJobKeypress(event)" autofocus>
                <button class="quick-add-btn" onclick="createNewJobFromInput()">${icon('plus')}</button>
            </div>
            ${sessionJobs.length > 0 ? `
            <div class="job-section" style="margin-top: var(--spacing-md);">
                <div class="job-section-header">Created Jobs (${sessionJobs.length})</div>
                ${renderNewJobTree(rootJobs, sessionJobs, 0)}
            </div>
            ` : `
            <div class="new-job-empty" style="padding: var(--spacing-xl); text-align: center; color: var(--color-text-placeholder);">
                <p>Type a job name above and press Enter</p>
                <p style="font-size: var(--font-size-sm); margin-top: var(--spacing-md);">Jobs will be added to your Projects.</p>
            </div>
            `}
        </div>
    `;
}

function renderNewJobTree(jobs, allSessionJobs, depth = 0) {
    if (jobs.length === 0) return '';

    return jobs.map(job => {
        // Find child jobs created this session
        const children = allSessionJobs.filter(j => j.parent_id === job.id);
        const indentStyle = depth > 0 ? `style="margin-left: ${depth * 20}px;"` : '';

        // Render the job card with swipe support and indent
        const cardHtml = `
            <div class="new-job-item" ${indentStyle}>
                ${renderJobCard(job, true)}
            </div>
        `;

        // Render children recursively
        const childrenHtml = children.length > 0 ? renderNewJobTree(children, allSessionJobs, depth + 1) : '';

        return cardHtml + childrenHtml;
    }).join('');
}

function handleNewJobKeypress(event) {
    if (event.key === 'Enter') {
        createNewJobFromInput();
    }
}

async function createNewJobFromInput() {
    const input = document.getElementById('new-job-input');
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    const projectsId = getProjectsContainerId();

    try {
        const response = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                parent_id: projectsId
            })
        });

        if (response.ok) {
            const newJob = await response.json();
            newJobSessionIds.push(newJob.id);
            input.value = '';
            await loadJobsData();
            // Re-focus input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById('new-job-input');
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create job:', error);
    }
}

// ============== New Child Job Screen ==============

function renderNewJobScreen(parentJobId) {
    const parentJob = jobsData.find(j => j.id === parentJobId);
    const parentName = parentJob ? parentJob.name : 'Job';
    const childJobs = jobsData.filter(j => j.parent_id === parentJobId);

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Add Jobs</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="job-section">
                <div class="job-section-header">Add to: ${escapeHtml(parentName)}</div>
                <div class="quick-add-section" style="margin-top: 0; padding-top: 0; border-top: none;">
                    <input type="text" id="quick-add-child-${parentJobId}" class="quick-add-input" placeholder="New job name..." onkeypress="handleQuickAddChildKeypress(event, '${parentJobId}')">
                    <button class="quick-add-btn" onclick="quickAddChildJob('${parentJobId}')">${icon('plus')}</button>
                </div>
            </div>
            ${childJobs.length > 0 ? `
            <div class="job-section">
                <div class="job-section-header">Child Jobs (${childJobs.length})</div>
                ${childJobs.map(job => renderJobCard(job, true)).join('')}
            </div>
            ` : ''}
        </div>
    `;
}

function handleQuickAddChildKeypress(event, parentJobId) {
    if (event.key === 'Enter') {
        quickAddChildJob(parentJobId);
    }
}

async function quickAddChildJob(parentJobId) {
    const input = document.getElementById(`quick-add-child-${parentJobId}`);
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    try {
        const response = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent_id: parentJobId })
        });

        if (response.ok) {
            input.value = '';
            await loadJobsData();
            // Re-focus the input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById(`quick-add-child-${parentJobId}`);
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create job:', error);
    }
}

// ============== Attach Screen ==============

function renderAttachScreen(jobId) {
    const job = jobsData.find(j => j.id === jobId);
    const jobName = job ? job.name : 'Job';

    return `
        <div class="focus-view-header" onclick="navigateFocusBack()">
            <span class="focus-back-btn">${icon('chevron-left')}</span>
            <div class="focus-view-header-content">
                <span class="focus-view-title">Add Assets</span>
                ${renderBreadcrumbs()}
            </div>
        </div>
        <div class="focus-view-content">
            <div class="job-section">
                <div class="job-section-header">Add to: ${escapeHtml(jobName)}</div>

                <div class="attach-option" onclick="showNewFileForm('${jobId}')">
                    <span class="attach-option-icon">${icon('pencil')}</span>
                    <span class="attach-option-label">Create new file</span>
                </div>

                <label class="attach-option">
                    <span class="attach-option-icon">${icon('folder')}</span>
                    <span class="attach-option-label">Upload files</span>
                    <input type="file" multiple style="display: none;" onchange="handleMultiFileUpload(event, '${jobId}')">
                </label>
            </div>

            <div id="new-file-form" class="job-section" style="display: none;">
                <div class="job-section-header">New File</div>
                <textarea class="job-description-input" id="new-file-content" placeholder="Start writing..." style="min-height: 150px;"></textarea>
                <div class="screen-actions" style="margin-top: 0.5rem;">
                    <button class="screen-action-btn" onclick="hideNewFileForm()">Cancel</button>
                    <button class="screen-action-btn primary" onclick="createNewFileWithContent('${jobId}')">Save</button>
                </div>
            </div>
        </div>
    `;
}

function showNewFileForm(jobId) {
    document.getElementById('new-file-form').style.display = 'block';
    document.getElementById('new-file-content').focus();
}

function hideNewFileForm() {
    document.getElementById('new-file-form').style.display = 'none';
    document.getElementById('new-file-content').value = '';
}

function generateFilenameFromContent(content) {
    // Get first line
    let firstLine = content.split('\n')[0].trim();
    // Strip markdown heading characters and other common prefixes
    firstLine = firstLine.replace(/^[#*\->\s]+/, '').trim();
    // Take first 5 words max
    const words = firstLine.split(/\s+/).slice(0, 5).join('_');
    // Remove special characters, keep alphanumeric and underscores
    let filename = words.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase();
    // Remove leading/trailing underscores
    filename = filename.replace(/^_+|_+$/g, '');
    // Fallback if empty
    if (!filename) {
        filename = 'note_' + Date.now();
    }
    // Limit length
    if (filename.length > 40) {
        filename = filename.substring(0, 40);
    }
    return filename + '.md';
}

async function createNewFileWithContent(jobId) {
    const content = document.getElementById('new-file-content').value;

    if (!content.trim()) {
        return;
    }

    const filename = generateFilenameFromContent(content);

    try {
        const response = await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            // Clear cache to force reload
            delete jobAssetsCache[jobId];
            // Navigate back to job detail (will trigger fresh asset load)
            navigateFocusBack();
        }
    } catch (error) {
        console.error('Failed to create file:', error);
    }
}

async function handleMultiFileUpload(event, jobId) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
        try {
            const content = await file.text();
            await fetch(`/api/jobs/${jobId}/assets/${encodeURIComponent(file.name)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        } catch (error) {
            console.error('Failed to upload file:', error);
        }
    }

    // Clear cache to force reload
    delete jobAssetsCache[jobId];
    navigateFocusBack();
}
