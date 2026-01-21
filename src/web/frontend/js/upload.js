// Euno - File Upload

// ============== File Upload ==============

function triggerUpload() {
    document.getElementById('file-input').click();
}

let uploadQueue = [];
let uploadTotal = 0;
let uploadCurrent = 0;

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (!files.length) return;
    event.target.value = '';
    queueUploads(files);
}

function queueUploads(files) {
    uploadQueue = uploadQueue.concat(files);
    uploadTotal = uploadQueue.length;
    uploadCurrent = 0;
    processUploadQueue();
}

function processUploadQueue() {
    if (uploadQueue.length === 0) {
        uploadTotal = 0;
        uploadCurrent = 0;
        return;
    }

    const file = uploadQueue.shift();
    uploadCurrent++;
    uploadFile(file);
}

function uploadFile(file) {
    const progressEl = document.getElementById('upload-progress');
    const filenameEl = document.getElementById('upload-filename');
    const percentEl = document.getElementById('upload-percent');
    const fillEl = document.getElementById('upload-fill');
    const statusEl = document.getElementById('upload-status');
    const uploadBtn = document.getElementById('upload-btn');

    const queueStatus = uploadTotal > 1 ? ` (${uploadCurrent}/${uploadTotal})` : '';
    filenameEl.textContent = file.name + queueStatus;
    percentEl.textContent = '0%';
    fillEl.style.width = '0%';
    statusEl.textContent = 'Uploading...';
    progressEl.classList.add('active');
    uploadBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    uploadXhr = new XMLHttpRequest();

    uploadXhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            percentEl.textContent = percent + '%';
            fillEl.style.width = percent + '%';

            if (e.total > 1024 * 1024) {
                const loadedMB = (e.loaded / (1024 * 1024)).toFixed(1);
                const totalMB = (e.total / (1024 * 1024)).toFixed(1);
                statusEl.textContent = `${loadedMB} MB / ${totalMB} MB`;
            }
        }
    };

    uploadXhr.onload = function() {
        if (uploadXhr.status === 200) {
            try {
                const response = JSON.parse(uploadXhr.responseText);
                statusEl.textContent = 'Complete!';
                fillEl.style.width = '100%';
                percentEl.textContent = '100%';

                switchTab('chat');
                addInlineMessage(`Uploaded: ${file.name}`, 'you');
                addInlineMessage(response.message || `File "${response.filename}" uploaded.`, 'friend');
            } catch (e) {
                statusEl.textContent = 'Upload complete';
            }
        } else {
            statusEl.textContent = 'Upload failed';
            switchTab('chat');
            addInlineMessage(`Upload failed: ${file.name}`, 'you');
            addInlineMessage('Sorry, the upload failed. Please try again.', 'friend');
        }

        uploadXhr = null;

        // Process next file in queue
        if (uploadQueue.length > 0) {
            setTimeout(processUploadQueue, 500);
        } else {
            uploadBtn.disabled = false;
            setTimeout(() => progressEl.classList.remove('active'), 1500);
        }
    };

    uploadXhr.onerror = function() {
        statusEl.textContent = 'Network error';
        switchTab('chat');
        addInlineMessage(`Upload failed: ${file.name}`, 'friend');
        uploadXhr = null;

        // Continue with next file despite error
        if (uploadQueue.length > 0) {
            setTimeout(processUploadQueue, 500);
        } else {
            uploadBtn.disabled = false;
            setTimeout(() => progressEl.classList.remove('active'), 2000);
        }
    };

    uploadXhr.open('POST', '/api/upload');
    uploadXhr.send(formData);
}

