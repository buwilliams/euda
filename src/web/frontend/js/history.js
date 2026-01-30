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
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function formatHistoryTime(timeStr) {
    const [hours, minutes] = timeStr.split(':').map(Number);
    const period = hours >= 12 ? 'p' : 'a';
    const hour12 = hours % 12 || 12;
    return `${hour12}:${String(minutes).padStart(2, '0')}${period}`;
}

// ============== History Navigation ==============

let historySlideDirection = null;

function navigateHistory(view) {
    historyViewHistory.push(historyView);
    historyView = view;
    historySlideDirection = 'forward';
    renderHistory();
}

function navigateHistoryBack() {
    // If we're at the root (list view) and have a return tab, go back to it
    if (historyViewHistory.length === 0 && historyView === 'list' && moreMenuReturnTab) {
        const returnTab = moreMenuReturnTab;
        moreMenuReturnTab = null;
        switchTab(returnTab);
        return;
    }

    // Otherwise navigate back in history stack
    if (historyViewHistory.length > 0) {
        historyView = historyViewHistory.pop();
    } else {
        historyView = 'list';
    }
    historySlideDirection = 'back';

    renderHistory();
}

// ============== History Data ==============

async function loadHistoryData() {
    try {
        const response = await fetch('/api/chat/conversations/recent?count=20');
        const data = await response.json();
        historyData = data.conversations || [];
        historyData.sort((a, b) => {
            const dateTimeA = `${a.date}T${a.time}`;
            const dateTimeB = `${b.date}T${b.time}`;
            return dateTimeB.localeCompare(dateTimeA);
        });
        renderHistory();
    } catch (error) {
        console.error('Failed to load history:', error);
        const container = document.getElementById('history-content');
        if (container) {
            container.innerHTML = '<div class="focus-empty">Failed to load history</div>';
        }
    }
}

// ============== History Rendering ==============

function renderHistory() {
    const container = document.getElementById('history-content');
    if (!container) return;

    let content;
    if (historyView === 'list') {
        content = renderHistoryList();
    } else if (historyView.startsWith('conversation-')) {
        const conversationId = historyView.substring(13);
        content = renderHistoryDetail(conversationId);
    } else {
        content = renderHistoryList();
    }

    // Apply slide animation
    if (historySlideDirection && container.querySelector('.view-slide-container')) {
        animateHistoryTransition(container, content, historySlideDirection);
        historySlideDirection = null;
    } else {
        container.innerHTML = `<div class="view-slide-container current">${content}</div>`;
    }

    // Initialize swipe handlers for history
    initHistorySwipeHandlers();
}

function animateHistoryTransition(container, newContent, direction) {
    const oldView = container.querySelector('.view-slide-container');
    if (!oldView) {
        container.innerHTML = `<div class="view-slide-container current">${newContent}</div>`;
        return;
    }

    const newView = document.createElement('div');
    newView.className = 'view-slide-container';
    newView.innerHTML = newContent;

    if (direction === 'forward') {
        newView.classList.add('slide-in-right');
    } else {
        newView.classList.add('slide-in-left');
    }

    container.appendChild(newView);
    newView.offsetHeight; // Trigger reflow

    if (direction === 'forward') {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-left');
    } else {
        oldView.classList.remove('current');
        oldView.classList.add('slide-out-right');
    }

    newView.classList.remove('slide-in-left', 'slide-in-right');
    newView.classList.add('current');

    setTimeout(() => {
        if (oldView.parentNode) oldView.remove();
    }, 300);
}

function renderHistoryList() {
    const header = `
        <div class="focus-view-header" onclick="navigateHistoryBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">History</span>
        </div>
    `;

    if (!historyData || historyData.length === 0) {
        return `
            ${header}
            <div class="focus-view-content">
                <div class="focus-empty">No conversations yet</div>
            </div>
        `;
    }

    const items = historyData.map(item => renderHistoryCard(item)).join('');

    return `
        ${header}
        <div class="focus-view-content" data-testid="history-list">
            ${items}
        </div>
    `;
}

function renderHistoryCard(item) {
    const friendlyDate = formatHistoryDate(item.date);
    const friendlyTime = formatHistoryTime(item.time);
    const preview = item.preview || 'No preview';

    const cardHtml = `
        <div class="card card-minimal" data-testid="history-card" onclick="navigateHistory('conversation-${item.conversation_id}')">
            <span class="card-title">${friendlyDate} ${friendlyTime}</span>
            <span class="card-preview">${escapeHtml(preview)}</span>
            <span class="card-arrow">${icon('chevron-right')}</span>
        </div>
    `;

    return wrapCardForHistorySwipe(cardHtml, item.conversation_id);
}

