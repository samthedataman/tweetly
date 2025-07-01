// background.js - Advanced Background Service Worker with Extensive Logging
console.group('🚀 Contextly.ai Background Service Worker Initialization');
console.log('📅 Start time:', new Date().toISOString());
console.log('🔧 Service Worker State:', self.serviceWorker?.state || 'unknown');
console.log('🌐 Browser:', navigator.userAgent.substring(0, 50) + '...');
console.log('📦 Extension ID:', chrome.runtime.id);
console.log('🔢 Manifest Version:', chrome.runtime.getManifest().manifest_version);
console.groupEnd();

// Initialize state
let userSettings = {
    earnMode: false,
    wallet: null,
    userId: null
};

// Screen capture queue
let captureQueue = [];
let isProcessingQueue = false;

// Initialize on install
chrome.runtime.onInstalled.addListener(async (details) => {
    console.group('🎯 Extension Installation/Update Handler');
    console.log('📋 Installation details:', JSON.stringify(details, null, 2));
    console.log('🔍 Reason:', details.reason);
    console.log('🔢 Previous version:', details.previousVersion || 'N/A');
    
    if (details.reason === 'install') {
        console.log('🆕 Fresh installation detected');
        
        // Set default settings
        const defaultSettings = {
            earnMode: false,
            autoSave: true,
            contextWarnings: true,
            smartTransfer: true
        };
        
        console.log('💾 Setting default settings:', JSON.stringify(defaultSettings, null, 2));
        await chrome.storage.sync.set(defaultSettings);
        console.log('✅ Default settings saved');

        // Create context menus
        console.log('📋 Creating context menus...');
        createContextMenus();
        console.log('✅ Context menus created');

        // Open onboarding
        console.log('🌐 Opening onboarding page...');
        const tab = await chrome.tabs.create({
            url: 'https://contextly.ai/welcome'
        });
        console.log('✅ Onboarding tab created:', tab.id);
    } else if (details.reason === 'update') {
        console.log('🔄 Extension updated from version', details.previousVersion);
    } else if (details.reason === 'chrome_update') {
        console.log('🌐 Chrome browser updated');
    }
    
    console.groupEnd();
});

// Create context menus
function createContextMenus() {
    console.group('📋 Creating Context Menus');
    
    const menus = [
        {
            id: 'contextly-save',
            title: 'Save to Contextly',
            contexts: ['selection']
        },
        {
            id: 'contextly-transfer',
            title: 'Transfer Context Here',
            contexts: ['editable']
        },
        {
            id: 'contextly-search',
            title: 'Search in Contextly',
            contexts: ['selection']
        },
        {
            id: 'contextly-dashboard',
            title: 'Open Contextly Dashboard',
            contexts: ['action']
        }
    ];
    
    menus.forEach((menu, index) => {
        console.log(`📌 Creating menu ${index + 1}/${menus.length}:`, menu.id);
        chrome.contextMenus.create(menu, () => {
            if (chrome.runtime.lastError) {
                console.error(`❌ Failed to create menu '${menu.id}':`, chrome.runtime.lastError);
            } else {
                console.log(`✅ Menu created: ${menu.id}`);
            }
        });
    });
    
    console.groupEnd();
}

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
    console.group('🕹️ Context Menu Click Handler');
    console.log('🆔 Menu ID:', info.menuItemId);
    console.log('📍 Tab info:', {
        id: tab.id,
        url: tab.url,
        title: tab.title,
        active: tab.active
    });
    console.log('📝 Selection text:', info.selectionText || 'None');
    console.log('📋 Full click info:', JSON.stringify(info, null, 2));
    
    switch (info.menuItemId) {
        case 'contextly-save':
            console.log('💾 Handling save selection...');
            handleSaveSelection(info.selectionText, tab);
            break;
        case 'contextly-transfer':
            console.log('🔄 Handling transfer context...');
            handleTransferContext(tab);
            break;
        case 'contextly-search':
            console.log('🔍 Handling search selection...');
            handleSearchSelection(info.selectionText, tab);
            break;
        case 'contextly-dashboard':
            console.log('📊 Opening dashboard...');
            chrome.tabs.create({ url: chrome.runtime.getURL('popup-tab.html') });
            break;
        default:
            console.log('⚠️ Unknown menu item:', info.menuItemId);
    }
    
    console.groupEnd();
});

// Import message protocol (in service worker, we'll inline it)
const MessageProtocol = {
    ACTIONS: {
        WALLET_CONNECT: 'wallet:connect',
        WALLET_DISCONNECT: 'wallet:disconnect',
        WALLET_SIGN: 'wallet:sign',
        WALLET_STATUS: 'wallet:status',
        CONVERSATION_CAPTURE: 'conversation:capture',
        CONVERSATION_SAVE: 'conversation:save',
        CONVERSATION_SEARCH: 'conversation:search',
        CONVERSATION_EXPORT: 'conversation:export',
        CONVERSATION_TRANSFER: 'conversation:transfer',
        JOURNEY_CAPTURE: 'journey:capture',
        JOURNEY_ANALYZE: 'journey:analyze',
        EARNINGS_UPDATE: 'earnings:update',
        EARNINGS_GET: 'earnings:get',
        UI_UPDATE_BADGE: 'ui:updateBadge',
        UI_SHOW_NOTIFICATION: 'ui:showNotification',
        UI_UPDATE_STATS: 'ui:updateStats',
        SYSTEM_HEALTH_CHECK: 'system:healthCheck',
        SYSTEM_ERROR: 'system:error',
        SYSTEM_CONFIG_UPDATE: 'system:configUpdate'
    }
};

