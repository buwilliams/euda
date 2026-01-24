// Euno - Focus View Memory Renderers
// Memory-related render helpers (short-term, long-term, reflection)

// ============== Memory Render Functions ==============

function renderShortTermMemoryContent(items, agentId) {
    if (!items || items.length === 0) {
        return `
            <div class="focus-empty">No short-term memory items.</div>
            <div class="memory-actions">
                <button class="btn-secondary memory-add" onclick="addMemoryItem('${agentId}')">+ Add Memory</button>
            </div>
        `;
    }

    const state = memoryPageState[agentId] || { page: 0, pageSize: 10 };
    const start = state.page * state.pageSize;
    const end = start + state.pageSize;
    const pageItems = items.slice(start, end);
    const totalPages = Math.ceil(items.length / state.pageSize);

    const typeColors = {
        person: 'type-person',
        place: 'type-place',
        thing: 'type-thing',
        goal: 'type-goal',
        concern: 'type-concern',
        idea: 'type-idea',
        learning: 'type-learning',
        behavior: 'type-behavior'
    };

    return `
        <div class="memory-list">
            ${pageItems.map(item => `
                <div class="memory-item">
                    <span class="memory-type-badge ${typeColors[item.type] || 'type-thing'}">${escapeHtml(item.type)}</span>
                    <span class="memory-description">${escapeHtml(item.short_description)}</span>
                    <button class="memory-delete" onclick="deleteMemoryItem('${agentId}', '${item.id}')" title="Delete">&times;</button>
                </div>
            `).join('')}
        </div>
        ${totalPages > 1 ? `
        <div class="memory-pagination">
            <button class="memory-page-btn" onclick="pageMemory('${agentId}', 'prev')" ${state.page === 0 ? 'disabled' : ''}>Prev</button>
            <span class="memory-page-info">${state.page + 1} / ${totalPages}</span>
            <button class="memory-page-btn" onclick="pageMemory('${agentId}', 'next')" ${end >= items.length ? 'disabled' : ''}>Next</button>
        </div>
        ` : ''}
        <div class="memory-actions">
            <button class="btn-secondary memory-add" onclick="addMemoryItem('${agentId}')">+ Add Memory</button>
        </div>
    `;
}

function renderLongTermMemoryContent(dates, currentDate, content, agentId) {
    if (!dates || dates.length === 0) {
        return '<div class="focus-empty">No long-term memory entries.</div>';
    }

    const currentIndex = dates.indexOf(currentDate);
    const hasPrev = currentIndex < dates.length - 1;
    const hasNext = currentIndex > 0;

    const memoryContent = content?.content || content?.entries?.join('\n\n') || 'No content for this date.';

    return `
        <div class="long-term-memory">
            <div class="memory-date-nav">
                <button class="memory-page-btn" onclick="loadLongTermMemoryDate('${agentId}', '${dates[currentIndex + 1] || currentDate}')" ${!hasPrev ? 'disabled' : ''}>Older</button>
                <span class="memory-date-current">${currentDate}</span>
                <button class="memory-page-btn" onclick="loadLongTermMemoryDate('${agentId}', '${dates[currentIndex - 1] || currentDate}')" ${!hasNext ? 'disabled' : ''}>Newer</button>
            </div>
            <div class="long-term-content">${escapeHtml(memoryContent)}</div>
        </div>
    `;
}

// ============== Reflection Render Functions ==============

function renderReflectionContent(data, agentId) {
    const logs = data?.logs || [];

    return `
        <div class="reflection-section">
            <div class="reflection-actions">
                <button class="btn-primary" onclick="triggerReflection('${agentId}', 'consolidate')">Run Consolidate</button>
            </div>
            <div class="reflection-logs">
                <div class="monitoring-section-title">Recent Activity (7 days)</div>
                ${logs.length === 0 ? '<div class="focus-empty">No reflection activity recorded.</div>' :
                  logs.slice(0, 20).map(log => {
                      const eventType = log.phase || log.event || 'unknown';
                      const eventClass = eventType === 'append' ? 'log-event-append' :
                                        eventType === 'consolidate' ? 'log-event-consolidate' :
                                        eventType === 'error' ? 'log-event-error' : '';
                      return `
                          <div class="reflection-log-entry">
                              <span class="log-time">${formatPromptTime(log.timestamp)}</span>
                              <span class="log-event ${eventClass}">${escapeHtml(eventType)}</span>
                              <span class="log-detail">${escapeHtml(log.message || log.details || '')}</span>
                          </div>
                      `;
                  }).join('')
                }
            </div>
        </div>
    `;
}

