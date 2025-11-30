/**
 * Unread Messages Counter
 * Uses WebSocket for real-time unread message count updates
 */

(function() {
    'use strict';
    
    let unreadSocket = null;
    let lastUnreadCount = 0;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    
    /**
     * Update unread count badge
     */
    function updateUnreadBadge(count) {
        const badge = document.getElementById('messagesUnreadBadge');
        const badgeMobile = document.getElementById('messagesUnreadBadgeMobile');
        const countEl = document.getElementById('messagesUnreadCount');
        const countElMobile = document.getElementById('messagesUnreadCountMobile');
        
        const previousCount = lastUnreadCount;
        
        if (count > 0) {
            // Show badge
            if (badge) {
                badge.classList.remove('hidden');
            }
            if (badgeMobile) {
                badgeMobile.classList.remove('hidden');
            }
            
            // Update count
            if (countEl) {
                countEl.textContent = count > 99 ? '99+' : count;
            }
            if (countElMobile) {
                countElMobile.textContent = count > 99 ? '99+' : count;
            }
            
            // Show SweetAlert2 toast if count increased and user is not on chat page
            if (count > previousCount && previousCount >= 0 && !isOnChatPage()) {
                const newMessages = count - previousCount;
                showChatNotificationToast(newMessages);
            }
            
            // Show browser notification if count increased
            if (count > previousCount && previousCount > 0) {
                showBrowserNotification(count - previousCount);
            }
            
            // Update page title
            updatePageTitle(count);
        } else {
            // Hide badge
            if (badge) {
                badge.classList.add('hidden');
            }
            if (badgeMobile) {
                badgeMobile.classList.add('hidden');
            }
            
            // Reset page title
            resetPageTitle();
        }
        
        lastUnreadCount = count;
    }
    
    /**
     * Check if user is currently on the chat page
     */
    function isOnChatPage() {
        return window.location.pathname.includes('/accounts/chat/');
    }
    
    /**
     * Show SweetAlert2 toast notification for new chat messages
     */
    function showChatNotificationToast(newMessagesCount) {
        if (typeof Swal === 'undefined') {
            return;
        }
        
        const message = newMessagesCount === 1 
            ? 'New message received' 
            : `${newMessagesCount} new messages`;
        
        const Toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 5000,
            timerProgressBar: true,
            customClass: {
                popup: 'swal2-toast-custom'
            },
            didOpen: (toast) => {
                toast.addEventListener('click', () => {
                    window.location.href = '/accounts/chat/';
                });
            }
        });
        
        Toast.fire({
            icon: 'info',
            title: message,
            html: '<small class="text-gray-600">Click to view messages</small>',
        });
    }
    
    /**
     * Connect to WebSocket for unread messages
     */
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/unread-messages/`;
        
        try {
            unreadSocket = new WebSocket(wsUrl);
            
            unreadSocket.onopen = function(e) {
                console.log('Unread messages WebSocket connected');
                reconnectAttempts = 0;
            };
            
            unreadSocket.onmessage = function(e) {
                const data = JSON.parse(e.data);
                if (data.type === 'unread_count') {
                    updateUnreadBadge(data.count);
                }
            };
            
            unreadSocket.onerror = function(e) {
                console.error('Unread messages WebSocket error:', e);
            };
            
            unreadSocket.onclose = function(e) {
                console.log('Unread messages WebSocket closed');
                // Attempt to reconnect
                if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, 1000 * reconnectAttempts);
                }
            };
        } catch (e) {
            console.error('Failed to create unread messages WebSocket:', e);
            // Fallback to polling if WebSocket fails
            fallbackToPolling();
        }
    }
    
    /**
     * Fallback to AJAX polling if WebSocket fails
     */
    function fetchUnreadCount() {
        fetch('/accounts/chat/unread-count/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateUnreadBadge(data.unread_count);
            }
        })
        .catch(error => {
            console.error('Error fetching unread count:', error);
        });
    }
    
    /**
     * Fallback to polling
     */
    let pollTimer = null;
    const POLL_INTERVAL = 10000; // 10 seconds
    
    function fallbackToPolling() {
        if (pollTimer) return; // Already polling
        
        console.log('Falling back to AJAX polling for unread messages');
        fetchUnreadCount();
        pollTimer = setInterval(fetchUnreadCount, POLL_INTERVAL);
    }
    
    /**
     * Show browser notification
     */
    function showBrowserNotification(newMessagesCount) {
        // Check if browser supports notifications
        if (!('Notification' in window)) {
            return;
        }
        
        // Check if permission is granted
        if (Notification.permission === 'granted') {
            const message = newMessagesCount === 1 
                ? 'You have 1 new message' 
                : `You have ${newMessagesCount} new messages`;
            
            const notification = new Notification('New Message', {
                body: message,
                icon: '/static/img/mynexthome.png', // Update with your icon path
                badge: '/static/img/mynexthome.png',
                tag: 'new-message',
                requireInteraction: false
            });
            
            // Close notification after 5 seconds
            setTimeout(() => {
                notification.close();
            }, 5000);
            
            // Handle click on notification
            notification.onclick = function() {
                window.focus();
                window.location.href = '/accounts/chat/';
                notification.close();
            };
        } else if (Notification.permission !== 'denied') {
            // Request permission
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    showBrowserNotification(newMessagesCount);
                }
            });
        }
    }
    
    /**
     * Update page title with unread count
     */
    function updatePageTitle(count) {
        const originalTitle = document.title.replace(/^\(\d+\)\s*/, ''); // Remove existing count
        document.title = `(${count}) ${originalTitle}`;
    }
    
    /**
     * Reset page title
     */
    function resetPageTitle() {
        document.title = document.title.replace(/^\(\d+\)\s*/, '');
    }
    
    /**
     * Start WebSocket connection
     */
    function startConnection() {
        connectWebSocket();
    }
    
    /**
     * Stop WebSocket connection
     */
    function stopConnection() {
        if (unreadSocket) {
            unreadSocket.close();
            unreadSocket = null;
        }
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }
    
    /**
     * Initialize when DOM is ready
     */
    function init() {
        // Only start if user is authenticated
        const isAuthenticated = document.body.getAttribute('data-user-authenticated') === 'true' ||
                               document.querySelector('[data-user-id]') !== null;
        
        if (isAuthenticated) {
            startConnection();
            
            // Reconnect when page becomes visible
            document.addEventListener('visibilitychange', function() {
                if (!document.hidden && !unreadSocket) {
                    startConnection();
                }
            });
            
            // Clean up on page unload
            window.addEventListener('beforeunload', stopConnection);
        }
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Make functions globally accessible for manual updates
    window.updateUnreadMessages = fetchUnreadCount;
    window.startUnreadConnection = startConnection;
    window.stopUnreadConnection = stopConnection;
})();