// Setup message handlers
const messageHandlers = {
    // Native UI handlers
    'getConnectionStatus': async (message, sender) => {
        const settings = await chrome.storage.sync.get(['earnMode', 'wallet']);
        return {
            connected: !!(settings.wallet && settings.wallet.address),
            earnMode: settings.earnMode || false
        };
    },

    'toggleEarnMode': async (message, sender) => {
        await chrome.storage.sync.set({ earnMode: message.enabled });
        return { success: true };
    },

    'openPopup': async (message, sender) => {
        // Open the extension popup
        chrome.action.openPopup();
        return { success: true };
    },

    'getPreviousConversations': async (message, sender) => {
        const data = await chrome.storage.local.get(['conversations']);
        const conversations = data.conversations || [];
        return conversations.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    },

    'getConversation': async (message, sender) => {
        const data = await chrome.storage.local.get(['conversations']);
        const conversations = data.conversations || [];
        return conversations.find(conv => conv.id === message.conversationId);
    },
    
    // Handler for popup signin request
    'open_popup_for_signin': async (message, sender) => {
        console.log('📱 Opening popup for signin request from content script');
        try {
            await chrome.action.openPopup();
            return { success: true };
        } catch (error) {
            console.error('Failed to open popup:', error);
            // Fallback: open in new tab
            await chrome.tabs.create({
                url: chrome.runtime.getURL('popup/popup.html')
            });
            return { success: true, openedInTab: true };
        }
    },

    [MessageProtocol.ACTIONS.JOURNEY_CAPTURE]: async (message, sender) => {
        const screenshot = await captureVisibleTab(sender.tab);
        return { screenshot };
    },

    [MessageProtocol.ACTIONS.UI_UPDATE_BADGE]: async (message) => {
        updateBadge(message.data);
        return { success: true };
    },

    [MessageProtocol.ACTIONS.JOURNEY_ANALYZE]: async (message) => {
        await processJourneyBatch(message.data.batch);
        return { success: true };
    },

    [MessageProtocol.ACTIONS.WALLET_STATUS]: async () => {
        return { wallet: userSettings.wallet, earnMode: userSettings.earnMode };
    },

    [MessageProtocol.ACTIONS.CONVERSATION_EXPORT]: async (message) => {
        const { format, data } = message.data;
        await handleDataExport(format, data);
        return { success: true };
    },

    [MessageProtocol.ACTIONS.EARNINGS_UPDATE]: async (message) => {
        userSettings.earnings = (userSettings.earnings || 0) + message.data.amount;
        await chrome.storage.sync.set({ earnings: userSettings.earnings });
        updateBadge({ earnings: userSettings.earnings });
        return { earnings: userSettings.earnings };
    },
    
    // Add handler for screenshot capture
    captureTab: async (message, sender) => {
        try {
            const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' });
            return { dataUrl };
        } catch (error) {
            console.error('Screenshot capture error:', error);
            return { error: error.message };
        }
    },

    [MessageProtocol.ACTIONS.UI_SHOW_NOTIFICATION]: async (message) => {
        const { message: text, type } = message.data;
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: 'Contextly.ai',
            message: text,
            priority: type === 'error' ? 2 : 1
        });
        return { success: true };
    },

    // Legacy handlers for backward compatibility
    'captureScreen': async (message, sender) => {
        const screenshot = await captureVisibleTab(sender.tab);
        return { screenshot };
    },

    'downloadData': async (message) => {
        await handleDataExport(message.format);
        return { success: true };
    },

    // Simple wallet connection handler - just stores data from frontend
    'wallet_connected': async (message, sender) => {
        console.log('🔗 Wallet connected notification received');
        
        try {
            const { data } = message;
            console.log('💾 Storing wallet connection data:', data);
            
            // Store wallet data in sync storage
            await chrome.storage.sync.set({ 
                wallet: {
                    address: data.address,
                    chainId: data.chainId,
                    walletType: data.walletType,
                    connected: true
                },
                authToken: data.token
            });
            
            // Update user settings
            userSettings.wallet = {
                address: data.address,
                chainId: data.chainId,
                walletType: data.walletType,
                connected: true
            };
            
            console.log('✅ Wallet connection stored successfully');
            return { success: true };
            
        } catch (error) {
            console.error('❌ Failed to store wallet connection:', error);
            return { success: false, error: error.message };
        }
    },

    'wallet_disconnected': async (message, sender) => {
        console.log('🔌 Wallet disconnected notification received');
        
        try {
            // Clear wallet data
            await chrome.storage.sync.remove(['wallet', 'authToken']);
            userSettings.wallet = null;
            
            console.log('✅ Wallet data cleared');
            return { success: true };
            
        } catch (error) {
            console.error('❌ Failed to clear wallet data:', error);
            return { success: false, error: error.message };
        }
    }
};

