// Debug injection script with dropdown functionality and conversation capture
console.log('🚀 DEBUG: Script loaded');

// Add visual indicator that script is loaded
const indicator = document.createElement('div');
indicator.textContent = '✅ Contextly Active';
indicator.style.cssText = 'position: fixed; bottom: 10px; right: 10px; background: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px; z-index: 9999; font-size: 12px;';
document.body.appendChild(indicator);
setTimeout(() => indicator.remove(), 3000); // Remove after 3 seconds

// Store logs in window for debugging
window.contextlyLogs = [];
const originalLog = console.log;
console.log = function(...args) {
    window.contextlyLogs.push(args.join(' '));
    originalLog.apply(console, args);
};

// Listen for auth token updates
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'AUTH_TOKEN_UPDATED') {
        console.log('🔑 Auth token updated! Reloading to apply changes...');
        // Store the new token and reload to ensure it's used
        chrome.storage.local.set({ authToken: message.authToken }, () => {
            location.reload();
        });
    }
});

let autoContextlyEnabled = false;
let earnMode = true; // Default to earn mode enabled - users earn CTXT tokens automatically
let conversationHistory = [];
let textEarnings = 0;
let syncAnimation = null;
let currentSessionId = null;

// Conversation capture state
let captureEnabled = false;
let currentConversation = null;
let messageObserver = null;
let lastMessageCount = 0;
let platform = detectPlatform();
let autoSaveInterval = null;
let lastSavedMessageCount = 0;
let autoSaveIntervalMs = 30000; // Auto-save every 30 seconds by default

// Platform detection
function detectPlatform() {
    const hostname = window.location.hostname;
    console.log('🌐 Detecting platform for:', hostname);

    if (hostname.includes('claude.ai')) return 'claude';
    if (hostname.includes('openai.com') || hostname.includes('chatgpt.com')) return 'chatgpt';
    if (hostname.includes('gemini.google.com') || hostname.includes('aistudio.google.com')) return 'gemini';
    return 'unknown';
}

// Conversation capture system
function initializeConversationCapture() {
    console.log('🎯 Initializing conversation capture for platform:', platform);

    if (captureEnabled) {
        console.log('📡 Capture already enabled');
        return;
    }

    captureEnabled = true;
    currentConversation = {
        session_id: currentSessionId,
        platform: platform,
        messages: [],
        title: '',
        created_at: new Date().toISOString(),
        last_updated: new Date().toISOString()
    };

    // Start monitoring for new messages
    startMessageObserver();

    // Initial capture of existing messages
    captureExistingMessages();

    // Start automatic saving to LanceDB
    startAutoSave();

    console.log('✅ Conversation capture initialized');
}

function startAutoSave() {
    // Clear any existing auto-save interval
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
    }

    console.log(`⏰ Starting auto-save to LanceDB every ${autoSaveIntervalMs / 1000} seconds`);

    // Set up the auto-save interval
    autoSaveInterval = setInterval(async () => {
        if (!currentConversation || !currentConversation.messages.length) {
            console.log('⏰ Auto-save: No conversation to save');
            return;
        }

        // Only save if there are new messages since last save
        if (currentConversation.messages.length > lastSavedMessageCount) {
            const newMessages = currentConversation.messages.length - lastSavedMessageCount;
            console.log(`⏰ Auto-save: Detected ${newMessages} new messages since last save`);
            
            // Update the last_updated timestamp
            currentConversation.last_updated = new Date().toISOString();
            
            // Show auto-save notification
            showNotification(
                '⏰ Auto-saving to LanceDB...',
                'info',
                2000,
                `${newMessages} new message${newMessages > 1 ? 's' : ''} to save`
            );

            try {
                await saveConversationToBackend();
                lastSavedMessageCount = currentConversation.messages.length;
                console.log(`⏰ Auto-save completed. Total messages saved: ${lastSavedMessageCount}`);
            } catch (error) {
                console.error('⏰ Auto-save failed:', error);
                showNotification(
                    '⚠️ Auto-save failed',
                    'error',
                    3000,
                    'Will retry on next interval'
                );
            }
        } else {
            console.log('⏰ Auto-save: No new messages to save');
        }
    }, autoSaveIntervalMs);

    // Also save when the page is about to unload
    window.addEventListener('beforeunload', async (e) => {
        if (currentConversation && currentConversation.messages.length > lastSavedMessageCount) {
            console.log('🚪 Page unloading, saving conversation...');
            // Note: This might not always complete due to browser restrictions
            await saveConversationToBackend();
        }
    });

    console.log('⏰ Auto-save started successfully');
}

function startMessageObserver() {
    if (messageObserver) {
        messageObserver.disconnect();
    }

    console.log('👀 Starting message observer for platform:', platform);

    // Find the messages container based on platform
    const messageContainer = getMessageContainer();
    if (!messageContainer) {
        console.warn('⚠️ Could not find message container for platform:', platform);
        return;
    }

    // Create mutation observer to detect new messages
    messageObserver = new MutationObserver((mutations) => {
        let hasNewMessages = false;

        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if new messages were added
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if it's a message element or contains message elements
                        if (isMessageElement(node) ||
                            node.querySelector('[data-testid="user-message"]') ||
                            node.querySelector('[class*="font-claude-message"]')) {
                            hasNewMessages = true;
                            console.log('🆕 New message node detected:', node);
                        }
                    }
                });
            }
        });

        if (hasNewMessages) {
            console.log('🆕 New messages detected, capturing...');
            setTimeout(() => captureNewMessages(), 500); // Small delay to ensure DOM is updated
        }
    });

    // Start observing
    messageObserver.observe(messageContainer, {
        childList: true,
        subtree: true
    });

    console.log('👀 Message observer started');
}

function getMessageContainer() {
    switch (platform) {
        case 'claude':
            // Claude conversation container
            return document.querySelector('[data-testid="conversation-turn-list"]') ||
                document.querySelector('div[class*="conversation"]') ||
                document.querySelector('main div[role="main"]') ||
                document.querySelector('.conversation-turn-list') ||
                document.querySelector('div:has(> div[data-is-streaming])');

        case 'chatgpt':
            // ChatGPT conversation container - look for the thread container
            return document.querySelector('#thread') ||
                document.querySelector('.flex.flex-col.text-sm.pb-25') ||
                document.querySelector('[role="main"]') ||
                document.querySelector('div[class*="conversation"]') ||
                document.querySelector('main');

        case 'gemini':
            // Gemini conversation container
            return document.querySelector('chat-window') ||
                document.querySelector('.conversation-container') ||
                document.querySelector('[role="main"]') ||
                document.querySelector('div[class*="conversation"]') ||
                document.querySelector('main');

        default:
            return document.querySelector('main') || document.body;
    }
}

function isMessageElement(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;

    switch (platform) {
        case 'claude':
            return element.matches('[data-testid*="turn"]') ||
                element.matches('div[class*="message"]') ||
                element.matches('div[data-is-streaming]') ||
                element.querySelector('[data-testid*="turn"]') !== null;

        case 'chatgpt':
            return element.matches('[data-message-id]') ||
                element.matches('div[class*="message"]') ||
                element.querySelector('[data-message-id]') !== null;

        case 'gemini':
            return element.matches('div[class*="message"]') ||
                element.matches('div[class*="response"]') ||
                element.querySelector('div[class*="message"]') !== null;

        default:
            return false;
    }
}

function captureExistingMessages() {
    console.log('📋 Capturing existing messages...');
    console.log('🔍 DOM state:', {
        bodyClasses: document.body.className,
        hasConversationElements: !!document.querySelector('[data-testid="user-message"], [data-testid="assistant-message"]'),
        platform: platform,
        url: window.location.href
    });

    const messages = extractAllMessages();
    console.log(`📝 Found ${messages.length} existing messages`);
    if (messages.length > 0) {
        console.log('📨 First message:', messages[0]);
        console.log('📨 Last message:', messages[messages.length - 1]);
    }

    if (messages.length > 0) {
        currentConversation.messages = messages;
        currentConversation.title = generateConversationTitle(messages);
        lastMessageCount = messages.length;

        // Show notification about initial capture
        showNotification(
            '📡 Conversation capture started',
            'info',
            3000,
            `Platform: ${platform} | Messages: ${messages.length} | Session: ${currentSessionId.substring(0, 15)}...`
        );

        // Show details of captured messages
        const userMessages = messages.filter(m => m.role === 'user').length;
        const assistantMessages = messages.filter(m => m.role === 'assistant').length;

        setTimeout(() => {
            showNotification(
                '📊 Message breakdown',
                'info',
                2500,
                `User: ${userMessages} | Assistant: ${assistantMessages} | Total chars: ${messages.reduce((sum, m) => sum + m.text.length, 0)}`
            );
        }, 1000);

        // Save to backend
        saveConversationToBackend();
    }
}

function captureNewMessages() {
    const messages = extractAllMessages();
    const newMessageCount = messages.length;

    if (newMessageCount > lastMessageCount) {
        const newMessages = newMessageCount - lastMessageCount;
        console.log(`📝 Captured ${newMessages} new messages`);

        // Show notification for new messages captured
        showNotification(
            `📝 New messages detected`,
            'info',
            2000,
            `Captured ${newMessages} new message${newMessages > 1 ? 's' : ''} | Total: ${newMessageCount}`
        );

        currentConversation.messages = messages;
        currentConversation.last_updated = new Date().toISOString();
        currentConversation.title = generateConversationTitle(messages);

        // Update earnings if in earn mode
        if (earnMode) {
            const newTokens = newMessages * 50; // Estimate 50 tokens per message
            textEarnings += newTokens;
            createFloatingText('earn');
            console.log(`💰 Earned ${newTokens} tokens!`);

            // Show earning notification
            showNotification(
                `💰 Tokens earned!`,
                'success',
                2500,
                `+${newTokens} CTXT tokens | Total: ${textEarnings}`
            );
        }

        lastMessageCount = newMessageCount;

        // Save to backend
        saveConversationToBackend();
    }
}

function extractAllMessages() {
    const messages = [];
    let messageElements = [];

    switch (platform) {
        case 'claude':
            // Updated selectors for Claude's new UI
            messageElements = document.querySelectorAll('[data-testid="user-message"], [class*="font-claude-message"], [data-testid*="turn"], div[data-is-streaming="false"], div[data-is-streaming="true"]');
            break;

        case 'chatgpt':
            // Updated selectors for ChatGPT's new interface
            messageElements = document.querySelectorAll('article[data-testid*="conversation-turn"], article');
            if (messageElements.length === 0) {
                // Fallback to older selectors
                messageElements = document.querySelectorAll('[data-message-id], div[class*="message"]');
            }
            break;

        case 'gemini':
            // Updated selectors for Gemini
            messageElements = document.querySelectorAll('message-content, .message-content, .conversation-turn, div[class*="message"], div[class*="response"]');
            break;

        default:
            // Generic fallback
            messageElements = document.querySelectorAll('div[class*="message"], p[class*="message"], div[role="listitem"]');
    }

    messageElements.forEach((element, index) => {
        const message = extractMessageFromElement(element, index);
        if (message && message.text.trim()) {
            messages.push(message);
        }
    });

    return messages;
}

function extractMessageFromElement(element, index) {
    let role = 'unknown';
    let text = '';
    let timestamp = new Date().toISOString();

    switch (platform) {
        case 'claude':
            // Updated Claude message extraction for new UI
            if (element.matches('[data-testid="user-message"]')) {
                role = 'user';
                // Extract text from user message - look for p tag with whitespace-pre-wrap
                const userP = element.querySelector('p.whitespace-pre-wrap, p');
                text = userP ? userP.innerText.trim() : element.innerText.trim();
            } else if (element.matches('[class*="font-claude-message"]')) {
                role = 'assistant';
                // Extract text from Claude's response - look for p tag with whitespace-normal
                const assistantP = element.querySelector('p.whitespace-normal, p');
                text = assistantP ? assistantP.innerText.trim() : element.innerText.trim();
            } else {
                // Fallback to old selectors
                role = element.querySelector('[data-testid="human-turn"]') ? 'user' :
                    element.querySelector('[data-testid="ai-turn"]') ? 'assistant' : 'unknown';
                const claudeContent = element.querySelector('.prose, [class*="content"], [class*="text"]');
                text = claudeContent ? claudeContent.innerText.trim() : element.innerText.trim();
            }
            break;

        case 'chatgpt':
            // ChatGPT message extraction for new interface
            // Check if it's an article element
            if (element.tagName === 'ARTICLE') {
                // Look for the message content within the structure you provided
                const messageContent = element.querySelector('.flex.max-w-full.flex-col.grow > div');
                
                // Check for user/assistant role indicators
                // In ChatGPT's structure, odd articles (1st, 3rd, 5th) are typically user messages
                // and even articles (2nd, 4th, 6th) are assistant messages
                const articleIndex = Array.from(element.parentElement.querySelectorAll('article')).indexOf(element);
                const isUser = element.querySelector('[data-message-author-role="user"]') || 
                              (articleIndex % 2 === 0); // 0-indexed, so even = user, odd = assistant
                
                role = isUser ? 'user' : 'assistant';
                
                // Extract text from the message content
                if (messageContent) {
                    // Look for markdown content or regular text
                    const textElement = messageContent.querySelector('[class*="markdown"], .prose, div[class*="text"]');
                    text = textElement ? textElement.innerText.trim() : messageContent.innerText.trim();
                } else {
                    // Fallback to getting all text
                    text = element.innerText.trim();
                }
            } else {
                // Fallback for older ChatGPT interface
                const chatgptRole = element.getAttribute('data-message-author-role');
                role = chatgptRole === 'user' ? 'user' :
                    chatgptRole === 'assistant' ? 'assistant' : 'unknown';
                
                const chatgptContent = element.querySelector('[class*="markdown"], [class*="content"], .prose');
                text = chatgptContent ? chatgptContent.innerText.trim() : element.innerText.trim();
            }
            break;

        case 'gemini':
            // Gemini message extraction
            role = element.classList.contains('user') || element.querySelector('[class*="user"]') ? 'user' : 'assistant';
            text = element.innerText.trim();
            break;

        default:
            // Generic extraction
            text = element.innerText.trim();
            role = index % 2 === 0 ? 'user' : 'assistant'; // Alternate assumption
    }

    return {
        role: role,
        text: text,
        timestamp: timestamp,
        platform: platform
    };
}

