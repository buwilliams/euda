// Euno - Chat & Daily Quote

// ============== Daily Quote ==============

// Cache the quote data for reuse
let focusQuoteData = null;

async function loadDailyQuote(retries = 3) {
    // Check if quote was dismissed this session
    if (sessionStorage.getItem('quoteDismissed')) {
        const container = document.getElementById('daily-quote-container');
        if (container) container.innerHTML = '';
        return;
    }

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
            focusQuoteData = data;
            renderQuote(data);
        } else {
            throw new Error('No quote in response');
        }
    } catch (error) {
        console.error('Failed to load daily quote:', error);
        // Fallback
        focusQuoteData = {
            quote: "The only way to do great work is to love what you do.",
            author: "Steve Jobs"
        };
        renderQuote(focusQuoteData);
    }
}

function renderQuote(data) {
    // Check if dismissed
    if (sessionStorage.getItem('quoteDismissed')) {
        const container = document.getElementById('daily-quote-container');
        if (container) container.innerHTML = '';
        return;
    }

    const container = document.getElementById('daily-quote-container');
    if (container) {
        container.innerHTML = `
            <div id="daily-quote" class="quote-container quote-swipeable">
                <div class="quote-text">"${escapeHtml(data.quote)}"</div>
                <div class="quote-author">— ${escapeHtml(data.author)}</div>
            </div>
        `;
        initQuoteSwipe();
    }
}

function dismissQuote() {
    sessionStorage.setItem('quoteDismissed', 'true');
    const container = document.getElementById('daily-quote-container');
    if (container) {
        const quote = container.querySelector('.quote-container');
        if (quote) {
            quote.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
            quote.style.opacity = '0';
            quote.style.transform = 'translateX(50px)';
            setTimeout(() => {
                container.innerHTML = '';
            }, 200);
        }
    }
}

// Quote swipe handling
let quoteSwipeStartX = 0;
let quoteSwipeElement = null;
let quoteSwipeActive = false;

function initQuoteSwipe() {
    const quote = document.getElementById('daily-quote');
    if (!quote) return;

    quote.addEventListener('touchstart', handleQuoteSwipeStart, { passive: true });
    quote.addEventListener('touchmove', handleQuoteSwipeMove, { passive: false });
    quote.addEventListener('touchend', handleQuoteSwipeEnd, { passive: true });

    quote.addEventListener('mousedown', handleQuoteMouseDown);
}

function handleQuoteSwipeStart(e) {
    quoteSwipeElement = e.currentTarget;
    quoteSwipeStartX = e.touches[0].clientX;
    quoteSwipeActive = false;
    quoteSwipeElement.style.transition = 'none';
}

function handleQuoteSwipeMove(e) {
    if (!quoteSwipeElement) return;
    const deltaX = e.touches[0].clientX - quoteSwipeStartX;
    if (Math.abs(deltaX) > 10) {
        quoteSwipeActive = true;
        e.preventDefault();
        quoteSwipeElement.style.transform = `translateX(${deltaX}px)`;
        quoteSwipeElement.style.opacity = Math.max(0, 1 - Math.abs(deltaX) / 150);
    }
}

function handleQuoteSwipeEnd(e) {
    if (!quoteSwipeElement) return;
    const deltaX = e.changedTouches ? e.changedTouches[0].clientX - quoteSwipeStartX : 0;

    if (quoteSwipeActive && Math.abs(deltaX) > 80) {
        dismissQuote();
    } else {
        quoteSwipeElement.style.transition = 'transform 0.2s ease, opacity 0.2s ease';
        quoteSwipeElement.style.transform = 'translateX(0)';
        quoteSwipeElement.style.opacity = '1';
    }
    quoteSwipeElement = null;
    quoteSwipeActive = false;
}

function handleQuoteMouseDown(e) {
    if (e.button !== 0) return;
    quoteSwipeElement = e.currentTarget;
    quoteSwipeStartX = e.clientX;
    quoteSwipeActive = false;
    quoteSwipeElement.style.transition = 'none';

    document.addEventListener('mousemove', handleQuoteMouseMove);
    document.addEventListener('mouseup', handleQuoteMouseUp);
}

