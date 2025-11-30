/**
 * Contact Agent/Owner Modal Functionality
 * Handles the contact form modal for property owners and agents
 */

(function() {
    'use strict';

    // Get DOM elements
    const contactModal = document.getElementById('contactModal');
    const closeContactModal = document.getElementById('closeContactModal');
    const cancelContact = document.getElementById('cancelContact');
    const contactForm = document.getElementById('contactForm');
    const submitContact = document.getElementById('submitContact');
    const submitContactText = document.getElementById('submitContactText');
    const submitContactLoading = document.getElementById('submitContactLoading');
    const contactPropertyId = document.getElementById('contactPropertyId');
    const contactPersonType = document.getElementById('contactPersonType');
    const contactModalTitle = document.getElementById('contactModalTitle');
    
    let currentProperty = null;

    /**
     * Function to open contact modal or directly start chat
     * @param {Object} property - Property object with id, has_agent, owner, agent info
     */
    function openContactModal(property) {
        if (!contactModal) return;
        
        currentProperty = property;
        
        // Check if user is authenticated
        const isAuthenticated = window.contactModalUserData && window.contactModalUserData.is_authenticated;
        
        if (!isAuthenticated) {
            // Show login prompt for non-authenticated users
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Login Required',
                    text: 'Please login to start a conversation with the property owner/agent.',
                    icon: 'info',
                    showCancelButton: true,
                    confirmButtonText: 'Login',
                    cancelButtonText: 'Cancel',
                    confirmButtonColor: '#16a34a',
                    cancelButtonColor: '#6b7280'
                }).then((result) => {
                    if (result.isConfirmed) {
                        // Redirect to login page
                        window.location.href = '/accounts/login/';
                    }
                });
            } else {
                alert('Please login to start a conversation.');
                window.location.href = '/accounts/login/';
            }
            return;
        }
        
        // For authenticated users, directly create/open chat
        if (contactPropertyId) {
            contactPropertyId.value = property.id;
        }
        
        // Update modal title
        const contactType = property.has_agent ? 'Agent' : 'Owner';
        if (contactPersonType) {
            contactPersonType.textContent = contactType;
        }
        if (contactModalTitle) {
            contactModalTitle.textContent = `Message ${contactType}`;
        }
        
        // Clear previous message
        const contactMessage = document.getElementById('contactMessage');
        if (contactMessage) {
            contactMessage.value = '';
        }
        
        contactModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Function to close contact modal
     */
    function closeContactModalFunc() {
        if (!contactModal) return;
        contactModal.classList.add('hidden');
        document.body.style.overflow = '';
        if (contactForm) {
            contactForm.reset();
        }
        currentProperty = null;
    }

    /**
     * Initialize modal event handlers
     */
    function initModalHandlers() {
        // Close modal handlers
        if (closeContactModal) {
            closeContactModal.addEventListener('click', closeContactModalFunc);
        }
        if (cancelContact) {
            cancelContact.addEventListener('click', closeContactModalFunc);
        }
        
        // Close on backdrop click
        if (contactModal) {
            contactModal.addEventListener('click', function(e) {
                if (e.target === contactModal) {
                    closeContactModalFunc();
                }
            });
        }

        // Close on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && contactModal && !contactModal.classList.contains('hidden')) {
                closeContactModalFunc();
            }
        });
    }

    /**
     * Initialize form submission handler
     */
    function initFormHandler() {
        if (!contactForm) return;

        contactForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Simplified - only need message (optional)
            const message = document.getElementById('contactMessage').value.trim();
            
            // Check if user is authenticated
            const isAuthenticated = window.contactModalUserData && window.contactModalUserData.is_authenticated;
            if (!isAuthenticated) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Login Required',
                        text: 'Please login to start a conversation.',
                        icon: 'info',
                        showCancelButton: true,
                        confirmButtonText: 'Login',
                        cancelButtonText: 'Cancel',
                        confirmButtonColor: '#16a34a',
                        cancelButtonColor: '#6b7280'
                    }).then((result) => {
                        if (result.isConfirmed) {
                            window.location.href = '/accounts/login/';
                        }
                    });
                } else {
                    alert('Please login to start a conversation.');
                    window.location.href = '/accounts/login/';
                }
                return;
            }

            // Show loading state
            if (submitContact) {
                submitContact.disabled = true;
                if (submitContactText) submitContactText.classList.add('hidden');
                if (submitContactLoading) submitContactLoading.classList.remove('hidden');
            }

            try {
                // Get CSRF token helper function
                function getCookie(name) {
                    let cookieValue = null;
                    if (document.cookie && document.cookie !== '') {
                        const cookies = document.cookie.split(';');
                        for (let i = 0; i < cookies.length; i++) {
                            const cookie = cookies[i].trim();
                            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                break;
                            }
                        }
                    }
                    return cookieValue;
                }

                const response = await fetch(`/accounts/properties/property/${contactPropertyId.value}/contact/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        message: message
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Directly redirect to chat
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else if (data.chat_id) {
                        window.location.href = `/accounts/chat/?chat=${data.chat_id}`;
                    } else {
                        closeContactModalFunc();
                    }
                } else {
                    // Handle error - check if login is required
                    if (data.requires_login) {
                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                title: 'Login Required',
                                text: data.error || 'Please login to start a conversation.',
                                icon: 'info',
                                showCancelButton: true,
                                confirmButtonText: 'Login',
                                cancelButtonText: 'Cancel',
                                confirmButtonColor: '#16a34a',
                                cancelButtonColor: '#6b7280'
                            }).then((result) => {
                                if (result.isConfirmed) {
                                    window.location.href = '/accounts/login/';
                                } else {
                                    closeContactModalFunc();
                                }
                            });
                        } else {
                            alert(data.error || 'Please login to start a conversation.');
                            window.location.href = '/accounts/login/';
                        }
                    } else {
                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                title: 'Error',
                                text: data.error || 'Failed to send message. Please try again.',
                                icon: 'error',
                                confirmButtonText: 'OK'
                            });
                        } else {
                            alert(data.error || 'Failed to send message. Please try again.');
                        }
                    }
                }
            } catch (error) {
                console.error('Error sending contact message:', error);
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Error',
                        text: 'An error occurred. Please try again later.',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                } else {
                    alert('An error occurred. Please try again later.');
                }
            } finally {
                // Reset button state
                if (submitContact) {
                    submitContact.disabled = false;
                    if (submitContactText) submitContactText.classList.remove('hidden');
                    if (submitContactLoading) submitContactLoading.classList.add('hidden');
                }
            }
        });
    }

    /**
     * Attach click handlers to all contact agent buttons
     */
    function attachContactButtonHandlers() {
        document.querySelectorAll('.contact-agent-btn').forEach(button => {
            // Check if handler already attached
            if (button.hasAttribute('data-contact-handler-attached')) {
                return;
            }
            button.setAttribute('data-contact-handler-attached', 'true');
            
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const propertyId = parseInt(this.getAttribute('data-property-id'));
                
                if (!propertyId) {
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            title: 'Error',
                            text: 'Property ID not found.',
                            icon: 'error',
                            confirmButtonText: 'OK'
                        });
                    } else {
                        alert('Property ID not found.');
                    }
                    return;
                }

                // Try to find property in loaded properties
                if (window.properties && Array.isArray(window.properties)) {
                    const property = window.properties.find(p => p.id === propertyId);
                    if (property) {
                        openContactModal(property);
                        return;
                    }
                }

                // If property not found in loaded data, fetch it
                fetch(`/accounts/properties/property/${propertyId}/`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(property => {
                    if (property && property.id) {
                        openContactModal(property);
                    } else {
                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                title: 'Error',
                                text: 'Property not found.',
                                icon: 'error',
                                confirmButtonText: 'OK'
                            });
                        } else {
                            alert('Property not found.');
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching property:', error);
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            title: 'Error',
                            text: 'Failed to load property information.',
                            icon: 'error',
                            confirmButtonText: 'OK'
                        });
                    } else {
                        alert('Failed to load property information.');
                    }
                });
            });
        });
    }

    // Make functions globally accessible
    window.openContactModal = openContactModal;
    window.attachContactButtonHandlers = attachContactButtonHandlers;

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initModalHandlers();
            initFormHandler();
            attachContactButtonHandlers();
        });
    } else {
        // DOM already loaded
        initModalHandlers();
        initFormHandler();
        attachContactButtonHandlers();
    }

    // Re-attach handlers when new property cards are added (for infinite scroll)
    const originalAttachPropertyCardListeners = window.attachPropertyCardListeners;
    if (originalAttachPropertyCardListeners) {
        window.attachPropertyCardListeners = function() {
            originalAttachPropertyCardListeners();
            attachContactButtonHandlers();
        };
    }
})();

