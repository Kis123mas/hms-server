# WebSocket Implementation

## Overview
Simple WebSocket implementation with email-based authentication. Only users whose email exists in the database can connect. All active connections are tracked in the database.

## Features
- ✅ Email-based authentication
- ✅ Connect/Disconnect functionality
- ✅ Real-time message sending and receiving
- ✅ Connection rejection for invalid emails
- ✅ Async WebSocket consumer
- ✅ Database tracking of active connections
- ✅ Automatic cleanup on disconnect
- ✅ API endpoint to view active connections

## WebSocket Endpoint
```
ws://localhost:8000/ws/connect/?email=user@example.com
```

## Authentication
The WebSocket authenticates users by checking if their email exists in the database:
- **Valid email**: Connection accepted
- **Invalid email**: Connection rejected with code 4001
- **No email provided**: Connection rejected with code 4000

## How to Use

### 1. Run Migrations
First, create and apply the database migration for the ActiveWebSocketConnection model:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Start the Server
Make sure your Django server is running with Daphne (ASGI server):
```bash
python manage.py runserver
```

### 2. Test with HTML Client
Open `websocket_test.html` in your browser:
```bash
# Open in browser
start websocket_test.html
```

### 3. View Active Connections
Check who's currently connected via the API endpoint:
```bash
GET /api/hms/active-connections
Authorization: Token <your-token>
```

Response:
```json
{
  "status": "success",
  "count": 2,
  "active_connections": [
    {
      "email": "user1@example.com",
      "connected_at": "2025-10-21T12:30:00Z",
      "last_activity": "2025-10-21T12:35:00Z"
    },
    {
      "email": "user2@example.com",
      "connected_at": "2025-10-21T12:32:00Z",
      "last_activity": "2025-10-21T12:34:00Z"
    }
  ]
}
```

### 4. Connect via JavaScript
```javascript
// Create WebSocket connection
const email = "user@example.com";
const socket = new WebSocket(`ws://localhost:8000/ws/connect/?email=${email}`);

// Connection opened
socket.onopen = function(e) {
    console.log("Connected to WebSocket");
};

// Receive messages
socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log("Message from server:", data);
};

// Send message
socket.send(JSON.stringify({
    message: "Hello Server!"
}));

// Close connection
socket.close();
```

### 5. Connection Events

**On Connect:**
```json
{
    "type": "connection_established",
    "message": "Connected successfully as user@example.com"
}
```

**On Message:**
```json
{
    "type": "message",
    "message": "Server received: Hello Server!",
    "from": "user@example.com"
}
```

**On Error:**
```json
{
    "type": "error",
    "message": "Invalid JSON format"
}
```

## Database Model

### ActiveWebSocketConnection
Tracks all active WebSocket connections:

**Fields:**
- `email` (EmailField, unique): User's email address
- `connected_at` (DateTimeField): When the connection was established
- `last_activity` (DateTimeField): Last activity timestamp (auto-updated)

**Behavior:**
- Created when user connects
- Deleted when user disconnects
- Unique constraint ensures one connection per email

## File Structure
```
hms-server/
├── hmsServer/
│   ├── asgi.py              # ASGI configuration with WebSocket routing
│   └── settings.py          # Added channels and CHANNEL_LAYERS
├── healthManagement/
│   ├── models.py            # Added ActiveWebSocketConnection model
│   ├── consumers.py         # WebSocket consumer with DB tracking
│   ├── routing.py           # WebSocket URL routing
│   ├── views.py             # Added get_active_connections endpoint
│   └── urls.py              # Added active-connections route
├── websocket_test.html      # HTML test client
└── WEBSOCKET_README.md      # This file
```

## Consumer Methods

### `connect()`
- Extracts email from query parameters
- Checks if email exists in database
- **Saves connection to database** (ActiveWebSocketConnection)
- Accepts or rejects connection

### `disconnect(close_code)`
- **Removes connection from database**
- Handles cleanup when connection closes
- Logs disconnection event

### `receive(text_data)`
- Receives messages from client
- Echoes message back to client
- Handles JSON parsing errors

### Database Methods

#### `save_connection(email)`
- Creates or updates ActiveWebSocketConnection record
- Uses `get_or_create` to handle reconnections
- Updates `last_activity` timestamp

#### `remove_connection(email)`
- Deletes ActiveWebSocketConnection record
- Called automatically on disconnect

## Error Codes
- **4000**: No email provided
- **4001**: Email not found in database
- **1000**: Normal closure

## Production Considerations

For production, replace the in-memory channel layer with Redis:

1. Install Redis channel layer:
```bash
pip install channels-redis
```

2. Update `settings.py`:
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

## Testing
1. Make sure you have a user with email in the database
2. Open `websocket_test.html` in your browser
3. Enter the email address
4. Click "Connect"
5. Send messages and see the responses

## Troubleshooting

**Connection rejected:**
- Verify the email exists in the database
- Check server logs for error messages

**WebSocket not connecting:**
- Ensure Django server is running
- Check that Daphne is installed
- Verify ASGI_APPLICATION is set correctly

**CORS issues:**
- WebSocket connections from different origins may require additional CORS configuration
