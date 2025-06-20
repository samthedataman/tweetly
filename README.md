# AI Chat to Twitter Chrome Extension 🐦✨

Share your AI conversations on Twitter/X and other platforms with style! This Chrome extension adds sharing capabilities to Claude.ai, ChatGPT, and Google AI Studio, with AI-powered text processing and image generation.

![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-blue?logo=googlechrome)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?logo=fastapi)
![AI Powered](https://img.shields.io/badge/AI-Powered-purple?logo=openai)

## 🌟 Features

### 🎯 Universal AI Platform Support
- **Claude.ai** - Full support with artifact handling
- **ChatGPT** - Seamless integration
- **Google AI Studio** - Complete compatibility

### 📤 Multi-Platform Sharing
- **🐦 Twitter/X** - Share conversations with automatic text condensing
- **📧 Email** - Send via your default email client
- **💬 SMS** - Share through text messages
- **📰 Substack** - Convert to newsletter articles
- **📄 Medium** - Create blog posts

### 🤖 AI-Powered Features
- **📝 Smart Condensing** - Automatically fit long messages into Twitter's 280-character limit
- **✨ Text Restyling** - Transform tone and style:
  - Professional
  - Casual
  - Humorous
  - Concise
  - Creative
  - Technical
- **🎨 Image Generation** - Create AI images with DALL-E 3
- **🖼️ Image Effects** - Add fun effects (tophat, monocle, synthwave, retro)

### 🎨 Smart UI Features
- **Floating Action Buttons** - Non-intrusive share buttons on AI messages
- **Text Selection Button** - Share selected text instantly
- **Platform-Adaptive Design** - Matches each AI platform's UI
- **Real-time Status Indicator** - Shows extension and processing status
- **Character Counter** - Color-coded warnings for Twitter limits

## 📋 Requirements

### Chrome Extension
- Google Chrome or Chromium-based browser
- Developer mode enabled for local installation

### Backend Server
- Python 3.8+
- API Keys:
  - Anthropic API key (for Claude text processing)
  - OpenAI API key (for DALL-E image generation)
  - Twitter API credentials (optional, for OAuth)

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-chat-twitter.git
cd ai-chat-twitter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# TWITTER_API_KEY=your_key_here (optional)
# TWITTER_API_SECRET=your_secret_here (optional)

# Run the server
python backend.py
```

The server will start on `http://localhost:8000`

### 2. Chrome Extension Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the project directory containing `manifest.json`
5. The extension icon will appear in your toolbar

### 3. Using the Extension

1. Visit Claude.ai, ChatGPT, or Google AI Studio
2. Look for the floating share buttons on AI messages
3. Click a button to share:
   - 🐦 Twitter - Opens compose window with condensed text
   - 📧 Email - Opens email client with formatted message
   - 💬 SMS - Opens SMS app with message
   - 📰 Substack/📄 Medium - Redirects to platform
4. Select any text to see the floating share button
5. Use the "Condense" or "Restyle" options for AI text processing

## 🛠️ Development

### Project Structure

```
ai-chat-twitter/
├── manifest.json        # Chrome extension manifest
├── content.js          # Main extension logic
├── styles.css          # Extension styles
├── icon.svg           # Extension icon
├── backend.py         # FastAPI backend server
├── requirements.txt   # Python dependencies
├── vercel.json       # Vercel deployment config
└── README.md         # This file
```

### Backend API Endpoints

- `GET /` - Health check
- `POST /condense` - Condense text for Twitter
- `POST /restyle` - Transform text style
- `POST /email` - Prepare email with conversation
- `POST /generate-image` - Generate AI image
- `POST /add-effect` - Add effects to images
- `GET /auth/twitter` - Twitter OAuth flow
- `GET /auth/twitter/callback` - OAuth callback

### Extension Configuration

Edit `manifest.json` to modify:
- Permissions
- Content script injection sites
- Extension metadata

### Styling

The extension uses platform-adaptive styling. Modify `styles.css` to change:
- Button appearance
- Dialog styles
- Animation effects
- Platform-specific themes

## 🚀 Deployment

### Backend Deployment (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
```

### Extension Publishing

1. Test thoroughly on all supported platforms
2. Create a ZIP file of extension files
3. Upload to Chrome Web Store
4. Follow Google's review process

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required for text processing
ANTHROPIC_API_KEY=your_anthropic_api_key

# Required for image generation
OPENAI_API_KEY=your_openai_api_key

# Optional - for Twitter OAuth
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret

# Server configuration
BASE_URL=http://localhost:8000
PORT=8000
```

### Chrome Extension Settings

The extension automatically detects the backend URL. For production, update the `BASE_URL` in `content.js`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style
- Test on all supported AI platforms
- Update documentation for new features
- Add error handling for edge cases
- Ensure backward compatibility

## 🐛 Troubleshooting

### Extension Not Working

1. Check if the backend server is running
2. Verify API keys are correctly set
3. Check browser console for errors
4. Ensure you're on a supported AI platform

### Text Processing Issues

1. Verify Anthropic API key is valid
2. Check server logs for errors
3. Ensure proper CORS configuration

### Image Generation Failures

1. Verify OpenAI API key is valid
2. Check API rate limits
3. Ensure image prompt is appropriate

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [Anthropic Claude](https://www.anthropic.com/) and [OpenAI](https://openai.com/)
- Icons and UI inspired by material design principles

## 📞 Support

- Report bugs via [GitHub Issues](https://github.com/yourusername/ai-chat-twitter/issues)
- Feature requests welcome!
- Contact: your.email@example.com

---

Made with ❤️ for the AI community