function generateConversationTitle(messages) {
    if (!messages || messages.length === 0) return 'New Conversation';

    // Use first user message as title, truncated
    const firstUserMessage = messages.find(m => m.role === 'user');
    if (firstUserMessage) {
        const title = firstUserMessage.text.substring(0, 50);
        return title.length < firstUserMessage.text.length ? title + '...' : title;
    }

    return 'New Conversation';
}

async function saveConversationToBackend() {
    console.log('🔵 ===========================================');
    console.log('🔵 SAVE CONVERSATION TRIGGERED');
    console.log('🔵 Time:', new Date().toISOString());
    console.log('🔵 ===========================================');
    
    if (!currentConversation || !currentConversation.messages.length) {
        console.log('📭 No conversation to save');
        console.log('Current conversation:', currentConversation);
        return;
    }

    try {
        console.log('💾 Saving conversation to backend...', {
            session_id: currentConversation.session_id,
            message_count: currentConversation.messages.length,
            platform: currentConversation.platform,
            title: currentConversation.title,
            last_message: currentConversation.messages[currentConversation.messages.length - 1]
        });

        // Start floating ETH token animations
        createFloatingETHTokens();

        // Show initial notification
        showNotification(
            '📡 Connecting to LanceDB...',
            'info',
            2000,
            `Session: ${currentConversation.session_id.substring(0, 20)}...`
        );

        const authToken = await getAuthToken();
        const walletInfo = await getWalletInfo();
        
        // Check if we have a valid auth token
        if (!authToken) {
            console.log('⚠️ No authentication token available');
            
            // Only show sign-in prompt if wallet is not connected
            if (!walletInfo.connected) {
                showNotification(
                    '🔐 Please sign in to save',
                    'warning',
                    5000,
                    'Sign in required to save conversations'
                );
                chrome.runtime.sendMessage({ action: 'open_popup_for_signin' });
            } else {
                showNotification(
                    '⚠️ Backend not connected',
                    'warning',
                    3000,
                    'Conversation captured locally'
                );
            }
            return;
        }

        // Show data being sent
        const dataSize = JSON.stringify(currentConversation).length;
        showNotification(
            '📤 Sending conversation to LanceDB',
            'info',
            3000,
            `Platform: ${currentConversation.platform} | Messages: ${currentConversation.messages.length} | Size: ${(dataSize / 1024).toFixed(2)}KB`
        );

        // Save conversation metadata with proper schema
        console.log('📤 Sending conversation metadata to backend...');
        const conversationPayload = {
            conversation_id: currentConversation.session_id, // Use conversation_id for LanceDB schema
            session_id: currentConversation.session_id,
            title: currentConversation.title,
            platform: currentConversation.platform || platform, // Ensure platform is always included
            created_at: currentConversation.created_at,
            last_updated: currentConversation.last_updated,
            message_count: currentConversation.messages.length,
            estimated_tokens: currentConversation.messages.length * 50, // Rough estimate
            user_id: walletInfo.address || 'anonymous' // Include user ID from wallet
        };
        
        console.log('📦 Conversation payload:', conversationPayload);
        console.log('🔑 Using auth token:', authToken ? `${authToken.substring(0, 20)}...` : 'None');
        
        const conversationResponse = await fetch('http://localhost:8000/v1/conversations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(conversationPayload)
        });
        
        console.log('📥 Conversation response status:', conversationResponse.status);
        console.log('📥 Conversation response headers:', conversationResponse.headers);

        if (conversationResponse.status === 401 || conversationResponse.status === 403) {
            // Authentication failed
            console.log('⚠️ Authentication failed during save');
            showNotification(
                '🔐 Please sign in to save',
                'warning',
                5000,
                'Your conversation is captured but needs authentication to save'
            );
            
            // Open popup for sign-in
            chrome.runtime.sendMessage({ action: 'open_popup_for_signin' });
            return;
        }

        if (!conversationResponse.ok) {
            throw new Error(`Failed to save conversation: ${conversationResponse.status}`);
        }

        // Show metadata saved notification
        showNotification(
            '✅ Conversation metadata saved to LanceDB',
            'success',
            2000,
            `Table: conversations | ID: ${currentConversation.session_id.substring(0, 15)}...`
        );

        // Save each message
        let messagesSaved = 0;
        for (const message of currentConversation.messages) {
            const messageData = {
                message: {  // Wrap in message object as expected by backend
                    id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
                    conversation_id: currentConversation.session_id, // Include conversation_id
                    session_id: currentConversation.session_id,
                    role: message.role,
                    text: message.text,  // Change from 'content' to 'text'
                    timestamp: Math.floor(new Date(message.timestamp).getTime() / 1000), // Convert to Unix timestamp
                    platform: message.platform || currentConversation.platform || platform // Ensure platform is included
                },
                conversation_id: currentConversation.session_id, // ConversationMessage needs this too
                session_id: currentConversation.session_id,
                wallet: walletInfo.address || 'anonymous'
            };
            
            console.log('📤 Sending message to backend:', messageData);
            
            const messageResponse = await fetch('http://localhost:8000/v1/conversations/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(messageData)
            });

            if (!messageResponse.ok) {
                // Check if it's an authentication error
                if (messageResponse.status === 401 || messageResponse.status === 403) {
                    console.warn('⚠️ Authentication failed while saving messages');
                    showNotification(
                        '🔐 Authentication expired',
                        'warning',
                        5000,
                        'Please sign in again to continue saving'
                    );
                    
                    // Only show sign-in prompt if wallet is not connected
                    if (!walletInfo.connected) {
                        chrome.runtime.sendMessage({ action: 'open_popup_for_signin' });
                    }
                    break; // Stop trying to save more messages
                } else {
                    console.warn('⚠️ Failed to save message:', messageResponse.status);
                }
            } else {
                messagesSaved++;
                // Show progress every 5 messages
                if (messagesSaved % 5 === 0 || messagesSaved === currentConversation.messages.length) {
                    showNotification(
                        '📝 Saving messages to LanceDB',
                        'info',
                        1500,
                        `Progress: ${messagesSaved}/${currentConversation.messages.length} messages | Table: messages`
                    );
                }
            }
        }

        console.log('✅ Conversation saved to backend successfully');

        // Show celebration ETH tokens on successful save
        createFloatingETHTokens();

        // Final success notification with summary
        showNotification(
            '🎉 Successfully saved to LanceDB!',
            'success',
            5000,
            `✓ ${messagesSaved} messages | ✓ ${currentConversation.estimated_tokens || messagesSaved * 50} tokens earned | ✓ Indexed for search`
        );

    } catch (error) {
        console.error('❌ Failed to save conversation:', error);
        showNotification('Failed to save conversation', 'error');
    }
}

// Listen for messages from popup to avoid conflicts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('🔔 Message received in content:', request);

    // Handle ping from background script
    if (request.action === 'ping') {
        console.log('🏓 Responding to ping from background script');
        sendResponse({ pong: true });
        return;
    }

    // Handle wallet connection requests
    if (request.action === 'connect_metamask') {
        console.log('🔗 Debug inject received wallet connection request');
        handleMetaMaskInDebugScript()
            .then(result => {
                console.log('✅ MetaMask connection successful in debug script:', result);
                sendResponse(result);
            })
            .catch(error => {
                console.error('❌ MetaMask connection failed in debug script:', error);
                sendResponse({ error: error.message });
            });
        return true; // Keep channel open for async response
    }

    // Handle message signing requests
    if (request.action === 'sign_message') {
        console.log('✍️ Debug inject received message signing request');
        handleMetaMaskSigningInDebugScript(request.message, request.address)
            .then(result => {
                console.log('✅ Message signing successful in debug script:', result);
                sendResponse(result);
            })
            .catch(error => {
                console.error('❌ Message signing failed in debug script:', error);
                sendResponse({ error: error.message });
            });
        return true; // Keep channel open for async response
    }

    if (request.action === 'toggleEarn') {
        earnMode = request.enabled;
        updateButtonAppearance();

        // Start capture when earn mode is enabled
        if (earnMode && !captureEnabled) {
            initializeConversationCapture();
        }
    }
    
    // Handle wallet connection updates from popup
    if (request.action === 'wallet_connected') {
        console.log('🔄 Wallet connection update received:', request.data);
        
        // Update local state if needed
        if (request.data.connected) {
            console.log('✅ Wallet connected:', request.data.address);
            // If we have an open dropdown, update it
            const dropdown = document.querySelector('.contextly-dropdown');
            if (dropdown) {
                updateButtonAppearance();
                // Refresh the dropdown to show updated wallet status
                const button = document.querySelector('.contextly-chat-button');
                if (button) {
                    dropdown.remove();
                    showDropdown(button);
                }
            }
        }
        
        sendResponse({ received: true });
        return true;
    }
    
    if (request.action === 'wallet_disconnected') {
        console.log('🔌 Wallet disconnected');
        
        // Update UI to reflect disconnected state
        const dropdown = document.querySelector('.contextly-dropdown');
        if (dropdown) {
            updateButtonAppearance();
            // Refresh the dropdown
            const button = document.querySelector('.contextly-chat-button');
            if (button) {
                dropdown.remove();
                showDropdown(button);
            }
        }
        
        sendResponse({ received: true });
        return true;
    }
});

// MetaMask connection handler for debug script
async function handleMetaMaskInDebugScript() {
    console.log('🦊 Attempting MetaMask connection from debug script...');

    return new Promise((resolve, reject) => {
        // Create a unique request ID
        const requestId = 'metamask_' + Date.now();

        // Listen for response from injected script
        const messageHandler = (event) => {
            if (event.data && event.data.type === 'METAMASK_RESPONSE' && event.data.requestId === requestId) {
                window.removeEventListener('message', messageHandler);

                if (event.data.error) {
                    console.error('❌ MetaMask error from page context:', event.data.error);
                    reject(new Error(event.data.error));
                } else {
                    console.log('✅ MetaMask success from page context:', event.data.result);
                    resolve(event.data.result);
                }
            }
        };

        window.addEventListener('message', messageHandler);

        // Inject script into page context to access window.ethereum
        const script = document.createElement('script');
        script.textContent = `
            (function() {
                const requestId = '${requestId}';
                console.log('🔍 Page context script checking MetaMask...');
                
                async function connectMetaMask() {
                    try {
                        // Check if MetaMask is available
                        if (typeof window.ethereum === 'undefined') {
                            throw new Error('MetaMask is not installed or not accessible. Please install MetaMask browser extension and refresh the page.');
                        }
                        
                        console.log('✅ MetaMask detected in page context');
                        
                        // Check if already connected
                        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                        
                        let address;
                        if (accounts.length > 0) {
                            console.log('✅ MetaMask already connected:', accounts[0]);
                            address = accounts[0];
                        } else {
                            console.log('🔐 Requesting MetaMask access...');
                            const newAccounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                            
                            if (newAccounts.length === 0) {
                                throw new Error('No accounts found in MetaMask');
                            }
                            
                            address = newAccounts[0];
                            console.log('✅ MetaMask connected:', address);
                        }
                        
                        // Get chain ID
                        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
                        const chainIdNumber = parseInt(chainId, 16);
                        
                        console.log('🔗 Chain ID:', chainIdNumber);
                        
                        const result = {
                            address: address,
                            chainId: chainIdNumber,
                            provider: 'metamask'
                        };
                        
                        // Send success response
                        window.postMessage({
                            type: 'METAMASK_RESPONSE',
                            requestId: requestId,
                            result: result
                        }, '*');
                        
                    } catch (error) {
                        console.error('❌ MetaMask error in page context:', error);
                        
                        let errorMessage = error.message;
                        if (error.code === 4001) {
                            errorMessage = 'User rejected the connection request';
                        }
                        
                        // Send error response
                        window.postMessage({
                            type: 'METAMASK_RESPONSE',
                            requestId: requestId,
                            error: errorMessage
                        }, '*');
                    }
                }
                
                // Execute immediately
                connectMetaMask();
            })();
        `;

        // Inject and clean up
        (document.head || document.documentElement).appendChild(script);
        script.remove();

        // Timeout after 10 seconds
        setTimeout(() => {
            window.removeEventListener('message', messageHandler);
            reject(new Error('MetaMask connection timeout'));
        }, 10000);
    });
}

// Load conversation history and user state
async function loadUserData() {
    try {
        // Get current session ID from URL or generate one
        currentSessionId = generateSessionId();

        // Load conversation history from backend
        const authToken = await getAuthToken();
        const walletInfo = await getWalletInfo();
        
        // Check if we have a valid auth token (not the placeholder or temp token)
        if (!authToken || authToken === 'placeholder_token' || authToken.startsWith('temp_token_')) {
            console.log('⚠️ Invalid or missing auth token');
            
            // Only show sign-in prompt if wallet is not connected
            if (!walletInfo.connected) {
                showNotification(
                    '🔐 Please sign in',
                    'warning',
                    5000,
                    'Click here to sign in to Contextly'
                );
                
                // Open popup for sign-in after a short delay
                setTimeout(() => {
                    chrome.runtime.sendMessage({ action: 'open_popup_for_signin' });
                }, 1000);
            } else {
                console.log('ℹ️ Wallet connected but no auth token, skipping backend call');
            }
            
            conversationHistory = [];
            return;
        }
        
        const response = await fetch('http://localhost:8000/v1/conversations/history', {
            headers: {
                'Authorization': 'Bearer ' + authToken
            }
        });

        if (response.status === 401 || response.status === 403) {
            // Authentication failed - check if wallet is connected before prompting
            console.log('⚠️ Backend authentication failed');
            
            if (!walletInfo.connected) {
                showNotification(
                    '🔐 Please sign in',
                    'warning',
                    5000,
                    'Click here to sign in to Contextly'
                );
                
                // Open popup for sign-in after a short delay
                setTimeout(() => {
                    chrome.runtime.sendMessage({ action: 'open_popup_for_signin' });
                }, 1000);
            } else {
                console.log('ℹ️ Wallet connected but backend auth failed, using local data');
            }
            
            conversationHistory = [];
            return;
        }

        if (response.ok) {
            const data = await response.json();
            conversationHistory = data.conversations || [];
        }
    } catch (error) {
        console.log('Failed to load user data:', error);
        // Initialize empty conversation history on error
        conversationHistory = [];
        
        // If it's a network error, show notification
        if (error.message && error.message.includes('fetch')) {
            showNotification(
                '⚠️ Connection error',
                'error',
                3000,
                'Please check your internet connection'
            );
        }
    }
}