function wrapCardForHistorySwipe(cardHtml, conversationId) {
    return `
        <div class="swipe-container" data-conversation-id="${conversationId}" data-type="history">
            <div class="swipe-action swipe-action-right restore">
                ${icon('chat-bubble-left')}
            </div>
            <div class="swipe-action swipe-action-left danger">
                ${icon('trash')}
            </div>
            <div class="swipe-card">
                ${cardHtml}
            </div>
        </div>
    `;
}

function renderHistoryDetail(conversationId) {
    const item = historyData.find(h => h.conversation_id === conversationId);

    if (!item) {
        return `
            <div class="focus-view-header" onclick="navigateHistoryBack()">
                <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
                <span class="focus-view-title">Not Found</span>
            </div>
            <div class="focus-view-content">
                <div class="focus-empty">This conversation no longer exists.</div>
            </div>
        `;
    }

    const friendlyDate = formatHistoryDate(item.date);
    const friendlyTime = formatHistoryTime(item.time);

    return `
        <div class="focus-view-header" onclick="navigateHistoryBack()">
            <span class="focus-back-btn" data-testid="back-btn">${icon('chevron-left')}</span>
            <span class="focus-view-title">${friendlyDate} ${friendlyTime}</span>
        </div>
        <div class="focus-view-content" data-testid="history-detail">
            <div class="history-detail">
                <div class="history-detail-preview">${marked.parse(item.preview || 'No preview')}</div>
                <div class="history-detail-meta">${item.message_count || '?'} messages</div>
            </div>
            <div class="task-detail-actions">
                <button class="task-detail-action" data-testid="continue-btn" onclick="loadConversation('${item.conversation_id}')">${icon('chat-bubble-left')} Continue</button>
                <button class="task-detail-action danger" data-testid="delete-btn" onclick="deleteConversation('${item.conversation_id}')">${icon('trash')} Delete</button>
            </div>
        </div>
    `;
}

// ============== History Swipe Handlers ==============

let historySwipeElement = null;
let historySwipeCard = null;
let historySwipeConversationId = null;

let historySwipeHandlersInitialized = false;

function initHistorySwipeHandlers() {
    const historyContent = document.getElementById('history-content');
    if (!historyContent) return;

    // Only initialize once - use event delegation
    if (historySwipeHandlersInitialized) return;
    historySwipeHandlersInitialized = true;

    // Touch events
    historyContent.addEventListener('touchstart', handleHistorySwipeStart, { passive: true });
    historyContent.addEventListener('touchmove', handleHistorySwipeMove, { passive: false });
    historyContent.addEventListener('touchend', handleHistorySwipeEnd, { passive: true });
    historyContent.addEventListener('touchcancel', handleHistorySwipeCancel, { passive: true });

    // Mouse events
    historyContent.addEventListener('mousedown', handleHistoryMouseDown, { passive: true });
    document.addEventListener('mousemove', handleHistoryMouseMove, { passive: false });
    document.addEventListener('mouseup', handleHistoryMouseUp, { passive: true });

    // Prevent click after swipe
    historyContent.addEventListener('click', handleHistorySwipeClick, { capture: true });
}

let historyIsMouseDown = false;
let historyDidSwipe = false;
let historySwipeStartX = 0;
let historySwipeStartY = 0;
let historySwipeDeltaX = 0;
let historyIsSwipeActive = false;
let historySwipeStartTime = 0;

function handleHistorySwipeClick(e) {
    if (historyDidSwipe) {
        e.stopPropagation();
        e.preventDefault();
        historyDidSwipe = false;
    }
}

function handleHistorySwipeStart(e) {
    const swipeContainer = e.target.closest('.swipe-container[data-type="history"]');
    if (!swipeContainer) return;

    const card = swipeContainer.querySelector('.swipe-card');
    if (!card) return;

    historySwipeElement = swipeContainer;
    historySwipeCard = card;
    historySwipeConversationId = swipeContainer.dataset.conversationId;

    const touch = e.touches[0];
    historySwipeStartX = touch.clientX;
    historySwipeStartY = touch.clientY;
    historySwipeDeltaX = 0;
    historySwipeStartTime = Date.now();
    historyIsSwipeActive = false;

    historySwipeCard.style.transition = 'none';
}

