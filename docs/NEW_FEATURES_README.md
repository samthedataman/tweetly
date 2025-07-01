# New Contextly API Features - Authenticated & Session-Tracked

## 🎯 Overview

This document describes the new API endpoints added to Contextly for graph visualization, journey analytics, and X (Twitter) authentication. **All endpoints now require authentication** and track user sessions with CTXT earnings.

## 🔐 Authentication Methods

All API endpoints (except registration) require authentication using one of these methods:

### 1. Wallet Authentication (Recommended)
```bash
# Headers required:
X-Wallet-Address: 0x1234...abcd
X-Wallet-Signature: 0xsignature_of_message

# Message to sign (default):
"Sign this message to authenticate with Contextly: YYYY-MM-DD"
```

### 2. X (Twitter) Authentication
```bash
# Header required:
X-Auth-Token: x_token_received_from_oauth

# First authenticate via /v1/auth/x/login
# Then use the token for subsequent requests
```

### 3. Session Authentication
```bash
# Header required:
X-Session-ID: session_id_from_previous_auth

# Sessions last 24 hours and track all activity
```

### 4. JWT Bearer Token
```bash
# Header required:
Authorization: Bearer <jwt_token>
```

## 📊 Session & Earnings Tracking

Every authenticated request:
- Creates or updates a session
- Tracks user activity
- Records CTXT earnings
- Links all actions to the authenticated user

### Get Session History
```bash
GET /v1/sessions/history

Response:
{
    "user_id": "user_123",
    "auth_method": "wallet",
    "total_ctxt_earned": 125.45,
    "session_count": 23,
    "sessions": [
        {
            "session_id": "sess_abc123",
            "platform": "claude",
            "message_count": 45,
            "ctxt_earned": 2.34,
            "topics": ["AI", "coding", "authentication"]
        }
    ],
    "current_session": {
        "session_id": "sess_current",
        "started_at": "2024-01-15T10:30:00Z",
        "auth_method": "wallet"
    }
}
```

### Get Earnings Details
```bash
GET /v1/earnings/details?days=30

Response:
{
    "user_id": "user_123",
    "total_ctxt_earned": 125.45,
    "period_days": 30,
    "daily_earnings": {
        "2024-01-15": {
            "messages": 1.23,
            "journeys": 0.45,
            "total": 1.68
        }
    },
    "earnings_by_type": {
        "messages": 95.20,
        "journeys": 25.15,
        "graphs": 5.10,
        "referrals": 0.00
    },
    "stats": {
        "total_conversations": 156,
        "total_journeys": 23,
        "graphs_created": 8,
        "average_daily": 4.18
    }
}
```

## 📊 Graph Visualization API

### Endpoint: `POST /v1/graph/visualize`

Generate interactive graph visualization data from user's knowledge graphs.

**Request Body:**
```json
{
    "wallet": "0x1234...",
    "session_id": "optional_session_id",
    "filter": {
        "entity_types": ["person", "concept", "tool"],
        "min_centrality": 0.5,
        "community_id": 1,
        "date_range": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z"
        }
    },
    "layout": "force",  // Options: "force", "hierarchical", "circular"
    "max_nodes": 100
}
```

**Response:**
```json
{
    "nodes": [
        {
            "id": "entity_123",
            "label": "Machine Learning",
            "type": "concept",
            "size": 45,
            "color": "#6366f1",
            "metadata": {
                "centrality_score": 0.85,
                "community_id": 1,
                "occurrence_count": 23,
                "first_seen": "2024-01-15T10:30:00Z",
                "last_seen": "2024-03-20T15:45:00Z"
            }
        }
    ],
    "edges": [
        {
            "source": "entity_123",
            "target": "entity_456",
            "type": "relates_to",
            "weight": 0.75,
            "label": "used_in"
        }
    ],
    "communities": [
        {
            "id": 1,
            "color": "#6366f1",
            "label": "AI/ML Concepts",
            "node_count": 15
        }
    ],
    "stats": {
        "total_nodes": 50,
        "total_edges": 125,
        "density": 0.102,
        "avg_degree": 5.0
    }
}
```

### Use Cases:
- Visualize knowledge networks with D3.js or similar libraries
- Identify key concepts and their relationships
- Explore community clusters in conversations
- Track evolution of topics over time

## 📈 Journey Analytics (Sankey Diagrams)

### Endpoint: `POST /v1/journeys/sankey`

Generate Sankey diagram data for user journey visualization.

**Request Body:**
```json
{
    "wallet": "0x1234...",  // Optional for individual user
    "aggregate": false,     // Set true for all users
    "filter": {
        "date_range": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z"
        },
        "platforms": ["claude", "chatgpt"],
        "min_duration": 60
    },
    "granularity": "domain"  // Options: "domain", "page", "section"
}
```