function generateSessionId() {
    // Extract conversation ID from the URL based on platform
    const url = window.location.href;
    let conversationId = null;
    
    // Extract conversation ID from URL patterns
    if (platform === 'claude') {
        // Claude: https://claude.ai/chat/df87f8f0-511f-44b4-9bc5-27410b1663eb
        const match = url.match(/\/chat\/([a-f0-9-]+)/);
        if (match) conversationId = match[1];
    } else if (platform === 'chatgpt') {
        // ChatGPT: https://chat.openai.com/c/abc123...
        const match = url.match(/\/c\/([a-zA-Z0-9-]+)/);
        if (match) conversationId = match[1];
    } else if (platform === 'gemini') {
        // Gemini: URL pattern may vary
        const match = url.match(/\/([a-zA-Z0-9-]+)$/);
        if (match) conversationId = match[1];
    }
    
    // If we found a conversation ID in the URL, use it
    if (conversationId) {
        console.log('📋 Using conversation ID from URL:', conversationId);
        return conversationId;
    }
    
    // Fallback: generate a unique ID
    const timestamp = Date.now();
    const fallbackId = `${platform}_${timestamp}_${Math.random().toString(36).substring(2, 9)}`;
    console.log('🆕 Generated new conversation ID:', fallbackId);
    return fallbackId;
}

async function getAuthToken() {
    // Get auth token from storage
    return new Promise((resolve) => {
        chrome.storage.local.get(['authToken'], (result) => {
            const token = result.authToken || null;
            if (token) {
                console.log('🔑 ===========================================');
                console.log('🔑 USING AUTH TOKEN:', token);
                console.log('📋 COPY TOKEN FOR TESTING:', token);
                console.log('🔑 ===========================================');
            }
            resolve(token);
        });
    });
}

// Get wallet information from storage
async function getWalletInfo() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['wallet', 'walletAddress', 'ctxtBalance', 'ethBalance', 'walletConnected'], (result) => {
            // Check both old and new storage formats
            const isConnected = result.wallet?.connected || result.walletConnected || false;
            const address = result.wallet?.address || result.walletAddress || null;
            
            resolve({
                connected: isConnected,
                address: address,
                ctxtBalance: result.ctxtBalance || '0',
                ethBalance: result.ethBalance || '0.00'
            });
        });
    });
}

// Connect wallet function
function connectWallet() {
    // Send message to background script to open popup
    chrome.runtime.sendMessage({ action: 'open_popup_for_signin' });
}

