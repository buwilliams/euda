// Euno - History Tab

// ============== Date Formatting ==============

function formatHistoryDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.getTime() === today.getTime()) {
        return 'Today';
    } else if (date.getTime() === yesterday.getTime()) {
        return 'Yesterday';
    } else if (date > new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)) {
        // Within last week - show day name
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        // Older - show "Dec 25" format
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function formatHistoryTime(timeStr) {
    // timeStr is "HH:MM" format
    const [hours, minutes] = timeStr.split(':').map(Number);
    const period = hours >= 12 ? 'p' : 'a';
    const hour12 = hours % 12 || 12;
    return `${hour12}:${String(minutes).padStart(2, '0')}${period}`;
}

// ============== History Navigation ==============

// Track navigation direction for animations
let historySlideDirection = null; // 'forward' or 'back'

function navigateHistory(view) {
    historyViewHistory.push(historyView);
    historyView = view;
    historySlideDirection = 'forward';
    renderHistory();
}

function navigateHistoryBack() {
    if (historyViewHistory.length > 0) {
        historyView = historyViewHistory.pop();
    } else {
        historyView = 'list';
    }
    historySlideDirection = 'back';
    renderHistory();
}

// ============== History ==============

async function loadHistoryData() {
    try {
        const response = await fetch('/api/conversations/recent/structured?count=20');
        const data = await response.json();
        historyData = data.conversations || [];
        renderHistory();
    } catch (error) {
        console.error('Failed to load history:', error);
        document.getElementById('history-list').innerHTML =
            '<div class="history-empty">Failed to load history</div>';
    }
}

function renderHistory() {
    const container = document.getElementById('history-list');

    let content;
    if (historyView === 'list') {
        if (!historyData || historyData.length === 0) {
            content = '<div class="focus-empty">No conversations yet</div>';
        } else {
            content = historyData.map(item => renderHistoryCard(item)).join('');
        }
    } else if (historyView.startsWith('conversation-')) {
        const sessionId = historyView.substring(13);
        content = renderHistoryDetailView(sessionId);
    }

    // Apply slide animation if direction is set
    if (historySlideDirection && container.querySelector('.view-slide-container')) {
        animateHistoryTransition(container, content, historySlideDirection);
        historySlideDirection = null;
    } else {
        // Initial render or no animation needed
        container.innerHTML = `<div class="view-slide-container current">${content}</div>`;
    }
}

function animateHistoryTransition(container, newContent, direction) {
    const oldView = container.querySelector('.view-slide-container');
    if (!oldView) {
        container.innerHTML = `<div class="view-slide-container current">${newContent}</div>`;
        return;
    }

    // Create new view
    const newView = document.createElement('div');
    newView.className = 'view-slide-container';
    newView.innerHTML = newContent;

    // Position new view off-screen
    if (direction === 'forward') {
        newView.classList.add('slide-in-right');
    } else {
        newView.classList.add('slide-in-left');
    }

    container.appendChild(newView);

    // Trigger reflow
    newView.offsetHeight;

    // Animate old view out and new view in
    if (direction === 'forward') {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-left');
    } else {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-right');
    }

    newView.classList.remove('slide-in-left', 'slide-in-right');
    newView.classList.add('current');

    // Clean up old view after animation
    setTimeout(() => {
        if (oldView.parentNode) {
            oldView.remove();
        }
    }, 300);
}

function renderHistoryCard(item) {
    const friendlyDate = formatHistoryDate(item.date);
    const friendlyTime = formatHistoryTime(item.time);
    return `
        <div class="card card-minimal" data-session-id="${item.session_id}" onclick="navigateHistory('conversation-${item.session_id}')">
            <span class="card-title">${friendlyDate} ${friendlyTime}</span>
            <span class="card-preview">${escapeHtml(item.preview || 'No preview')}</span>
            <span class="card-arrow">›</span>
        </div>
    `;
}

function renderHistoryDetailView(sessionId) {
    const item = historyData.find(h => h.session_id === sessionId);
    if (!item) {
        return `
            <div class="focus-view-header" onclick="navigateHistoryBack()">
                <span class="focus-back-btn">←</span>
                <span class="focus-view-title">Conversation Not Found</span>
            </div>
            <div class="focus-empty">This conversation no longer exists.</div>
        `;
    }

    return `
        <div class="focus-view-header" onclick="navigateHistoryBack()">
            <span class="focus-back-btn">←</span>
            <span class="focus-view-title">${item.date} at ${item.time}</span>
        </div>
        <div class="focus-view-content">
            <div class="history-detail">
                <div class="history-detail-preview">${marked.parse(item.preview || 'No preview')}</div>
                <div class="history-detail-meta">${item.message_count || '?'} messages</div>
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" onclick="loadConversation('${item.session_id}')">💬 Continue Conversation</button>
                <button class="task-detail-action" onclick="archiveConversation('${item.session_id}')">📦 Archive</button>
                <button class="task-detail-action danger" onclick="deleteConversation('${item.session_id}', event)">🗑 Delete</button>
            </div>
        </div>
    `;
}

function toggleHistoryCard(sessionId) {
    // Legacy function - now just navigates
    navigateHistory('conversation-' + sessionId);
}

async function loadConversation(oldSessionId) {
    try {
        const response = await fetch('/api/conversations/fork', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: oldSessionId })
        });
        if (!response.ok) throw new Error('Failed to fork');
        const data = await response.json();

        sessionId = data.new_session_id;
        localStorage.setItem('sessionId', sessionId);
        viewingHistorySessionId = oldSessionId;

        inlineMessages.innerHTML = '';
        for (const msg of data.messages) {
            addInlineMessage(msg.content, msg.role === 'user' ? 'you' : 'friend');
        }

        // Switch to chat tab
        switchTab('chat');
        contextInput.focus();
    } catch (error) {
        console.error('Failed to load conversation:', error);
        alert('Failed to load conversation');
    }
}

// Legacy alias for forkConversation
async function forkConversation(oldSessionId) {
    return loadConversation(oldSessionId);
}

async function archiveConversation(targetSessionId) {
    // For now, archive just deletes - could be enhanced to move to archive
    if (!confirm('Archive this conversation? (This will remove it from history)')) return;
    await deleteConversationById(targetSessionId);
}

async function deleteConversationById(targetSessionId) {
    try {
        const response = await fetch(`/api/conversations/${targetSessionId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete');

        // If we deleted the conversation we're currently viewing, clear the chat
        if (targetSessionId === viewingHistorySessionId) {
            inlineMessages.innerHTML = '';
            viewingHistorySessionId = null;
        }

        // Refresh history list
        await loadHistoryData();
    } catch (error) {
        console.error('Failed to delete conversation:', error);
        alert('Failed to delete conversation');
    }
}

async function deleteConversation(targetSessionId, event) {
    if (event) event.stopPropagation();
    if (!confirm('Delete this conversation permanently?')) return;
    await deleteConversationById(targetSessionId);
}

