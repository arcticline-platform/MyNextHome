# WebSocket Configuration Guide

This document outlines the WebSocket configuration for MyNextHome application.

## Prerequisites

1. **Redis Server**: WebSockets use Redis as the channel layer backend
   ```bash
   # Install Redis (Ubuntu/Debian)
   sudo apt-get install redis-server
   
   # Start Redis
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   
   # Verify Redis is running
   redis-cli ping
   # Should return: PONG
   ```

2. **Python Packages**: Already included in `requirements.txt`
   - `channels==4.2.0`
   - `channels_redis==4.2.1`
   - `redis==5.2.1`

## Configuration

### 1. Settings (`MyNextHome/settings.py`)

- **INSTALLED_APPS**: `channels` and `channels_redis` are added
- **ASGI_APPLICATION**: Set to `'MyNextHome.asgi.application'`
- **CHANNEL_LAYERS**: Configured with Redis backend
  ```python
  CHANNEL_LAYERS = {
      'default': {
          'BACKEND': 'channels_redis.core.RedisChannelLayer',
          'CONFIG': {
              "hosts": [("127.0.0.1", 6379)],
              "capacity": 1500,
              "expiry": 10,
          },
      },
  }
  ```

### 2. ASGI Configuration (`MyNextHome/asgi.py`)

The ASGI application is properly configured with:
- `ProtocolTypeRouter`: Routes HTTP and WebSocket traffic
- `AllowedHostsOriginValidator`: Validates WebSocket origins
- `AuthMiddlewareStack`: Handles authentication for WebSocket connections
- `URLRouter`: Routes WebSocket URLs

### 3. WebSocket Routes (`core/routing.py`)

All WebSocket endpoints are defined:
- `/ws/online_status/` - Online status updates
- `/ws/notify/` - General notifications
- `/ws/user_notification/` - User-specific notifications
- `/ws/payment-status/<payment_id>/` - Payment status updates
- `/ws/chat/<chat_id>/` - Real-time chat messaging
- `/ws/unread-messages/` - Unread message count updates

### 4. Consumers (`core/consumers.py`)

All consumers include:
- **Authentication checks**: All consumers verify user authentication
- **Error handling**: Proper error handling and connection closing
- **Group management**: Proper joining/leaving of channel groups
- **Database operations**: Using `@database_sync_to_async` decorator

## Running the Application

### Development

For development, use Django's runserver with ASGI support:

```bash
# Option 1: Using daphne (recommended for production-like testing)
pip install daphne
daphne -b 0.0.0.0 -p 8000 MyNextHome.asgi:application

# Option 2: Using uvicorn (already in requirements.txt)
uvicorn MyNextHome.asgi:application --host 0.0.0.0 --port 8000

# Option 3: Django runserver (for basic testing, not recommended for WebSockets)
python manage.py runserver
```

### Production

For production, use an ASGI server:

```bash
# Using daphne
daphne -b 0.0.0.0 -p 8000 MyNextHome.asgi:application

# Using uvicorn with workers
uvicorn MyNextHome.asgi:application --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn with uvicorn workers
gunicorn MyNextHome.asgi:application -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Testing WebSocket Connections

### 1. Check Redis Connection

```bash
redis-cli ping
```

### 2. Test WebSocket Connection (using browser console)

```javascript
// Connect to unread messages WebSocket
const ws = new WebSocket('ws://127.0.0.1:8000/ws/unread-messages/');

ws.onopen = () => {
    console.log('WebSocket connected');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
};
```

### 3. Verify Authentication

All WebSocket endpoints require authentication. Unauthenticated users will receive a close code `4001`.

## Troubleshooting

### Issue: WebSocket connection fails

1. **Check Redis is running**:
   ```bash
   redis-cli ping
   ```

2. **Check Redis connection in settings**:
   - Verify `CHANNEL_LAYERS` configuration
   - Check Redis host and port (default: 127.0.0.1:6379)

3. **Check ASGI application**:
   - Verify `ASGI_APPLICATION` is set in settings
   - Ensure `channels` is in `INSTALLED_APPS`

4. **Check server logs**:
   - Look for connection errors
   - Check authentication failures

### Issue: Messages not being received

1. **Check channel layer**:
   - Verify Redis is running
   - Check group names match between senders and receivers

2. **Check consumer logic**:
   - Verify group_add/group_discard calls
   - Check message type handlers

3. **Check frontend WebSocket connection**:
   - Verify WebSocket URL is correct
   - Check browser console for errors

## Security Considerations

1. **Authentication**: All WebSocket endpoints require authentication
2. **Origin Validation**: `AllowedHostsOriginValidator` prevents unauthorized origins
3. **Access Control**: Consumers verify user access (e.g., chat access)
4. **Error Handling**: Proper error codes and connection closing

## Performance

- **Channel Layer Capacity**: Set to 1500 messages per channel
- **Message Expiry**: 10 seconds
- **Connection Pooling**: Redis handles connection pooling automatically
- **Scalability**: Multiple ASGI workers can share the same Redis channel layer

