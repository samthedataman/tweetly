// messageProtocol.js - Unified message passing protocol for Contextly

class MessageProtocol {
    static ACTIONS = {
        // Wallet operations
        WALLET_CONNECT: 'wallet:connect',
        WALLET_DISCONNECT: 'wallet:disconnect',
        WALLET_SIGN: 'wallet:sign',
        WALLET_STATUS: 'wallet:status',
        
        // Conversation operations
        CONVERSATION_CAPTURE: 'conversation:capture',
        CONVERSATION_SAVE: 'conversation:save',
        CONVERSATION_SEARCH: 'conversation:search',
        CONVERSATION_EXPORT: 'conversation:export',
        CONVERSATION_TRANSFER: 'conversation:transfer',
        
        // Journey operations
        JOURNEY_CAPTURE: 'journey:capture',
        JOURNEY_ANALYZE: 'journey:analyze',
        
        // Earnings operations
        EARNINGS_UPDATE: 'earnings:update',
        EARNINGS_GET: 'earnings:get',
        
        // UI operations
        UI_UPDATE_BADGE: 'ui:updateBadge',
        UI_SHOW_NOTIFICATION: 'ui:showNotification',
        UI_UPDATE_STATS: 'ui:updateStats',
        
        // System operations
        SYSTEM_HEALTH_CHECK: 'system:healthCheck',
        SYSTEM_ERROR: 'system:error',
        SYSTEM_CONFIG_UPDATE: 'system:configUpdate'
    };

    static createMessage(action, data = {}, metadata = {}) {
        return {
            id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
            action: action,
            data: data,
            metadata: {
                timestamp: Date.now(),
                source: this.getSource(),
                ...metadata
            }
        };
    }

    static createResponse(originalMessage, data = {}, error = null) {
        return {
            id: `res_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
            requestId: originalMessage.id,
            action: originalMessage.action,
            success: !error,
            data: data,
            error: error ? {
                message: error.message || error,
                code: error.code || 'UNKNOWN_ERROR',
                stack: error.stack
            } : null,
            metadata: {
                timestamp: Date.now(),
                source: this.getSource(),
                responseTime: Date.now() - originalMessage.metadata.timestamp
            }
        };
    }

    static getSource() {
        if (typeof chrome !== 'undefined' && chrome.runtime) {
            if (chrome.runtime.getManifest) {
                // We're in extension context
                if (window.location.protocol === 'chrome-extension:') {
                    // Background or popup
                    return window.location.pathname.includes('popup') ? 'popup' : 'background';
                } else {
                    // Content script
                    return 'content';
                }
            }
        }
        return 'unknown';
    }

    static async sendMessage(message) {
        return new Promise((resolve, reject) => {
            if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
                chrome.runtime.sendMessage(message, (response) => {
                    if (chrome.runtime.lastError) {
                        reject(new Error(chrome.runtime.lastError.message));
                    } else if (response && response.error) {
                        reject(new Error(response.error.message));
                    } else {
                        resolve(response);
                    }
                });
            } else {
                reject(new Error('Chrome runtime not available'));
            }
        });
    }

    static async sendToTab(tabId, message) {
        return new Promise((resolve, reject) => {
            if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.sendMessage) {
                chrome.tabs.sendMessage(tabId, message, (response) => {
                    if (chrome.runtime.lastError) {
                        reject(new Error(chrome.runtime.lastError.message));
                    } else if (response && response.error) {
                        reject(new Error(response.error.message));
                    } else {
                        resolve(response);
                    }
                });
            } else {
                reject(new Error('Chrome tabs API not available'));
            }
        });
    }

    static setupListener(handlers = {}) {
        if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
            chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
                // Validate message format
                if (!message || !message.action) {
                    sendResponse(this.createResponse(message, null, new Error('Invalid message format')));
                    return true;
                }

                // Find handler for action
                const handler = handlers[message.action] || handlers['*'];
                
                if (handler) {
                    // Execute handler
                    Promise.resolve(handler(message, sender))
                        .then(result => {
                            sendResponse(this.createResponse(message, result));
                        })
                        .catch(error => {
                            console.error(`Error handling ${message.action}:`, error);
                            sendResponse(this.createResponse(message, null, error));
                        });
                } else {
                    sendResponse(this.createResponse(message, null, new Error(`No handler for action: ${message.action}`)));
                }

                // Return true to indicate async response
                return true;
            });
        }
    }

    static async request(action, data = {}, options = {}) {
        const message = this.createMessage(action, data);
        
        try {
            const response = await this.sendMessage(message);
            
            if (!response.success) {
                throw new Error(response.error?.message || 'Request failed');
            }
            
            return response.data;
        } catch (error) {
            if (options.fallback) {
                return options.fallback;
            }
            throw error;
        }
    }

    static async requestWithRetry(action, data = {}, options = {}) {
        const maxRetries = options.maxRetries || 3;
        const retryDelay = options.retryDelay || 1000;
        
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await this.request(action, data, options);
            } catch (error) {
                if (i === maxRetries - 1) {
                    throw error;
                }
                
                console.warn(`Request failed, retrying in ${retryDelay}ms...`, error);
                await new Promise(resolve => setTimeout(resolve, retryDelay * (i + 1)));
            }
        }
    }

    static batch(requests) {
        return Promise.all(
            requests.map(({ action, data, options }) => 
                this.request(action, data, options).catch(error => ({
                    error: error.message,
                    action: action
                }))
            )
        );
    }
}

// Helper functions for common operations
class MessageHelpers {
    static async captureConversation(conversation) {
        return MessageProtocol.request(
            MessageProtocol.ACTIONS.CONVERSATION_CAPTURE,
            conversation
        );
    }

    static async updateEarnings(amount) {
        return MessageProtocol.request(
            MessageProtocol.ACTIONS.EARNINGS_UPDATE,
            { amount }
        );
    }

    static async showNotification(message, type = 'info') {
        return MessageProtocol.request(
            MessageProtocol.ACTIONS.UI_SHOW_NOTIFICATION,
            { message, type }
        );
    }

    static async updateBadge(text, color) {
        return MessageProtocol.request(
            MessageProtocol.ACTIONS.UI_UPDATE_BADGE,
            { text, color }
        );
    }

    static async connectWallet(walletType = 'privy') {
        return MessageProtocol.request(
            MessageProtocol.ACTIONS.WALLET_CONNECT,
            { walletType }
        );
    }

    static async getWalletStatus() {
        return MessageProtocol.request(
            MessageProtocol.ACTIONS.WALLET_STATUS,
            {},
            { fallback: { connected: false } }
        );
    }
}

// Export for use across extension
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MessageProtocol, MessageHelpers };
} else {
    window.MessageProtocol = MessageProtocol;
    window.MessageHelpers = MessageHelpers;
}