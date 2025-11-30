/**
 * Share Property Functionality
 * Reusable JavaScript for sharing property listings
 * 
 * Usage:
 * - Add class "share-property-btn" to any button
 * - Add data-property-id attribute with the property ID
 * - Optionally add data-property-url for custom URL (defaults to current page with ?property=ID)
 * - Call initSharePropertyButtons() after DOM is ready
 * 
 * Or use shareProperty(propertyId, options) directly
 */

(function() {
    'use strict';

    /**
     * Share a property using Web Share API or clipboard
     * @param {number|string} propertyId - The property ID
     * @param {Object} options - Configuration options
     * @param {string} options.url - Custom share URL (optional)
     * @param {string} options.title - Property title (optional)
     * @param {string} options.text - Share text (optional)
     * @param {string} options.price - Property price (optional)
     * @param {string} options.currency - Currency code (optional)
     * @param {Function} options.onSuccess - Success callback (optional)
     * @param {Function} options.onError - Error callback (optional)
     */
    async function shareProperty(propertyId, options = {}) {
        if (!propertyId) {
            console.error('Property ID is required');
            return;
        }

        // Generate shareable URL
        const shareUrl = options.url || `${window.location.origin}${window.location.pathname}?property=${propertyId}`;
        const shareTitle = options.title || 'Property Listing';
        const priceText = options.price ? `${options.currency || 'UGX'} ${formatNumber(options.price)}` : '';
        const shareText = options.text || `Check out this property: ${shareTitle}${priceText ? ' - ' + priceText : ''}`;

        // Try Web Share API first (mobile devices)
        if (navigator.share) {
            try {
                await navigator.share({
                    title: shareTitle,
                    text: shareText,
                    url: shareUrl
                });
                
                // Show success message
                if (typeof Swal !== 'undefined') {
                    const Toast = Swal.mixin({
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 2000,
                        timerProgressBar: true
                    });
                    
                    Toast.fire({
                        icon: 'success',
                        title: 'Shared successfully!'
                    });
                }
                
                if (options.onSuccess) {
                    options.onSuccess({ method: 'web-share', url: shareUrl });
                }
                return;
            } catch (error) {
                // User cancelled or error occurred, fall through to clipboard
                if (error.name !== 'AbortError') {
                    console.error('Error sharing:', error);
                    if (options.onError) {
                        options.onError(error);
                    }
                } else {
                    // User cancelled, don't show error
                    return;
                }
            }
        }
        
        // Fallback to clipboard
        try {
            await navigator.clipboard.writeText(shareUrl);
            
            // Show success message
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Link Copied!',
                    text: 'Property link has been copied to your clipboard.',
                    icon: 'success',
                    timer: 2000,
                    showConfirmButton: false,
                    confirmButtonColor: '#057153',
                });
            }
            
            if (options.onSuccess) {
                options.onSuccess({ method: 'clipboard', url: shareUrl });
            }
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = shareUrl;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                document.execCommand('copy');
                textArea.remove();
                
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Link Copied!',
                        text: 'Property link has been copied to your clipboard.',
                        icon: 'success',
                        timer: 2000,
                        showConfirmButton: false,
                        confirmButtonColor: '#057153',
                    });
                }
                
                if (options.onSuccess) {
                    options.onSuccess({ method: 'clipboard-fallback', url: shareUrl });
                }
            } catch (fallbackErr) {
                textArea.remove();
                console.error('Failed to copy:', fallbackErr);
                
                // Last resort: show the URL in a modal
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Share Property',
                        html: `
                            <p class="mb-4">Copy this link to share:</p>
                            <input type="text" id="shareUrlInput" value="${shareUrl}" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md" 
                                   readonly>
                            <button onclick="document.getElementById('shareUrlInput').select(); document.execCommand('copy'); Swal.close();" 
                                    class="mt-2 w-full bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700">
                                Copy Link
                            </button>
                        `,
                        confirmButtonColor: '#057153',
                    });
                }
                
                if (options.onError) {
                    options.onError(fallbackErr);
                }
            }
        }
    }

    /**
     * Format number with commas
     * @param {number|string} num - Number to format
     * @returns {string} Formatted number
     */
    function formatNumber(num) {
        if (num === null || num === undefined || num === '') return '0';
        const numValue = typeof num === 'string' ? parseFloat(num) : num;
        return isNaN(numValue) ? '0' : numValue.toLocaleString('en-US');
    }

    /**
     * Initialize share buttons on the page
     * Automatically attaches click handlers to all elements with class "share-property-btn"
     */
    function initSharePropertyButtons() {
        document.querySelectorAll('.share-property-btn').forEach(button => {
            // Skip if already initialized
            if (button.hasAttribute('data-share-initialized')) {
                return;
            }
            
            button.setAttribute('data-share-initialized', 'true');
            
            button.addEventListener('click', async function(e) {
                e.stopPropagation();
                
                const propertyId = this.getAttribute('data-property-id');
                if (!propertyId) {
                    console.error('Property ID not found on share button');
                    return;
                }
                
                // Get optional attributes
                const customUrl = this.getAttribute('data-property-url');
                const propertyTitle = this.getAttribute('data-property-title');
                const propertyText = this.getAttribute('data-property-text');
                const propertyPrice = this.getAttribute('data-property-price');
                const propertyCurrency = this.getAttribute('data-property-currency');
                
                // Try to get property data from window.properties if available
                let property = null;
                if (window.properties && Array.isArray(window.properties)) {
                    property = window.properties.find(p => p.id == propertyId);
                }
                
                // Build options
                const options = {
                    url: customUrl || undefined,
                    title: propertyTitle || (property ? property.title : undefined),
                    text: propertyText || undefined,
                    price: propertyPrice || (property ? property.price : undefined),
                    currency: propertyCurrency || (property ? property.price_currency : undefined)
                };
                
                await shareProperty(propertyId, options);
            });
        });
    }

    /**
     * Initialize share button for a specific element
     * Useful for dynamically created elements
     * @param {HTMLElement} element - The button element to initialize
     */
    function initSharePropertyButton(element) {
        if (!element || !element.classList.contains('share-property-btn')) {
            console.error('Element must have class "share-property-btn"');
            return;
        }
        
        if (element.hasAttribute('data-share-initialized')) {
            return;
        }
        
        element.setAttribute('data-share-initialized', 'true');
        
        element.addEventListener('click', async function(e) {
            e.stopPropagation();
            
            const propertyId = this.getAttribute('data-property-id');
            if (!propertyId) {
                console.error('Property ID not found on share button');
                return;
            }
            
            const customUrl = this.getAttribute('data-property-url');
            const propertyTitle = this.getAttribute('data-property-title');
            const propertyText = this.getAttribute('data-property-text');
            const propertyPrice = this.getAttribute('data-property-price');
            const propertyCurrency = this.getAttribute('data-property-currency');
            
            let property = null;
            if (window.properties && Array.isArray(window.properties)) {
                property = window.properties.find(p => p.id == propertyId);
            }
            
            const options = {
                url: customUrl || undefined,
                title: propertyTitle || (property ? property.title : undefined),
                text: propertyText || undefined,
                price: propertyPrice || (property ? property.price : undefined),
                currency: propertyCurrency || (property ? property.price_currency : undefined)
            };
            
            await shareProperty(propertyId, options);
        });
    }

    // Auto-initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSharePropertyButtons);
    } else {
        // DOM already loaded
        initSharePropertyButtons();
    }

    // Expose functions globally
    window.shareProperty = shareProperty;
    window.initSharePropertyButtons = initSharePropertyButtons;
    window.initSharePropertyButton = initSharePropertyButton;

})();

