/**
 * Chat functionality with WebSocket and AJAX polling fallback
 */

let chatSocket = null;
let chatId = null;
let currentUserId = null;
let lastMessageId = null;
let pollInterval = null;
let typingTimeout = null;
let isTyping = false;
let useWebSocket = true;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const POLL_INTERVAL = 10000; // 10 seconds

/**
 * Initialize chat
 */
function initChat(chatIdParam, currentUserIdParam) {
    chatId = chatIdParam;
    currentUserId = currentUserIdParam;
    
    // Try WebSocket first
    connectWebSocket();
    
    // Set up message form
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    
    if (messageForm) {
        messageForm.addEventListener('submit', handleSendMessage);
    }
    
    if (messageInput) {
        messageInput.addEventListener('input', handleTyping);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e);
            }
        });
    }
    
    // Load initial messages
    loadMessages();
}

/**
 * Connect to WebSocket
 */
function connectWebSocket() {
    if (!useWebSocket) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${chatId}/`;
    
    try {
        chatSocket = new WebSocket(wsUrl);
        
        chatSocket.onopen = function(e) {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
            stopPolling();
        };
        
        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            handleWebSocketMessage(data);
        };
        
        chatSocket.onerror = function(e) {
            console.error('WebSocket error:', e);
            fallbackToPolling();
        };
        
        chatSocket.onclose = function(e) {
            console.log('WebSocket closed');
            if (useWebSocket && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                setTimeout(connectWebSocket, 1000 * reconnectAttempts);
            } else {
                fallbackToPolling();
            }
        };
    } catch (e) {
        console.error('Failed to create WebSocket:', e);
        fallbackToPolling();
    }
}

/**
 * Fallback to AJAX polling
 */
function fallbackToPolling() {
    if (!useWebSocket) return; // Already polling
    
    console.log('Falling back to AJAX polling');
    useWebSocket = false;
    
    if (chatSocket) {
        chatSocket.close();
        chatSocket = null;
    }
    
    startPolling();
}

/**
 * Start AJAX polling
 */
function startPolling() {
    if (pollInterval) return;
    
    pollInterval = setInterval(function() {
        loadMessages(true);
    }, POLL_INTERVAL);
    
    // Load immediately
    loadMessages(true);
}

/**
 * Stop polling
 */
function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

/**
 * Handle WebSocket messages
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'chat_history':
            displayMessages(data.messages);
            break;
        case 'chat_message':
            addMessage(data.message);
            // Don't show toast if user is viewing this chat
            // Toast will be handled by unreadMessages.js for other chats
            break;
        case 'typing_status':
            if (data.user.id !== currentUserId) {
                showTypingIndicator(data.user.username, data.is_typing);
            }
            break;
        case 'read_receipt':
            // Handle read receipts if needed
            break;
    }
}

/**
 * Load messages via AJAX
 */
function loadMessages(isPolling = false) {
    const url = `/accounts/chat/${chatId}/messages/`;
    const params = new URLSearchParams();
    if (lastMessageId && isPolling) {
        params.append('last_message_id', lastMessageId);
    }
    
    fetch(`${url}?${params.toString()}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (isPolling && lastMessageId) {
                // Only add new messages
                const newMessages = data.messages.filter(msg => msg.id > lastMessageId);
                newMessages.forEach(msg => addMessage(msg));
            } else {
                // Display all messages
                displayMessages(data.messages);
            }
            
            // Update last message ID
            if (data.messages.length > 0) {
                lastMessageId = Math.max(...data.messages.map(m => m.id));
            }
        }
    })
    .catch(error => {
        console.error('Error loading messages:', error);
    })
    .finally(() => {
        const loadingEl = document.getElementById('messagesLoading');
        if (loadingEl) {
            loadingEl.classList.add('hidden');
        }
        const messagesList = document.getElementById('messagesList');
        if (messagesList) {
            messagesList.classList.remove('hidden');
        }
    });
}

/**
 * Display messages
 */