// Message listener with unified protocol
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.group('📨 Message Received in Background');
    const timestamp = new Date().toISOString();
    console.log('⏰ Timestamp:', timestamp);
    console.log('🎯 Action:', request.action);
    console.log('📦 Request data:', JSON.stringify(request.data || {}, null, 2));
    console.log('📤 Sender info:', {
        tab: sender.tab ? {
            id: sender.tab.id,
            url: sender.tab.url,
            title: sender.tab.title
        } : 'No tab (extension origin)',
        frameId: sender.frameId,
        id: sender.id,
        origin: sender.origin
    });
    
    // Handle async responses
    (async () => {
        const startTime = performance.now();
        try {
            // Wallet connections are now handled directly by popup, no background involvement needed
            {
                // Handle other actions through messageHandlers
                const handler = messageHandlers[request.action];
                if (handler) {
                    console.log(`✅ Handler found for action: ${request.action}`);
                    console.log('🔄 Executing handler...');
                    const result = await handler(request, sender);
                    const endTime = performance.now();
                    console.log(`✅ Handler completed in ${(endTime - startTime).toFixed(2)}ms`);
                    console.log('📤 Response:', JSON.stringify(result, null, 2));
                    sendResponse(result);
                } else {
                    console.log(`❌ No handler found for action: ${request.action}`);
                    console.log('Available handlers:', Object.keys(messageHandlers));
                    sendResponse({ error: `Unknown action: ${request.action}` });
                }
            }
        } catch (error) {
            console.error('❌ Background script error:', error);
            console.error('Error stack:', error.stack);
            sendResponse({ error: error.message });
        }
        console.groupEnd();
    })();

    return true; // Keep channel open for async response
});

// Wallet connections are now handled directly in popup using chrome.scripting.executeScript
// No background script involvement needed - much simpler and more reliable!

// Message signing is also handled directly in popup using chrome.scripting.executeScript
// No complex background logic needed!

// Capture visible tab
async function captureVisibleTab(tab) {
    console.group('📸 Capturing Visible Tab');
    const startTime = performance.now();
    
    console.log('📍 Tab details:', {
        id: tab.id,
        url: tab.url,
        title: tab.title,
        windowId: tab.windowId,
        active: tab.active
    });
    
    try {
        // Check if we have permission
        console.log('🔐 Checking permissions...');
        const hasPermission = await chrome.permissions.contains({
            permissions: ['activeTab'],
            origins: [tab.url]
        });
        console.log('Permission status:', hasPermission ? '✅ Granted' : '❌ Denied');

        if (!hasPermission) {
            console.warn('⚠️ No permission to capture tab:', tab.url);
            console.groupEnd();
            return null;
        }

        // Capture the visible area
        console.log('📷 Capturing visible area...');
        const captureOptions = {
            format: 'jpeg',
            quality: 85
        };
        console.log('Capture options:', captureOptions);
        
        const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, captureOptions);
        console.log('✅ Screenshot captured');
        console.log('- Original size:', (dataUrl.length / 1024).toFixed(2) + ' KB');

        // Compress if needed
        console.log('🗜️ Compressing image...');
        const compressed = await compressImage(dataUrl);
        console.log('✅ Image compressed');
        console.log('- Compressed size:', (compressed.length / 1024).toFixed(2) + ' KB');
        console.log('- Compression ratio:', ((1 - compressed.length / dataUrl.length) * 100).toFixed(1) + '%');

        // Add to capture queue
        const queueItem = {
            screenshot: compressed,
            url: tab.url,
            title: tab.title,
            timestamp: Date.now(),
            tabId: tab.id
        };
        
        captureQueue.push(queueItem);
        console.log('📦 Added to capture queue');
        console.log('- Queue length:', captureQueue.length);
        console.log('- Queue item:', { ...queueItem, screenshot: '[DATA]' });

        // Process queue if not already processing
        if (!isProcessingQueue && captureQueue.length >= 5) {
            console.log('🔄 Queue threshold reached, triggering processing...');
            processScreenCaptureQueue();
        } else {
            console.log('🕑 Queue not ready for processing');
            console.log('- Is processing:', isProcessingQueue);
            console.log('- Queue length:', captureQueue.length);
        }

        const endTime = performance.now();
        console.log(`⏱️ Total capture time: ${(endTime - startTime).toFixed(2)}ms`);
        console.groupEnd();
        return compressed;

    } catch (error) {
        console.error('❌ Screen capture error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        console.groupEnd();
        return null;
    }
}

// Compress image to reduce size
async function compressImage(dataUrl) {
    console.group('🗜️ Image Compression');
    const startTime = performance.now();
    console.log('Input data URL length:', (dataUrl.length / 1024).toFixed(2) + ' KB');
    
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
            console.log('🇼️ Original image dimensions:', {
                width: img.width,
                height: img.height,
                aspectRatio: (img.width / img.height).toFixed(2)
            });
            
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            // Calculate new dimensions (max 1280px wide)
            const maxWidth = 1280;
            const scale = Math.min(1, maxWidth / img.width);
            console.log('📏 Scaling calculation:', {
                maxWidth: maxWidth,
                originalWidth: img.width,
                scale: scale.toFixed(3),
                needsScaling: scale < 1
            });

            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            console.log('🌍 New dimensions:', {
                width: canvas.width,
                height: canvas.height
            });

            // Draw and compress
            console.log('🎨 Drawing scaled image to canvas...');
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            // Convert to blob with compression
            const quality = 0.8;
            console.log('📦 Converting to JPEG blob with quality:', quality);
            canvas.toBlob((blob) => {
                console.log('🎯 Blob created:', {
                    size: (blob.size / 1024).toFixed(2) + ' KB',
                    type: blob.type
                });
                
                const reader = new FileReader();
                reader.onloadend = () => {
                    const endTime = performance.now();
                    const outputLength = reader.result.length;
                    console.log('✅ Compression complete:', {
                        outputSize: (outputLength / 1024).toFixed(2) + ' KB',
                        compressionRatio: ((1 - outputLength / dataUrl.length) * 100).toFixed(1) + '%',
                        processingTime: (endTime - startTime).toFixed(2) + 'ms'
                    });
                    console.groupEnd();
                    resolve(reader.result);
                };
                reader.readAsDataURL(blob);
            }, 'image/jpeg', quality);
        };
        
        img.onerror = (error) => {
            console.error('❌ Image load error:', error);
            console.groupEnd();
            resolve(dataUrl); // Return original on error
        };
        
        img.src = dataUrl;
    });
}

