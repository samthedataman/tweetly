# Enhanced Conversation Capture & Navigation Guide

## Overview

This guide details the enhanced conversation capture system and improved popup navigation features for Contextly. These updates ensure 100% capture coverage across all AI platforms and provide seamless conversation management.

## Enhanced Features

### 1. **100% Conversation Capture**

#### Complete Selector Coverage

The enhanced content script (`content_enhanced.js`) includes comprehensive selectors for:

**Claude:**
- Regular messages with all DOM variations
- Streaming messages with real-time capture
- Artifacts in iframes
- Code blocks with syntax highlighting
- Model indicators and metadata
- Edit/regeneration events

**ChatGPT:**
- User and assistant messages
- System messages
- Plugin responses
- DALL-E image generations
- File uploads/downloads
- Code interpreter results
- Canvas interactions
- Model switching indicators

**Gemini:**
- Query and response messages
- Streaming responses
- Code execution results
- Extension responses
- Image analysis
- Multi-modal content
- Citation sources

#### Advanced Content Extraction

```javascript
// Enhanced extraction methods
- Markdown preservation
- Code block formatting
- Table structure retention
- LaTeX/Math expressions
- List formatting
- Nested content handling
```

#### Real-time Monitoring

- Multiple MutationObservers for different containers
- Streaming message detection
- Dynamic content loading handling
- Periodic scanning for missed content
- Attribute change monitoring

### 2. **Enhanced Popup Navigation**

#### Conversation List Features

- **Advanced Search**: Full-text search across titles, summaries, and topics
- **Smart Filters**: 
  - Platform filter (Claude, ChatGPT, Gemini)
  - Date filter (Today, This Week, This Month)
  - Sort options (Recent, Most Messages, Most Relevant)
- **Rich Previews**: 
  - Auto-generated titles with emojis
  - Summary previews
  - Topic tags
  - Message counts
  - Action item indicators

#### Conversation Detail View

- Full conversation display
- Key points and action items
- Topic analysis
- Message timestamps
- Copy entire conversation
- Share functionality

### 3. **One-Click Resume Feature**

#### How It Works

1. Click "Resume" button in conversation detail
2. Opens appropriate AI platform (or uses current tab)
3. Automatically inserts conversation context
4. Positions cursor for continuation
5. Optional auto-submit

#### Resume Modes

**Smart Context** (Default):
- Last 3 exchanges
- Key points summary
- Relevant context only

**Full Context**:
- Complete conversation history
- All messages included
- Best for complex discussions

**Summary Context**:
- Brief overview only
- Minimal token usage
- Quick continuation

## Implementation Guide

### 1. Update Content Script

Replace the current content.js with enhanced version:

```javascript
// In manifest.json
"content_scripts": [{
  "matches": ["*://claude.ai/*", "*://chat.openai.com/*", "*://gemini.google.com/*"],
  "js": [
    "content/content_enhanced.js",
    "content/resume_handler.js",
    "content/content.js"
  ]
}]
```

### 2. Update Popup

Replace popup.js with enhanced version:

```javascript
// In popup.html
<script src="popup_enhanced.js"></script>
```

### 3. Add Resume Handler

The resume handler enables conversation continuation:

```javascript
// Automatically initialized when content script loads
// Handles platform-specific input detection
// Manages text insertion and submission
```

## Selector Reference

### Claude Selectors

```javascript
// Messages
'div[data-is-human="true"]' // User messages
'div[data-is-streaming="false"]' // Completed AI messages
'div[data-is-streaming="true"]' // Streaming messages

// Artifacts
'iframe[title*="artifact"]'
'iframe[src*="artifact"]'

// Code blocks
'pre:has(code)'
'div[class*="code-block"]'
```

### ChatGPT Selectors

```javascript
// Messages
'div[data-message-author-role="user"]'
'div[data-message-author-role="assistant"]'
'div[class*="agent-turn"]'

// Special content
'div[class*="plugin-result"]'
'img[alt*="DALL"]'
'div[class*="code-execution"]'
```

### Gemini Selectors

```javascript
// Messages
'.query-text'
'.model-response-text'
'message-content[class*="user"]'
'message-content[class*="model"]'

// Special content
'div[class*="code-execution"]'
'.executed-code'
'div[class*="extension-response"]'
```

## Testing Guide

### 1. Capture Testing

Test each platform with:
- Regular text messages
- Code blocks
- Lists and tables
- Math expressions
- Images/files
- Streaming responses
- Edits/regenerations

### 2. Resume Testing

1. Have a conversation on any platform
2. Open Contextly popup
3. Find conversation in list
4. Click to view details
5. Click "Resume" button
6. Verify context is inserted correctly

### 3. Edge Cases

- Very long conversations (1000+ messages)
- Multi-language content
- Special characters and emojis
- Rapid message sending
- Platform UI updates

## Performance Considerations

### Memory Usage

- Message deduplication with hashing
- Efficient DOM querying
- Cleanup of old observers
- Periodic garbage collection

### CPU Usage

- Throttled mutation handling
- Batched message processing
- Optimized text extraction
- Minimal re-renders

## Troubleshooting

### Messages Not Captured

1. Check browser console for errors
2. Verify selectors match current DOM
3. Check if platform updated UI
4. Ensure content script is injected

### Resume Not Working

1. Verify input field selectors
2. Check for platform-specific restrictions
3. Ensure proper permissions
4. Test with different context modes

### Performance Issues

1. Reduce observer scope
2. Increase processing intervals
3. Limit message history
4. Clear old conversations

## Future Enhancements

1. **Voice Message Support**: Capture audio transcriptions
2. **Image OCR**: Extract text from images
3. **Real-time Collaboration**: Share live conversations
4. **Cross-Platform Sync**: Continue across devices
5. **AI-Powered Search**: Semantic conversation search

## Migration Steps

1. Backup current extension data
2. Update content scripts
3. Update popup files
4. Test on each platform
5. Monitor for issues
6. Gather user feedback

## Support

For issues or questions:
- Check console logs for detailed debugging
- Review selector configuration
- Test with latest platform updates
- Report issues with platform/browser details