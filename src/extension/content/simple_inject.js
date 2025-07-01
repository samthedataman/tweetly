// Simplified Contextly Carousel Injection
console.log('🚀 Contextly Simple Carousel loaded');

// Configuration
let earnMode = true;
let walletAddress = '0x87ac32...f375b3';
let conversationHistory = [];
let currentSessionId = null;
let messageObserver = null;
let lastStreamingState = new Map();

// Platform detection
function detectPlatform() {
    const hostname = window.location.hostname;
    if (hostname.includes('claude.ai')) return 'claude';
    if (hostname.includes('openai.com') || hostname.includes('chatgpt.com')) return 'chatgpt';
    if (hostname.includes('gemini.google.com') || hostname.includes('aistudio.google.com')) return 'gemini';
    return 'unknown';
}

const platform = detectPlatform();

// Create the simplified carousel UI
function createCarousel() {
    // Remove existing carousel
    const existing = document.getElementById('contextly-carousel');
    if (existing) existing.remove();
    
    const carousel = document.createElement('div');
    carousel.id = 'contextly-carousel';
    carousel.innerHTML = `
        <div class="contextly-header">
            <div class="contextly-brand">
                <img src="${chrome.runtime.getURL('icons/icon48.png')}" width="24" height="24" alt="Contextly">
                <span class="contextly-title">Contextly</span>
                <span class="wallet-badge">🟢 ${walletAddress}</span>
                ${earnMode ? '<span class="earn-badge">💰 EARNING</span>' : ''}
            </div>
            <button class="contextly-toggle" id="toggleCarousel">−</button>
        </div>
        <div class="contextly-content" id="carouselContent">
            <div class="conversation-track" id="conversationTrack">
                ${conversationHistory.length > 0 ? conversationHistory.map(conv => `
                    <div class="conversation-card" data-session-id="${conv.session_id}">
                        <div class="conv-icon">${conv.platform === 'claude' ? '🤖' : conv.platform === 'chatgpt' ? '💬' : '✨'}</div>
                        <div class="conv-title">${conv.title || 'Untitled'}</div>
                        <div class="conv-preview">${conv.preview || ''}</div>
                        <div class="conv-stats">
                            <span>💬 ${conv.message_count || 0}</span>
                            <span>🪙 ${conv.estimated_tokens || 0}</span>
                        </div>
                    </div>
                `).join('') : `
                    <div class="empty-state">
                        <div class="empty-icon">💬</div>
                        <div class="empty-text">No conversations yet</div>
                        <div class="empty-subtext">Start chatting to see your history here</div>
                    </div>
                `}
            </div>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(carousel);
    
    // Add event listeners
    setupCarouselEvents();
}

// Setup carousel event handlers
function setupCarouselEvents() {
    // Toggle minimize/maximize
    const toggleBtn = document.getElementById('toggleCarousel');
    const content = document.getElementById('carouselContent');
    
    toggleBtn.addEventListener('click', () => {
        content.classList.toggle('minimized');
        toggleBtn.textContent = content.classList.contains('minimized') ? '+' : '−';
    });
    
    // Handle conversation card clicks
    document.querySelectorAll('.conversation-card').forEach(card => {
        card.addEventListener('click', () => {
            const sessionId = card.dataset.sessionId;
            injectConversation(sessionId);
        });
    });
}

// Inject conversation into Claude's input
async function injectConversation(sessionId) {
    const conversation = conversationHistory.find(c => c.session_id === sessionId);
    if (!conversation) return;
    
    // Show loading notification
    showToast('📥 Loading conversation...', 'info');
    
    try {
        // Find Claude's input field using the selectors you provided
        let inputField = null;
        
        // Try different selectors
        const selectors = [
            'div[contenteditable="true"].ProseMirror',
            '.ProseMirror[contenteditable="true"]',
            '[aria-label="Write your prompt to Claude"] .ProseMirror'
        ];
        
        for (const selector of selectors) {
            inputField = document.querySelector(selector);
            if (inputField) break;
        }
        
        if (!inputField) {
            console.error('Could not find input field');
            showToast('❌ Could not find input field', 'error');
            return;
        }
        
        // Build conversation text
        const conversationText = conversation.messages
            .map(msg => `${msg.role.toUpperCase()}: ${msg.text}`)
            .join('\n\n');
        
        // Clear existing content
        inputField.innerHTML = '';
        
        // Create paragraph with text
        const p = document.createElement('p');
        p.textContent = conversationText;
        inputField.appendChild(p);
        
        // Trigger input event to update Claude's state
        inputField.dispatchEvent(new Event('input', { bubbles: true }));
        inputField.focus();
        
        showToast('✅ Conversation loaded!', 'success');
        
    } catch (error) {
        console.error('Failed to inject conversation:', error);
        showToast('❌ Failed to load conversation', 'error');
    }
}

// Simple toast notification
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `contextly-toast contextly-toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after duration
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Setup streaming message observer (based on old content.js)
function setupMessageObserver() {
    console.log('👀 Setting up message observer for', platform);
    
    // Platform-specific setup for capturing streaming content
    if (platform === 'claude') {
        // Monitor for streaming status changes
        setInterval(() => {
            const streamingDivs = document.querySelectorAll('div[data-is-streaming]');
            streamingDivs.forEach(div => {
                const currentState = div.getAttribute('data-is-streaming');
                const prevState = lastStreamingState.get(div);
                
                // Check if streaming just finished
                if (prevState === 'true' && currentState === 'false') {
                    console.log('🏁 Message finished streaming!');
                    captureNewMessage(div);
                }
                
                lastStreamingState.set(div, currentState);
            });
        }, 500);
    }
    
    // Generic observer for all platforms
    const observer = new MutationObserver((mutations) => {
        let hasNewMessages = false;
        
        mutations.forEach(mutation => {
            // Check for new message elements
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check for message indicators
                        if (node.matches?.('[data-testid="user-message"]') ||
                            node.matches?.('[class*="font-claude-message"]') ||
                            node.querySelector?.('[data-testid="user-message"]') ||
                            node.querySelector?.('[class*="font-claude-message"]')) {
                            hasNewMessages = true;
                        }
                    }
                });
            }
            
            // Check for streaming attribute changes
            if (mutation.type === 'attributes' && 
                mutation.attributeName === 'data-is-streaming' &&
                mutation.target.getAttribute('data-is-streaming') === 'false') {
                hasNewMessages = true;
            }
        });
        
        if (hasNewMessages) {
            console.log('🆕 New messages detected');
            setTimeout(captureConversation, 1000);
        }
    });
    
    // Find container to observe
    const container = document.querySelector('main, [role="main"], body');
    if (container) {
        observer.observe(container, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-is-streaming', 'class']
        });
        console.log('✅ Observer attached to', container);
    }
}