function handleQuoteMouseMove(e) {
    if (!quoteSwipeElement) return;
    const deltaX = e.clientX - quoteSwipeStartX;
    if (Math.abs(deltaX) > 5) {
        quoteSwipeActive = true;
        quoteSwipeElement.style.transform = `translateX(${deltaX}px)`;
        quoteSwipeElement.style.opacity = Math.max(0, 1 - Math.abs(deltaX) / 150);
    }
}

function handleQuoteMouseUp(e) {
    document.removeEventListener('mousemove', handleQuoteMouseMove);
    document.removeEventListener('mouseup', handleQuoteMouseUp);

    if (!quoteSwipeElement) return;
    const deltaX = e.clientX - quoteSwipeStartX;

    if (quoteSwipeActive && Math.abs(deltaX) > 80) {
        dismissQuote();
    } else {
        quoteSwipeElement.style.transition = 'transform 0.2s ease, opacity 0.2s ease';
        quoteSwipeElement.style.transform = 'translateX(0)';
        quoteSwipeElement.style.opacity = '1';
    }
    quoteSwipeElement = null;
    quoteSwipeActive = false;
}

// ============== Inline Chat ==============

const contextInput = document.getElementById('context-input');
const contextSendBtn = document.getElementById('context-send-btn');
const inlineMessages = document.getElementById('inline-messages');

// Message queue for sequential processing
let messageQueue = [];
let lastFailedMessage = null; // Store failed message for retry
let isProcessingQueue = false;

// Cached quote for chat empty state
let cachedChatQuote = null;