// Process screen capture queue
async function processScreenCaptureQueue() {
    console.group('🔄 Processing Screen Capture Queue');
    console.log('📈 Queue status:', {
        isProcessing: isProcessingQueue,
        queueLength: captureQueue.length,
        timestamp: new Date().toISOString()
    });
    
    if (isProcessingQueue) {
        console.log('⏸️ Already processing, skipping...');
        console.groupEnd();
        return;
    }
    
    if (captureQueue.length === 0) {
        console.log('📦 Queue is empty, nothing to process');
        console.groupEnd();
        return;
    }

    isProcessingQueue = true;
    const startTime = performance.now();

    try {
        // Take batch of 5 screenshots
        const batchSize = Math.min(5, captureQueue.length);
        console.log(`📦 Taking batch of ${batchSize} screenshots from queue`);
        const batch = captureQueue.splice(0, batchSize);
        
        console.log('📊 Batch details:', batch.map(item => ({
            url: item.url,
            title: item.title,
            timestamp: new Date(item.timestamp).toISOString(),
            tabId: item.tabId,
            screenshotSize: (item.screenshot.length / 1024).toFixed(2) + ' KB'
        })));

        // Send to content script for processing
        console.log('🔍 Finding active tab...');
        const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (activeTab) {
            console.log('📤 Sending batch to content script...');
            console.log('Active tab:', {
                id: activeTab.id,
                url: activeTab.url,
                title: activeTab.title
            });
            
            await chrome.tabs.sendMessage(activeTab.id, {
                action: 'processScreenshots',
                batch: batch
            });
            console.log('✅ Batch sent to content script');
        } else {
            console.log('⚠️ No active tab found');
        }

        // Store locally as backup
        console.log('💾 Storing screenshots locally as backup...');
        await storeScreenshotsLocally(batch);
        console.log('✅ Screenshots stored locally');

    } catch (error) {
        console.error('❌ Queue processing error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    } finally {
        isProcessingQueue = false;
        const endTime = performance.now();
        console.log(`⏱️ Processing completed in ${(endTime - startTime).toFixed(2)}ms`);
        console.log('📦 Remaining queue length:', captureQueue.length);

        // Process remaining if any
        if (captureQueue.length >= 5) {
            console.log('🔄 More items in queue, scheduling next batch processing in 1 second...');
            setTimeout(() => processScreenCaptureQueue(), 1000);
        }
        
        console.groupEnd();
    }
}

// Store screenshots locally
async function storeScreenshotsLocally(batch) {
    console.group('💾 Storing Screenshots Locally');
    const startTime = performance.now();
    
    try {
        console.log('📦 Batch size:', batch.length);
        console.log('🗺️ Batch items:', batch.map(item => ({
            url: item.url,
            title: item.title,
            timestamp: new Date(item.timestamp).toISOString()
        })));
        
        // Get existing screenshots
        console.log('📂 Loading existing screenshots...');
        const result = await chrome.storage.local.get(['screenshots']);
        const screenshots = result.screenshots || [];
        console.log('Existing screenshots count:', screenshots.length);

        // Add new batch
        console.log('➕ Adding new batch (metadata only, no image data)...');
        const metadataItems = batch.map(item => ({
            ...item,
            screenshot: null // Don't store actual image data locally
        }));
        screenshots.push(...metadataItems);
        console.log('Total screenshots after addition:', screenshots.length);

        // Keep only last 100 entries
        const originalLength = screenshots.length;
        if (screenshots.length > 100) {
            const removed = screenshots.length - 100;
            screenshots.splice(0, removed);
            console.log(`🗑️ Removed ${removed} old entries (keeping last 100)`);
        }

        // Save metadata
        console.log('💾 Saving screenshot metadata...');
        await chrome.storage.local.set({ screenshots });
        
        // Verify storage
        const usage = await chrome.storage.local.getBytesInUse(['screenshots']);
        console.log('📈 Storage usage for screenshots:', (usage / 1024).toFixed(2) + ' KB');
        
        const endTime = performance.now();
        console.log(`✅ Screenshots stored successfully in ${(endTime - startTime).toFixed(2)}ms`);

    } catch (error) {
        console.error('❌ Local storage error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    }
    
    console.groupEnd();
}

// Update extension badge
function updateBadge(data) {
    console.group('🎯 Update Extension Badge');
    console.log('📋 Badge data:', data);
    
    if (data.contextUsage > 80) {
        const badgeText = `${data.contextUsage}%`;
        console.log('⚠️ High context usage detected');
        console.log('Badge text:', badgeText);
        console.log('Badge color: Red (#ef4444)');
        chrome.action.setBadgeText({ text: badgeText });
        chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
    } else if (data.earnMode && data.earnings > 0) {
        const badgeText = `₳${data.earnings.toFixed(1)}`;
        console.log('💰 Earn mode with earnings');
        console.log('Badge text:', badgeText);
        console.log('Badge color: Green (#10b981)');
        chrome.action.setBadgeText({ text: badgeText });
        chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
    } else {
        console.log('🔄 Clearing badge');
        chrome.action.setBadgeText({ text: '' });
    }
    
    console.groupEnd();
}

// Handle save selection
async function handleSaveSelection(text, tab) {
    try {
        // Send to content script
        await chrome.tabs.sendMessage(tab.id, {
            action: 'saveSelection',
            text: text,
            context: {
                url: tab.url,
                title: tab.title,
                timestamp: Date.now()
            }
        });

        // Show notification
        await chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: 'Contextly.ai',
            message: 'Selection saved successfully!'
        });

    } catch (error) {
        console.error('Save selection error:', error);
    }
}

// Handle transfer context
async function handleTransferContext(tab) {
    try {
        // Get stored context
        const result = await chrome.storage.local.get(['lastContext']);

        if (result.lastContext) {
            // Send to content script to paste
            await chrome.tabs.sendMessage(tab.id, {
                action: 'pasteContext',
                context: result.lastContext
            });
        } else {
            // No context available
            await chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon128.png',
                title: 'Contextly.ai',
                message: 'No context available to transfer'
            });
        }

    } catch (error) {
        console.error('Transfer context error:', error);
    }
}

