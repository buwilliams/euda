// Euno - Focus Job Actions (CRUD Operations)

// ============== Job Actions ==============

function showArchiveInput(event, jobId) {
    event.stopPropagation();
    if (archivingTaskId === jobId) {
        archivingTaskId = null;
    } else {
        archivingTaskId = jobId;
    }
    renderFocusTab();
    setTimeout(() => {
        const input = document.getElementById(`archive-reason-${jobId}`);
        if (input) input.focus();
    }, 50);
}

async function confirmArchiveJob(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/archive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            archivingTaskId = null;
            await loadJobsData();
            if (focusView === `job-${jobId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to archive job:', error);
    }
}

async function completeJob(event, jobId) {
    if (event) event.stopPropagation();

    try {
        const response = await fetch(`/api/jobs/${jobId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            await loadJobsData();
            if (focusView === `job-${jobId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to complete job:', error);
    }
}

async function restoreJob(event, jobId) {
    if (event) event.stopPropagation();

    try {
        const response = await fetch(`/api/jobs/${jobId}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            await loadJobsData();
            if (focusView === `completed-${jobId}`) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to restore job:', error);
    }
}

async function deleteJob(event, jobId) {
    if (event) event.stopPropagation();
    if (!confirm('Delete this job?')) return;

    const wasViewingJob = focusView === `job-${jobId}` || focusView === `completed-${jobId}`;

    try {
        const response = await fetch(`/api/jobs/${jobId}?delete_children=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadJobsData();
            if (wasViewingJob) {
                navigateFocusBack();
            }
        }
    } catch (error) {
        console.error('Failed to delete job:', error);
    }
}

async function quickAddJob(inputId, parentId = null) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const name = input.value.trim();
    if (!name) return;

    try {
        const body = { name };
        if (parentId) {
            body.parent_id = parentId;
        }

        const response = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            input.value = '';
            await loadJobsData();
            // Re-focus the input for rapid entry
            setTimeout(() => {
                const newInput = document.getElementById(inputId);
                if (newInput) newInput.focus();
            }, 50);
        }
    } catch (error) {
        console.error('Failed to create job:', error);
    }
}

function handleQuickAddKeypress(event, inputId, parentId = null) {
    if (event.key === 'Enter') {
        quickAddJob(inputId, parentId);
    }
}

async function quickDeleteJob(event, jobId) {
    event.stopPropagation();
    if (!confirm('Delete this job and all children?')) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}?delete_children=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadJobsData();
        }
    } catch (error) {
        console.error('Failed to delete job:', error);
    }
}