// Format seconds into human-readable time
function formatPauseTime(seconds) {
    if (seconds >= 60) {
        const minutes = Math.ceil(seconds / 60);
        return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
    return `${seconds} second${seconds !== 1 ? 's' : ''}`;
}

// Retry the last failed message
function retryLastMessage() {
    if (lastFailedMessage) {
        const message = lastFailedMessage;
        lastFailedMessage = null;
        // Remove the error message with retry button
        const retryMsg = document.querySelector('.pause-error-message');
        if (retryMsg) retryMsg.remove();
        // Re-send the message
        sendChatMessage(message);
    }
}

// ============== Job Context (for context-aware chat routing) ==============

let currentJobContext = null;
let currentJobName = null;

function setJobContext(jobId) {
    // Get job to check if it's a system container
    const job = typeof jobsData !== 'undefined' ? jobsData.find(j => j.id === jobId) : null;

    // Don't show context for system containers (Agents, Projects, System) or agent inbox jobs
    // But DO show for jobs that are descendants of agents (jobs the agent worked on)
    if (job) {
        const tags = job.tags || [];
        // Only exclude the container jobs themselves, not their descendants
        const isSystemContainer = tags.includes('system:agents') ||
                                  tags.includes('system:projects') ||
                                  tags.includes('system:system');
        // Agent inbox jobs are the root jobs for each agent (have agent_id or agent-inbox tag)
        const isAgentInbox = tags.includes('agent-inbox') || job.agent_id;

        if (isSystemContainer || isAgentInbox) {
            clearJobContext();
            return;
        }
    }

    currentJobContext = jobId;
    currentJobName = job ? job.name : 'this job';
    updateInputContext();
}

function clearJobContext() {
    currentJobContext = null;
    currentJobName = null;
    updateInputContext();

    // Also directly hide the label in case updateInputContext returns early
    const label = document.getElementById('job-context-label');
    if (label) {
        label.classList.remove('active');
        label.textContent = '';
    }
}

function updateInputContext() {
    if (!contextInput) return;
    const label = document.getElementById('job-context-label');

    if (currentJobContext && label) {
        contextInput.placeholder = "Ask about this job...";
        label.textContent = '@job';
        label.classList.add('active');
        label.onclick = clearJobContext;
        label.title = `Replying to: ${currentJobName || 'Job'} (click to clear)`;
    } else if (label) {
        contextInput.placeholder = "What's on your mind?";
        label.classList.remove('active');
        label.textContent = '';
        label.onclick = null;
        label.title = '';
    }
}

async function sendJobFeedback(jobId, message) {
    // Show user message with job context indicator
    const jobName = currentJobName || 'job';
    addInlineMessage(message, 'you', `Re: ${jobName}`);
    contextInput.value = '';
    contextInput.style.height = 'auto';
    addInlineThinking();

    try {
        const response = await fetch(`/api/jobs/${jobId}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const result = await response.json();

        removeInlineThinking();

        if (!response.ok) {
            addInlineMessage(`Failed to send feedback: ${result.detail || 'Unknown error'}`, 'friend');
            return;
        }

        addInlineMessage(`Feedback sent to **${result.to_agent}**. They'll work on it and get back to you.`, 'friend');
        showChatNotification();

        // Refresh job data if loadAllJobs exists
        if (typeof loadAllJobs === 'function') {
            await loadAllJobs();
        }
        if (typeof renderFocusTab === 'function') {
            renderFocusTab();
        }
    } catch (error) {
        console.error('Failed to send feedback:', error);
        removeInlineThinking();
        addInlineMessage('Failed to send feedback. Please try again.', 'friend');
    }
}

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

    // Add user message to UI immediately (with job context indicator if viewing a job)
    if (currentJobContext && currentJobName) {
        addInlineMessage(message, 'you', `Re: ${currentJobName}`);
    } else {
        addInlineMessage(message, 'you');
    }
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

        // Check if this message came from voice input (for TTS response)
        const voiceInput = typeof window.wasLastInputVoice === 'function' ? window.wasLastInputVoice() : false;

        try {
            // Include job context if user is viewing a job in Focus
            const payload = {
                message,
                agent_id: 'chat',
                session_id: sessionId,
                voice_input: voiceInput
            };
            if (currentJobContext) {
                payload.job_context = currentJobContext;
            }

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                removeInlineThinking();

                // Handle agent paused error specially
                if (response.status === 503 && data.detail && data.detail.error === 'agent_paused') {
                    const detail = data.detail;
                    const timeStr = formatPauseTime(detail.remaining_seconds || 60);
                    lastFailedMessage = message; // Store for retry

                    // Create message with retry button using safe DOM methods
                    const div = document.createElement('div');
                    div.className = 'inline-message inline-message-friend pause-error-message';

                    const content = document.createElement('div');
                    content.className = 'message-content';

                    const p = document.createElement('p');
                    p.textContent = "I'm taking a short break due to high activity. I'll be back in about ";
                    const strong = document.createElement('strong');
                    strong.textContent = timeStr;
                    p.appendChild(strong);
                    p.appendChild(document.createTextNode('.'));

                    const btn = document.createElement('button');
                    btn.textContent = 'Try Again';
                    btn.className = 'retry-button';
                    btn.onclick = retryLastMessage;

                    content.appendChild(p);
                    content.appendChild(btn);
                    div.appendChild(content);

                    removeChatEmptyState();
                    inlineMessages.appendChild(div);
                    const chatPane = document.getElementById('tab-chat');
                    if (chatPane) chatPane.scrollTop = chatPane.scrollHeight;
                } else {
                    // Generic error
                    const errorMsg = typeof data.detail === 'string' ? data.detail : 'Unknown error';
                    addInlineMessage(`Something went wrong: ${errorMsg}`, 'friend');
                }

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

            // Play TTS audio if included in response
            if (data.audio_base64 && typeof playTTSAudio === 'function') {
                playTTSAudio(data.audio_base64);
            }

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

function addInlineMessage(content, role, context = null) {
    // Remove empty state when first message is added
    removeChatEmptyState();

    const div = document.createElement('div');
    div.className = `inline-message inline-message-${role}`;
    const html = role === 'friend' ? marked.parse(content) : escapeHtml(content);

    // Add context label if provided (e.g., "Re: Job Name")
    const contextHtml = context ? `<div class="message-context">${escapeHtml(context)}</div>` : '';

    div.innerHTML = `${contextHtml}<div class="message-content">${html}</div>`;
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

function showChatNotification() {
    // Only show notification if not on chat tab
    if (activeTab !== 'chat') {
        unseenChatMessages++;
        updateChatBadge();
    }
}

function clearChatNotification() {
    unseenChatMessages = 0;
    updateChatBadge();
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