function injectContextlyButton() {
    console.log('🔍 DEBUG: Looking for interface on platform:', platform);

    // Remove existing buttons and dropdowns
    document.querySelectorAll('.contextly-debug-btn, .contextly-dropdown').forEach(el => el.remove());

    let container = null;

    if (platform === 'chatgpt') {
        // ChatGPT specific selectors
        // Try the footer actions container first
        container = document.querySelector('div[data-testid="composer-footer-actions"]');
        
        if (!container) {
            // Try alternative selectors for ChatGPT
            container = document.querySelector('.flex.items-center.max-xs\\:gap-1.gap-2.overflow-x-auto.\\[scrollbar-width\\:none\\]');
        }
        
        if (!container) {
            // Try the specific selector provided by user
            const threadBottom = document.querySelector('#thread-bottom');
            if (threadBottom) {
                container = threadBottom.querySelector('.bg-primary-surface-primary.absolute.start-2\\.5.end-0.bottom-2\\.5.z-2.flex.items-center > div > div:nth-child(1)');
            }
        }
        
        if (!container) {
            // Look for the attach button and find its container
            const attachBtn = document.querySelector('button[aria-label="Upload files and more"], div[data-testid="composer-action-file-upload"] button');
            if (attachBtn) {
                container = attachBtn.closest('div[data-testid="composer-footer-actions"]') || 
                           attachBtn.closest('.flex.items-center.gap-2');
            }
        }
        
        if (container) {
            console.log('✅ Found ChatGPT container:', container);
        }
    } else if (platform === 'gemini') {
        // Gemini specific - find the container that holds Deep Research and Canvas
        // Look for the parent container of the buttons, not the toolbox-drawer itself
        const leadingActionsWrapper = document.querySelector('.leading-actions-wrapper');
        if (leadingActionsWrapper) {
            container = leadingActionsWrapper;
            console.log('✅ Found Gemini leading actions wrapper:', container);
        } else {
            // Try to find the input area container
            const inputArea = document.querySelector('input-area-v2');
            if (inputArea) {
                const wrapper = inputArea.querySelector('div > div > div');
                if (wrapper) {
                    container = wrapper;
                }
            }
        }
        
        if (container) {
            console.log('✅ Found Gemini container:', container);
        }
    } else {
        // Claude and other platforms
        // Method 1: Find by button with plus icon
        const plusButton = document.querySelector('button[aria-label*="attachments"], button[data-testid*="plus"], button:has(svg path[d*="M224,128a8"])');
        if (plusButton) {
            console.log('✅ Found plus button:', plusButton);
            container = plusButton.closest('div[class*="flex"][class*="items-center"]');
            if (container) {
                console.log('✅ Found container via plus button:', container);
            }
        }

        // Method 2: Find any div with multiple buttons
        if (!container) {
            const allContainers = document.querySelectorAll('div[class*="flex"][class*="items-center"]');
            for (let div of allContainers) {
                const buttons = div.querySelectorAll('button');
                if (buttons.length >= 2 && buttons.length <= 5) {
                    console.log('✅ Found container with buttons:', div, 'Button count:', buttons.length);
                    container = div;
                    break;
                }
            }
        }
    }

    if (!container) {
        console.log('❌ No container found');
        return;
    }

    // Create button with dropdown functionality
    const contextlyBtn = document.createElement('div');
    contextlyBtn.className = 'contextly-debug-btn';
    
    if (platform === 'chatgpt') {
        // ChatGPT style button
        contextlyBtn.innerHTML = `
            <div style="view-transition-name:var(--vt-composer-contextly-action)">
                <div>
                    <span class="inline-block" data-state="closed">
                        <div class="radix-state-open:bg-black/10 inline-flex h-9 rounded-full border text-[13px] font-medium text-token-text-secondary border-token-border-default can-hover:hover:bg-token-main-surface-secondary focus-visible:outline-black dark:focus-visible:outline-white">
                            <button class="contextly-main-btn flex h-full min-w-8 items-center justify-center p-2" aria-pressed="false" aria-label="Contextly Save">
                                <img src="${chrome.runtime.getURL('icons/icon48.png')}" width="20" height="20" style="border-radius: 50%;" alt="Contextly">
                                <span style="width:fit-content;opacity:1;transform:none">
                                    <div class="[display:var(--force-hide-label)] ps-1 pe-1 font-semibold whitespace-nowrap">Contextly</div>
                                </span>
                            </button>
                        </div>
                    </span>
                </div>
            </div>
        `;
    } else if (platform === 'gemini') {
        // Gemini style button - matches Deep Research and Canvas
        contextlyBtn.innerHTML = `
            <button class="contextly-main-btn contextly-debug-btn" aria-label="Contextly" style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                border-radius: 24px;
                border: 1px solid #e0e0e0;
                background: white;
                cursor: pointer;
                transition: all 0.2s;
                font-family: 'Google Sans Text', 'Roboto', sans-serif;
                font-size: 14px;
                font-weight: 500;
                color: #5f6368;
                line-height: 20px;
                white-space: nowrap;
                box-shadow: none;
                height: 40px;
                margin-left: 16px;
            ">
                <img src="${chrome.runtime.getURL('icons/icon48.png')}" width="20" height="20" style="border-radius: 50%;" alt="">
                <span>Contextly</span>
            </button>
        `;
    } else {
        // Claude and other platforms style
        contextlyBtn.innerHTML = `
            <div class="relative shrink-0">
                <div>
                    <div class="flex items-center">
                        <div class="flex shrink-0" data-state="closed" style="opacity: 1; transform: none;">
                            <button class="contextly-main-btn inline-flex items-center justify-center relative shrink-0 can-focus select-none disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:drop-shadow-none border-0.5 transition-all h-8 min-w-8 rounded-lg flex items-center px-2 gap-1.5 group !pointer-events-auto !outline-offset-1 text-text-300 border-border-300 active:scale-[0.98] hover:text-text-200/90 hover:bg-bg-100" type="button" aria-label="Contextly" title="Save conversation" style="margin-right: 12px;">
                                <img src="${chrome.runtime.getURL('icons/icon48.png')}" width="20" height="20" style="border-radius: 50%;" alt="Contextly">
                                <span style="font-size: 13px; font-weight: 500;">Contextly</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Add click handler for dropdown toggle
    const mainBtn = contextlyBtn.querySelector('.contextly-main-btn');
    mainBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        console.log('🎯 Contextly button clicked!');

        // Check if dropdown is already open
        const existingDropdown = document.querySelector('.contextly-dropdown');
        
        if (existingDropdown) {
            // Close the dropdown if it exists
            console.log('🔽 Closing dropdown');
            existingDropdown.remove();
        } else {
            // Open the dropdown if it doesn't exist
            console.log('🔼 Opening dropdown');
            showDropdown(mainBtn);
        }
    });

    // Insert based on platform
    if (platform === 'chatgpt') {
        // For ChatGPT, check if there's a search button or other specific elements
        const searchBtn = container.querySelector('div[data-testid="system-hint-search"]');
        if (searchBtn) {
            // Insert after search button
            searchBtn.insertAdjacentElement('afterend', contextlyBtn);
            console.log('✅ Button inserted after search button');
        } else {
            // Otherwise append to container
            container.appendChild(contextlyBtn);
            console.log('✅ Button appended to ChatGPT container');
        }
    } else if (platform === 'gemini') {
        // For Gemini, insert after the toolbox-drawer to avoid disrupting the layout
        const toolboxDrawer = container.querySelector('toolbox-drawer');
        
        if (toolboxDrawer) {
            // Insert our button after the entire toolbox-drawer
            toolboxDrawer.insertAdjacentElement('afterend', contextlyBtn);
            console.log('✅ Button inserted after toolbox-drawer');
        } else {
            // Fallback - append to container
            container.appendChild(contextlyBtn);
            console.log('✅ Button appended to Gemini container');
        }
    } else {
        // For Claude and others, insert before last child
        if (container.lastElementChild) {
            container.insertBefore(contextlyBtn, container.lastElementChild);
            console.log('✅ Button inserted before last child');
        } else {
            container.appendChild(contextlyBtn);
            console.log('✅ Button appended');
        }
    }

    // Update initial appearance
    updateButtonAppearance();
}

async function showDropdown(buttonElement) {
    const dropdown = document.createElement('div');
    dropdown.className = 'contextly-dropdown';

    // Get button position for positioning dropdown above it
    const rect = buttonElement.getBoundingClientRect();

    // Load fresh conversation history
    await loadUserData();

    // Get wallet info from storage
    const walletInfo = await getWalletInfo();
    
    dropdown.innerHTML = `
        <div class="contextly-dropdown-content">
            <!-- Header with Wallet Info -->
            <div class="contextly-header" style="background: rgba(20, 20, 20, 0.95); border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                <!-- Wallet Status Bar -->
                <div style="padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${walletInfo.connected ? `
                            <span style="color: #10b981; font-size: 12px;">🟢 Connected</span>
                            <span style="font-family: monospace; font-size: 11px; color: #888;">${walletInfo.address ? walletInfo.address.slice(0, 6) + '...' + walletInfo.address.slice(-4) : '0x...'}</span>
                        ` : `
                            <span style="color: #ef4444; font-size: 12px;">🔴 Not Connected</span>
                            <button onclick="connectWallet()" style="padding: 2px 8px; font-size: 11px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">Connect</button>
                        `}
                    </div>
                    <div style="display: flex; gap: 12px; font-size: 11px;">
                        <span style="color: #888;">CTXT: <span style="color: #10b981; font-weight: 600;">${walletInfo.ctxtBalance || '0'}</span></span>
                        <span style="color: #888;">ETH: <span style="color: #60a5fa;">${walletInfo.ethBalance || '0.00'}</span></span>
                    </div>
                </div>
                
                <!-- Main Header -->
                <div style="padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <img src="${chrome.runtime.getURL('icons/icon48.png')}" width="24" height="24" alt="Contextly" style="border-radius: 50%;">
                        <span style="font-weight: 600; color: #fff;">Conversations</span>
                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                            <input type="checkbox" id="earnModeToggle" ${earnMode ? 'checked' : ''} style="cursor: pointer;">
                            <span style="font-size: 12px; color: ${earnMode ? '#10b981' : '#888'};">
                                ${earnMode ? '● Earn Mode' : '○ Earn Mode'}
                            </span>
                        </label>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="quick-action-btn" data-action="instant-save" title="Save Current" style="padding: 4px 8px; font-size: 12px;">
                            💾 Save
                        </button>
                        <button class="quick-action-btn" data-action="auto-save" title="Auto Save" style="padding: 4px 8px; font-size: 12px;">
                            🔄 ${autoContextlyEnabled ? 'Auto On' : 'Auto Off'}
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Conversations Content -->
            <div class="contextly-conversations-container" style="padding: 12px;">
                <style>
                    .contextly-conversations-list::-webkit-scrollbar {
                        height: 6px;
                    }
                    .contextly-conversations-list::-webkit-scrollbar-track {
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 3px;
                    }
                    .contextly-conversations-list::-webkit-scrollbar-thumb {
                        background: rgba(255, 255, 255, 0.2);
                        border-radius: 3px;
                    }
                    .contextly-conversations-list::-webkit-scrollbar-thumb:hover {
                        background: rgba(255, 255, 255, 0.3);
                    }
                </style>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div style="font-size: 12px; color: #888;">Click any conversation to load • Scroll for more →</div>
                </div>
                    ${(() => {
                        // Combine current conversation with history
                        const allConversations = [];
                        
                        // Add current conversation if it exists
                        if (currentConversation && currentConversation.messages && currentConversation.messages.length > 0) {
                            allConversations.push({
                                session_id: currentSessionId,
                                title: currentConversation.title || 'Current Conversation',
                                preview: currentConversation.messages[0]?.text?.substring(0, 100) + '...' || '',
                                message_count: currentConversation.messages.length,
                                estimated_tokens: currentConversation.messages.length * 50,
                                platform: platform,
                                last_updated: new Date().toISOString(),
                                is_current: true
                            });
                        }
                        
                        // Add historical conversations
                        allConversations.push(...conversationHistory);
                        
                        return allConversations.length > 0 ? `
                        <div class="contextly-conversations-list" style="
                            display: flex;
                            gap: 12px;
                            overflow-x: auto;
                            overflow-y: hidden;
                            padding-bottom: 12px;
                            white-space: nowrap;
                            -webkit-overflow-scrolling: touch;
                        ">
                            ${allConversations.map(conv => `
                                <div class="conversation-card" data-session-id="${conv.session_id}" style="
                                    flex: 0 0 220px;
                                    display: flex;
                                    flex-direction: column;
                                    background: rgba(255, 255, 255, 0.05);
                                    border: 1px solid rgba(255, 255, 255, 0.1);
                                    border-radius: 12px;
                                    padding: 16px;
                                    cursor: pointer;
                                    transition: all 0.2s ease;
                                    ${conv.is_current ? 'border-color: #10b981; box-shadow: 0 0 0 1px #10b981;' : ''}
                                ">
                                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                                        <div style="
                                            width: 32px;
                                            height: 32px;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            border-radius: 8px;
                                            overflow: hidden;
                                            background: rgba(255, 255, 255, 0.05);
                                        ">
                                            ${conv.platform === 'claude' ? 
                                                `<img src="${chrome.runtime.getURL('icons/claude.png')}" width="24" height="24" alt="Claude" style="object-fit: contain;">` : 
                                              conv.platform === 'chatgpt' ? 
                                                `<img src="${chrome.runtime.getURL('icons/openai.png')}" width="24" height="24" alt="ChatGPT" style="object-fit: contain;">` : 
                                              conv.platform === 'gemini' ? 
                                                `<img src="${chrome.runtime.getURL('icons/gemini.png')}" width="24" height="24" alt="Gemini" style="object-fit: contain;">` : 
                                                '<span style="font-size: 18px;">❓</span>'
                                            }
                                        </div>
                                        ${conv.is_current ? '<span style="color: #10b981; font-size: 11px; font-weight: 600;">● LIVE</span>' : `<span style="font-size: 11px; color: #666;">${formatTimeAgo(conv.last_updated)}</span>`}
                                    </div>
                                    
                                    <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                        ${conv.title || 'Untitled Chat'}
                                    </h4>
                                    
                                    <p style="margin: 0 0 12px 0; font-size: 12px; color: #888; line-height: 1.4; height: 32px; overflow: hidden; white-space: normal;">
                                        ${conv.preview || 'No preview available'}
                                    </p>
                                    
                                    <div style="margin-top: auto; display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #888;">
                                        <span>💬 ${conv.message_count || 0}</span>
                                        <span>🪙 ${conv.estimated_tokens || 0}</span>
                                    </div>
                                    
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div style="text-align: center; padding: 40px 20px; color: #888;">
                            <div style="font-size: 48px; margin-bottom: 16px;">💬</div>
                            <p style="margin: 0 0 8px 0;">No conversations yet</p>
                            <p style="margin: 0; font-size: 12px; opacity: 0.8;">Start chatting to see your history here</p>
                        </div>
                    `;
                    })()}
            </div>
        </div>
    `;

    // Position dropdown intelligently to stay within viewport
    dropdown.style.position = 'fixed';
    dropdown.style.zIndex = '10000';

    // Temporarily add to DOM to get dimensions
    dropdown.style.visibility = 'hidden';
    document.body.appendChild(dropdown);

    const dropdownRect = dropdown.getBoundingClientRect();
    const dropdownWidth = dropdownRect.width;
    const dropdownHeight = dropdownRect.height;

    // Calculate position to keep within viewport
    let left = rect.left;
    let top = rect.top - dropdownHeight - 8;

    // Check if dropdown would go off right edge
    if (left + dropdownWidth > window.innerWidth) {
        left = window.innerWidth - dropdownWidth - 20;
    }

    // Check if dropdown would go off left edge
    if (left < 20) {
        left = 20;
    }

    // Check if dropdown would go off top
    if (top < 20) {
        // Position below button instead
        top = rect.bottom + 8;

        // If still goes off bottom, position at bottom of screen
        if (top + dropdownHeight > window.innerHeight - 20) {
            top = window.innerHeight - dropdownHeight - 20;
        }
    }

    // Apply calculated position
    dropdown.style.left = `${left}px`;
    dropdown.style.top = `${top}px`;
    dropdown.style.visibility = 'visible';

    // Add hover effects and click handlers to conversation cards
    dropdown.querySelectorAll('.conversation-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.3)';
            card.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            // Show save button on hover
            const saveBtn = card.querySelector('.save-btn');
            if (saveBtn) saveBtn.style.display = 'block';
        });
        card.addEventListener('mouseleave', () => {
            if (!card.style.borderColor.includes('16, 185, 129')) {
                card.style.transform = 'translateY(0)';
                card.style.boxShadow = 'none';
                card.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            }
            // Hide save button on leave
            const saveBtn = card.querySelector('.save-btn');
            if (saveBtn) saveBtn.style.display = 'none';
        });
        
        // Click to inject conversation
        card.addEventListener('click', async (e) => {
            if (e.target.closest('.save-btn')) return; // Don't inject if clicking save button
            
            const sessionId = card.dataset.sessionId;
            console.log('💉 Injecting conversation:', sessionId);
            
            // Visual feedback
            card.style.background = 'rgba(16, 185, 129, 0.2)';
            
            // Close dropdown and inject
            await injectConversationToChat(sessionId);
            dropdown.remove();
        });
    });

    // Add event listeners
    dropdown.addEventListener('click', (e) => {
        e.stopPropagation();

        // Handle earn mode toggle
        if (e.target.id === 'earnModeToggle') {
            earnMode = e.target.checked;
            updateEarnMode(earnMode);
            return;
        }

        // Handle tab switching
        const tab = e.target.closest('.contextly-tab');
        if (tab) {
            switchTab(tab.dataset.tab);
            return;
        }

        // Handle quick action buttons
        const quickAction = e.target.closest('.quick-action-btn');
        if (quickAction) {
            handleQuickAction(quickAction.dataset.action);
            return;
        }

        // Handle conversation squares
        const square = e.target.closest('.conversation-square');
        if (square) {
            const actionBtn = e.target.closest('.square-action-btn');
            if (actionBtn) {
                handleSquareAction(actionBtn.dataset.action, square.dataset.sessionId);
            }
            return;
        }

        // Handle conversation cards (legacy)
        const card = e.target.closest('.contextly-conversation-card');
        if (card) {
            const actionBtn = e.target.closest('.quick-btn');
            if (actionBtn) {
                handleConversationAction(actionBtn.dataset.action, card.dataset.sessionId);
            } else if (e.target.closest('.conversation-main')) {
                // Click on main area loads conversation
                handleConversationAction('insert', card.dataset.sessionId);
            }
            return;
        }

        // Handle tool cards
        const toolCard = e.target.closest('.tool-card');
        if (toolCard) {
            handleToolAction(toolCard.dataset.action);
            return;
        }

        // Handle format buttons
        const formatBtn = e.target.closest('.format-btn');
        if (formatBtn) {
            handleDropdownAction(formatBtn.dataset.action);
            return;
        }

        // Handle filter chips
        const filterChip = e.target.closest('.filter-chip');
        if (filterChip) {
            handleFilter(filterChip.dataset.filter);
            return;
        }
    });

    // Search functionality
    const searchInput = dropdown.querySelector('#searchConversations');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterConversations(e.target.value);
        });
    }

    // Close dropdown when clicking outside
    const closeDropdown = (e) => {
        if (!dropdown.contains(e.target) && !buttonElement.contains(e.target)) {
            dropdown.remove();
            document.removeEventListener('click', closeDropdown);
        }
    };

    setTimeout(() => {
        document.addEventListener('click', closeDropdown);
    }, 0);
}

async function handleDropdownAction(action, element) {
    console.log('🎯 Dropdown action:', action);

    try {
        switch (action) {
            case 'save-txt':
                await saveConversation('txt');
                break;
            case 'save-pdf':
                await saveConversation('pdf');
                break;
            case 'save-markdown':
                await saveConversation('markdown');
                break;
            case 'save-clipboard':
                await saveToClipboard();
                break;
            case 'share-email':
                await shareViaEmail();
                break;
            case 'share-sms':
                await shareViaSMS();
                break;
            case 'toggle-auto':
                autoContextlyEnabled = !autoContextlyEnabled;
                console.log('🔄 Auto Contextly:', autoContextlyEnabled);
                if (autoContextlyEnabled) {
                    startSyncAnimation();
                    textEarnings += Math.floor(Math.random() * 50) + 10; // Simulate earning
                }
                updateButtonAppearance();
                updateToggleStates();
                break;
            case 'toggle-earn':
                console.log('💰 Earn toggle clicked');
                break;
            case 'insert-chat':
                await insertConversation(element.dataset.sessionId);
                break;
            case 'view-all-history':
                await showAllHistory();
                break;
        }
    } catch (error) {
        console.error('Action failed:', error);
        showNotification('Action failed. Please try again.', 'error');
    }

    // Close dropdown
    document.querySelectorAll('.contextly-dropdown').forEach(el => el.remove());
}

async function saveConversation(format) {
    try {
        showNotification(`Saving conversation as ${format.toUpperCase()}...`, 'info');

        const response = await fetch(`http://localhost:8000/v1/conversations/${currentSessionId}/export/${format}`, {
            headers: {
                'Authorization': 'Bearer ' + await getAuthToken()
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `conversation_${currentSessionId}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showNotification(`Conversation saved as ${format.toUpperCase()}!`, 'success');
        } else {
            throw new Error('Save failed');
        }
    } catch (error) {
        showNotification('Failed to save conversation', 'error');
    }
}

async function saveToClipboard() {
    try {
        showNotification('Copying to clipboard...', 'info');

        const response = await fetch(`http://localhost:8000/v1/conversations/${currentSessionId}/export/clipboard`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + await getAuthToken(),
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            await navigator.clipboard.writeText(data.content);
            showNotification('Conversation copied to clipboard!', 'success');
        } else {
            throw new Error('Copy failed');
        }
    } catch (error) {
        showNotification('Failed to copy to clipboard', 'error');
    }
}

async function shareViaEmail() {
    const email = prompt('Enter email address:');
    if (!email) return;

    try {
        showNotification('Sending email...', 'info');

        const response = await fetch(`http://localhost:8000/v1/conversations/${currentSessionId}/share/email`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + await getAuthToken(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                recipient: email,
                format: 'txt'
            })
        });

        if (response.ok) {
            showNotification(`Email sent to ${email}!`, 'success');
        } else {
            throw new Error('Email failed');
        }
    } catch (error) {
        showNotification('Failed to send email', 'error');
    }
}

async function shareViaSMS() {
    const phone = prompt('Enter phone number:');
    if (!phone) return;

    try {
        showNotification('Sending SMS...', 'info');

        const response = await fetch(`http://localhost:8000/v1/conversations/${currentSessionId}/share/sms`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + await getAuthToken(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                recipient: phone
            })
        });

        if (response.ok) {
            showNotification(`SMS sent to ${phone}!`, 'success');
        } else {
            throw new Error('SMS failed');
        }
    } catch (error) {
        showNotification('Failed to send SMS', 'error');
    }
}

async function insertConversation(sessionId) {
    try {
        showNotification('Loading conversation...', 'info');

        const response = await fetch(`http://localhost:8000/v1/conversations/${sessionId}/full`, {
            headers: {
                'Authorization': 'Bearer ' + await getAuthToken()
            }
        });

        if (response.ok) {
            const conversation = await response.json();

            // Find Claude's text input
            const textArea = document.querySelector('textarea, [contenteditable="true"]');
            if (textArea) {
                const conversationText = conversation.messages.map(msg =>
                    `${msg.role.toUpperCase()}: ${msg.text}`
                ).join('\n\n');

                if (textArea.tagName === 'TEXTAREA') {
                    textArea.value = conversationText;
                    textArea.dispatchEvent(new Event('input', { bubbles: true }));
                } else {
                    textArea.innerText = conversationText;
                    textArea.dispatchEvent(new Event('input', { bubbles: true }));
                }

                showNotification('Conversation inserted!', 'success');

                // Close dropdown after insertion
                document.querySelectorAll('.contextly-dropdown').forEach(el => el.remove());
            } else {
                showNotification('Could not find text input', 'error');
            }
        } else {
            throw new Error('Load failed');
        }
    } catch (error) {
        showNotification('Failed to load conversation', 'error');
    }
}

// Handle square actions (new interface)
async function handleSquareAction(action, sessionId) {
    console.log('🎯 Square action:', action, 'Session:', sessionId);

    switch (action) {
        case 'save-current':
            await saveCurrentConversationWithNotification();
            break;
        case 'inject-conversation':
            await injectConversationToChat(sessionId);
            break;
    }
}

