# Contextly Enhanced Backend Guide

## Overview

The Contextly backend has been enhanced with cutting-edge technologies including **LanceDB** for vector storage and **GraphRAG** for intelligent context retrieval. This guide covers the new features and how to use them.

## Architecture

### Technology Stack

- **Vector Database**: LanceDB Cloud (with advanced indexing)
- **Graph Processing**: NetworkX + GraphRAG
- **Cache**: Upstash Redis
- **LLM**: OpenAI GPT-4o
- **Database**: MongoDB
- **Embeddings**: OpenAI + Sentence Transformers

### Key Features

1. **Advanced Vector Search** - Using LanceDB for billion-scale vector operations
2. **GraphRAG Integration** - Knowledge graph construction from conversations
3. **Intelligent Summarization** - Multi-mode conversation summaries
4. **Auto Title Generation** - Smart titles with emoji support
5. **Enhanced Conversation Management** - Dropdown-ready listing with previews
6. **Multimodal Support** - Text, code, and image embeddings
7. **Cross-Platform Transfer** - Graph-enhanced context transfer

## API Endpoints

### Conversation Management

#### Summarize Conversations
```bash
POST /v1/conversations/summarize
```

Request:
```json
{
  "session_id": "session-123",
  "messages": [...],
  "mode": "brief",  // or "detailed", "progressive"
  "max_length": 500
}
```

Response:
```json
{
  "session_id": "session-123",
  "summary": "Conversation summary...",
  "key_points": ["Point 1", "Point 2"],
  "topics": ["topic1", "topic2"],
  "action_items": ["Todo 1", "Todo 2"],
  "timestamp": 1234567890,
  "message_count": 15,
  "platform": "claude"
}
```

#### Generate Titles
```bash
POST /v1/conversations/title
```

Request:
```json
{
  "session_id": "session-123",
  "messages": [...],
  "style": "descriptive",  // or "topical", "creative"
  "include_emoji": true
}
```

Response:
```json
{
  "session_id": "session-123",
  "title": "🤖 GraphRAG Implementation Guide",
  "style": "descriptive"
}
```

#### List Conversations
```bash
POST /v1/conversations/list
```

Request:
```json
{
  "wallet": "0x...",
  "platform": "claude",  // optional
  "limit": 50,
  "offset": 0,
  "sort_by": "recent",  // or "relevant", "length"
  "search_query": "graphrag"  // optional
}
```

Response:
```json
{
  "conversations": [
    {
      "session_id": "session-123",
      "title": "🤖 GraphRAG Implementation Guide",
      "platform": "claude",
      "last_message": "2024-01-20T10:30:00Z",
      "message_count": 23,
      "summary_preview": "Discussion about implementing GraphRAG...",
      "topics": ["graphrag", "implementation", "python"],
      "has_action_items": true,
      "token_count": 1500
    }
  ],
  "total": 150,
  "offset": 0,
  "limit": 50
}
```

### GraphRAG Features

#### Build Knowledge Graph
```bash
POST /v1/graph/build
```

Parameters:
- `session_id`: Session to build graph from
- `wallet`: User wallet address

Response:
```json
{
  "success": true,
  "graph_id": "graph_session-123",
  "metrics": {
    "node_count": 45,
    "edge_count": 78,
    "community_count": 5,
    "density": 0.164,
    "avg_degree": 3.47
  },
  "communities": 5,
  "main_entities": ["GraphRAG", "LanceDB", "Vector Search", ...]
}
```

#### Query Knowledge Graph
```bash
POST /v1/graph/query
```

Parameters:
- `query`: Natural language query
- `session_id`: Optional session filter
- `wallet`: Optional wallet filter

Response:
```json
{
  "query": "How does GraphRAG work?",
  "answer": "Based on the knowledge graph, GraphRAG works by...",
  "entities": [
    {
      "name": "GraphRAG",
      "type": "technology",
      "relevance": 0.95,
      "community_id": 0
    }
  ],
  "session_id": "session-123"
}
```

### Enhanced Features

#### Generate Insights
```bash
POST /v1/insights/generate
```

Parameters:
- `wallet`: User wallet address
- `time_range`: Days to analyze (default: 7)

Response:
```json
{
  "insights": [
    "You've been focusing on GraphRAG implementations",
    "Peak productivity hours are 2-6 PM",
    "Consider exploring community detection algorithms"
  ],
  "stats": {
    "total_conversations": 45,
    "top_topics": [["graphrag", 15], ["lancedb", 12]],
    "platform_distribution": {"claude": 20, "chatgpt": 15, "gemini": 10}
  }
}
```

## Running the Backend

### Production Backend (requires external services)

1. Set up environment variables in `.env`:
```env
OPENAI_API_KEY=your-key
LANCEDB_URI=db://your-lancedb-uri
LANCEDB_API_KEY=your-lancedb-key
UPSTASH_REDIS_REST_URL=https://your-upstash-url
UPSTASH_REDIS_REST_TOKEN=your-token
MONGODB_URL=mongodb://localhost:27017
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend:
```bash
python backend_enhanced.py
```

### Demo Backend (no external dependencies)

For testing and development:
```bash
python backend_demo.py
```

The demo backend provides:
- In-memory storage
- Simplified summarization
- Mock GraphRAG responses
- Basic title generation

## Integration with Chrome Extension

The Chrome extension integrates with these endpoints to provide:

1. **Smart Conversation Management**
   - Auto-generated titles in the dropdown
   - Summary previews for quick context
   - Topic-based filtering

2. **Enhanced Context Transfer**
   - Graph-based context understanding
   - Intelligent summary generation
   - Cross-platform optimization

3. **Advanced Search**
   - Vector similarity search
   - Entity-based filtering
   - Knowledge graph queries

## GraphRAG Implementation Details

### How It Works

1. **Entity Extraction**: GPT-4 extracts entities and relationships from conversations
2. **Graph Construction**: NetworkX builds a knowledge graph
3. **Community Detection**: Identifies clusters of related concepts
4. **Hierarchical Summarization**: Generates summaries at multiple levels
5. **Query Processing**: Natural language queries traverse the graph

### Benefits

- **Better Context Understanding**: Graph structure captures relationships
- **Holistic Insights**: Community summaries provide big-picture view
- **Precise Retrieval**: Entity-based search is more accurate
- **Scalability**: Handles large conversation histories efficiently

## Performance Optimizations

1. **Vector Indexing**: IVF_PQ for billion-scale search
2. **Caching**: Redis for frequently accessed data
3. **Batch Processing**: Efficient embedding generation
4. **Incremental Updates**: Graph updates without full rebuild

## Testing

Run the test suite:
```bash
python test_backend.py
```

This tests:
- Summarization endpoints
- Title generation
- Conversation listing
- Graph construction
- Knowledge queries

## Future Enhancements

1. **Real-time Graph Updates**: Stream processing for live updates
2. **Multi-user Collaboration**: Shared knowledge graphs
3. **Advanced Analytics**: ML-based pattern detection
4. **Voice/Video Support**: Multimodal conversation handling

## Troubleshooting

### Common Issues

1. **LanceDB Connection**: Ensure API key is valid
2. **MongoDB Not Running**: Start with `mongod`
3. **Port Already in Use**: Check with `lsof -i :8000`

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

1. **API Keys**: Never commit credentials
2. **PII Removal**: All text is anonymized
3. **Authentication**: JWT tokens for API access
4. **Rate Limiting**: Implemented via Upstash

## Support

For issues or questions:
- GitHub: [contextly/contextly](https://github.com/contextly/contextly)
- Docs: http://localhost:8000/docs (when running)