// Handle search selection
async function handleSearchSelection(text, tab) {
    try {
        // Open popup with search query
        await chrome.action.openPopup();

        // Send search query to popup
        setTimeout(() => {
            chrome.runtime.sendMessage({
                action: 'performSearch',
                query: text
            });
        }, 100);

    } catch (error) {
        // Fallback: open in new tab
        chrome.tabs.create({
            url: `https://contextly.ai/search?q=${encodeURIComponent(text)}`
        });
    }
}

// Handle data export
async function handleDataExport(format, specificData = null) {
    console.group('📤 Data Export Handler');
    console.log('📋 Export format:', format);
    console.log('📅 Export timestamp:', new Date().toISOString());
    const startTime = performance.now();
    
    try {
        // Get all stored data
        console.log('📂 Loading data for export...');
        const data = specificData || await chrome.storage.local.get(null);
        const dataKeys = Object.keys(data);
        console.log('📑 Data keys found:', dataKeys);
        console.log('📊 Data sizes:', dataKeys.reduce((acc, key) => {
            const size = JSON.stringify(data[key]).length;
            acc[key] = (size / 1024).toFixed(2) + ' KB';
            return acc;
        }, {}));

        let exportData;
        let filename;
        let mimeType;

        console.log(`🔄 Converting to ${format.toUpperCase()} format...`);
        
        switch (format) {
            case 'json':
                exportData = JSON.stringify(data, null, 2);
                filename = `contextly_export_${Date.now()}.json`;
                mimeType = 'application/json';
                console.log('📝 JSON export details:', {
                    totalKeys: dataKeys.length,
                    stringLength: exportData.length,
                    sizeKB: (exportData.length / 1024).toFixed(2)
                });
                break;

            case 'csv':
                exportData = await convertToCSV(data);
                filename = `contextly_export_${Date.now()}.csv`;
                mimeType = 'text/csv';
                console.log('📈 CSV export details:', {
                    rows: exportData.split('\n').length,
                    sizeKB: (exportData.length / 1024).toFixed(2)
                });
                break;

            case 'markdown':
                exportData = await convertToMarkdown(data);
                filename = `contextly_export_${Date.now()}.md`;
                mimeType = 'text/markdown';
                console.log('📝 Markdown export details:', {
                    lines: exportData.split('\n').length,
                    sizeKB: (exportData.length / 1024).toFixed(2)
                });
                break;
                
            default:
                console.error('❌ Unknown export format:', format);
                console.groupEnd();
                return;
        }

        // Create blob and download
        console.log('🔗 Creating blob...');
        const blob = new Blob([exportData], { type: mimeType });
        console.log('Blob details:', {
            size: (blob.size / 1024).toFixed(2) + ' KB',
            type: blob.type
        });
        
        const url = URL.createObjectURL(blob);
        console.log('🌐 Object URL created:', url);

        console.log('📥 Initiating download...');
        const downloadId = await chrome.downloads.download({
            url: url,
            filename: filename,
            saveAs: true
        });
        console.log('✅ Download initiated with ID:', downloadId);
        console.log('📄 Filename:', filename);

        // Clean up
        setTimeout(() => {
            URL.revokeObjectURL(url);
            console.log('🧽 Object URL revoked');
        }, 1000);
        
        const endTime = performance.now();
        console.log(`✅ Export completed in ${(endTime - startTime).toFixed(2)}ms`);

    } catch (error) {
        console.error('❌ Export error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        
        // Show user notification
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: 'Export Failed',
            message: `Failed to export data: ${error.message}`
        });
    }
    
    console.groupEnd();
}

