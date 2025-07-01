# Contextly.ai - AI Conversation Intelligence Platform

<div align="center">
  <img src="icons/icon128.png" alt="Contextly Logo" width="128" height="128">
  
  **Capture, organize, and monetize your AI conversations across Claude, ChatGPT, and Gemini**
  
  [![Chrome Web Store](https://img.shields.io/badge/Chrome-Extension-4285F4?logo=google-chrome&logoColor=white)](https://chrome.google.com/webstore)
  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
  [![Version](https://img.shields.io/badge/version-3.0.0-green.svg)](manifest.json)
</div>

## 🚀 Features

### Core Capabilities
- **🔄 Universal AI Capture** - Automatically capture conversations from Claude, ChatGPT, and Gemini
- **🧠 GraphRAG Intelligence** - Knowledge graph construction for deep context understanding
- **📊 Smart Summarization** - Multi-mode conversation summaries with key insights
- **🏷️ Auto-Titling** - Intelligent conversation titles with emoji categorization
- **💰 Web3 Earn Mode** - Monetize your AI interactions on Base blockchain
- **🔍 Vector Search** - Lightning-fast semantic search across all conversations
- **📱 Cross-Platform Transfer** - Seamlessly move context between AI platforms

### Advanced Features
- **Knowledge Graphs** - Extract entities and relationships from conversations
- **Progressive Summarization** - Handle ultra-long conversations efficiently
- **Multimodal Support** - Process text, code, and images
- **Real-time Insights** - Behavioral analytics and usage patterns
- **Gasless Transactions** - Web3 features without transaction fees

## 📁 Project Structure

```
contextly/
├── src/
│   ├── extension/          # Chrome Extension
│   │   ├── background/     # Service worker scripts
│   │   ├── content/        # Content scripts for AI platforms
│   │   ├── popup/          # Extension popup UI
│   │   ├── adapters/       # Platform & wallet adapters
│   │   └── services/       # Core services
│   │
│   ├── backend/           # Backend API
│   │   ├── api/           # FastAPI endpoints
│   │   ├── models/        # Data models
│   │   ├── services/      # Business logic
│   │   └── utils/         # Utility functions
│   │
│   ├── shared/            # Shared modules
│   │   ├── config.js      # Configuration
│   │   └── messageProtocol.js # Message handling
│   │
│   └── tests/             # Test suites
│
├── docs/                  # Documentation
├── scripts/               # Build & deployment scripts
├── icons/                 # Extension icons
└── requirements.txt       # Python dependencies
```

## 🛠️ Technology Stack

### Frontend (Chrome Extension)
- **Core**: Vanilla JavaScript, Chrome Extension Manifest V3
- **Blockchain**: Web3.js, Base Network Integration
- **UI**: Custom CSS with modern design system

### Backend
- **Framework**: FastAPI (Python 3.7+)
- **Vector DB**: LanceDB Cloud for embeddings
- **Graph Processing**: NetworkX + GraphRAG
- **Cache**: Upstash Redis
- **Database**: MongoDB
- **AI/ML**: OpenAI GPT-4, Sentence Transformers

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Node.js 14+ (for development tools)
- Chrome/Brave browser
- MongoDB (optional for full backend)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/contextly/contextly.git
   cd contextly
   ```

2. **Set up the backend**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Copy environment template
   cp .env.example .env
   # Edit .env with your API keys

   # Run the backend (demo mode)
   python src/backend/api/backend_demo.py
   ```

3. **Install the Chrome Extension**
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `contextly` directory

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:

```env
# Required
OPENAI_API_KEY=your-openai-key

# Optional (for full features)
LANCEDB_URI=db://your-lancedb-uri
LANCEDB_API_KEY=your-lancedb-key
UPSTASH_REDIS_REST_URL=https://your-upstash-url
UPSTASH_REDIS_REST_TOKEN=your-token
MONGODB_URL=mongodb://localhost:27017
```

### Extension Configuration
Edit `src/shared/config.js` to customize:
- API endpoints
- Platform selectors
- Feature flags

## 📖 Usage Guide

### Basic Usage

1. **Install Extension**: Add to Chrome from the Web Store or load unpacked
2. **Start Capturing**: Visit Claude, ChatGPT, or Gemini - conversations auto-capture
3. **View Summaries**: Click extension icon to see organized conversations
4. **Search & Filter**: Use the search bar to find specific topics

### Advanced Features

#### Enable Earn Mode
1. Click the extension icon
2. Toggle to "Earn Mode"
3. Connect your wallet (Coinbase Smart Wallet recommended)
4. Start earning CTXT tokens for quality conversations

#### Build Knowledge Graphs
```javascript
// Via API
POST /v1/graph/build
{
  "session_id": "your-session-id",
  "wallet": "0x..."
}
```

#### Generate Insights
Access behavioral analytics and recommendations through the insights API.

## 🧪 Testing

### Run Tests
```bash
# Backend tests
python src/tests/test_backend.py

# Extension tests
npm test
```

### Manual Testing
Use the demo backend for development:
```bash
python src/backend/api/backend_demo.py
```

## 📚 API Documentation

### Key Endpoints

#### Conversation Management
- `POST /v1/conversations/summarize` - Generate summaries
- `POST /v1/conversations/title` - Auto-generate titles
- `POST /v1/conversations/list` - List with previews

#### GraphRAG
- `POST /v1/graph/build` - Build knowledge graph
- `POST /v1/graph/query` - Query with natural language

#### Analytics
- `POST /v1/insights/generate` - User behavior insights

Full API documentation available at `http://localhost:8000/docs` when running.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📈 Roadmap

- [ ] Real-time collaboration features
- [ ] Mobile app companion
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Voice conversation support
- [ ] Plugin system for custom integrations

## 🔒 Security

- All conversations are anonymized before storage
- PII is automatically removed
- Wallet signatures verify ownership
- JWT authentication for API access

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- Microsoft Research for GraphRAG concepts
- LanceDB team for vector database
- Base/Coinbase for blockchain infrastructure

## 📞 Support

- **Documentation**: [docs.contextly.ai](https://docs.contextly.ai)
- **Issues**: [GitHub Issues](https://github.com/contextly/contextly/issues)
- **Discord**: [Join our community](https://discord.gg/contextly)
- **Email**: support@contextly.ai

---

<div align="center">
  Made with ❤️ by the Contextly Team
  
  [Website](https://contextly.ai) • [Twitter](https://twitter.com/contextly_ai) • [Blog](https://blog.contextly.ai)
</div>