// Euno - Renderer Loader
// Dynamically loads and manages pluggable UI renderers

// Cache for loaded renderer modules
const rendererCache = {};

// Cache for renderer metadata
let rendererMetadataCache = null;

/**
 * Fetch the list of available renderers from the API.
 * @returns {Promise<Array>} List of renderer metadata objects
 */
async function fetchRendererList() {
    if (rendererMetadataCache !== null) {
        return rendererMetadataCache;
    }

    try {
        const response = await fetch('/api/renderers');
        if (!response.ok) {
            console.error('Failed to fetch renderers:', response.status);
            return [];
        }
        const data = await response.json();
        rendererMetadataCache = data.renderers || [];
        return rendererMetadataCache;
    } catch (error) {
        console.error('Error fetching renderers:', error);
        return [];
    }
}

/**
 * Load a renderer module by name.
 * Uses dynamic import to load the component.js file.
 * @param {string} name - Renderer name
 * @returns {Promise<Object|null>} Renderer module with render() function, or null if not found
 */
async function loadRenderer(name) {
    // Return cached renderer if available
    if (rendererCache[name]) {
        return rendererCache[name];
    }

    try {
        // Dynamic import of the renderer's component.js
        // Always use cache-busting during development to ensure fresh content
        const cacheBuster = `?v=${Date.now()}`;
        const module = await import(`/api/renderers/${name}/component.js${cacheBuster}`);

        // Validate the module has required exports
        if (typeof module.render !== 'function') {
            console.error(`Renderer '${name}' missing required render() function`);
            return null;
        }

        // Cache the module
        rendererCache[name] = module;
        return module;
    } catch (error) {
        console.error(`Failed to load renderer '${name}':`, error);
        return null;
    }
}

/**
 * Check if a string is a valid render envelope.
 * An envelope is a JSON object with 'renderer' and 'data' fields.
 * @param {string} content - String to check
 * @returns {Object|null} Parsed envelope or null if not valid
 */
function parseRenderEnvelope(content) {
    if (!content || typeof content !== 'string') {
        return null;
    }

    // Quick check - must start with { to be JSON
    const trimmed = content.trim();
    if (!trimmed.startsWith('{')) {
        return null;
    }

    try {
        const parsed = JSON.parse(trimmed);

        // Validate envelope structure
        if (parsed && typeof parsed.renderer === 'string' && parsed.data !== undefined) {
            return parsed;
        }
    } catch (e) {
        // Not valid JSON
    }

    return null;
}

/**
 * Render an envelope's content into a container element.
 * @param {Object} envelope - Parsed envelope with renderer, data, and optional display hint
 * @param {HTMLElement} container - Container element to render into
 * @param {Object} context - Optional context (e.g., { display: 'embed' })
 * @returns {Promise<boolean>} True if rendered successfully, false otherwise
 */
async function renderEnvelope(envelope, container, context = {}) {
    if (!envelope || !envelope.renderer || !container) {
        return false;
    }

    const renderer = await loadRenderer(envelope.renderer);
    if (!renderer) {
        // Renderer not found - show fallback
        container.innerHTML = `<div class="renderer-error">Renderer '${escapeHtml(envelope.renderer)}' not available</div>`;
        return false;
    }

    try {
        // Merge display hint from envelope with provided context
        const ctx = {
            display: envelope.display || 'embed',
            ...context,
        };

        // Call the renderer's render function
        await renderer.render(container, envelope.data, ctx);
        return true;
    } catch (error) {
        console.error(`Error rendering with '${envelope.renderer}':`, error);
        container.innerHTML = `<div class="renderer-error">Error rendering content</div>`;
        return false;
    }
}

/**
 * Process message content, detecting and rendering any envelope content.
 * If the content is an envelope, renders it; otherwise returns null.
 * @param {string} content - Message content to process
 * @param {HTMLElement} container - Container element for rendering
 * @returns {Promise<boolean>} True if envelope was rendered, false if content is not an envelope
 */
async function processMessageContent(content, container) {
    const envelope = parseRenderEnvelope(content);
    if (!envelope) {
        return false;
    }

    return await renderEnvelope(envelope, container, { display: 'embed' });
}

/**
 * Clear the renderer cache.
 * Call this to force reload of renderer modules.
 */
function invalidateRendererCache() {
    Object.keys(rendererCache).forEach(key => delete rendererCache[key]);
    rendererMetadataCache = null;
}

/**
 * Get metadata for a specific renderer.
 * @param {string} name - Renderer name
 * @returns {Promise<Object|null>} Renderer metadata or null if not found
 */
async function getRendererMetadata(name) {
    const renderers = await fetchRendererList();
    return renderers.find(r => r.name === name) || null;
}

/**
 * Check if a renderer exists and is available.
 * @param {string} name - Renderer name
 * @returns {Promise<boolean>} True if renderer is available
 */
async function isRendererAvailable(name) {
    const metadata = await getRendererMetadata(name);
    return metadata !== null;
}
