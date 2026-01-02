// Euno - Chat & Daily Quote

// ============== Daily Quote ==============

function getTodayKey() {
    return new Date().toISOString().split('T')[0]; // YYYY-MM-DD
}

function getCachedQuote() {
    const cached = localStorage.getItem('dailyQuote');
    if (!cached) return null;
    try {
        const data = JSON.parse(cached);
        if (data.date === getTodayKey()) {
            return data;
        }
    } catch (e) {}
    return null;
}

function cacheQuote(data) {
    localStorage.setItem('dailyQuote', JSON.stringify({
        ...data,
        date: getTodayKey()
    }));
}

async function loadDailyQuote() {
    // Remove any existing quote first
    const existingQuote = document.getElementById('daily-quote');
    if (existingQuote) existingQuote.remove();

    // Check cache first
    const cached = getCachedQuote();
    if (cached) {
        // Show cached quote immediately (no loading state)
        const quoteDiv = document.createElement('div');
        quoteDiv.id = 'daily-quote';
        quoteDiv.className = 'quote-container';
        inlineMessages.insertBefore(quoteDiv, inlineMessages.firstChild);
        renderQuote(cached);
        return;
    }

    // Show loading state in messages area
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'daily-quote';
    loadingDiv.className = 'quote-container';
    loadingDiv.innerHTML = `<div class="quote-loading">Loading today's reflection...</div>`;
    inlineMessages.insertBefore(loadingDiv, inlineMessages.firstChild);

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
            cacheQuote(data);
            renderQuote(data);
        } else {
            throw new Error('No quote in response');
        }
    } catch (error) {
        console.error('Failed to load daily quote:', error);
        // Fallback
        const fallback = {
            quote: "The only way to do great work is to love what you do.",
            author: "Steve Jobs"
        };
        cacheQuote(fallback);
        renderQuote(fallback);
    }
}

function renderQuote(data) {
    const quoteDiv = document.getElementById('daily-quote');
    if (quoteDiv) {
        quoteDiv.innerHTML = `
            <div class="quote-text">"${escapeHtml(data.quote)}"</div>
            <div class="quote-author">— ${escapeHtml(data.author)}</div>
        `;
        // Ensure chat stays scrolled to top after quote renders
        const chatPane = document.getElementById('tab-chat');
        if (chatPane) chatPane.scrollTop = 0;
    }
}

// ============== Inline Chat ==============

const contextInput = document.getElementById('context-input');
const contextSendBtn = document.getElementById('context-send-btn');
const inlineMessages = document.getElementById('inline-messages');

async function sendContextMessage() {
    const message = contextInput.value.trim();
    if (!message || isWaiting) return;

    // Switch to chat tab if not already there
    if (activeTab !== 'chat') {
        switchTab('chat');
    }

    // Add user message
    addInlineMessage(message, 'you');
    contextInput.value = '';
    contextInput.style.height = 'auto';
    setContextWaiting(true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, agent_id: 'friend' })
        });

        const data = await response.json();

        if (!response.ok) {
            removeInlineThinking();
            addInlineMessage(`Something went wrong: ${data.detail || 'Unknown error'}`, 'friend');
            setContextWaiting(false);
            return;
        }

        removeInlineThinking();
        addInlineMessage(data.response, 'friend');

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
    // Switch to chat tab
    switchTab('chat');
    // Reload the quote
    loadDailyQuote();
    // Clear expanded cards state
    expandedCards.clear();
}

