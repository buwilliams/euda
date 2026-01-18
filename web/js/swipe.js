// Euno - Swipe Gesture Handling for Job Cards

// ============== Swipe State ==============

let swipeStartX = 0;
let swipeStartY = 0;
let swipeCurrentX = 0;
let swipeDeltaX = 0;
let swipeElement = null;
let swipeCard = null;
let swipeJobId = null;
let swipeIsCompleted = false;
let swipeThreshold = 80; // pixels to trigger action
let swipeMaxDistance = 120;
let isSwipeActive = false;
let swipeStartTime = 0;

// ============== Swipe Initialization ==============

function initSwipeHandlers() {
    const focusContent = document.getElementById('focus-content');
    if (!focusContent) return;

    // Touch events (mobile)
    focusContent.addEventListener('touchstart', handleSwipeStart, { passive: true });
    focusContent.addEventListener('touchmove', handleSwipeMove, { passive: false });
    focusContent.addEventListener('touchend', handleSwipeEnd, { passive: true });
    focusContent.addEventListener('touchcancel', handleSwipeCancel, { passive: true });

    // Mouse events (desktop)
    focusContent.addEventListener('mousedown', handleMouseDown, { passive: true });
    document.addEventListener('mousemove', handleMouseMove, { passive: false });
    document.addEventListener('mouseup', handleMouseUp, { passive: true });

    // Prevent click after swipe
    focusContent.addEventListener('click', handleSwipeClick, { capture: true });
}

function handleSwipeClick(e) {
    // If a swipe just occurred, prevent the click from navigating
    if (didSwipe) {
        e.stopPropagation();
        e.preventDefault();
        didSwipe = false;
    }
}

// ============== Touch Event Handlers ==============

function handleSwipeStart(e) {
    // Find swipeable card
    const swipeContainer = e.target.closest('.swipe-container');
    if (!swipeContainer) return;

    const card = swipeContainer.querySelector('.swipe-card');
    if (!card) return;

    swipeElement = swipeContainer;
    swipeCard = card;
    swipeJobId = swipeContainer.dataset.jobId;
    swipeIsCompleted = swipeContainer.dataset.completed === 'true';

    const touch = e.touches[0];
    swipeStartX = touch.clientX;
    swipeStartY = touch.clientY;
    swipeCurrentX = swipeStartX;
    swipeDeltaX = 0;
    swipeStartTime = Date.now();
    isSwipeActive = false;

    // Remove transition during swipe
    swipeCard.style.transition = 'none';
}

function handleSwipeMove(e) {
    if (!swipeElement || !swipeCard) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - swipeStartX;
    const deltaY = touch.clientY - swipeStartY;

    // If vertical movement is greater, don't swipe (allow scrolling)
    if (!isSwipeActive && Math.abs(deltaY) > Math.abs(deltaX)) {
        resetSwipeState();
        return;
    }

    // Once we determine it's a horizontal swipe, prevent vertical scroll
    if (Math.abs(deltaX) > 10) {
        isSwipeActive = true;
        e.preventDefault();
    }

    if (!isSwipeActive) return;

    swipeCurrentX = touch.clientX;
    swipeDeltaX = deltaX;

    // Clamp the swipe distance
    const clampedDelta = Math.max(-swipeMaxDistance, Math.min(swipeMaxDistance, deltaX));

    // Apply transform
    swipeCard.style.transform = `translateX(${clampedDelta}px)`;

    // Show appropriate action background
    updateSwipeActionVisibility(clampedDelta);
}

function handleSwipeEnd(e) {
    if (!swipeElement || !swipeCard) return;

    const duration = Date.now() - swipeStartTime;
    const velocity = Math.abs(swipeDeltaX) / duration;

    // Trigger action if threshold met or fast swipe
    const shouldTrigger = Math.abs(swipeDeltaX) >= swipeThreshold || (velocity > 0.5 && Math.abs(swipeDeltaX) > 30);

    if (shouldTrigger && isSwipeActive) {
        if (swipeDeltaX < 0) {
            // Swipe left
            triggerSwipeLeftAction();
        } else if (swipeDeltaX > 0) {
            // Swipe right
            triggerSwipeRightAction();
        }
    }

    // Animate back to original position
    if (swipeCard) {
        swipeCard.style.transition = 'transform 0.2s ease-out';
        swipeCard.style.transform = 'translateX(0)';
    }

    // Hide action backgrounds
    hideSwipeActions();

    // Reset state after animation
    setTimeout(() => {
        resetSwipeState();
    }, 200);
}

function handleSwipeCancel() {
    if (swipeCard) {
        swipeCard.style.transition = 'transform 0.2s ease-out';
        swipeCard.style.transform = 'translateX(0)';
    }
    hideSwipeActions();
    resetSwipeState();
}

// ============== Mouse Event Handlers (Desktop) ==============

let isMouseDown = false;
let didSwipe = false; // Track if a swipe occurred to prevent click

function handleMouseDown(e) {
    didSwipe = false;
    // Only handle left mouse button
    if (e.button !== 0) return;

    // Find swipeable card
    const swipeContainer = e.target.closest('.swipe-container');
    if (!swipeContainer) return;

    const card = swipeContainer.querySelector('.swipe-card');
    if (!card) return;

    // Don't start swipe if clicking on a button or interactive element
    if (e.target.closest('button, a, input, textarea, select')) return;

    isMouseDown = true;
    swipeElement = swipeContainer;
    swipeCard = card;
    swipeJobId = swipeContainer.dataset.jobId;
    swipeIsCompleted = swipeContainer.dataset.completed === 'true';

    swipeStartX = e.clientX;
    swipeStartY = e.clientY;
    swipeCurrentX = swipeStartX;
    swipeDeltaX = 0;
    swipeStartTime = Date.now();
    isSwipeActive = false;

    // Remove transition during swipe
    swipeCard.style.transition = 'none';
}

