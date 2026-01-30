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
                display: block;
                border: 1px solid var(--color-border, #e0e0e0);
                border-radius: var(--radius-lg, 12px);
                overflow: hidden;
                text-decoration: none;
                color: inherit;
                background: var(--color-bg-white, #fff);
                transition: box-shadow 0.2s ease, border-color 0.2s ease;
                max-width: 500px;
            }
            .link-preview-card:hover {
                border-color: var(--color-border-hover, #ccc);
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }
            .link-preview-image {
                width: 100%;
                max-height: 250px;
                overflow: hidden;
                background: var(--color-bg-subtle, #f5f5f5);
            }
            .link-preview-image img {
                width: 100%;
                height: auto;
                display: block;
                object-fit: cover;
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