// Convert data to CSV
async function convertToCSV(data) {
    const conversations = data.conversations || [];
    const headers = ['Platform', 'Role', 'Message', 'Timestamp', 'Session ID'];

    const rows = conversations.flatMap(conv =>
        conv.messages.map(msg => [
            conv.platform,
            msg.role,
            `"${msg.text.replace(/"/g, '""')}"`,
            new Date(msg.timestamp).toISOString(),
            conv.session_id
        ])
    );

    return [headers, ...rows].map(row => row.join(',')).join('\n');
}

// Convert data to Markdown
async function convertToMarkdown(data) {
    const conversations = data.conversations || [];
    let markdown = '# Contextly.ai Export\n\n';

    markdown += `Export Date: ${new Date().toISOString()}\n\n`;
    markdown += `Total Conversations: ${conversations.length}\n\n`;

    conversations.forEach((conv, i) => {
        markdown += `## Conversation ${i + 1} - ${conv.platform}\n\n`;
        markdown += `**Session ID**: ${conv.session_id}\n\n`;
        markdown += `**Started**: ${new Date(conv.startTime).toLocaleString()}\n\n`;

        conv.messages.forEach(msg => {
            markdown += `**${msg.role}**: ${msg.text}\n\n`;
        });

        markdown += '---\n\n';
    });

    return markdown;
}

// Web navigation tracking (for journey analysis)
chrome.webNavigation.onCompleted.addListener(async (details) => {
    console.group('🌐 Web Navigation Completed');
    console.log('📋 Navigation details:', {
        url: details.url,
        tabId: details.tabId,
        frameId: details.frameId,
        processId: details.processId,
        transitionType: details.transitionType,
        transitionQualifiers: details.transitionQualifiers,
        timeStamp: new Date(details.timeStamp).toISOString()
    });
    
    if (details.frameId !== 0) {
        console.log('🖼️ Ignoring non-main frame navigation');
        console.groupEnd();
        return;
    }
    
    // Check if on supported AI platform
    const supportedDomains = [
        'claude.ai',
        'chat.openai.com',
        'chatgpt.com',
        'gemini.google.com',
        'aistudio.google.com'
    ];
    
    const isSupported = supportedDomains.some(domain => details.url.includes(domain));
    
    if (isSupported) {
        // Show active badge
        chrome.action.setBadgeText({ text: '●', tabId: details.tabId });
        chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId: details.tabId });
        console.log(`✅ Contextly active on supported platform`);
    } else {
        // Clear badge
        chrome.action.setBadgeText({ text: '', tabId: details.tabId });
    }

    // Check if earn mode is enabled
    console.log('💰 Checking earn mode status...');
    const settings = await chrome.storage.sync.get(['earnMode']);
    console.log('Earn mode:', settings.earnMode ? '✅ Enabled' : '❌ Disabled');
    
    if (!settings.earnMode) {
        console.log('🔓 Earn mode disabled, skipping journey tracking');
        console.groupEnd();
        return;
    }

    // Check if URL should be tracked
    console.log('🔍 Checking if URL should be tracked...');
    const shouldTrack = shouldTrackUrl(details.url);
    console.log('Should track:', shouldTrack ? '✅ Yes' : '❌ No');
    
    if (shouldTrack) {
        console.log('📦 Adding to journey...');
        // Add to journey
        await addToJourney({
            url: details.url,
            timestamp: Date.now(),
            tabId: details.tabId,
            transitionType: details.transitionType
        });
        console.log('✅ Added to journey');
    }
    
    console.groupEnd();
});

// Check if URL should be tracked
function shouldTrackUrl(url) {
    // Skip certain URLs
    const skipPatterns = [
        /^chrome:\/\//,
        /^chrome-extension:\/\//,
        /^about:/,
        /^data:/,
        /^file:/,
        /^javascript:/
    ];

    return !skipPatterns.some(pattern => pattern.test(url));
}