**Response:**
```json
{
    "nodes": [
        {
            "id": "research",
            "name": "Research",
            "type": "source",
            "visits": 150
        },
        {
            "id": "coding",
            "name": "Coding",
            "type": "target",
            "visits": 120
        }
    ],
    "links": [
        {
            "source": "research",
            "target": "coding",
            "value": 85,
            "avg_duration": 245,
            "conversion_rate": 0.71
        }
    ],
    "patterns": [
        {
            "pattern": ["research", "coding", "debugging"],
            "frequency": 45,
            "avg_quality_score": 0.82
        }
    ],
    "insights": {
        "most_common_paths": [
            ["research", "coding"],
            ["planning", "implementation", "testing"]
        ],
        "dropout_points": [
            {
                "page": "complex_analysis",
                "dropout_rate": 0.35
            }
        ],
        "high_value_paths": [
            {
                "path": ["research", "coding", "documentation"],
                "avg_earnings": 0.15
            }
        ]
    }
}
```

### Use Cases:
- Visualize user flow through different AI platforms
- Identify common research patterns
- Optimize user experience based on journey data
- Track conversion funnels

## 🐦 X (Twitter) Authentication

### 1. Initiate Authentication
**Endpoint:** `POST /v1/auth/x/login`

```json
{
    "callback_url": "https://yourapp.com/auth/callback",
    "telegram_chat_id": "123456789",
    "telegram_user_id": "987654321"
}
```

**Response:**
```json
{
    "auth_url": "https://twitter.com/i/oauth/authorize?...",
    "session_id": "abc123",
    "state": "pending"
}
```

### 2. Handle Callback
**Endpoint:** `GET /v1/auth/x/callback?oauth_token=...&oauth_verifier=...`

Automatically handles OAuth callback and links X account.

### 3. Check Status
**Endpoint:** `GET /v1/auth/x/status?wallet=0x1234...`

```json
{
    "authenticated": true,
    "x_username": "user123",
    "x_id": "x_abc123",
    "linked_at": "2024-01-15T10:30:00Z"
}
```

### 4. Verify Authentication
**Endpoint:** `POST /v1/auth/verify`

Supports both wallet and X authentication:

```json
// Wallet auth
{
    "type": "wallet",
    "wallet": "0x1234...",
    "signature": "0xabc...",
    "message": "Sign this message..."
}

// X auth
{
    "type": "x",
    "x_id": "x_123456",
    "telegram_user_id": "987654321"
}
```

## 🚀 Quick Start

1. **Start the backend:**
   ```bash
   python src/backend/api/backend_enhanced.py
   ```

2. **Test the endpoints:**
   ```bash
   python test_new_endpoints.py
   ```

3. **View API docs:**
   Open http://localhost:8000/docs in your browser

## 🔧 Implementation Notes

- **Graph Visualization**: Currently uses LanceDB embeddings. For production, consider integrating Neo4j for true graph database capabilities.
- **Journey Analytics**: Simplified implementation using intent/category. Can be enhanced with actual URL tracking.
- **X Authentication**: Mock implementation for demo. Production requires proper OAuth1.0a/2.0 flow with X API credentials.

## 📦 Dependencies

Make sure these are installed:
```bash
pip install networkx pandas numpy urllib3
```

## 🎨 Frontend Integration

### Graph Visualization (D3.js example):
```javascript
// Fetch graph data
const response = await fetch('/v1/graph/visualize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        wallet: userWallet,
        max_nodes: 100
    })
});

const graphData = await response.json();

// Render with D3.js
const simulation = d3.forceSimulation(graphData.nodes)
    .force("link", d3.forceLink(graphData.edges).id(d => d.id))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2));
```

### Sankey Diagram (Plotly example):
```javascript
// Fetch journey data
const journeyData = await fetch('/v1/journeys/sankey', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        wallet: userWallet,
        aggregate: false
    })
}).then(r => r.json());

// Render with Plotly
const data = [{
    type: "sankey",
    node: {
        pad: 15,
        thickness: 20,
        label: journeyData.nodes.map(n => n.name),
        color: journeyData.nodes.map(n => n.type === 'source' ? '#6366f1' : '#10b981')
    },
    link: {
        source: journeyData.links.map(l => journeyData.nodes.findIndex(n => n.id === l.source)),
        target: journeyData.links.map(l => journeyData.nodes.findIndex(n => n.id === l.target)),
        value: journeyData.links.map(l => l.value)
    }
}];

Plotly.newPlot('sankey-chart', data);
```

## 📞 Support

For questions or issues with the new endpoints, please open an issue on GitHub or contact the development team.