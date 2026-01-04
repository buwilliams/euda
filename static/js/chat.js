// Euno - Chat & Daily Quote

// ============== Daily Quote ==============

async function loadDailyQuote(retries = 3) {
    // Find the quote container in Focus tab (may not exist yet if Focus hasn't rendered)
    const container = document.getElementById('daily-quote-container');
    if (!container) {
        // Retry after a short delay if container doesn't exist yet
        if (retries > 0) {
            setTimeout(() => loadDailyQuote(retries - 1), 200);
        }
        return;
    }

    // Show loading state
    container.innerHTML = `<div id="daily-quote" class="quote-container"><div class="quote-loading">Loading today's reflection...</div></div>`;

    try {
        const response = await fetch('/api/daily-quote', {
            credentials: 'same-origin'
        });
        if (!response.ok) {
            console.error('Daily quote API error:', response.status, response.statusText);
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        if (data.quote) {
            renderQuote(data);
        } else {
            throw new Error('No quote in response');
        }
    } catch (error) {
        console.error('Failed to load daily quote:', error);
        // Fallback
        renderQuote({
            quote: "The only way to do great work is to love what you do.",
            author: "Steve Jobs"
        });
    }
}

function renderQuote(data) {
    const container = document.getElementById('daily-quote-container');
    if (container) {
        container.innerHTML = `
            <div id="daily-quote" class="quote-container">
                <div class="quote-text">"${escapeHtml(data.quote)}"</div>
                <div class="quote-author">— ${escapeHtml(data.author)}</div>
            </div>
        `;
    }
}

// ============== Inline Chat ==============

const contextInput = document.getElementById('context-input');
const contextSendBtn = document.getElementById('context-send-btn');
const inlineMessages = document.getElementById('inline-messages');

async function sendContextMessage() {
    const message = contextInput.value.trim();
    if (!message || isWaiting) return;

    // Add user message
    addInlineMessage(message, 'you');
    contextInput.value = '';
    contextInput.style.height = 'auto';
    setContextWaiting(true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                agent_id: 'friend',
                session_id: sessionId  // Include current session
            })
        });

        const data = await response.json();

        if (!response.ok) {
            removeInlineThinking();
            addInlineMessage(`Something went wrong: ${data.detail || 'Unknown error'}`, 'friend');
            setContextWaiting(false);
            return;
        }

        // Store session ID from server (creates new one if we didn't have one)
        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem('sessionId', sessionId);
        }

        removeInlineThinking();
        addInlineMessage(data.response, 'friend');
        showChatNotification();

        // If the agent cleared the conversation, clear the UI after showing the response
        if (data.clear_chat) {
            setTimeout(() => {
                inlineMessages.innerHTML = '';
                loadDailyQuote();
            }, 1500);  // Brief delay so user sees the confirmation
        }
    } catch (error) {
        console.error('Chat error:', error);
        removeInlineThinking();
        addInlineMessage('I had trouble processing that. Could you try again?', 'friend');
        showChatNotification();
    }

    setContextWaiting(false);
    contextInput.focus();
}

function addInlineMessage(content, role) {
    const div = document.createElement('div');
    div.className = `inline-message inline-message-${role}`;
    const html = role === 'friend' ? marked.parse(content) : escapeHtml(content);
    div.innerHTML = `<div class="message-content">${html}</div>`;
    inlineMessages.appendChild(div);
    // Scroll to bottom of chat tab
    const chatPane = document.getElementById('tab-chat');
    if (chatPane) chatPane.scrollTop = chatPane.scrollHeight;
}

function addInlineThinking() {
    const div = document.createElement('div');
    div.className = 'inline-message inline-message-friend';
    div.id = 'inline-thinking';
    div.innerHTML = `<div class="message-content" style="color: #999; font-style: italic;">Thinking<span class="thinking-dots"><span></span><span></span><span></span></span></div>`;
    inlineMessages.appendChild(div);
    const chatPane = document.getElementById('tab-chat');
    if (chatPane) chatPane.scrollTop = chatPane.scrollHeight;
}

function removeInlineThinking() {
    const el = document.getElementById('inline-thinking');
    if (el) el.remove();
}

function setContextWaiting(waiting) {
    isWaiting = waiting;
    contextInput.disabled = waiting;
    contextSendBtn.disabled = waiting;
    if (waiting) addInlineThinking();
}

let notificationTimeout = null;

function showChatNotification() {
    // Only show notification if not on chat tab
    if (activeTab !== 'chat') {
        contextSendBtn.classList.add('has-notification');
        // Auto-clear after 3 seconds to avoid being annoying
        if (notificationTimeout) clearTimeout(notificationTimeout);
        notificationTimeout = setTimeout(clearChatNotification, 3000);
    }
}

function clearChatNotification() {
    contextSendBtn.classList.remove('has-notification');
    if (notificationTimeout) {
        clearTimeout(notificationTimeout);
        notificationTimeout = null;
    }
}

// Auto-expand context textarea
contextInput.addEventListener('input', () => {
    contextInput.style.height = 'auto';
    contextInput.style.height = Math.min(contextInput.scrollHeight, 200) + 'px';
});

// Enter to send in context input
contextInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isWaiting) {
        e.preventDefault();
        sendContextMessage();
    }
});

// ============== Chat Overlay (Legacy) ==============

function openChat() {
    // Now just focus the inline input
    contextInput.focus();
}

function openChatWith(message) {
    contextInput.value = message;
    contextInput.focus();
}

function sendPrompt(message) {
    contextInput.value = message;
    sendContextMessage();
}

function closeChat() {
    // No-op now
}

async function resetUI() {
    // Clear all messages
    inlineMessages.innerHTML = '';
    // Clear session to start a new conversation
    sessionId = null;
    localStorage.removeItem('sessionId');
    viewingHistorySessionId = null;
    // Switch to chat tab for new conversation
    switchTab('chat');
    // Clear expanded cards state
    expandedCards.clear();
}