// Add to journey tracking
async function addToJourney(navigation) {
    console.group('🛤️ Adding to Journey');
    console.log('📋 Navigation to add:', navigation);
    const startTime = performance.now();
    
    try {
        // Get current journey
        console.log('📂 Loading current journey...');
        const result = await chrome.storage.local.get(['currentJourney']);
        let journey = result.currentJourney || null;
        
        if (!journey) {
            console.log('🆕 No current journey, creating new one...');
            journey = {
                id: generateJourneyId(),
                startTime: Date.now(),
                pages: []
            };
            console.log('New journey created:', {
                id: journey.id,
                startTime: new Date(journey.startTime).toISOString()
            });
        } else {
            console.log('📦 Existing journey found:', {
                id: journey.id,
                pageCount: journey.pages.length,
                startTime: new Date(journey.startTime).toISOString(),
                duration: ((Date.now() - journey.startTime) / 1000 / 60).toFixed(2) + ' minutes'
            });
        }

        // Add navigation
        console.log('➕ Adding navigation to journey...');
        journey.pages.push(navigation);
        console.log('Journey now has', journey.pages.length, 'pages');

        // Check if journey should be closed (30 min inactivity)
        const inactivityThreshold = 30 * 60 * 1000; // 30 minutes
        if (journey.pages.length >= 2) {
            const lastPage = journey.pages[journey.pages.length - 2];
            const timeSinceLastPage = navigation.timestamp - lastPage.timestamp;
            console.log('⏱️ Time since last page:', (timeSinceLastPage / 1000 / 60).toFixed(2) + ' minutes');
            
            if (timeSinceLastPage > inactivityThreshold) {
                console.log('🕑 Inactivity threshold exceeded, closing journey...');
                // Close current journey and start new one
                await saveJourney(journey);
                
                console.log('🆕 Starting new journey after inactivity...');
                journey = {
                    id: generateJourneyId(),
                    startTime: Date.now(),
                    pages: [navigation]
                };
                console.log('New journey created:', journey.id);
            }
        }

        // Save current journey
        console.log('💾 Saving current journey state...');
        await chrome.storage.local.set({ currentJourney: journey });
        
        const endTime = performance.now();
        console.log(`✅ Journey updated successfully in ${(endTime - startTime).toFixed(2)}ms`);

    } catch (error) {
        console.error('❌ Journey tracking error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    }
    
    console.groupEnd();
}

// Generate journey ID
function generateJourneyId() {
    return `journey_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Save completed journey
async function saveJourney(journey) {
    console.group('💾 Saving Completed Journey');
    console.log('🏁 Journey to save:', {
        id: journey.id,
        pageCount: journey.pages.length,
        startTime: new Date(journey.startTime).toISOString()
    });
    const startTime = performance.now();
    
    try {
        // Get existing journeys
        console.log('📂 Loading existing journeys...');
        const result = await chrome.storage.local.get(['journeys']);
        const journeys = result.journeys || [];
        console.log('Existing journeys count:', journeys.length);

        // Add metadata
        console.log('📝 Adding journey metadata...');
        journey.endTime = Date.now();
        journey.duration = journey.endTime - journey.startTime;
        journey.pageCount = journey.pages.length;
        
        const metadata = {
            endTime: new Date(journey.endTime).toISOString(),
            duration: (journey.duration / 1000 / 60).toFixed(2) + ' minutes',
            pageCount: journey.pageCount,
            avgTimePerPage: (journey.duration / journey.pageCount / 1000).toFixed(2) + ' seconds'
        };
        console.log('Journey metadata:', metadata);

        // Add to list
        console.log('➕ Adding journey to storage list...');
        journeys.push(journey);

        // Keep only last 50 journeys
        const originalCount = journeys.length;
        if (journeys.length > 50) {
            const removed = journeys.length - 50;
            journeys.splice(0, removed);
            console.log(`🗑️ Removed ${removed} old journeys (keeping last 50)`);
        }

        // Save
        console.log('💾 Saving journeys to local storage...');
        await chrome.storage.local.set({ journeys });
        console.log('✅ Journeys saved successfully');

        // Send to server if earn mode
        console.log('💰 Checking earn mode for server submission...');
        const settings = await chrome.storage.sync.get(['earnMode']);
        console.log('Earn mode:', settings.earnMode ? '✅ Enabled' : '❌ Disabled');
        
        if (settings.earnMode) {
            console.log('📤 Sending journey to server...');
            await sendJourneyToServer(journey);
        }
        
        const endTime = performance.now();
        console.log(`✅ Journey saved in ${(endTime - startTime).toFixed(2)}ms`);

    } catch (error) {
        console.error('❌ Save journey error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    }
    
    console.groupEnd();
}

// Send journey to server
async function sendJourneyToServer(journey) {
    console.group('📤 Send Journey to Server');
    const startTime = performance.now();
    
    try {
        // Get user wallet
        console.log('🔐 Getting user wallet...');
        const settings = await chrome.storage.sync.get(['wallet']);
        
        if (!settings.wallet) {
            console.log('❌ No wallet found, skipping submission');
            console.groupEnd();
            return;
        }
        
        console.log('💳 Wallet found:', {
            address: `${settings.wallet.address.substring(0, 8)}...`,
            hasWallet: true
        });

        // Calculate earnings
        const earned = calculateJourneyEarnings(journey);
        
        // Prepare payload
        const payload = {
            journey: journey,
            earned: earned
        };
        
        console.log('📦 Request payload:', {
            journeyId: journey.id,
            pageCount: journey.pageCount,
            duration: (journey.duration / 1000 / 60).toFixed(2) + ' minutes',
            earned: earned.toFixed(4) + ' CTXT',
            payloadSize: (JSON.stringify(payload).length / 1024).toFixed(2) + ' KB'
        });

        // Send to API
        const apiUrl = 'http://localhost:8000/v1/journeys/analyze';
        console.log('🌐 API endpoint:', apiUrl);
        console.log('📡 Sending journey data...');
        
        // Get auth token from storage
        const authData = await chrome.storage.local.get('authToken');
        const authToken = authData.authToken;
        
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add authorization if we have a token
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else {
            // Fallback to wallet address header for backwards compatibility
            headers['X-Wallet-Address'] = settings.wallet.address;
        }
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        
        console.log('📨 Response received:', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok
        });

        if (response.ok) {
            const responseData = await response.json();
            console.log('✅ Journey submitted successfully');
            console.log('📤 Server response:', responseData);
        } else {
            console.error('❌ Journey submission failed:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
        }
        
        const endTime = performance.now();
        console.log(`⏱️ Journey submission time: ${(endTime - startTime).toFixed(2)}ms`);

    } catch (error) {
        console.error('❌ Journey submission error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    }
    
    console.groupEnd();
}

// Calculate journey earnings
function calculateJourneyEarnings(journey) {
    console.group('💰 Calculate Journey Earnings');
    console.log('🛤️ Journey details:', {
        id: journey.id,
        pageCount: journey.pageCount,
        duration: (journey.duration / 1000 / 60).toFixed(2) + ' minutes'
    });
    
    const baseRate = 0.01; // CTXT per journey
    const pageBonus = journey.pageCount * 0.001;
    const durationBonus = Math.min(journey.duration / (60 * 60 * 1000), 1) * 0.005; // Max 1 hour
    
    const totalEarnings = baseRate + pageBonus + durationBonus;
    
    console.log('📊 Earnings calculation:');
    console.log('- Base rate:', baseRate + ' CTXT');
    console.log('- Page bonus:', pageBonus.toFixed(4) + ' CTXT', `(${journey.pageCount} pages × 0.001)`);
    console.log('- Duration bonus:', durationBonus.toFixed(4) + ' CTXT', '(max 0.005 for 1 hour)');
    console.log('- Total earnings:', totalEarnings.toFixed(4) + ' CTXT');
    
    console.groupEnd();
    return totalEarnings;
}

// Periodic tasks
const periodicTaskInterval = setInterval(async () => {
    console.group('⏰ Periodic Task Execution');
    console.log('📅 Timestamp:', new Date().toISOString());
    const startTime = performance.now();
    
    // Check for pending captures
    console.log('📸 Checking capture queue...');
    console.log('Queue length:', captureQueue.length);
    if (captureQueue.length >= 5) {
        console.log('🔄 Queue threshold met, processing captures...');
        await processScreenCaptureQueue();
    } else {
        console.log('⏸️ Queue below threshold, skipping processing');
    }

    // Update user stats
    console.log('📊 Checking for stats update...');
    const settings = await chrome.storage.sync.get(['earnMode', 'wallet']);
    console.log('Settings:', {
        earnMode: settings.earnMode ? '✅ Enabled' : '❌ Disabled',
        walletConnected: !!settings.wallet,
        walletAddress: settings.wallet?.address ? `${settings.wallet.address.substring(0, 8)}...` : 'None'
    });
    
    if (settings.earnMode && settings.wallet) {
        console.log('📡 Fetching latest earnings...');
        // Fetch latest earnings
        try {
            const apiUrl = `http://localhost:8000/v1/stats/${settings.wallet.address}`;
            console.log('API URL:', apiUrl);
            
            // Get auth token from storage
            const authData = await chrome.storage.local.get('authToken');
            const authToken = authData.authToken;
            
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Add authorization if we have a token
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            } else {
                // Fallback to wallet address header for backwards compatibility
                headers['X-Wallet-Address'] = settings.wallet.address;
            }
            
            const response = await fetch(apiUrl, {
                headers: headers
            });
            console.log('Response status:', response.status, response.statusText);
            
            if (response.ok) {
                const stats = await response.json();
                console.log('📊 Stats received:', stats);
                userSettings = { ...userSettings, ...stats };
                console.log('✅ User settings updated');
            } else {
                console.log('⚠️ Failed to fetch stats:', response.status);
            }
        } catch (error) {
            console.error('❌ Stats update error:', error);
            console.error('Error details:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });
        }
    } else {
        console.log('🔓 Skipping stats update (earn mode disabled or no wallet)');
    }
    
    const endTime = performance.now();
    console.log(`⏱️ Periodic tasks completed in ${(endTime - startTime).toFixed(2)}ms`);
    console.groupEnd();
}, 60000); // Every minute