// Handle conversation-specific actions
async function handleConversationAction(action, sessionId) {
    switch (action) {
        case 'preview':
            await showConversationPreview(sessionId);
            break;
        case 'insert':
            await insertConversation(sessionId);
            break;
        case 'download':
            await downloadConversation(sessionId);
            break;
        case 'insert-from-preview':
            await insertConversation(sessionId);
            closePreviewModal();
            break;
        case 'close-preview':
            closePreviewModal();
            break;
    }
}

// Save current conversation with user feedback
async function saveCurrentConversationWithNotification() {
    try {
        // Initialize capture if not already started
        if (!captureEnabled) {
            initializeConversationCapture();
            // Give it a moment to capture existing messages
            await new Promise(resolve => setTimeout(resolve, 1000));
        } else {
            // Force immediate save of current state
            await saveConversationToBackend();
        }

        showNotification('💾 Current conversation saved!', 'success');

        // Add floating animation
        createFloatingText('save');

    } catch (error) {
        console.error('❌ Failed to save current conversation:', error);
        showNotification('Failed to save conversation', 'error');
    }
}

// Alias for backward compatibility
async function injectConversation(sessionId) {
    return injectConversationToChat(sessionId);
}

// Inject conversation content into chat input
async function injectConversationToChat(sessionId) {
    try {
        console.log('🚀 Injecting conversation:', sessionId);

        let conversation;
        
        // Check if it's the current conversation
        if (currentConversation && currentConversation.session_id === sessionId) {
            console.log('📋 Using current conversation from memory');
            conversation = currentConversation;
        } else {
            // Try to find in conversation history first
            const historyConv = conversationHistory.find(c => c.session_id === sessionId);
            if (historyConv && historyConv.messages) {
                console.log('📋 Using conversation from history');
                conversation = historyConv;
            } else {
                // Fallback to backend fetch
                console.log('📋 Fetching conversation from backend');
                const authToken = await getAuthToken();
                const response = await fetch(`http://localhost:8000/v1/conversations/${sessionId}`, {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                if (!response.ok) {
                    throw new Error(`Failed to load conversation: ${response.status}`);
                }

                conversation = await response.json();
            }
        }
        
        console.log('📋 Loaded conversation:', conversation);

        // Find the chat input based on platform
        const chatInput = findChatInput();
        if (!chatInput) {
            showNotification('Could not find chat input', 'error');
            return;
        }

        // Format conversation for injection
        const formattedText = formatConversationForInjection(conversation.messages);

        // Inject into chat input
        await injectTextIntoInput(chatInput, formattedText);

        showNotification('✨ Conversation injected into chat!', 'success');

        // Add floating animation
        createFloatingText('inject');

        // Close dropdown after injection
        document.querySelectorAll('.contextly-dropdown').forEach(el => el.remove());

    } catch (error) {
        console.error('❌ Failed to inject conversation:', error);
        showNotification('Failed to inject conversation', 'error');
    }
}

// Find chat input based on current platform
function findChatInput() {
    let selectors = [];

    switch (platform) {
        case 'claude':
            selectors = [
                'div[contenteditable="true"].ProseMirror',
                '.ProseMirror[contenteditable="true"]',
                'div[contenteditable="true"][data-placeholder*="Talk to Claude"]',
                'div[contenteditable="true"][class*="ProseMirror"]',
                'textarea[placeholder*="Talk to Claude"]',
                'textarea[placeholder*="Message"]',
                'div[contenteditable="true"][role="textbox"]',
                '[aria-label*="Write your prompt to Claude"] .ProseMirror',
                'textarea',
                '[contenteditable="true"]'
            ];
            break;

        case 'chatgpt':
            selectors = [
                'textarea[placeholder*="Message"]',
                'textarea[data-id="root"]',
                'div[contenteditable="true"]',
                '#prompt-textarea',
                'textarea',
                '[contenteditable="true"]'
            ];
            break;

        case 'gemini':
            selectors = [
                'textarea[placeholder*="Enter a prompt"]',
                'div[contenteditable="true"]',
                'textarea',
                '[contenteditable="true"]'
            ];
            break;

        default:
            selectors = [
                'textarea',
                '[contenteditable="true"]',
                'input[type="text"]'
            ];
    }

    // Try each selector
    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && element.offsetParent !== null) { // Check if visible
            console.log('✅ Found chat input:', selector, 'Element:', element);
            return element;
        }
    }

    console.warn('⚠️ Could not find chat input for platform:', platform);
    console.log('Tried selectors:', selectors);
    return null;
}

// Format conversation messages for injection
function formatConversationForInjection(messages) {
    if (!messages || messages.length === 0) {
        return '';
    }

    // For current conversation, just get the last user message
    // For historical conversations, format as context
    if (messages.length === 1) {
        return messages[0].content || messages[0].text || '';
    }

    // Create a clean, readable format for multiple messages
    const formattedMessages = messages.slice(-5).map(msg => {  // Last 5 messages only
        const role = msg.role === 'user' ? 'Human' : 'Assistant';
        const content = msg.content || msg.text || '';
        return `${role}: ${content.substring(0, 500)}${content.length > 500 ? '...' : ''}`;
    });

    return `Context from previous conversation:\n\n${formattedMessages.join('\n\n')}\n\nContinuing from above:`;
}

// Inject text into input element
async function injectTextIntoInput(inputElement, text) {
    console.log('💉 Injecting text into input element:', inputElement);

    // Focus the input first
    inputElement.focus();

    if (inputElement.tagName === 'TEXTAREA' || inputElement.tagName === 'INPUT') {
        // For textarea and input elements
        inputElement.value = text;

        // Trigger proper input event
        const inputEvent = new InputEvent('input', { 
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: text
        });
        inputElement.dispatchEvent(inputEvent);
        inputElement.dispatchEvent(new Event('change', { bubbles: true }));

        // Set cursor at the end
        inputElement.setSelectionRange(text.length, text.length);

    } else if (inputElement.contentEditable === 'true') {
        // Clear existing content first
        inputElement.innerHTML = '';
        
        // For ProseMirror-based editors (like Claude)
        if (inputElement.classList.contains('ProseMirror')) {
            // Create paragraph nodes for each line
            const lines = text.split('\n');
            lines.forEach((line, index) => {
                const p = document.createElement('p');
                p.textContent = line || '\u200B'; // Zero-width space for empty lines
                inputElement.appendChild(p);
            });
        } else {
            // Standard contenteditable
            inputElement.innerHTML = text.replace(/\n/g, '<br>');
        }

        // Trigger proper input event
        const inputEvent = new InputEvent('input', { 
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: text
        });
        inputElement.dispatchEvent(inputEvent);
        
        // Also dispatch a 'beforeinput' event for some frameworks
        const beforeInputEvent = new InputEvent('beforeinput', {
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: text
        });
        inputElement.dispatchEvent(beforeInputEvent);

        // Set cursor at the end
        const range = document.createRange();
        const selection = window.getSelection();
        range.selectNodeContents(inputElement);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    // Additional platform-specific triggers
    if (platform === 'claude') {
        // Claude might need additional events
        inputElement.dispatchEvent(new Event('keyup', { bubbles: true }));
    } else if (platform === 'chatgpt') {
        // ChatGPT might need focus events
        inputElement.dispatchEvent(new Event('focus', { bubbles: true }));
    }

    console.log('✅ Text injected successfully');
}

// Show conversation preview
async function showConversationPreview(sessionId) {
    try {
        const response = await fetch(`http://localhost:8000/v1/conversations/${sessionId}/preview`, {
            headers: {
                'Authorization': 'Bearer ' + await getAuthToken()
            }
        });

        if (response.ok) {
            const preview = await response.json();
            const modal = document.getElementById('previewModal');
            const content = document.getElementById('previewContent');

            content.innerHTML = `
                <div class="preview-messages">
                    ${preview.messages.slice(0, 5).map(msg => `
                        <div class="preview-message ${msg.role}">
                            <div class="message-role">${msg.role}</div>
                            <div class="message-text">${msg.text.slice(0, 200)}${msg.text.length > 200 ? '...' : ''}</div>
                        </div>
                    `).join('')}
                    ${preview.messages.length > 5 ? `<div class="preview-more">+${preview.messages.length - 5} more messages</div>` : ''}
                </div>
            `;

            modal.style.display = 'block';
            modal.dataset.sessionId = sessionId;
        }
    } catch (error) {
        showNotification('Failed to load preview', 'error');
    }
}

// Close preview modal
function closePreviewModal() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Download conversation
async function downloadConversation(sessionId) {
    try {
        await saveConversation('txt', sessionId);
    } catch (error) {
        showNotification('Failed to download', 'error');
    }
}

// Switch tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.contextly-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab panels
    document.querySelectorAll('.contextly-tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-tab`);
    });
}

// Filter conversations
function filterConversations(searchTerm) {
    const squares = document.querySelectorAll('.conversation-square');
    const cards = document.querySelectorAll('.contextly-conversation-card');
    const term = searchTerm.toLowerCase();

    [...squares, ...cards].forEach(item => {
        const title = item.querySelector('.conversation-title')?.textContent.toLowerCase() || '';
        const preview = item.querySelector('.conversation-preview')?.textContent.toLowerCase() || '';
        const visible = title.includes(term) || preview.includes(term);
        item.style.display = visible ? 'flex' : 'none';
    });
}

// Format date for display
function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 86400000) { // Less than 24 hours
        return formatTimeAgo(timestamp);
    } else {
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    }
}

// Update earn mode
function updateEarnMode(enabled) {
    earnMode = enabled;
    const modeLabel = document.querySelector('.mode-label');
    const modeStatus = document.querySelector('.mode-status');

    if (modeLabel) {
        modeLabel.textContent = enabled ? 'EARN MODE' : 'FREE MODE';
    }
    if (modeStatus) {
        modeStatus.textContent = enabled ? '● EARNING' : '○ OFF';
        modeStatus.classList.toggle('earning', enabled);
    }

    // Start animations if earning
    if (enabled) {
        startEarningAnimation();
    }

    // Save state
    chrome.storage.local.set({ earnMode: enabled });
    showNotification(enabled ? 'Earn mode activated! 💰' : 'Free mode activated');
}

// Handle quick actions
async function handleQuickAction(action) {
    switch (action) {
        case 'auto-save':
            autoContextlyEnabled = !autoContextlyEnabled;
            const btn = document.querySelector(`[data-action="auto-save"]`);
            btn.classList.toggle('active', autoContextlyEnabled);
            showNotification(autoContextlyEnabled ? 'Auto-save enabled' : 'Auto-save disabled');

            // Start conversation capture when auto-save is enabled
            if (autoContextlyEnabled && !captureEnabled) {
                initializeConversationCapture();
            }
            break;
        case 'instant-save':
            // Initialize capture if not already started
            if (!captureEnabled) {
                initializeConversationCapture();
            } else {
                // Force immediate save
                await saveConversationToBackend();
            }
            await saveConversation('txt');
            break;
        case 'screenshot':
            await captureScreenshot();
            break;
        case 'share':
            await shareConversation();
            break;
        case 'export':
            showExportOptions();
            break;
    }
}

// Handle tool actions
async function handleToolAction(action) {
    switch (action) {
        case 'save-all':
            await saveAllFormats();
            break;
        case 'screenshot':
            await captureScreenshot();
            break;
        case 'summarize':
            await summarizeConversation();
            break;
        case 'translate':
            await translateConversation();
            break;
        case 'export-code':
            await extractCode();
            break;
        case 'share-link':
            await createShareLink();
            break;
    }
}

// Handle filters
function handleFilter(filter) {
    // Update active filter
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.filter === filter);
    });

    // Filter conversation squares and cards
    const squares = document.querySelectorAll('.conversation-square');
    const cards = document.querySelectorAll('.contextly-conversation-card');

    [...squares, ...cards].forEach(item => {
        const sessionId = item.dataset.sessionId;
        const conv = conversationHistory.find(c => c.session_id === sessionId);
        let visible = true;

        if (conv) {
            if (filter === 'claude' && conv.platform !== 'claude') visible = false;
            if (filter === 'chatgpt' && conv.platform !== 'chatgpt') visible = false;
            if (filter === 'gemini' && conv.platform !== 'gemini') visible = false;
            if (filter === 'recent') {
                // Show only last 24 hours
                const age = Date.now() - new Date(conv.last_updated).getTime();
                visible = age < 86400000; // 24 hours
            }
        }

        item.style.display = visible ? (item.classList.contains('conversation-square') ? 'flex' : 'flex') : 'none';
    });
}

// Start earning animation
function startEarningAnimation() {
    const earnHeader = document.querySelector('.contextly-earn-header');
    if (earnHeader) {
        earnHeader.classList.add('earning');

        // Create floating tokens
        setInterval(() => {
            if (earnMode) {
                createFloatingToken();
            }
        }, 3000);
    }
}

function formatTimeAgo(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diff = Math.floor((now - time) / 1000);

    if (diff < 60) return 'now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d`;
    return `${Math.floor(diff / 604800)}w`;
}

function startSyncAnimation() {
    const syncEl = document.getElementById('syncAnimation');
    if (syncEl) {
        syncEl.classList.add('syncing');

        // Create floating text effect
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                createFloatingText('sync');
            }, i * 200);
        }
    }
}

function createFloatingText(type) {
    const floatingText = document.createElement('div');
    floatingText.className = 'contextly-floating-text';

    switch (type) {
        case 'sync':
            floatingText.textContent = '✨';
            break;
        case 'earn':
            floatingText.textContent = '+💰';
            break;
        case 'save':
            floatingText.textContent = '💾';
            break;
        case 'inject':
            floatingText.textContent = '🚀';
            break;
        case 'crystal':
            floatingText.textContent = '🔮';
            break;
        default:
            floatingText.textContent = '+1';
    }

    // Position near the button
    const button = document.querySelector('.contextly-main-btn');
    if (button) {
        const rect = button.getBoundingClientRect();
        floatingText.style.position = 'fixed';
        floatingText.style.left = `${rect.left + Math.random() * 30}px`;
        floatingText.style.top = `${rect.top - 10}px`;
        floatingText.style.zIndex = '10001';
        floatingText.style.pointerEvents = 'none';
        floatingText.style.color = '#3b82f6';
        floatingText.style.fontSize = '14px';
        floatingText.style.fontWeight = 'bold';
        floatingText.style.animation = 'contextly-float-up 2s ease-out forwards';

        document.body.appendChild(floatingText);

        setTimeout(() => {
            floatingText.remove();
        }, 2000);
    }
}

