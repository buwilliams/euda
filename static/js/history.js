// Euno - History Tab

// ============== History Navigation ==============

function navigateHistory(view) {
    historyViewHistory.push(historyView);
    historyView = view;
    renderHistory();
}

function navigateHistoryBack() {
    if (historyViewHistory.length > 0) {
        historyView = historyViewHistory.pop();
    } else {
        historyView = 'list';
    }
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

    if (historyView === 'list') {
        if (!historyData || historyData.length === 0) {
            container.innerHTML = '<div class="focus-empty">No conversations yet</div>';
            return;
        }
        container.innerHTML = historyData.map(item => renderHistoryCard(item)).join('');
    } else if (historyView.startsWith('conversation-')) {
        const sessionId = historyView.substring(13);
        container.innerHTML = renderHistoryDetailView(sessionId);
    }
}

function renderHistoryCard(item) {
    return `
        <div class="card card-minimal" data-session-id="${item.session_id}" onclick="navigateHistory('conversation-${item.session_id}')">
            <span class="card-title">${item.date} ${item.time}</span>
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