function handleMouseMove(e) {
    if (!isMouseDown || !swipeElement || !swipeCard) return;

    const deltaX = e.clientX - swipeStartX;
    const deltaY = e.clientY - swipeStartY;

    // If vertical movement is greater initially, cancel swipe
    if (!isSwipeActive && Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 10) {
        resetSwipeState();
        isMouseDown = false;
        return;
    }

    // Once horizontal movement is detected, activate swipe
    if (Math.abs(deltaX) > 5) {
        isSwipeActive = true;
        didSwipe = true;
    }

    if (!isSwipeActive) return;

    swipeCurrentX = e.clientX;
    swipeDeltaX = deltaX;

    // Clamp the swipe distance
    const clampedDelta = Math.max(-swipeMaxDistance, Math.min(swipeMaxDistance, deltaX));

    // Apply transform
    swipeCard.style.transform = `translateX(${clampedDelta}px)`;

    // Show appropriate action background
    updateSwipeActionVisibility(clampedDelta);
}

function handleMouseUp(e) {
    if (!isMouseDown) return;
    isMouseDown = false;

    if (!swipeElement || !swipeCard) return;

    const duration = Date.now() - swipeStartTime;
    const velocity = Math.abs(swipeDeltaX) / duration;

    // Trigger action if threshold met or fast swipe
    const shouldTrigger = Math.abs(swipeDeltaX) >= swipeThreshold || (velocity > 0.5 && Math.abs(swipeDeltaX) > 30);

    if (shouldTrigger && isSwipeActive) {
        if (swipeDeltaX < 0) {
            triggerSwipeLeftAction();
        } else if (swipeDeltaX > 0) {
            triggerSwipeRightAction();
        }
    }

    // Animate back to original position
    if (swipeCard) {
        swipeCard.style.transition = 'transform 0.2s ease-out';
        swipeCard.style.transform = 'translateX(0)';
    }

    // Hide action backgrounds
    hideSwipeActions();

    // Reset state after animation
    setTimeout(() => {
        resetSwipeState();
    }, 200);
}

// ============== Swipe Actions ==============

function triggerSwipeLeftAction() {
    if (!swipeJobId) return;

    if (swipeIsCompleted) {
        // Delete completed job
        deleteJob(null, swipeJobId);
    } else {
        // Complete active job
        completeJob(null, swipeJobId);
    }
}

function triggerSwipeRightAction() {
    if (!swipeJobId) return;

    if (swipeIsCompleted) {
        // Restore completed job
        restoreJob(null, swipeJobId);
    } else {
        // Open when picker for active job
        openWhenPicker('job', swipeJobId);
    }
}

// ============== Visual Feedback ==============

function updateSwipeActionVisibility(deltaX) {
    if (!swipeElement) return;

    const leftAction = swipeElement.querySelector('.swipe-action-left');
    const rightAction = swipeElement.querySelector('.swipe-action-right');

    if (deltaX < 0 && leftAction) {
        // Swiping left - show left action (on right side)
        const progress = Math.min(1, Math.abs(deltaX) / swipeThreshold);
        leftAction.style.opacity = progress;
        leftAction.classList.toggle('triggered', Math.abs(deltaX) >= swipeThreshold);
    } else if (leftAction) {
        leftAction.style.opacity = 0;
        leftAction.classList.remove('triggered');
    }

    if (deltaX > 0 && rightAction) {
        // Swiping right - show right action (on left side)
        const progress = Math.min(1, Math.abs(deltaX) / swipeThreshold);
        rightAction.style.opacity = progress;
        rightAction.classList.toggle('triggered', Math.abs(deltaX) >= swipeThreshold);
    } else if (rightAction) {
        rightAction.style.opacity = 0;
        rightAction.classList.remove('triggered');
    }
}

function hideSwipeActions() {
    if (!swipeElement) return;

    const leftAction = swipeElement.querySelector('.swipe-action-left');
    const rightAction = swipeElement.querySelector('.swipe-action-right');

    if (leftAction) {
        leftAction.style.opacity = 0;
        leftAction.classList.remove('triggered');
    }
    if (rightAction) {
        rightAction.style.opacity = 0;
        rightAction.classList.remove('triggered');
    }
}

function resetSwipeState() {
    if (swipeCard) {
        swipeCard.style.transition = '';
        swipeCard.style.transform = '';
    }
    swipeElement = null;
    swipeCard = null;
    swipeJobId = null;
    swipeIsCompleted = false;
    swipeDeltaX = 0;
    isSwipeActive = false;
}

// ============== Card Wrapper Functions ==============

function wrapCardForSwipe(cardHtml, jobId, isCompleted = false) {
    const leftActionIcon = isCompleted ? icon('trash') : icon('check');
    const leftActionClass = isCompleted ? 'danger' : 'complete';

    const rightActionIcon = isCompleted ? icon('arrow-uturn-left') : icon('calendar');
    const rightActionClass = isCompleted ? 'restore' : 'when';

    return `
        <div class="swipe-container" data-job-id="${jobId}" data-completed="${isCompleted}">
            <div class="swipe-action swipe-action-right ${rightActionClass}">
                ${rightActionIcon}
            </div>
            <div class="swipe-action swipe-action-left ${leftActionClass}">
                ${leftActionIcon}
            </div>
            <div class="swipe-card">
                ${cardHtml}
            </div>
        </div>
    `;
}