// Capture new message
function captureNewMessage(element) {
    if (earnMode) {
        showToast('💰 +50 CTXT earned!', 'success', 2000);
    }
}

// Capture current conversation
function captureConversation() {
    console.log('📸 Capturing conversation...');
    
    // Extract messages based on platform
    const messages = [];
    
    if (platform === 'claude') {
        // Get user messages
        document.querySelectorAll('[data-testid="user-message"]').forEach((el, i) => {
            const text = el.querySelector('p')?.textContent || el.textContent;
            if (text?.trim()) {
                messages.push({
                    role: 'user',
                    text: text.trim(),
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        // Get assistant messages
        document.querySelectorAll('[class*="font-claude-message"]').forEach((el, i) => {
            const text = el.querySelector('p')?.textContent || el.textContent;
            if (text?.trim()) {
                messages.push({
                    role: 'assistant',
                    text: text.trim(),
                    timestamp: new Date().toISOString()
                });
            }
        });
    }
    
    if (messages.length > 0) {
        // Create conversation object
        const conversation = {
            session_id: `session_${Date.now()}`,
            platform: platform,
            title: messages[0]?.text.substring(0, 50) + '...' || 'New Chat',
            preview: messages[0]?.text.substring(0, 100) + '...' || '',
            messages: messages,
            message_count: messages.length,
            estimated_tokens: messages.length * 50,
            created_at: new Date().toISOString()
        };
        
        // Add to history (keep last 10)
        conversationHistory.unshift(conversation);
        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(0, 10);
        }
        
        // Update carousel
        updateCarouselContent();
        
        // Show notification
        showToast(`📝 Captured ${messages.length} messages`, 'info', 2000);
    }
}

// Update carousel content
function updateCarouselContent() {
    const track = document.getElementById('conversationTrack');
    if (!track) return;
    
    track.innerHTML = conversationHistory.map(conv => `
        <div class="conversation-card" data-session-id="${conv.session_id}">
            <div class="conv-icon">${conv.platform === 'claude' ? '🤖' : conv.platform === 'chatgpt' ? '💬' : '✨'}</div>
            <div class="conv-title">${conv.title}</div>
            <div class="conv-preview">${conv.preview}</div>
            <div class="conv-stats">
                <span>💬 ${conv.message_count}</span>
                <span>🪙 ${conv.estimated_tokens}</span>
            </div>
        </div>
    `).join('');
    
    // Re-attach click handlers
    document.querySelectorAll('.conversation-card').forEach(card => {
        card.addEventListener('click', () => {
            const sessionId = card.dataset.sessionId;
            injectConversation(sessionId);
        });
    });
}

// Add styles
const styles = `
    #contextly-carousel {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #1a1a1a;
        border-top: 1px solid #333;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        transition: all 0.3s ease;
    }
    
    .contextly-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        background: #0f0f0f;
        border-bottom: 1px solid #333;
    }
    
    .contextly-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .contextly-brand img {
        border-radius: 50%;
    }
    
    .contextly-title {
        font-weight: 600;
        color: #fff;
        font-size: 16px;
    }
    
    .wallet-badge {
        font-size: 12px;
        color: #10b981;
        background: rgba(16, 185, 129, 0.1);
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
    }
    
    .earn-badge {
        font-size: 12px;
        color: #fbbf24;
        background: rgba(251, 191, 36, 0.1);
        padding: 4px 8px;
        border-radius: 4px;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .contextly-toggle {
        background: #333;
        border: none;
        color: #fff;
        width: 32px;
        height: 32px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
    }
    
    .contextly-toggle:hover {
        background: #444;
    }
    
    .contextly-content {
        padding: 20px;
        height: 180px;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    
    .contextly-content.minimized {
        height: 0;
        padding: 0;
    }
    
    .conversation-track {
        display: flex;
        gap: 16px;
        overflow-x: auto;
        padding-bottom: 10px;
    }
    
    .conversation-track::-webkit-scrollbar {
        height: 6px;
    }
    
    .conversation-track::-webkit-scrollbar-track {
        background: #2a2a2a;
        border-radius: 3px;
    }
    
    .conversation-track::-webkit-scrollbar-thumb {
        background: #555;
        border-radius: 3px;
    }
    
    .conversation-track::-webkit-scrollbar-thumb:hover {
        background: #666;
    }
    
    .conversation-card {
        flex: 0 0 280px;
        background: #2a2a2a;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .conversation-card:hover {
        background: #333;
        border-color: #444;
        transform: translateY(-2px);
    }
    
    .conv-icon {
        font-size: 24px;
    }
    
    .conv-title {
        font-weight: 600;
        color: #fff;
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .conv-preview {
        color: #999;
        font-size: 12px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .conv-stats {
        display: flex;
        gap: 12px;
        margin-top: auto;
        font-size: 11px;
        color: #666;
    }
    
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 140px;
        color: #666;
        text-align: center;
        gap: 8px;
        width: 100%;
    }
    
    .empty-icon {
        font-size: 48px;
        opacity: 0.3;
    }
    
    .empty-text {
        font-weight: 600;
        font-size: 16px;
    }
    
    .empty-subtext {
        font-size: 14px;
        color: #555;
    }
    
    .contextly-toast {
        position: fixed;
        bottom: 220px;
        right: 20px;
        background: #333;
        color: #fff;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 10000;
        opacity: 0;
        transform: translateX(100px);
        transition: all 0.3s ease;
        max-width: 300px;
    }
    
    .contextly-toast.show {
        opacity: 1;
        transform: translateX(0);
    }
    
    .contextly-toast-success {
        background: #10b981;
    }
    
    .contextly-toast-error {
        background: #ef4444;
    }
    
    .contextly-toast-info {
        background: #3b82f6;
    }
`;

// Initialize
function initialize() {
    // Add styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
    
    // Load mock data for demo
    conversationHistory = [
        {
            session_id: 'demo_1',
            platform: 'claude',
            title: 'Building a React Dashboard...',
            preview: 'Help me build a modern dashboard with React and TypeScript...',
            message_count: 24,
            estimated_tokens: 3200,
            messages: []
        },
        {
            session_id: 'demo_2',
            platform: 'chatgpt',
            title: 'Python Data Analysis...',
            preview: 'Analyzing sales data with pandas and creating visualizations...',
            message_count: 18,
            estimated_tokens: 2400,
            messages: []
        }
    ];
    
    // Create carousel
    createCarousel();
    
    // Setup message observer
    setupMessageObserver();
    
    // Set up auto-capture
    if (earnMode) {
        setInterval(() => {
            captureConversation();
        }, 30000); // Capture every 30 seconds
    }
    
    console.log('✅ Contextly Simple Carousel initialized');
}

// Wait for page to load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}