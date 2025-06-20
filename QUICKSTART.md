# 🚀 AI Chat to Twitter - Quick Start

## Setup in 3 Steps

### 1. Start Backend (1 minute)
```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python backend.py
```
Server runs at http://localhost:8000

### 2. Install Chrome Extension (1 minute)
1. Open Chrome → `chrome://extensions/`
2. Turn on "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the folder with these files

### 3. Use It!
1. Go to Claude.ai, ChatGPT, or Google AI Studio
2. Hover over any message
3. Click the buttons:
   - 🐦 Tweet it
   - 📊 Condense it
   - ✨ Restyle it

## Files You Need

```
your-folder/
├── backend.py         # Run this
├── requirements.txt   # Install these
├── manifest.json      # Chrome extension files
├── content.js         # Chrome extension files
└── styles.css         # Chrome extension files
```

## That's It! 🎉

No API keys needed. No database. Just works!

## Troubleshooting

**Can't see buttons?**
- Refresh the page
- Make sure backend is running
- Check Chrome console (F12) for errors

**Server error?**
- Make sure port 8000 is free
- Try: `python backend.py` again

## How It Works

1. Extension adds buttons to AI chat messages
2. Click button → sends text to backend
3. Backend processes text (condense/restyle)
4. Opens Twitter with processed text

Simple as that!