function displayMessages(messages) {
    const messagesList = document.getElementById('messagesList');
    if (!messagesList) return;
    
    messagesList.innerHTML = '';
    
    messages.forEach(message => {
        addMessage(message, false);
    });
    
    scrollToBottom();
    
    // Update last message ID
    if (messages.length > 0) {
        lastMessageId = Math.max(...messages.map(m => m.id));
    }
}

/**
 * Add a single message to the chat
 */
function addMessage(message, scroll = true) {
    const messagesList = document.getElementById('messagesList');
    if (!messagesList) return;
    
    // Check if message is from current user
    // If sender is null/undefined, it's a guest message (not from current user)
    // If sender exists and sender.id matches currentUserId, it's from current user
    const isOwnMessage = message.sender && message.sender.id && parseInt(message.sender.id) === parseInt(currentUserId);
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`;
    messageDiv.setAttribute('data-message-id', message.id);
    
    const messageContent = `
        <div class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
            isOwnMessage 
                ? 'bg-primary-600 text-white' 
                : 'bg-white text-gray-900 border border-gray-200'
        }">
            ${!isOwnMessage && message.sender ? `
                <div class="text-xs font-semibold mb-1 text-primary-600">
                    ${message.sender.name || message.sender.username || 'Guest'}
                </div>
            ` : ''}
            ${!isOwnMessage && !message.sender ? `
                <div class="text-xs font-semibold mb-1 text-primary-600">
                    Guest
                </div>
            ` : ''}
            <div class="text-sm whitespace-pre-wrap">${escapeHtml(message.content)}</div>
            <div class="text-xs mt-1 ${isOwnMessage ? 'text-primary-100' : 'text-gray-500'}">
                ${formatTime(message.created)}
            </div>
        </div>
    `;
    
    messageDiv.innerHTML = messageContent;
    messagesList.appendChild(messageDiv);
    
    if (scroll) {
        scrollToBottom();
    }
}

/**
 * Handle send message
 */
function handleSendMessage(e) {
    e.preventDefault();
    
    const messageInput = document.getElementById('messageInput');
    const content = messageInput.value.trim();
    
    if (!content) return;
    
    // Clear input
    messageInput.value = '';
    
    // Send via WebSocket if available, otherwise AJAX
    if (useWebSocket && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'chat_message',
            content: content
        }));
    } else {
        sendMessageViaAJAX(content);
    }
    
    // Stop typing indicator
    if (isTyping) {
        sendTypingStatus(false);
        isTyping = false;
    }
}

/**
 * Send message via AJAX
 */
function sendMessageViaAJAX(content) {
    fetch(`/accounts/chat/${chatId}/send/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'same-origin',
        body: JSON.stringify({ content: content })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addMessage(data.message);
        } else {
            console.error('Error sending message:', data.error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Error',
                    text: data.error || 'Failed to send message',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
    });
}

/**
 * Handle typing indicator
 */
function handleTyping() {
    if (!isTyping) {
        isTyping = true;
        sendTypingStatus(true);
    }
    
    // Clear existing timeout
    if (typingTimeout) {
        clearTimeout(typingTimeout);
    }
    
    // Set timeout to stop typing indicator
    typingTimeout = setTimeout(function() {
        if (isTyping) {
            isTyping = false;
            sendTypingStatus(false);
        }
    }, 3000);
}

/**
 * Send typing status
 */
function sendTypingStatus(typing) {
    if (useWebSocket && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'typing',
            is_typing: typing
        }));
    }
}

/**
 * Show typing indicator
 */
function showTypingIndicator(username, typing) {
    const indicator = document.getElementById('typingIndicator');
    const typingUser = document.getElementById('typingUser');
    
    if (indicator && typingUser) {
        if (typing) {
            typingUser.textContent = username;
            indicator.classList.remove('hidden');
        } else {
            indicator.classList.add('hidden');
        }
    }
}

/**
 * Scroll to bottom of messages
 */
function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Format time
 */
function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) { // Less than 1 minute
        return 'Just now';
    } else if (diff < 3600000) { // Less than 1 hour
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    } else if (diff < 86400000) { // Less than 1 day
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    } else {
        return date.toLocaleDateString();
    }
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get CSRF cookie
 */
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

// Make functions globally accessible
window.initChat = initChat;