console.log('⏰ Periodic task interval started (60 seconds)');

// Final initialization summary
console.group('🎆 Contextly.ai Background Service Summary');
console.log('✅ Service Worker Status: Ready');
console.log('📦 Message Handlers Registered:', Object.keys(messageHandlers).length);
console.log('📋 Available Actions:', Object.keys(messageHandlers));
console.log('🕑 Periodic Tasks: Running (60s interval)');
console.log('🌐 Navigation Tracking: Active');
console.log('📸 Screen Capture Queue: Initialized');
console.log('📡 API Endpoint:', 'http://localhost:8000');
console.log('🔐 Permissions:', [
    'storage',
    'activeTab', 
    'tabs',
    'contextMenus',
    'downloads',
    'webNavigation',
    'notifications',
    'scripting'
]);
console.log('🎉 Background service fully operational!');
console.groupEnd();

// Add performance monitoring
if (self.performance && self.performance.memory) {
    setInterval(() => {
        console.group('📊 Performance Metrics');
        console.log('🧮 Memory Usage:', {
            usedJSHeapSize: (performance.memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB',
            totalJSHeapSize: (performance.memory.totalJSHeapSize / 1048576).toFixed(2) + ' MB',
            jsHeapSizeLimit: (performance.memory.jsHeapSizeLimit / 1048576).toFixed(2) + ' MB'
        });
        console.log('📦 Queue Status:', {
            captureQueueLength: captureQueue.length,
            isProcessingQueue: isProcessingQueue
        });
        console.groupEnd();
    }, 300000); // Every 5 minutes
}