function handleHistorySwipeMove(e) {
    if (!historySwipeElement || !historySwipeCard) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - historySwipeStartX;
    const deltaY = touch.clientY - historySwipeStartY;

    if (!historyIsSwipeActive && Math.abs(deltaY) > Math.abs(deltaX)) {
        resetHistorySwipeState();
        return;
    }

    if (Math.abs(deltaX) > 10) {
        historyIsSwipeActive = true;
        e.preventDefault();
    }

    if (!historyIsSwipeActive) return;

    historySwipeDeltaX = deltaX;
    const clampedDelta = Math.max(-swipeMaxDistance, Math.min(swipeMaxDistance, deltaX));
    historySwipeCard.style.transform = `translateX(${clampedDelta}px)`;
    updateHistorySwipeActionVisibility(clampedDelta);
}

function handleHistorySwipeEnd() {
    if (!historySwipeElement || !historySwipeCard) return;

    const duration = Date.now() - historySwipeStartTime;
    const velocity = Math.abs(historySwipeDeltaX) / duration;
    const shouldTrigger = Math.abs(historySwipeDeltaX) >= swipeThreshold || (velocity > 0.5 && Math.abs(historySwipeDeltaX) > 30);

    if (shouldTrigger && historyIsSwipeActive) {
        if (historySwipeDeltaX < 0) {
            triggerHistorySwipeLeft();
        } else if (historySwipeDeltaX > 0) {
            triggerHistorySwipeRight();
        }
    }

    if (historySwipeCard) {
        historySwipeCard.style.transition = 'transform 0.2s ease-out';
        historySwipeCard.style.transform = 'translateX(0)';
    }

    hideHistorySwipeActions();
    setTimeout(() => resetHistorySwipeState(), 200);
}

function handleHistorySwipeCancel() {
    if (historySwipeCard) {
        historySwipeCard.style.transition = 'transform 0.2s ease-out';
        historySwipeCard.style.transform = 'translateX(0)';
    }
    hideHistorySwipeActions();
    resetHistorySwipeState();
}

function handleHistoryMouseDown(e) {
    historyDidSwipe = false;
    if (e.button !== 0) return;

    const swipeContainer = e.target.closest('.swipe-container[data-type="history"]');
    if (!swipeContainer) return;

    const card = swipeContainer.querySelector('.swipe-card');
    if (!card) return;

    if (e.target.closest('button, a, input, textarea, select')) return;

    historyIsMouseDown = true;
    historySwipeElement = swipeContainer;
    historySwipeCard = card;
    historySwipeConversationId = swipeContainer.dataset.conversationId;

    historySwipeStartX = e.clientX;
    historySwipeStartY = e.clientY;
    historySwipeDeltaX = 0;
    historySwipeStartTime = Date.now();
    historyIsSwipeActive = false;

    historySwipeCard.style.transition = 'none';
}

function handleHistoryMouseMove(e) {
    if (!historyIsMouseDown || !historySwipeElement || !historySwipeCard) return;

    const deltaX = e.clientX - historySwipeStartX;
    const deltaY = e.clientY - historySwipeStartY;

    if (!historyIsSwipeActive && Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 10) {
        resetHistorySwipeState();
        historyIsMouseDown = false;
        return;
    }

    if (Math.abs(deltaX) > 5) {
        historyIsSwipeActive = true;
        historyDidSwipe = true;
    }

    if (!historyIsSwipeActive) return;

    historySwipeDeltaX = deltaX;
    const clampedDelta = Math.max(-swipeMaxDistance, Math.min(swipeMaxDistance, deltaX));
    historySwipeCard.style.transform = `translateX(${clampedDelta}px)`;
    updateHistorySwipeActionVisibility(clampedDelta);
}

function handleHistoryMouseUp() {
    if (!historyIsMouseDown) return;
    historyIsMouseDown = false;

    if (!historySwipeElement || !historySwipeCard) return;

    const duration = Date.now() - historySwipeStartTime;
    const velocity = Math.abs(historySwipeDeltaX) / duration;
    const shouldTrigger = Math.abs(historySwipeDeltaX) >= swipeThreshold || (velocity > 0.5 && Math.abs(historySwipeDeltaX) > 30);

    if (shouldTrigger && historyIsSwipeActive) {
        if (historySwipeDeltaX < 0) {
            triggerHistorySwipeLeft();
        } else if (historySwipeDeltaX > 0) {
            triggerHistorySwipeRight();
        }
    }

    if (historySwipeCard) {
        historySwipeCard.style.transition = 'transform 0.2s ease-out';
        historySwipeCard.style.transform = 'translateX(0)';
    }

    hideHistorySwipeActions();
    setTimeout(() => resetHistorySwipeState(), 200);
}

