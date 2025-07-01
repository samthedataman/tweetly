# Contextly Project Structure

## Overview

This document describes the organization and architecture of the Contextly codebase.

## Directory Structure

```
contextly/
├── src/                        # Source code
│   ├── extension/              # Chrome Extension code
│   │   ├── background/         # Background service worker
│   │   │   └── background.js   # Main background script
│   │   │
│   │   ├── content/            # Content scripts
│   │   │   └── content.js      # Injected into AI platforms
│   │   │
│   │   ├── popup/              # Extension popup
│   │   │   ├── popup.html      # Popup UI
│   │   │   ├── popup.js        # Popup logic
│   │   │   └── styles.css      # Popup styling
│   │   │
│   │   ├── adapters/           # Platform integrations
│   │   │   ├── apiAdapter.js   # API communication
│   │   │   ├── walletAdapter.js # Web3 wallet integration
│   │   │   └── baseIntegration.js # Base blockchain
│   │   │
│   │   └── services/           # Core services
│   │       ├── contractService.js # Smart contract interaction
│   │       ├── gaslessService.js  # Gasless transactions
│   │       └── progressiveOnboarding.js # User onboarding
│   │
│   ├── backend/                # Backend API
│   │   ├── api/                # API endpoints
│   │   │   ├── backend.py      # Original backend
│   │   │   ├── backend_enhanced.py # Enhanced with GraphRAG
│   │   │   └── backend_demo.py # Demo version
│   │   │
│   │   ├── models/             # Data models (future)
│   │   ├── services/           # Business logic (future)
│   │   └── utils/              # Utilities (future)
│   │
│   ├── shared/                 # Shared modules
│   │   ├── config.js           # Configuration
│   │   └── messageProtocol.js  # Message handling
│   │
│   └── tests/                  # Test suites
│       ├── test_backend.py     # Backend tests
│       └── integration-test.js # Extension tests
│
├── docs/                       # Documentation
│   ├── BACKEND_GUIDE.md        # Backend documentation
│   └── PROJECT_STRUCTURE.md    # This file
│
├── scripts/                    # Build and utility scripts
│   └── build.js                # Build script
│
├── icons/                      # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
│
├── build/                      # Build output (git ignored)
├── venv/                       # Python virtual environment
│
├── manifest.json               # Extension manifest
├── requirements.txt            # Python dependencies
├── package.json                # Node.js configuration
├── README.md                   # Project documentation
├── CONTRIBUTING.md             # Contribution guidelines
├── CHANGELOG.md                # Version history
├── LICENSE                     # MIT License
├── .env.example                # Environment template
├── .env                        # Environment variables (git ignored)
└── .gitignore                  # Git ignore rules
```

## Key Components

### Extension Architecture

1. **Background Script** (`background.js`)
   - Manages extension lifecycle
   - Handles message routing
   - Manages context menus
   - Coordinates screen capture
   - Tracks user journeys

2. **Content Script** (`content.js`)
   - Injected into AI platform pages
   - Captures conversations in real-time
   - Extracts text and artifacts
   - Handles platform-specific logic
   - Monitors DOM changes

3. **Popup Interface** (`popup.js`, `popup.html`)
   - User interface for the extension
   - Displays conversation summaries
   - Manages wallet connection
   - Shows earnings and stats
   - Provides quick actions

### Backend Architecture

1. **API Layer** (`backend_enhanced.py`)
   - FastAPI-based REST API
   - GraphRAG integration
   - Vector search with LanceDB
   - Knowledge graph construction
   - Smart summarization

2. **Data Storage**
   - **MongoDB**: Metadata and user data
   - **LanceDB**: Vector embeddings
   - **Redis**: Caching layer
   - **In-memory**: Demo mode storage

3. **Processing Pipeline**
   - Text anonymization
   - Embedding generation
   - Entity extraction
   - Graph construction
   - Community detection

### Shared Components

1. **Message Protocol** (`messageProtocol.js`)
   - Standardized message format
   - Action definitions
   - Request/response handling

2. **Configuration** (`config.js`)
   - Platform definitions
   - API endpoints
   - Feature flags
   - UI constants

## Data Flow

1. **Capture Flow**
   ```
   AI Platform → Content Script → Background → API → Storage
   ```

2. **Retrieval Flow**
   ```
   Popup → Background → API → Vector Search → Results
   ```

3. **Graph Construction**
   ```
   Conversations → Entity Extraction → Graph Building → Community Detection
   ```

## Development Guidelines

### Code Organization

- Keep files focused and single-purpose
- Use descriptive names for functions and variables
- Add comments for complex logic
- Follow the existing code style

### Module Boundaries

- Extension code shouldn't directly access backend
- Use message passing between extension components
- Keep platform-specific code in adapters
- Share common utilities in the shared directory

### Testing Strategy

- Unit tests for individual functions
- Integration tests for API endpoints
- Manual testing for UI components
- End-to-end tests for critical flows

## Build Process

1. **Development Build**
   ```bash
   npm run build
   ```

2. **Production Build**
   ```bash
   npm run build:prod
   ```

3. **Package Extension**
   ```bash
   npm run package
   ```

## Deployment

### Extension Deployment
1. Build the extension
2. Upload to Chrome Web Store
3. Submit for review

### Backend Deployment
1. Set up environment variables
2. Deploy to cloud provider
3. Configure MongoDB and Redis
4. Set up LanceDB connection

## Security Considerations

- API keys stored in environment variables
- PII automatically removed from text
- Secure message passing protocols
- JWT authentication for API access
- Wallet signature verification