function createFloatingETHTokens() {
    // Create multiple ETH tokens that float up from different positions
    const numTokens = 5 + Math.floor(Math.random() * 3); // 5-7 tokens
    
    for (let i = 0; i < numTokens; i++) {
        setTimeout(() => {
            const ethToken = document.createElement('div');
            ethToken.className = 'contextly-eth-token';
            
            // ETH symbol or emoji
            ethToken.innerHTML = '⟠'; // ETH symbol, could also use 'Ξ' or an SVG
            
            // Random starting position across the screen
            const startX = 20 + Math.random() * (window.innerWidth - 40);
            const startY = window.innerHeight - 100;
            
            // Random horizontal drift
            const drift = (Math.random() - 0.5) * 100;
            
            ethToken.style.cssText = `
                position: fixed;
                left: ${startX}px;
                top: ${startY}px;
                z-index: 10001;
                pointer-events: none;
                color: #627EEA;
                font-size: ${24 + Math.random() * 16}px;
                font-weight: bold;
                text-shadow: 0 0 10px rgba(98, 126, 234, 0.5);
                animation: ethTokenFloat 3s ease-out forwards;
                --drift: ${drift}px;
                --rotation: ${Math.random() * 360}deg;
            `;
            
            document.body.appendChild(ethToken);
            
            // Remove after animation
            setTimeout(() => {
                ethToken.remove();
            }, 3000);
        }, i * 150); // Stagger the token creation
    }
}