function updateHistorySwipeActionVisibility(deltaX) {
    if (!historySwipeElement) return;

    const leftAction = historySwipeElement.querySelector('.swipe-action-left');
    const rightAction = historySwipeElement.querySelector('.swipe-action-right');

    if (deltaX < 0 && leftAction) {
        const progress = Math.min(1, Math.abs(deltaX) / swipeThreshold);
        leftAction.style.opacity = progress;
        leftAction.classList.toggle('triggered', Math.abs(deltaX) >= swipeThreshold);
    } else if (leftAction) {
        leftAction.style.opacity = 0;
        leftAction.classList.remove('triggered');
    }

    if (deltaX > 0 && rightAction) {
        const progress = Math.min(1, Math.abs(deltaX) / swipeThreshold);
        rightAction.style.opacity = progress;
        rightAction.classList.toggle('triggered', Math.abs(deltaX) >= swipeThreshold);
    } else if (rightAction) {
        rightAction.style.opacity = 0;
        rightAction.classList.remove('triggered');
    }
}

function hideHistorySwipeActions() {
    if (!historySwipeElement) return;

    const leftAction = historySwipeElement.querySelector('.swipe-action-left');
    const rightAction = historySwipeElement.querySelector('.swipe-action-right');

    if (leftAction) {
        leftAction.style.opacity = 0;
        leftAction.classList.remove('triggered');
    }
    if (rightAction) {
        rightAction.style.opacity = 0;
        rightAction.classList.remove('triggered');
    }
}

function resetHistorySwipeState() {
    if (historySwipeCard) {
        historySwipeCard.style.transition = '';
        historySwipeCard.style.transform = '';
    }
    historySwipeElement = null;
    historySwipeCard = null;
    historySwipeConversationId = null;
    historySwipeDeltaX = 0;
    historyIsSwipeActive = false;
}

// ============== Swipe Actions ==============

function triggerHistorySwipeLeft() {
    // Swipe left = delete
    if (!historySwipeConversationId) return;
    deleteConversation(historySwipeConversationId);
}

function triggerHistorySwipeRight() {
    // Swipe right = load into chat
    if (!historySwipeConversationId) return;
    loadConversation(historySwipeConversationId);
}

// ============== History Actions ==============

async function loadConversation(oldConversationId) {
    try {
        const response = await fetch('/api/chat/conversations/fork', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: oldConversationId })
        });
        if (!response.ok) throw new Error('Failed to fork');
        const data = await response.json();

        conversationId = data.new_conversation_id;
        viewingHistoryConversationId = oldConversationId;

        if (oldConversationId && oldConversationId.startsWith('topic-')) {
            const topicId = oldConversationId.substring(6);
            const topic = typeof topicsData !== 'undefined' ? topicsData.find(j => j.id === topicId) : null;
            chatTopicContext = topicId;
            chatTopicName = topic ? topic.name : 'Topic';
            if (typeof topicConversationIds !== 'undefined') {
                topicConversationIds[topicId] = conversationId;
            }
            if (typeof updateInputContext === 'function') {
                updateInputContext();
            }
        } else {
            chatTopicContext = null;
            chatTopicName = null;
            if (typeof updateInputContext === 'function') {
                updateInputContext();
            }
        }

        inlineMessages.innerHTML = '';
        for (const msg of data.messages) {
            addInlineMessage(msg.content, msg.role === 'user' ? 'you' : 'friend');
        }

        // Clear the return tab so we go to chat
        moreMenuReturnTab = null;
        switchTab('chat');
        contextInput.focus();
    } catch (error) {
        console.error('Failed to load conversation:', error);
    }
}

async function deleteConversation(targetConversationId) {
    try {
        const response = await fetch(`/api/chat/conversations/${targetConversationId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete');

        if (targetConversationId === viewingHistoryConversationId) {
            inlineMessages.innerHTML = '';
            viewingHistoryConversationId = null;
        }

        // If viewing detail, go back to list
        if (historyView.startsWith('conversation-')) {
            historyView = 'list';
        }

        await loadHistoryData();
    } catch (error) {
        console.error('Failed to delete conversation:', error);
    }
}

// Legacy aliases
async function forkConversation(oldConversationId) {
    return loadConversation(oldConversationId);
}

async function archiveConversation(targetConversationId) {
    await deleteConversation(targetConversationId);
}

async function deleteConversationById(targetConversationId) {
    await deleteConversation(targetConversationId);
}
