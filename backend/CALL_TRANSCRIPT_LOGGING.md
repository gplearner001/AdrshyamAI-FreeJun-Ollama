# Call Transcript Logging and Webhook Integration

This document describes the call transcript logging system that automatically saves conversation transcripts to PostgreSQL and optionally sends them to a configured webhook endpoint.

## Overview

When a call ends, the system automatically:
1. Saves the complete conversation transcript to a PostgreSQL database
2. Sends the transcript to a configured webhook URL (if available)
3. Tracks webhook delivery status

## Configuration

### Database Setup

Add your PostgreSQL connection string to the `.env` file:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/teler_db
```

The database schema will be automatically created on startup.

### Webhook Configuration

Add your webhook URL to the `.env` file (optional):

```bash
WEBHOOK_URL=https://your-webhook-endpoint.com/transcripts
```

You can also configure the webhook URL dynamically via the API.

## Database Schema

The system creates a `call_transcripts` table with the following structure:

```sql
CREATE TABLE call_transcripts (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(255) UNIQUE NOT NULL,
    connection_id VARCHAR(255),
    call_type VARCHAR(50),
    status VARCHAR(50),
    from_number VARCHAR(50),
    to_number VARCHAR(50),
    language VARCHAR(10),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    conversation JSONB,
    metadata JSONB,
    knowledge_base_id VARCHAR(255),
    webhook_sent BOOLEAN DEFAULT FALSE,
    webhook_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Get Transcript by Call ID

```http
GET /api/transcripts/{call_id}
```

Returns the complete transcript for a specific call.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "call_id": "call_1234567890",
    "conversation": [
      {
        "role": "user",
        "content": "Hello, I need help with my account"
      },
      {
        "role": "assistant",
        "content": "I'd be happy to help you with your account. What do you need assistance with?"
      }
    ],
    "metadata": {
      "call_type": "phone_call",
      "start_time": "2025-10-15T10:30:00",
      "end_time": "2025-10-15T10:35:00"
    },
    "duration_seconds": 300,
    "language": "en-IN",
    "webhook_sent": true
  }
}
```

### Get Recent Transcripts

```http
GET /api/transcripts?limit=50
```

Returns the most recent call transcripts.

**Query Parameters:**
- `limit` (optional): Maximum number of transcripts to return (default: 50)

### Get Webhook Configuration

```http
GET /api/webhook/config
```

Returns the current webhook configuration.

**Response:**
```json
{
  "success": true,
  "data": {
    "webhook_url": "https://your-webhook-endpoint.com/transcripts",
    "is_configured": true
  }
}
```

### Update Webhook Configuration

```http
POST /api/webhook/config
Content-Type: application/json

{
  "webhook_url": "https://your-webhook-endpoint.com/transcripts"
}
```

Updates the webhook URL dynamically.

### Retry Webhook Delivery

```http
POST /api/webhook/retry/{call_id}
```

Retries sending a transcript to the webhook for a specific call.

### Get Pending Webhooks

```http
GET /api/webhook/pending
```

Returns all transcripts that haven't been successfully sent to the webhook yet.

## Webhook Payload Format

When a transcript is sent to your webhook, it will receive a POST request with the following JSON payload:

```json
{
  "call_id": "call_1234567890",
  "conversation": [
    {
      "role": "user",
      "content": "Hello, I need help with my account"
    },
    {
      "role": "assistant",
      "content": "I'd be happy to help you with your account. What do you need assistance with?"
    }
  ],
  "metadata": {
    "call_type": "phone_call",
    "start_time": "2025-10-15T10:30:00.123456",
    "end_time": "2025-10-15T10:35:00.123456",
    "connection_id": "conn_1234567890.123456",
    "from_number": "+1234567890",
    "to_number": "+0987654321",
    "call_state": {
      "status": "ended",
      "language": "en-IN",
      "knowledge_base_id": "kb_123"
    }
  },
  "timestamp": "2025-10-15T10:35:00.123456"
}
```

## Webhook Implementation Guidelines

Your webhook endpoint should:

1. Accept POST requests with JSON payload
2. Return HTTP status 200, 201, or 202 to indicate success
3. Process the request within 30 seconds (timeout limit)
4. Handle retries gracefully (the system will retry up to 3 times on failure)

### Example Webhook Handler (Python/Flask)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/transcripts', methods=['POST'])
def receive_transcript():
    data = request.get_json()

    call_id = data.get('call_id')
    conversation = data.get('conversation')
    metadata = data.get('metadata')

    # Process the transcript
    print(f"Received transcript for call: {call_id}")
    print(f"Conversation has {len(conversation)} messages")

    # Store or process the data as needed
    # ... your logic here ...

    return jsonify({'status': 'success'}), 200
```

