// Euno - Global State
// Configure marked
marked.setOptions({ breaks: true, gfm: true, headerIds: false, mangle: false });

// State
let sessionId = localStorage.getItem('sessionId') || null;
let viewingHistorySessionId = null;
let isWaiting = false;
let activeTab = localStorage.getItem('activeTab') || 'chat';
let expandedCards = new Set();
let tasksData = [];
let completedTasksData = [];
let projectsData = [];
let projectNotesData = {};
let historyData = [];
let uploadXhr = null;
let settingsData = null;

// Focus tab navigation state
let focusView = 'menu';
let focusViewHistory = [];
let archivingTaskId = null;

// Tab order for slide animations (left to right)
const TAB_ORDER = ['chat', 'focus', 'history', 'about', 'settings'];
let previousTab = activeTab;

// History tab navigation state
let historyView = 'list';
let historyViewHistory = [];

// Elements
const appContainer = document.getElementById('app-container');
