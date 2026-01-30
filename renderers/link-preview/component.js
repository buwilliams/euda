/**
 * Link Preview Renderer
 *
 * Displays rich link previews from Open Graph metadata.
 * Expects data with: url, title, description, image, site_name
 */

/**
 * Render a link preview card.
 * @param {HTMLElement} container - Container element to render into
 * @param {Object} data - Link preview data
 * @param {Object} ctx - Render context (display mode, etc.)
 */
export function render(container, data, ctx) {
    const { url, title, description, image, site_name, type } = data || {};

    if (!url) {
        container.innerHTML = '<div class="link-preview-error">No URL provided</div>';
        return;
    }

    // Extract domain for display
    let domain = '';
    try {
        domain = new URL(url).hostname.replace(/^www\./, '');
    } catch (e) {
        domain = url;
    }

    // Build the card HTML
    const hasImage = image && image.trim();
    const hasTitle = title && title.trim();
    const hasDescription = description && description.trim();

    const imageHtml = hasImage
        ? `<div class="link-preview-image">
               <img src="${escapeHtml(image)}" alt="${escapeHtml(title || 'Preview')}" loading="lazy" onerror="this.parentElement.style.display='none'">
           </div>`
        : '';

    const titleHtml = hasTitle
        ? `<div class="link-preview-title">${escapeHtml(title)}</div>`
        : `<div class="link-preview-title">${escapeHtml(domain)}</div>`;

    const descriptionHtml = hasDescription
        ? `<div class="link-preview-description">${escapeHtml(description)}</div>`
        : '';

    const siteHtml = site_name
        ? `<span class="link-preview-site">${escapeHtml(site_name)}</span>`
        : `<span class="link-preview-site">${escapeHtml(domain)}</span>`;

    container.innerHTML = `
        <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="link-preview-card">
            ${imageHtml}
            <div class="link-preview-content">
                ${titleHtml}
                ${descriptionHtml}
                <div class="link-preview-meta">
                    ${siteHtml}
                </div>
            </div>
        </a>
        <style>
            .link-preview-card {
                display: block !important;
                border: 2px solid #ccc !important;
                border-radius: 12px !important;
                overflow: hidden !important;
                text-decoration: none !important;
                color: inherit !important;
                background: #fff !important;
                transition: box-shadow 0.2s ease, border-color 0.2s ease !important;
                max-width: min(500px, 100%) !important;
                width: 100% !important;
                margin: 8px 0 !important;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
                box-sizing: border-box !important;
            }
            .link-preview-card:hover {
                border-color: #999 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
            }
            .link-preview-image {
                width: 100% !important;
                height: 180px !important;
                overflow: hidden !important;
                background: #f0f0f0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 12px !important;
                box-sizing: border-box !important;
            }
            .link-preview-image img {
                max-width: 100% !important;
                max-height: 100% !important;
                width: auto !important;
                height: auto !important;
                display: block !important;
                object-fit: contain !important;
            }
            .link-preview-content {
                padding: 12px 16px;
            }
            .link-preview-title {
                font-weight: 600;
                font-size: 1rem;
                line-height: 1.3;
                margin-bottom: 4px;
                color: var(--color-text-primary, #333);
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            .link-preview-description {
                font-size: 0.875rem;
                line-height: 1.4;
                color: var(--color-text-secondary, #666);
                margin-bottom: 8px;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            .link-preview-meta {
                font-size: 0.75rem;
                color: var(--color-text-muted, #999);
            }
            .link-preview-site {
                text-transform: lowercase;
            }
            .link-preview-error {
                padding: 12px 16px;
                background: var(--color-bg-subtle, #f5f5f5);
                border-radius: var(--radius-md, 8px);
                color: var(--color-text-muted, #999);
                font-style: italic;
            }
        </style>
    `;
}

/**
 * Cleanup function called when renderer is unmounted.
 * @param {HTMLElement} container - Container element
 */
export function destroy(container) {
    container.innerHTML = '';
}

/**
 * Escape HTML to prevent XSS.
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
