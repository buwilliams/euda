// Euno - Browser Notifications
// Uses Web Notifications API for cross-browser system notifications

// State
let notificationPermission = 'default';
let browserNotificationsEnabled = true;  // Default on
let lastNotificationTime = 0;
const NOTIFICATION_THROTTLE_MS = 1000;  // Max 1 per second

// Check if browser supports notifications
function hasNotificationSupport() {
    return 'Notification' in window;
}

// Initialize notification system
function initNotifications() {
    if (!hasNotificationSupport()) {
        console.log('Browser notifications not supported');
        return;
    }

    notificationPermission = Notification.permission;

    // Load user preference from localStorage
    const saved = localStorage.getItem('browserNotificationsEnabled');
    if (saved !== null) {
        browserNotificationsEnabled = saved === 'true';
    }

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);

    console.log('Browser notifications initialized', {
        permission: notificationPermission,
        enabled: browserNotificationsEnabled
    });
}

// Check if page is currently visible
function isPageVisible() {
    return !document.hidden;
}

// Determine if we should show browser notification
function shouldShowBrowserNotification() {
    if (!hasNotificationSupport()) return false;
    if (!browserNotificationsEnabled) return false;
    if (notificationPermission !== 'granted') return false;

    // Show if page is hidden OR not on chat tab
    return !isPageVisible() || activeTab !== 'chat';
}

// Request notification permission
async function requestNotificationPermission() {
    if (!hasNotificationSupport()) return false;
    if (notificationPermission === 'granted') return true;
    if (notificationPermission === 'denied') return false;

    try {
        const permission = await Notification.requestPermission();
        notificationPermission = permission;
        console.log('Notification permission:', permission);
        return permission === 'granted';
    } catch (error) {
        console.error('Failed to request notification permission:', error);
        return false;
    }
}

// Show browser notification
function showBrowserNotification(message, agentName = 'Euno') {
    if (!shouldShowBrowserNotification()) return;

    // Throttle notifications
    const now = Date.now();
    if (now - lastNotificationTime < NOTIFICATION_THROTTLE_MS) {
        console.log('Notification throttled');
        return;
    }
    lastNotificationTime = now;

    // Truncate long messages
    const body = message.length > 100
        ? message.substring(0, 97) + '...'
        : message;

    try {
        const notification = new Notification(agentName, {
            body: body,
            icon: '/static/images/euno-logo.png',
            badge: '/static/images/euno-logo.png',
            tag: 'euno-agent-message',  // Replace previous
            requireInteraction: false,
            silent: false,
            timestamp: Date.now(),
            data: {
                type: 'agent_message',
                agent: agentName,
                timestamp: new Date().toISOString()
            }
        });

        // Handle notification click
        notification.onclick = function() {
            window.focus();
            if (typeof switchTab === 'function') {
                switchTab('chat');
            }
            notification.close();
        };

        // Auto-close after 5 seconds as backup
        setTimeout(() => notification.close(), 5000);

        console.log('Browser notification shown:', agentName, body);
    } catch (error) {
        console.error('Failed to show notification:', error);
    }
}

// Request permission when user receives first message while away
function maybeRequestNotificationPermission() {
    if (!hasNotificationSupport()) return;
    if (notificationPermission !== 'default') return;

    // Only request if user is not on chat tab or page is hidden
    if (!isPageVisible() || activeTab !== 'chat') {
        console.log('Requesting notification permission...');
        requestNotificationPermission();
    }
}

// Handle visibility changes
function handleVisibilityChange() {
    if (isPageVisible() && activeTab === 'chat') {
        // Clear notification badge when user returns to chat
        if (typeof clearChatNotification === 'function') {
            clearChatNotification();
        }
    }
}

// Toggle browser notifications on/off
function setBrowserNotificationsEnabled(enabled) {
    browserNotificationsEnabled = enabled;
    localStorage.setItem('browserNotificationsEnabled', enabled.toString());
    console.log('Browser notifications', enabled ? 'enabled' : 'disabled');
}

// Get current notification status (for settings UI)
function getNotificationStatus() {
    return {
        supported: hasNotificationSupport(),
        permission: notificationPermission,
        enabled: browserNotificationsEnabled
    };
}