### Example Webhook Handler (Node.js/Express)

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/transcripts', (req, res) => {
  const { call_id, conversation, metadata } = req.body;

  console.log(`Received transcript for call: ${call_id}`);
  console.log(`Conversation has ${conversation.length} messages`);

  // Process the transcript
  // ... your logic here ...

  res.status(200).json({ status: 'success' });
});

app.listen(3000);
```

## How It Works

### Call Lifecycle

1. **Call Starts**: WebSocket connection established, conversation history begins recording
2. **During Call**: All user and AI messages are stored in memory
3. **Call Ends**: When the call ends (user hangs up or timeout):
   - Transcript is saved to PostgreSQL database
   - If webhook is configured, transcript is sent to webhook URL
   - Webhook delivery status is tracked in database

### Automatic Transcript Saving

Transcripts are automatically saved when:
- User ends the call (goodbye/hang up)
- Call times out due to inactivity
- WebSocket connection is closed

### Webhook Retry Logic

If webhook delivery fails:
- System retries up to 3 times automatically
- Each retry waits before attempting again
- Failed deliveries remain marked as pending in the database
- You can manually retry using the `/api/webhook/retry/{call_id}` endpoint

## Monitoring and Troubleshooting

### Check Database Status

```bash
curl http://localhost:8000/health
```

Look for `database_available` in the response.

### View Recent Transcripts

```bash
curl http://localhost:8000/api/transcripts?limit=10
```

### Check Pending Webhooks

```bash
curl http://localhost:8000/api/webhook/pending
```

### View Logs

The system logs all transcript operations:

```bash
tail -f backend/logs/app.log | grep "transcript"
```

Look for log messages like:
- `💾 Saving call transcript for {connection_id}`
- `Call transcript saved to database: {call_id}`
- `Sending call transcript to webhook for call_id: {call_id}`
- `Call transcript sent to webhook: {call_id}`

## Security Considerations

1. **Database Connection**: Use strong passwords and limit database access
2. **Webhook URLs**: Use HTTPS endpoints only in production
3. **Authentication**: Consider adding webhook signature verification
4. **Data Privacy**: Transcripts contain conversation data - handle according to privacy regulations

## Example Usage

### Python Client

```python
import requests

# Get a specific transcript
response = requests.get('http://localhost:8000/api/transcripts/call_1234567890')
transcript = response.json()['data']

# Get recent transcripts
response = requests.get('http://localhost:8000/api/transcripts?limit=10')
transcripts = response.json()['data']

# Configure webhook
requests.post('http://localhost:8000/api/webhook/config', json={
    'webhook_url': 'https://your-webhook.com/transcripts'
})

# Retry webhook for a specific call
requests.post('http://localhost:8000/api/webhook/retry/call_1234567890')
```

## Troubleshooting

### Database Connection Issues

If database is not available:
- Check DATABASE_URL in .env file
- Verify PostgreSQL is running
- Check network connectivity
- Review logs for connection errors

### Webhook Delivery Failures

If webhooks are not being delivered:
- Verify WEBHOOK_URL is correct
- Check webhook endpoint is accessible
- Ensure endpoint returns 200/201/202 status
- Review webhook logs for errors
- Use `/api/webhook/pending` to see failed deliveries
- Use `/api/webhook/retry/{call_id}` to manually retry

### Missing Transcripts

If transcripts are not being saved:
- Check if call ended properly
- Verify conversation history is not empty
- Review logs for save errors
- Check database connection status

## Future Enhancements

Potential improvements:
- Webhook authentication/signature verification
- Custom webhook headers configuration
- Transcript export formats (CSV, PDF)
- Real-time transcript streaming
- Search and filtering capabilities
- Analytics and reporting
