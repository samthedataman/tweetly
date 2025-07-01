# Contextly Repository Structure

## Overview
This document describes the organized structure of the Contextly repository.

## Directory Structure

```
contextly/
├── docs/                       # All documentation files
│   ├── BACKEND_GUIDE.md
│   ├── CHANGELOG.md
│   ├── CONTRIBUTING.md
│   ├── PROJECT_STRUCTURE.md
│   └── ...
│
├── icons/                      # Application icons
│   ├── icon16.png
│   ├── icon48.png
│   ├── icon128.png
│   └── ai-provider icons
│
├── scripts/                    # Utility scripts
│   ├── build.js               # Build script
│   ├── database/              # Database management scripts
│   │   ├── ensure_all_tables.py
│   │   ├── fix_lancedb_schema.py
│   │   └── wipe_and_init_tables.py
│   └── debug/                 # Debug utilities
│       ├── debug_endpoints.py
│       ├── debug_graph_viz.py
│       └── ...
│
├── src/                       # Source code
│   ├── backend/               # Backend API code
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   ├── blockchain/            # Blockchain contracts and services
│   ├── extension/             # Browser extension code
│   │   ├── background/
│   │   ├── content/
│   │   ├── popup/
│   │   └── ...
│   ├── shared/                # Shared utilities
│   └── tests/                 # Unit tests within src
│
├── tests/                     # All test files
│   ├── test_all_endpoints.py
│   ├── test_auth.py
│   ├── test_lancedb_data.js
│   └── ...
│
├── build/                     # Build artifacts (gitignored)
├── logs/                      # Application logs (gitignored)
├── node_modules/              # Node dependencies (gitignored)
├── venv/                      # Python virtual environment (gitignored)
│
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── manifest.json              # Extension manifest
├── package.json               # Node.js dependencies
├── requirements.txt           # Python dependencies
├── README.md                  # Project README
└── vercel.json               # Vercel deployment config
```

## Key Directories

### `/docs`
Contains all project documentation including guides, changelogs, and technical specifications.

### `/src`
Main source code directory with subdirectories for backend, blockchain, extension, and shared code.

### `/tests`
Contains all test files for both Python and JavaScript components.

### `/scripts`
Utility scripts organized by purpose:
- `database/` - Database initialization and management
- `debug/` - Debugging and troubleshooting utilities

## Configuration Files

- `.env.example` - Template for environment variables
- `manifest.json` - Chrome extension manifest
- `package.json` - Node.js project configuration
- `requirements.txt` - Python dependencies
- `vercel.json` - Vercel deployment configuration