function showNotification(message, type = 'info', duration = 3000, details = null) {
    const notification = document.createElement('div');
    notification.className = `contextly-notification contextly-notification-${type}`;

    // Create notification content with optional details
    if (details) {
        notification.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 4px;">${message}</div>
            <div style="font-size: 12px; opacity: 0.9; font-family: monospace;">${details}</div>
        `;
    } else {
        notification.textContent = message;
    }

    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '12px 20px';
    notification.style.borderRadius = '8px';
    notification.style.fontSize = '14px';
    notification.style.fontWeight = '500';
    notification.style.zIndex = '10002';
    notification.style.maxWidth = '350px';
    notification.style.wordWrap = 'break-word';
    notification.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
    notification.style.animation = 'slideInRight 0.3s ease-out';

    if (type === 'success') {
        notification.style.backgroundColor = '#10b981';
        notification.style.color = 'white';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#ef4444';
        notification.style.color = 'white';
    } else {
        notification.style.backgroundColor = '#3b82f6';
        notification.style.color = 'white';
    }

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

function updateButtonAppearance() {
    const button = document.querySelector('.contextly-main-btn');
    if (button) {
        if (autoContextlyEnabled) {
            button.style.backgroundColor = '#3b82f6';
            button.style.borderColor = '#3b82f6';
            button.style.color = 'white';
        } else {
            button.style.backgroundColor = '';
            button.style.borderColor = '';
            button.style.color = '';
        }
    }
}

function updateToggleStates() {
    const autoToggle = document.getElementById('autoContextlyToggle');
    const earnToggle = document.getElementById('earnToggle');

    if (autoToggle) {
        const toggleSwitch = autoToggle.querySelector('.contextly-toggle-switch');
        toggleSwitch.classList.toggle('active', autoContextlyEnabled);
    }

    if (earnToggle) {
        earnToggle.classList.toggle('visible', autoContextlyEnabled && earnMode);
        const toggleSwitch = earnToggle.querySelector('.contextly-toggle-switch');
        toggleSwitch.classList.toggle('active', earnMode);
    }
}

// Add CSS styles
const style = document.createElement('style');
style.textContent = `
    .contextly-dropdown {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        border-radius: 16px;
        overflow: hidden;
        background: #1a1a1a;
        border: 1px solid rgba(255, 255, 255, 0.1);
        width: 420px;
        max-width: calc(100vw - 40px);
        max-height: 480px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .contextly-dropdown-content {
        display: flex;
        flex-direction: column;
        height: 100%;
        background: #1a1a1a;
    }
    
    /* Earn Mode Header */
    .contextly-earn-header {
        background: linear-gradient(135deg, #2a2a2a 0%, #1f1f1f 100%);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding: 12px;
        position: relative;
        overflow: hidden;
    }
    
    .contextly-earn-header.earning::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            45deg,
            transparent 30%,
            rgba(59, 130, 246, 0.1) 50%,
            transparent 70%
        );
        animation: shimmer 3s infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
        100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
    }
    
    .earn-mode-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        position: relative;
        z-index: 1;
    }
    
    .earn-mode-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
    }
    
    .earn-logo {
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .earn-mode-info {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .earn-mode-title {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .mode-label {
        font-size: 16px;
        font-weight: 700;
        color: #fff;
        letter-spacing: 0.5px;
    }
    
    .mode-status {
        font-size: 12px;
        color: #999;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .mode-status.earning {
        color: #10b981;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .earn-stats {
        display: flex;
        gap: 12px;
    }
    
    .stat-chip {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        font-size: 12px;
    }
    
    .stat-icon {
        font-size: 14px;
    }
    
    .stat-value {
        font-weight: 600;
        color: #3b82f6;
    }
    
    .stat-label {
        color: #999;
    }
    
    /* Wallet Address Styling */
    .wallet-address {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: #10b981;
        background: rgba(16, 185, 129, 0.1);
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    .wallet-connection-status {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
        border-bottom: 1px solid rgba(16, 185, 129, 0.2);
        backdrop-filter: blur(10px);
    }
    
    /* Big Toggle Switch */
    .big-toggle {
        position: relative;
        display: inline-block;
        width: 80px;
        height: 40px;
        cursor: pointer;
    }
    
    .big-toggle input {
        opacity: 0;
        width: 0;
        height: 0;
    }
    
    .toggle-track {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: #2a2a2a;
        border: 2px solid #3a3a3a;
        border-radius: 40px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 8px;
    }
    
    .toggle-icon {
        font-size: 20px;
        transition: opacity 0.3s ease;
    }
    
    .toggle-icon.off {
        opacity: 0.5;
    }
    
    .toggle-icon.on {
        opacity: 0.5;
    }
    
    .big-toggle input:checked + .toggle-track {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        border-color: #3b82f6;
    }
    
    .big-toggle input:checked + .toggle-track .toggle-icon.off {
        opacity: 0.2;
    }
    
    .big-toggle input:checked + .toggle-track .toggle-icon.on {
        opacity: 1;
    }
    
    .toggle-track::after {
        content: '';
        position: absolute;
        height: 32px;
        width: 32px;
        left: 4px;
        bottom: 2px;
        background: white;
        border-radius: 50%;
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    .big-toggle input:checked + .toggle-track::after {
        transform: translateX(40px);
    }
    
    /* Quick Actions Bar */
    .contextly-quick-actions {
        display: flex;
        gap: 6px;
        padding: 8px 12px;
        background: #222;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .quick-action-btn {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        padding: 8px 6px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid transparent;
        border-radius: 8px;
        color: #999;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .quick-action-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
        transform: translateY(-2px);
    }
    
    .quick-action-btn.active {
        background: rgba(59, 130, 246, 0.2);
        border-color: #3b82f6;
        color: #3b82f6;
    }
    
    .action-icon {
        font-size: 20px;
    }
    
    .action-label {
        font-size: 11px;
        font-weight: 500;
    }
    
    .contextly-window-title {
        flex: 1;
        font-size: 14px;
        font-weight: 500;
        color: #ffffff;
        margin-left: 8px;
    }
    
    .contextly-window-controls {
        display: flex;
        gap: 8px;
    }
    
    .contextly-window-btn {
        width: 28px;
        height: 28px;
        border: none;
        background: transparent;
        color: #999;
        font-size: 16px;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.15s ease;
    }
    
    .contextly-window-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
    }
    
    .contextly-window-btn.close:hover {
        background: #e81123;
        color: white;
    }
    
    /* Tab navigation */
    .contextly-tabs {
        display: flex;
        background: #1a1a1a;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding: 0 16px;
    }
    
    .contextly-tab {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 12px 20px;
        background: none;
        border: none;
        color: #999;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
    }
    
    .contextly-tab:hover {
        color: #fff;
        background: rgba(255, 255, 255, 0.05);
    }
    
    .contextly-tab.active {
        color: #fff;
        border-bottom-color: #3b82f6;
    }
    
    .tab-icon {
        font-size: 16px;
    }
    
    /* Tab content */
    .contextly-tab-content {
        flex: 1;
        overflow: hidden;
        background: #1a1a1a;
        position: relative;
        min-height: 0;
    }
    
    .contextly-tab-panel {
        display: none;
        padding: 16px;
        height: 100%;
        overflow-y: auto;
        overflow-x: hidden;
    }
    
    .contextly-tab-panel.active {
        display: block;
    }
    
    /* Search bar */
    .contextly-search-bar {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
    }
    
    .contextly-search-input {
        flex: 1;
        padding: 8px 12px;
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        border-radius: 6px;
        color: #fff;
        font-size: 14px;
    }
    
    .contextly-search-input:focus {
        outline: none;
        border-color: #3b82f6;
    }
    
    .contextly-search-btn {
        padding: 8px 16px;
        background: #3a3a3a;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
    }
    
    /* Conversations Grid */
    .contextly-conversations-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 12px;
        max-height: 320px;
        overflow-y: auto;
        padding: 8px 4px;
        margin-top: 8px;
    }
    
    .contextly-conversations-grid::-webkit-scrollbar {
        width: 6px;
    }
    
    .contextly-conversations-grid::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 3px;
    }
    
    .contextly-conversations-grid::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 3px;
    }
    
    .contextly-conversations-grid::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    /* Conversation Squares */
    .conversation-square {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        min-height: 140px;
        display: flex;
        flex-direction: column;
    }
    
    .conversation-square:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    
    .conversation-square-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .platform-badge {
        width: 24px;
        height: 24px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
    }
    
    .platform-badge.claude {
        background: linear-gradient(135deg, #ff6b35, #f7931e);
    }
    
    .platform-badge.chatgpt {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    
    .platform-badge.gemini {
        background: linear-gradient(135deg, #8b5cf6, #a855f7);
    }
    
    .conversation-square-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .conversation-square .conversation-title {
        font-size: 13px;
        font-weight: 600;
        color: #fff;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 0;
    }
    
    .conversation-square .conversation-preview {
        font-size: 11px;
        color: #999;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 0;
        flex: 1;
    }
    
    .conversation-square .conversation-stats {
        display: flex;
        gap: 8px;
        margin-top: auto;
        margin-bottom: 8px;
    }
    
    .conversation-square .stat-item {
        font-size: 10px;
        color: #666;
        background: rgba(255, 255, 255, 0.05);
        padding: 2px 6px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 2px;
    }
    
    .conversation-square .conversation-time {
        font-size: 10px;
        color: #666;
        background: rgba(255, 255, 255, 0.05);
        padding: 2px 6px;
        border-radius: 8px;
    }
    
    .conversation-square-actions {
        display: flex;
        gap: 6px;
        opacity: 0;
        transform: translateY(4px);
        transition: all 0.2s ease;
    }
    
    .conversation-square:hover .conversation-square-actions {
        opacity: 1;
        transform: translateY(0);
    }
    
    .square-action-btn {
        flex: 1;
        height: 28px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 500;
    }
    
    .square-action-btn.save-btn {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .square-action-btn.save-btn:hover {
        background: #10b981;
        color: white;
        transform: scale(1.05);
    }
    
    .square-action-btn.inject-btn {
        background: rgba(59, 130, 246, 0.15);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .square-action-btn.inject-btn:hover {
        background: #3b82f6;
        color: white;
        transform: scale(1.05);
    }
    
    .contextly-conversation-card {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        transition: all 0.2s ease;
        overflow: hidden;
    }
    
    .contextly-conversation-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(59, 130, 246, 0.3);
        transform: translateX(4px);
    }
    
    .conversation-main {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        cursor: pointer;
    }
    
    .conversation-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
        position: relative;
        overflow: hidden;
    }
    
    .conversation-icon.claude {
        background: linear-gradient(135deg, #ff6b35, #f7931e);
    }
    
    .conversation-icon.chatgpt {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    
    .conversation-icon.gemini {
        background: linear-gradient(135deg, #8b5cf6, #a855f7);
    }
    
    .conversation-content {
        flex: 1;
        min-width: 0;
    }
    
    .conversation-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    
    .conversation-title {
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .conversation-time {
        font-size: 11px;
        color: #666;
        flex-shrink: 0;
    }
    
    .conversation-preview {
        font-size: 12px;
        color: #999;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 6px;
    }
    
    .conversation-stats {
        display: flex;
        gap: 12px;
        font-size: 11px;
        color: #666;
    }
    
    .conversation-stats .stat {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .conversation-quick-actions {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 4px;
        background: rgba(0, 0, 0, 0.2);
        border-left: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    .quick-btn {
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
        background: rgba(255, 255, 255, 0.05);
        color: #999;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .quick-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
        transform: scale(1.1);
    }
    
    .quick-btn.primary {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
    }
    
    .quick-btn.primary:hover {
        background: #3b82f6;
        color: white;
    }
    
    .conversation-info {
        flex: 1;
        min-width: 0;
    }
    
    .conversation-title {
        font-size: 14px;
        font-weight: 500;
        color: #fff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 4px;
    }
    
    .conversation-meta {
        display: flex;
        gap: 8px;
        font-size: 12px;
        color: #999;
    }
    
    .conversation-actions {
        display: flex;
        gap: 4px;
        opacity: 0;
        transition: opacity 0.2s ease;
    }
    
    .contextly-conversation-tile:hover .conversation-actions {
        opacity: 1;
    }
    
    .conv-action-btn {
        width: 28px;
        height: 28px;
        border: none;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.15s ease;
    }
    
    .conv-action-btn:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: scale(1.1);
    }
    
    /* Search and Filters */
    .contextly-search-bar {
        margin-bottom: 16px;
    }
    
    .contextly-search-input {
        width: 100%;
        padding: 10px 16px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: #fff;
        font-size: 14px;
        margin-bottom: 12px;
    }
    
    .contextly-search-input:focus {
        outline: none;
        border-color: #3b82f6;
        background: rgba(255, 255, 255, 0.08);
    }
    
    .search-filters {
        display: flex;
        gap: 8px;
    }
    
    .filter-chip {
        padding: 6px 12px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid transparent;
        border-radius: 20px;
        color: #999;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .filter-chip:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
    }
    
    .filter-chip.active {
        background: rgba(59, 130, 246, 0.2);
        border-color: #3b82f6;
        color: #3b82f6;
    }
    
    /* Empty state */
    .contextly-empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 300px;
        text-align: center;
        color: #999;
    }
    
    .empty-illustration {
        position: relative;
        margin-bottom: 24px;
    }
    
    .empty-icon-main {
        font-size: 64px;
        opacity: 0.2;
    }
    
    .empty-icon-small {
        position: absolute;
        font-size: 24px;
        opacity: 0.3;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    .contextly-empty-state h3 {
        font-size: 18px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 8px;
    }
    
    .contextly-empty-state p {
        font-size: 14px;
        margin-bottom: 20px;
    }
    
    /* Tools Tab */
    .contextly-tools-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .tool-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 20px 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: center;
    }
    
    .tool-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(59, 130, 246, 0.3);
        transform: translateY(-2px);
    }
    
    .tool-icon {
        font-size: 32px;
        margin-bottom: 4px;
    }
    
    .tool-card h4 {
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        margin: 0;
    }
    
    .tool-card p {
        font-size: 11px;
        color: #666;
        margin: 0;
    }
    
    .contextly-format-section {
        padding: 16px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
    }
    
    .contextly-format-section h4 {
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 12px;
    }
    
    .format-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .format-btn {
        padding: 8px 16px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #999;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .format-btn:hover {
        background: rgba(59, 130, 246, 0.2);
        border-color: #3b82f6;
        color: #3b82f6;
    }
    
    /* Insights Tab */
    .insights-overview {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .insight-card {
        padding: 16px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        text-align: center;
    }
    
    .insight-card.primary {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.1));
        border-color: rgba(59, 130, 246, 0.3);
    }
    
    .insight-value {
        font-size: 28px;
        font-weight: 700;
        color: #fff;
        margin-bottom: 4px;
    }
    
    .insight-label {
        font-size: 12px;
        color: #999;
        margin-bottom: 8px;
    }
    
    .insight-trend {
        font-size: 11px;
        color: #10b981;
    }
    
    .mini-chart {
        font-size: 20px;
        opacity: 0.5;
    }
    
    /* Achievements */
    .contextly-achievements {
        margin-bottom: 24px;
    }
    
    .contextly-achievements h4 {
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 12px;
    }
    
    .achievement-list {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }
    
    .achievement {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        font-size: 13px;
        color: #666;
        opacity: 0.5;
    }
    
    .achievement.unlocked {
        opacity: 1;
        background: rgba(16, 185, 129, 0.1);
        border-color: rgba(16, 185, 129, 0.3);
        color: #fff;
    }
    
    .achievement-icon {
        font-size: 20px;
    }
    
    /* Actions grid */
    .contextly-actions-grid {
        display: grid;
        gap: 24px;
    }
    
    .contextly-action-group h4 {
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 12px;
    }
    
    .contextly-action-btn {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;
        padding: 12px 16px;
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        color: #fff;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s ease;
        margin-bottom: 8px;
    }
    
    .contextly-action-btn:hover {
        background: #333;
        border-color: #4a4a4a;
        transform: translateX(4px);
    }
    
    .action-icon {
        font-size: 20px;
    }
    
    /* Settings */
    .contextly-settings-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    
    .contextly-setting-item {
        padding: 12px;
        background: #2a2a2a;
        border-radius: 8px;
        transition: opacity 0.2s ease;
    }
    
    .contextly-setting-item.disabled {
        opacity: 0.5;
        pointer-events: none;
    }
    
    .contextly-toggle-label {
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
    }
    
    .contextly-toggle-label input {
        display: none;
    }
    
    .toggle-slider {
        width: 44px;
        height: 24px;
        background: #3a3a3a;
        border-radius: 12px;
        position: relative;
        transition: background 0.2s ease;
    }
    
    .toggle-slider::after {
        content: '';
        width: 20px;
        height: 20px;
        background: #fff;
        border-radius: 50%;
        position: absolute;
        top: 2px;
        left: 2px;
        transition: transform 0.2s ease;
    }
    
    input:checked + .toggle-slider {
        background: #3b82f6;
    }
    
    input:checked + .toggle-slider::after {
        transform: translateX(20px);
    }
    
    .setting-text {
        font-size: 14px;
        font-weight: 500;
        color: #fff;
    }
    
    .setting-desc {
        font-size: 12px;
        color: #999;
        margin-top: 4px;
        margin-left: 56px;
    }
    
    /* Stats */
    .contextly-stats-section {
        margin-top: 24px;
        padding: 16px;
        background: #252525;
        border-radius: 8px;
    }
    
    .contextly-stats-section h4 {
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 12px;
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }
    
    .stat-item {
        text-align: center;
        padding: 12px;
        background: #2a2a2a;
        border-radius: 6px;
    }
    
    .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: #3b82f6;
        display: block;
    }
    
    .stat-label {
        font-size: 12px;
        color: #999;
        margin-top: 4px;
    }
    
    /* Preview modal */
    .contextly-preview-modal {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 90%;
        max-width: 500px;
        background: #1a1a1a;
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
        z-index: 1000;
    }
    
    .preview-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        background: #252525;
        border-bottom: 1px solid #3a3a3a;
    }
    
    .preview-title {
        font-size: 16px;
        font-weight: 500;
        color: #fff;
    }
    
    .preview-close {
        width: 32px;
        height: 32px;
        border: none;
        background: transparent;
        color: #999;
        font-size: 20px;
        cursor: pointer;
        border-radius: 4px;
    }
    
    .preview-close:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
    }
    
    .preview-content {
        padding: 16px;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .preview-message {
        margin-bottom: 12px;
        padding: 8px 12px;
        background: #2a2a2a;
        border-radius: 6px;
    }
    
    .message-role {
        font-size: 12px;
        font-weight: 600;
        color: #3b82f6;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    
    .message-text {
        font-size: 14px;
        color: #e0e0e0;
        line-height: 1.5;
    }
    
    .preview-more {
        text-align: center;
        color: #999;
        font-size: 14px;
        margin-top: 12px;
    }
    
    .preview-actions {
        display: flex;
        gap: 8px;
        padding: 16px;
        background: #252525;
        border-top: 1px solid #3a3a3a;
    }
    
    /* Buttons */
    .contextly-btn-primary,
    .contextly-btn-secondary {
        padding: 8px 20px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .contextly-btn-primary {
        background: #3b82f6;
        color: white;
    }
    
    .contextly-btn-primary:hover {
        background: #2563eb;
        transform: translateY(-1px);
    }
    
    .contextly-btn-secondary {
        background: #3a3a3a;
        color: #fff;
    }
    
    .contextly-btn-secondary:hover {
        background: #4a4a4a;
    }
    
    .contextly-dropdown-section {
        margin: 4px 0;
    }
    
    .contextly-dropdown-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        border-radius: 8px;
        cursor: pointer;
        color: rgba(255, 255, 255, 0.9);
        font-size: 14px;
        transition: all 0.15s ease;
    }
    
    .contextly-dropdown-item:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }
    
    .contextly-dropdown-item svg {
        flex-shrink: 0;
        opacity: 0.7;
    }
    
    .contextly-dropdown-divider {
        height: 1px;
        background: rgba(255, 255, 255, 0.1);
        margin: 8px 4px;
    }
    
    .contextly-toggle {
        justify-content: space-between;
    }
    
    .contextly-toggle-switch {
        width: 32px;
        height: 18px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 9px;
        position: relative;
        transition: all 0.2s ease;
        flex-shrink: 0;
    }
    
    .contextly-toggle-switch::after {
        content: '';
        position: absolute;
        width: 14px;
        height: 14px;
        background: white;
        border-radius: 7px;
        top: 2px;
        left: 2px;
        transition: all 0.2s ease;
    }
    
    .contextly-toggle-switch.active {
        background: #3b82f6;
    }
    
    .contextly-toggle-switch.active::after {
        transform: translateX(14px);
    }
    
    .contextly-earn-item {
        opacity: 0;
        transform: translateY(-4px);
        transition: all 0.2s ease;
        pointer-events: none;
        max-height: 0;
        overflow: hidden;
        padding-top: 0;
        padding-bottom: 0;
    }
    
    .contextly-earn-item.visible {
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
        max-height: 50px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    .contextly-section-header {
        font-size: 12px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        padding: 0 12px;
    }
    
    .contextly-sync-section {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1));
        border-radius: 8px;
        margin: 4px 0 12px 0;
        padding: 12px;
    }
    
    .contextly-sync-status {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .contextly-sync-animation {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: linear-gradient(45deg, #3b82f6, #8b5cf6);
        position: relative;
        overflow: hidden;
    }
    
    .contextly-sync-animation::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        animation: contextly-shine 2s infinite;
    }
    
    .contextly-sync-animation.syncing::before {
        animation: contextly-shine 0.8s infinite;
    }
    
    .contextly-sync-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .sync-label {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
    }
    
    .sync-counter {
        font-size: 14px;
        font-weight: 600;
        color: #3b82f6;
    }
    
    .contextly-history-section {
        max-height: 300px;
        overflow-y: auto;
    }
    
    .contextly-history-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 12px;
    }
    
    .contextly-history-item {
        padding: 12px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        cursor: pointer;
        transition: all 0.15s ease;
    }
    
    .contextly-history-item:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(59, 130, 246, 0.3);
        transform: translateY(-1px);
    }
    
    .history-item-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    
    .history-platform {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    
    .platform-badge svg {
        width: 16px;
        height: 16px;
        display: block;
    }
    
    .platform-claude { 
        background: linear-gradient(45deg, #ff6b35, #f7931e); 
    }
    .platform-claude svg { 
        fill: #fff; 
    }
    
    .platform-chatgpt { 
        background: linear-gradient(45deg, #10b981, #059669); 
    }
    .platform-chatgpt svg { 
        fill: #fff; 
    }
    
    .platform-gemini { 
        background: linear-gradient(45deg, #8b5cf6, #a855f7); 
    }
    .platform-gemini svg { 
        fill: #fff; 
    }
    
    .platform-unknown { 
        background: #6b7280; 
    }
    .platform-unknown svg { 
        fill: #fff; 
    }
    
    .history-title {
        flex: 1;
        font-size: 13px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .history-time {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
        flex-shrink: 0;
    }
    
    .history-preview {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
        line-height: 1.4;
        margin-bottom: 8px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .history-stats {
        display: flex;
        gap: 8px;
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
    }
    
    @keyframes contextly-shine {
        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
        100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
    }
    
    @keyframes contextly-float-up {
        0% {
            opacity: 1;
            transform: translateY(0);
        }
        100% {
            opacity: 0;
            transform: translateY(-50px) scale(1.2);
        }
    }
    
    .contextly-floating-text {
        animation: contextly-float-up 2s ease-out forwards;
    }
    
    @keyframes slideInRight {
        0% {
            opacity: 0;
            transform: translateX(100px);
        }
        100% {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes sparkleRadiate {
        0% {
            opacity: 1;
            transform: translate(0, 0) scale(1);
        }
        100% {
            opacity: 0;
            transform: translate(var(--sparkle-x), var(--sparkle-y)) scale(0.5);
        }
    }
    
    @keyframes contextly-rotate {
        0% {
            transform: rotate(0deg);
        }
        100% {
            transform: rotate(360deg);
        }
    }
    
    @keyframes ethTokenFloat {
        0% {
            opacity: 0;
            transform: translateY(0) translateX(0) rotate(0deg) scale(0.5);
        }
        10% {
            opacity: 1;
            transform: translateY(-20px) translateX(calc(var(--drift) * 0.1)) rotate(calc(var(--rotation) * 0.1)) scale(1);
        }
        90% {
            opacity: 1;
            transform: translateY(-400px) translateX(var(--drift)) rotate(var(--rotation)) scale(1.2);
        }
        100% {
            opacity: 0;
            transform: translateY(-500px) translateX(var(--drift)) rotate(var(--rotation)) scale(1.5);
        }
    }
    
    /* Status Indicator Styles */
    .contextly-status-indicator {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(10, 10, 10, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        z-index: 10000;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .contextly-status-indicator:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4);
    }
    
    .contextly-status-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .contextly-status-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        animation: contextly-rotate 3s linear infinite;
    }
    
    .contextly-status-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .contextly-status-title {
        font-size: 14px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .contextly-status-mode {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
    }
`;
document.head.appendChild(style);

// Function to create floating status indicator
function createStatusIndicator() {
    // Remove existing indicator
    const existing = document.querySelector('.contextly-status-indicator');
    if (existing) existing.remove();

    const indicator = document.createElement('div');
    indicator.className = 'contextly-status-indicator';
    indicator.innerHTML = `
        <div class="contextly-status-content">
            <img src="${chrome.runtime.getURL('icons/icon48.png')}" alt="Contextly" class="contextly-status-avatar">
            <div class="contextly-status-text">
                <div class="contextly-status-title">Contextly Active</div>
                <div class="contextly-status-mode">${earnMode ? 'Earn Mode' : 'Free Mode'}</div>
            </div>
        </div>
    `;

    document.body.appendChild(indicator);
}

// MetaMask connection handler for debug script
async function handleMetaMaskInDebugScript() {
    console.log('🔍 Starting MetaMask connection from debug script...');

    return new Promise((resolve, reject) => {
        // Create and inject script into page context to access window.ethereum
        const script = document.createElement('script');
        script.textContent = `
            (function() {
                console.log('🔍 Page context script checking MetaMask...');
                
                if (typeof window.ethereum === 'undefined') {
                    console.error('❌ MetaMask not found in page context');
                    window.postMessage({
                        type: 'METAMASK_DEBUG_RESPONSE',
                        error: 'MetaMask is not installed or not accessible'
                    }, '*');
                    return;
                }
                
                console.log('✅ MetaMask detected in page context');
                
                // Try to connect
                window.ethereum.request({ method: 'eth_requestAccounts' })
                    .then(accounts => {
                        if (accounts.length === 0) {
                            throw new Error('No accounts available');
                        }
                        
                        // Get chain ID
                        return window.ethereum.request({ method: 'eth_chainId' })
                            .then(chainId => {
                                window.postMessage({
                                    type: 'METAMASK_DEBUG_RESPONSE',
                                    result: {
                                        address: accounts[0],
                                        chainId: parseInt(chainId, 16),
                                        provider: 'metamask'
                                    }
                                }, '*');
                            });
                    })
                    .catch(error => {
                        console.error('❌ MetaMask connection failed in page context:', error);
                        window.postMessage({
                            type: 'METAMASK_DEBUG_RESPONSE',
                            error: error.message || 'Connection failed'
                        }, '*');
                    });
            })();
        `;

        // Listen for response from page context
        const handleResponse = (event) => {
            if (event.data && event.data.type === 'METAMASK_DEBUG_RESPONSE') {
                window.removeEventListener('message', handleResponse);

                if (event.data.error) {
                    console.error('❌ MetaMask error from page context:', event.data.error);
                    reject(new Error(event.data.error));
                } else {
                    console.log('✅ MetaMask connected from page context:', event.data.result);
                    resolve(event.data.result);
                }
            }
        };

        window.addEventListener('message', handleResponse);

        // Inject the script
        (document.head || document.documentElement).appendChild(script);
        script.remove(); // Clean up

        // Timeout after 10 seconds
        setTimeout(() => {
            window.removeEventListener('message', handleResponse);
            reject(new Error('MetaMask connection timeout'));
        }, 10000);
    });
}

// MetaMask message signing handler for debug script
async function handleMetaMaskSigningInDebugScript(message, address) {
    console.log('✍️ Starting MetaMask message signing from debug script...');

    return new Promise((resolve, reject) => {
        // Create and inject script into page context to access window.ethereum
        const script = document.createElement('script');
        script.textContent = `
            (function() {
                console.log('✍️ Page context script signing message...');
                
                if (typeof window.ethereum === 'undefined') {
                    console.error('❌ MetaMask not found in page context');
                    window.postMessage({
                        type: 'METAMASK_SIGN_RESPONSE',
                        error: 'MetaMask is not installed or not accessible'
                    }, '*');
                    return;
                }
                
                console.log('✅ MetaMask detected, signing message...');
                
                // Sign the message
                window.ethereum.request({
                    method: 'personal_sign',
                    params: ['${message}', '${address}']
                })
                .then(signature => {
                    console.log('✅ Message signed successfully');
                    window.postMessage({
                        type: 'METAMASK_SIGN_RESPONSE',
                        result: { signature }
                    }, '*');
                })
                .catch(error => {
                    console.error('❌ MetaMask signing failed in page context:', error);
                    let errorMessage = error.message || 'Signing failed';
                    if (error.code === 4001) {
                        errorMessage = 'User rejected the signature request';
                    }
                    window.postMessage({
                        type: 'METAMASK_SIGN_RESPONSE',
                        error: errorMessage
                    }, '*');
                });
            })();
        `;

        // Listen for response from page context
        const handleResponse = (event) => {
            if (event.data && event.data.type === 'METAMASK_SIGN_RESPONSE') {
                window.removeEventListener('message', handleResponse);

                if (event.data.error) {
                    console.error('❌ MetaMask signing error from page context:', event.data.error);
                    reject(new Error(event.data.error));
                } else {
                    console.log('✅ MetaMask signing successful from page context:', event.data.result);
                    resolve(event.data.result);
                }
            }
        };

        window.addEventListener('message', handleResponse);

        // Inject the script
        (document.head || document.documentElement).appendChild(script);
        script.remove(); // Clean up

        // Timeout after 30 seconds (signing might take longer)
        setTimeout(() => {
            window.removeEventListener('message', handleResponse);
            reject(new Error('MetaMask signing timeout'));
        }, 30000);
    });
}

// Function to create sparkle effect at a specific element
function createSparkleEffectAtButton(element) {
    const rect = element.getBoundingClientRect();
    const sparkleCount = 6;

    for (let i = 0; i < sparkleCount; i++) {
        const sparkle = document.createElement('div');
        sparkle.textContent = '✨';
        sparkle.style.cssText = `
            position: fixed;
            left: ${rect.left + rect.width / 2}px;
            top: ${rect.top + rect.height / 2}px;
            font-size: 14px;
            pointer-events: none;
            z-index: 10001;
            opacity: 0;
            animation: sparkleRadiate 1s ease-out forwards;
            animation-delay: ${i * 0.1}s;
        `;

        // Set direction for each sparkle
        const angle = (i / sparkleCount) * 360;
        const distance = 30;
        const x = Math.cos(angle * Math.PI / 180) * distance;
        const y = Math.sin(angle * Math.PI / 180) * distance;
        sparkle.style.setProperty('--sparkle-x', `${x}px`);
        sparkle.style.setProperty('--sparkle-y', `${y}px`);

        document.body.appendChild(sparkle);

        setTimeout(() => sparkle.remove(), 1200);
    }
}

// Function to show conversation carousel
function showConversationCarousel() {
    // Get current conversation messages
    const currentMessages = currentConversation ? currentConversation.messages : [];
    
    // Group messages into conversations (could be enhanced with better grouping logic)
    const conversations = [];
    if (currentMessages.length > 0) {
        conversations.push({
            id: currentSessionId,
            title: currentConversation.title || 'Current Conversation',
            messages: currentMessages,
            platform: platform,
            timestamp: currentConversation.created_at
        });
    }
    
    // Add historical conversations
    conversationHistory.forEach(conv => {
        conversations.push({
            id: conv.session_id,
            title: conv.title,
            messages: conv.messages || [],
            platform: conv.platform,
            timestamp: conv.last_updated
        });
    });
    
    // Create carousel UI
    const carousel = document.createElement('div');
    carousel.className = 'contextly-carousel';
    carousel.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        height: 400px;
        background: rgba(20, 20, 20, 0.95);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        z-index: 10000;
        padding: 20px;
        overflow: hidden;
    `;
    
    carousel.innerHTML = `
        <div class="carousel-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="color: #fff; font-size: 18px; font-weight: 600; margin: 0;">
                🔮 Your Conversations (${conversations.length})
            </h3>
            <button class="carousel-close" style="background: none; border: none; color: #999; font-size: 24px; cursor: pointer; padding: 0 8px;">×</button>
        </div>
        
        <div class="carousel-content" style="display: flex; gap: 16px; overflow-x: auto; overflow-y: hidden; padding-bottom: 16px;">
            ${conversations.map((conv, index) => `
                <div class="conversation-card" data-conversation-id="${conv.id}" style="
                    flex: 0 0 280px;
                    background: rgba(40, 40, 40, 0.8);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 16px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                ">
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                        <div>
                            <h4 style="color: #fff; font-size: 14px; font-weight: 500; margin: 0 0 4px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                ${conv.title}
                            </h4>
                            <span style="color: #888; font-size: 12px;">
                                ${conv.platform} • ${formatTimeAgo(conv.timestamp)}
                            </span>
                        </div>
                        <span class="platform-icon" style="font-size: 20px;">
                            ${conv.platform === 'claude' ? '🤖' : conv.platform === 'chatgpt' ? '💬' : '✨'}
                        </span>
                    </div>
                    
                    <div class="card-preview" style="color: #ccc; font-size: 13px; line-height: 1.4; max-height: 100px; overflow: hidden; margin-bottom: 16px;">
                        ${conv.messages.length > 0 ? conv.messages.slice(0, 3).map(msg => 
                            `<p style="margin: 0 0 8px 0; opacity: 0.8;">
                                <strong>${msg.role === 'user' ? '👤' : '🤖'}:</strong> 
                                ${msg.text ? msg.text.substring(0, 100) : ''}${msg.text && msg.text.length > 100 ? '...' : ''}
                            </p>`
                        ).join('') : '<p style="margin: 0; opacity: 0.6;">No messages yet</p>'}
                    </div>
                    
                    <div class="card-stats" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="color: #888; font-size: 12px;">
                            💬 ${conv.messages.length} messages
                        </span>
                        <span style="color: #888; font-size: 12px;">
                            🪙 ${conv.messages.length * 50} tokens
                        </span>
                    </div>
                    
                    <div class="card-actions" style="display: flex; gap: 8px;">
                        <button class="inject-conv" data-id="${conv.id}" style="
                            background: rgba(255, 255, 255, 0.1);
                            color: white;
                            border: 1px solid rgba(255, 255, 255, 0.2);
                            border-radius: 8px;
                            padding: 8px;
                            font-size: 12px;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        ">
                            🚀
                        </button>
                    </div>
                </div>
            `).join('')}
            
            ${conversations.length === 0 ? `
                <div style="flex: 1; display: flex; align-items: center; justify-content: center; color: #666;">
                    <div style="text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 16px;">💬</div>
                        <p>No conversations captured yet</p>
                        <p style="font-size: 12px; opacity: 0.8;">Start chatting to see your conversations here!</p>
                    </div>
                </div>
            ` : ''}
        </div>
        
        <div class="carousel-footer" style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
            <span style="color: #888; font-size: 12px;">
                💡 Tip: Click a conversation to view details
            </span>
            <button class="save-all-btn" style="
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            ">
                💾 Save All to LanceDB
            </button>
        </div>
    `;
    
    document.body.appendChild(carousel);
    
    // Add hover effects
    carousel.querySelectorAll('.conversation-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.3)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = 'none';
        });
    });
    
    // Close button handler
    carousel.querySelector('.carousel-close').addEventListener('click', () => {
        carousel.remove();
    });
    
    
    // Save all button handler
    carousel.querySelector('.save-all-btn').addEventListener('click', async () => {
        const btn = carousel.querySelector('.save-all-btn');
        btn.textContent = '⏳ Saving all...';
        for (const conv of conversations) {
            await saveSpecificConversation(conv);
        }
        btn.textContent = '✅ All saved!';
        showNotification('🎉 All conversations saved to LanceDB!', 'success', 3000);
    });
    
    // Inject conversation handlers
    carousel.querySelectorAll('.inject-conv').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const convId = btn.dataset.id;
            const conv = conversations.find(c => c.id === convId);
            if (conv) {
                injectConversation(conv.id);
                carousel.remove();
            }
        });
    });
}

// Helper function to save a specific conversation
async function saveSpecificConversation(conv) {
    if (!conv.messages || conv.messages.length === 0) return;
    
    const conversationToSave = {
        session_id: conv.id,
        title: conv.title,
        platform: conv.platform,
        messages: conv.messages,
        created_at: conv.timestamp,
        last_updated: new Date().toISOString()
    };
    
    // Use existing save logic
    currentConversation = conversationToSave;
    await saveConversationToBackend();
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    loadUserData();
    // createStatusIndicator(); // Commented out - was covering chat interface

    // Auto-start conversation capture (earn mode is default)
    chrome.storage.local.get(['earnMode'], (result) => {
        if (result.earnMode === false) {
            earnMode = false;
        } else {
            // Default to true if not explicitly set to false
            earnMode = true;
            chrome.storage.local.set({ earnMode: true });
            initializeConversationCapture();
        }
    });
});

// Try immediately
setTimeout(() => {
    // loadUserData();
    injectContextlyButton();
    // createStatusIndicator(); // Commented out - was covering chat interface

    // Auto-start conversation capture (earn mode is default)
    chrome.storage.local.get(['earnMode'], (result) => {
        if (result.earnMode === false) {
            earnMode = false;
        } else {
            // Default to true if not explicitly set to false
            earnMode = true;
            chrome.storage.local.set({ earnMode: true });
            initializeConversationCapture();
        }
    });
}, 1000);

// Try periodically
setInterval(() => {
    if (!document.querySelector('.contextly-debug-btn')) {
        injectContextlyButton();
    }
}, 3000);

// For Gemini, try more aggressively since it's a single-page app
if (platform === 'gemini') {
    console.log('🎯 Setting up Gemini-specific injection...');
    
    // MutationObserver for Gemini
    const geminiObserver = new MutationObserver((mutations) => {
        // Check if Deep Research or Canvas buttons appeared
        const hasActionButtons = Array.from(document.querySelectorAll('button')).some(btn => {
            const text = btn.textContent.trim();
            return text.includes('Deep Research') || text.includes('Canvas');
        });
        
        if (hasActionButtons && !document.querySelector('.contextly-debug-btn')) {
            console.log('🔄 Gemini interface changed, injecting button...');
            injectContextlyButton();
        }
    });
    
    // Observe the entire body for changes
    geminiObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Also use interval as fallback
    const geminiInterval = setInterval(() => {
        const hasButtons = Array.from(document.querySelectorAll('button')).some(btn => 
            btn.textContent.includes('Deep Research') || 
            btn.textContent.includes('Canvas')
        );
        
        if (hasButtons && !document.querySelector('.contextly-debug-btn')) {
            console.log('🔄 Gemini buttons detected, injecting Contextly button...');
            injectContextlyButton();
        }
        
        // Also check if we're on the main chat interface
        const chatWindow = document.querySelector('chat-window');
        if (chatWindow && !document.querySelector('.contextly-debug-btn')) {
            injectContextlyButton();
        }
    }, 1000);
    
    // Stop checking after 30 seconds
    setTimeout(() => clearInterval(geminiInterval), 30000);
}

console.log('🎯 DEBUG: Script setup complete with full functionality!');