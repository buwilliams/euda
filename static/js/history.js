// Euno - History Tab

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
    if (!historyData || historyData.length === 0) {
        container.innerHTML = '<div class="focus-empty">No conversations yet</div>';
        return;
    }
    container.innerHTML = historyData.map(item => renderHistoryCard(item)).join('');
}

function renderHistoryCard(item) {
    const isExpanded = expandedCards.has(`history-${item.session_id}`);

    if (isExpanded) {
        return `
            <div class="card card-full" data-session-id="${item.session_id}">
                <div class="card-header">
                    <span class="card-title" onclick="toggleHistoryCard('${item.session_id}')">${item.date} at ${item.time}</span>
                    <button class="card-collapse" onclick="event.stopPropagation(); toggleHistoryCard('${item.session_id}')">−</button>
                </div>
                <div class="card-body">
                    <div class="card-preview" style="white-space: normal;">${escapeHtml(item.preview || 'No preview')}</div>
                    <div class="card-meta">${item.message_count || '?'} messages</div>
                </div>
                <div class="card-actions">
                    <button class="card-action primary" onclick="loadConversation('${item.session_id}')">Load</button>
                    <button class="card-action" onclick="archiveConversation('${item.session_id}')">Archive</button>
                    <button class="card-action danger" onclick="deleteConversation('${item.session_id}', event)">Delete</button>
                </div>
            </div>
        `;
    } else {
        return `
            <div class="card card-minimal" data-session-id="${item.session_id}">
                <span class="card-title" onclick="toggleHistoryCard('${item.session_id}')">${item.date} ${item.time}</span>
                <span class="card-preview">${escapeHtml(item.preview || 'No preview')}</span>
            </div>
        `;
    }
}

function toggleHistoryCard(sessionId) {
    const key = `history-${sessionId}`;
    if (expandedCards.has(key)) {
        expandedCards.delete(key);
    } else {
        expandedCards.add(key);
    }
    renderHistory();
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

