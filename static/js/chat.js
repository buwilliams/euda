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

// Message queue for sequential processing
let messageQueue = [];
let isProcessingQueue = false;

// Cached quote for chat empty state
let cachedChatQuote = null;

// Show empty state with quote when chat is empty
function showChatEmptyState() {
    // Only show if there are no messages (empty state doesn't count as a message)
    const hasMessages = Array.from(inlineMessages.children).some(
        child => !child.classList.contains('chat-empty-state')
    );
    if (hasMessages) return;

    const quoteHtml = cachedChatQuote
        ? `<div class="chat-empty-quote">
               <div class="quote-text">"${escapeHtml(cachedChatQuote.quote)}"</div>
               <div class="quote-author">— ${escapeHtml(cachedChatQuote.author)}</div>
           </div>`
        : '<div class="chat-empty-quote"><div class="quote-text" style="color: #999;">Loading...</div></div>';

    inlineMessages.innerHTML = `
        <div class="chat-empty-state" id="chat-empty-state">
            <div class="chat-empty-greeting">What's on your mind?</div>
            ${quoteHtml}
        </div>
    `;
}

// Load quote for chat empty state
async function loadChatQuote() {
    try {
        const response = await fetch('/api/daily-quote', { credentials: 'same-origin' });
        if (response.ok) {
            const data = await response.json();
            if (data.quote) {
                cachedChatQuote = data;
                // Re-render empty state if it's showing
                const emptyState = document.getElementById('chat-empty-state');
                if (emptyState) {
                    showChatEmptyState();
                }
            }
        }
    } catch (error) {
        console.error('Failed to load chat quote:', error);
    }
}

// Remove empty state when messages are added
function removeChatEmptyState() {
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) {
        emptyState.remove();
    }
}

function sendContextMessage() {
    const message = contextInput.value.trim();
    if (!message) return;

    // Add user message to UI immediately
    addInlineMessage(message, 'you');
    contextInput.value = '';
    contextInput.style.height = 'auto';

    // Queue the message for processing
    messageQueue.push(message);
    processMessageQueue();
}

async function processMessageQueue() {
    // If already processing or queue is empty, return
    if (isProcessingQueue || messageQueue.length === 0) return;

    isProcessingQueue = true;
    addInlineThinking();

    while (messageQueue.length > 0) {
        const message = messageQueue.shift();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    agent_id: 'friend',
                    session_id: sessionId
                })
            });

            const data = await response.json();

            if (!response.ok) {
                removeInlineThinking();
                addInlineMessage(`Something went wrong: ${data.detail || 'Unknown error'}`, 'friend');
                if (messageQueue.length > 0) addInlineThinking();
                continue;
            }

            // Store session ID from server
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem('sessionId', sessionId);
            }

            removeInlineThinking();
            addInlineMessage(data.response, 'friend');
            showChatNotification();

            // If the agent cleared the conversation, clear the UI
            if (data.clear_chat) {
                messageQueue = []; // Clear any pending messages
                setTimeout(() => {
                    inlineMessages.innerHTML = '';
                    showChatEmptyState();
                }, 1500);
                break;
            }

            // Show thinking again if more messages in queue
            if (messageQueue.length > 0) addInlineThinking();

        } catch (error) {
            console.error('Chat error:', error);
            removeInlineThinking();
            addInlineMessage('I had trouble processing that. Could you try again?', 'friend');
            showChatNotification();
            if (messageQueue.length > 0) addInlineThinking();
        }
    }

    isProcessingQueue = false;
    removeInlineThinking();
}

function addInlineMessage(content, role) {
    // Remove empty state when first message is added
    removeChatEmptyState();

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

let notificationTimeout = null;

function showChatNotification() {
    // Only show notification if not on chat tab
    if (activeTab !== 'chat') {
        // Increment unseen counter and update badge
        unseenChatMessages++;
        updateChatBadge();
        // Also pulse the send button
        contextSendBtn.classList.add('has-notification');
        // Auto-clear pulse after 3 seconds to avoid being annoying
        if (notificationTimeout) clearTimeout(notificationTimeout);
        notificationTimeout = setTimeout(() => {
            contextSendBtn.classList.remove('has-notification');
        }, 3000);
    }
}

function clearChatNotification() {
    // Reset counter and hide badge
    unseenChatMessages = 0;
    updateChatBadge();
    contextSendBtn.classList.remove('has-notification');
    if (notificationTimeout) {
        clearTimeout(notificationTimeout);
        notificationTimeout = null;
    }
}

function updateChatBadge() {
    const badge = document.getElementById('chat-badge');
    if (badge) {
        badge.textContent = unseenChatMessages;
        badge.style.display = unseenChatMessages > 0 ? 'inline' : 'none';
    }
}

// Auto-expand context textarea
contextInput.addEventListener('input', () => {
    contextInput.style.height = 'auto';
    contextInput.style.height = Math.min(contextInput.scrollHeight, 200) + 'px';
});

// Enter to send in context input
contextInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
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
    // Show empty state with quote
    showChatEmptyState();
    // Clear session to start a new conversation
    sessionId = null;
    localStorage.removeItem('sessionId');
    viewingHistorySessionId = null;
    // Switch to chat tab for new conversation
    switchTab('chat');
    // Clear expanded cards state
    expandedCards.clear();
}

