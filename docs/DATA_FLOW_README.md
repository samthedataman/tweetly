# Contextly Extension Data Flow: Popup to LanceDB

## Overview
This document explains the complete end-to-end data flow from the Contextly browser extension popup to the LanceDB server, including all intermediate steps, message passing, and data transformations.

## Architecture Components

### 1. Frontend Components
- **Popup** (`popup.html` + `popup_merged.js`): Main user interface
- **Content Scripts** (`content.js`): Injected into AI platform pages (Claude, ChatGPT, Gemini)
- **Background Service Worker** (`background.js`): Handles cross-origin requests and message routing

### 2. Backend Components
- **FastAPI Server** (`backend.py`): REST API endpoints
- **LanceDB Cloud**: Vector database for storing conversations
- **OpenAI API**: For generating embeddings

## Data Flow Stages

### Stage 1: User Interaction in Popup
```javascript
// popup_merged.js
// User enables "Earn Mode" to start capturing conversations
modeToggle.addEventListener('click', () => {
    earnMode = !earnMode;
    chrome.storage.local.set({ earnMode });
    // Notifies content scripts to start/stop capturing
});
```

### Stage 2: Content Script Message Capture
When a user types in Claude/ChatGPT/Gemini, the content script captures messages:

```javascript
// content.js
// Monitors DOM for new messages
const observer = new MutationObserver((mutations) => {
    // Extracts message text and role (user/assistant)
    const messageData = {
        role: isUserMessage ? 'user' : 'assistant',
        text: extractedText,
        platform: detectPlatform(), // 'claude', 'chatgpt', 'gemini'
        timestamp: new Date().toISOString()
    };
    
    // Logs to browser console
    console.log('🔍 CONTEXTLY: Processing message...');
    console.log(`  Role: ${role}`);
    console.log(`  Platform: ${platform}`);
    console.log(`  Text preview: ${text.substring(0, 100)}...`);
});
```

### Stage 3: Message Routing through Background Worker
Content scripts can't make cross-origin requests, so they send data to the background worker:

```javascript
// content.js sends to background
chrome.runtime.sendMessage({
    type: 'SAVE_MESSAGE',
    data: {
        message: messageData,
        wallet: userWallet,
        earnMode: true
    }
});

// background.js receives and forwards to API
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'SAVE_MESSAGE') {
        fetch('https://api.contextly.ai/api/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(request.data)
        });
    }
});
```

### Stage 4: Backend API Processing
The FastAPI backend receives and processes the message:

```python
# backend.py
@app.post("/api/message")
async def save_message(data: MessageRequest):
    # Log incoming data
    print(f"🔵 INCOMING MESSAGE CAPTURE:")
    print(f"  - Role: {data.message.role}")
    print(f"  - Platform: {data.platform}")
    print(f"  - Wallet: {data.wallet}")
    print(f"  - Raw Text: {data.message.text[:200]}...")
    
    # Generate embedding using OpenAI
    embedding = await generate_embedding(data.message.text)
    
    # Prepare data for LanceDB
    conversation_data = {
        "id": str(uuid.uuid4()),
        "session_id": data.session_id,
        "platform": data.platform,
        "role": data.message.role,  # 'user' or 'assistant'
        "wallet": data.wallet,
        "text": data.message.text,  # Raw text is stored
        "embedding": embedding,  # 1536D vector from OpenAI
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": json.dumps({
            "url": data.url,
            "earn_mode": data.earn_mode
        })
    }
```

### Stage 5: LanceDB Storage
Data is stored in LanceDB Cloud with the following schema:

```python
# init_lancedb.py
conversations_v2_schema = pa.schema([
    ("id", pa.string()),           # Unique message ID
    ("session_id", pa.string()),    # Groups related messages
    ("platform", pa.string()),      # 'claude', 'chatgpt', 'gemini'
    ("role", pa.string()),          # 'user' or 'assistant'
    ("wallet", pa.string()),        # User's wallet address
    ("text", pa.string()),          # Raw message text
    ("embedding", pa.list_(pa.float32(), 1536)),  # OpenAI embeddings
    ("timestamp", pa.string()),     # ISO timestamp
    ("metadata", pa.string()),      # JSON metadata
])
```

### Stage 6: Data Retrieval
When users search or view conversations:

```javascript
// popup_merged.js
async searchConversations(query) {
    const response = await fetch(`${API_BASE_URL}/api/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
            wallet: this.wallet,
            query: query,
            platform_filter: this.platformFilter
        })
    });
    
    const results = await response.json();
    // Results include both user and assistant messages
    // Distinguished by the 'role' field
}
```

## Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│   Popup     │────▶│  Content    │────▶│  Background  │────▶│  FastAPI    │────▶│ LanceDB  │
│             │     │  Script     │     │   Worker     │     │  Backend    │     │  Cloud   │
└─────────────┘     └─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
      │                    │                     │                    │                  │
      │                    │                     │                    │                  │
   Enable             Capture DOM           Route Request         Process &          Store with
  Earn Mode           Messages              to Backend           Generate           Embeddings
                     (user/assistant)                            Embeddings
```

## Key Features

### 1. Role Differentiation
- Every message is tagged with `role: 'user'` or `role: 'assistant'`
- This allows reconstruction of full conversations with proper attribution

### 2. Multi-Platform Support
- Content scripts detect platform: Claude, ChatGPT, or Gemini
- Each platform's DOM structure is handled differently
- Platform stored with each message for filtering

### 3. Real-Time Capture
- Messages captured as users type (with debouncing)
- Both sides of conversation stored (user inputs + AI responses)
- Timestamps preserve conversation flow

### 4. Privacy & Security
- Wallet address used for user identification
- Messages only captured in "Earn Mode"
- HTTPS/WSS for all communications
- API authentication via JWT tokens

### 5. Search Capabilities
- Vector search using OpenAI embeddings
- Full-text search on raw message content
- Filter by platform, date, role
- Semantic similarity search

## Logging & Debugging

### Browser Console (Content Script)
```
🔍 CONTEXTLY: Processing message...
  Role: user
  Platform: claude
  Text preview: Can you help me understand how...
💰 CONTEXTLY: Earn mode active - saving to cloud...
✅ CONTEXTLY: Message saved successfully
```

### Backend Logs
```
🔵 INCOMING MESSAGE CAPTURE:
  - Role: assistant
  - Platform: claude
  - Wallet: 0x1234...5678
  - Raw Text: I'll help you understand...
📊 EMBEDDING: Generated 1536D vector
💾 LANCEDB: Stored in conversations_v2 table
```

## Error Handling

1. **Network Failures**: Retry with exponential backoff
2. **Invalid Messages**: Schema validation before storage
3. **Missing Embeddings**: Fallback to text-only search
4. **Rate Limiting**: Queue messages locally if API limit reached

## Performance Considerations

1. **Debouncing**: Messages debounced by 1000ms to avoid excessive API calls
2. **Batch Processing**: Multiple messages can be sent in one request
3. **Local Caching**: Recent conversations cached in browser storage
4. **Compression**: Large messages compressed before transmission

## Future Enhancements

1. **Streaming**: WebSocket connection for real-time updates
2. **Offline Support**: Queue messages when offline, sync when connected
3. **Encryption**: End-to-end encryption for sensitive conversations
4. **Export Formats**: Support for more export formats (PDF, Markdown, etc.)