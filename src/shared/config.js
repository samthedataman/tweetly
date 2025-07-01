// config.js - Configuration management for Contextly

class Config {
    static DEFAULTS = {
        // API Configuration
        api: {
            baseUrl: process.env.NODE_ENV === 'development' ? 
                'http://localhost:8000' : 
                'https://api.contextly.ai',
            timeout: 30000,
            retries: 3
        },

        // Wallet Configuration
        wallet: {
            type: 'privy', // 'privy' or 'walletconnect'
            privy: {
                appId: 'clq6re36k03xfku0fnosk3xpg'
            },
            walletconnect: {
                projectId: 'YOUR_WALLETCONNECT_PROJECT_ID'
            }
        },

        // Feature Flags
        features: {
            earnMode: true,
            autoSave: true,
            contextWarnings: true,
            smartTransfer: true,
            journeyCapture: true,
            offlineMode: true
        },

        // UI Configuration
        ui: {
            theme: 'dark',
            accentColor: '#6366f1',
            position: 'bottom-right',
            animations: true,
            notifications: true
        },

        // Storage Configuration
        storage: {
            maxLocalConversations: 100,
            syncInterval: 60000, // 1 minute
            cacheExpiry: 86400000 // 24 hours
        },

        // Platform Specific
        platforms: {
            claude: {
                selectors: {
                    streaming: true,
                    artifacts: true
                }
            },
            chatgpt: {
                selectors: {
                    markdown: true
                }
            },
            gemini: {
                selectors: {
                    turnFooter: true
                }
            }
        },

        // Privacy Configuration
        privacy: {
            anonymize: true,
            patterns: {
                email: true,
                phone: true,
                ssn: true,
                creditCard: true
            }
        }
    };

    constructor() {
        this.config = { ...Config.DEFAULTS };
        this.listeners = new Map();
        this.initialized = false;
    }

    async init() {
        try {
            // Load from chrome storage
            const stored = await chrome.storage.sync.get('config');
            if (stored.config) {
                this.config = this.deepMerge(this.config, stored.config);
            }

            // Load user preferences
            const preferences = await chrome.storage.sync.get([
                'earnMode',
                'wallet',
                'theme',
                'apiUrl'
            ]);

            // Apply preferences
            if (preferences.earnMode !== undefined) {
                this.config.features.earnMode = preferences.earnMode;
            }
            if (preferences.apiUrl) {
                this.config.api.baseUrl = preferences.apiUrl;
            }
            if (preferences.theme) {
                this.config.ui.theme = preferences.theme;
            }

            this.initialized = true;
            this.notifyListeners('init', this.config);
        } catch (error) {
            console.error('Config initialization error:', error);
            // Use defaults on error
            this.initialized = true;
        }
    }

    get(path, defaultValue = undefined) {
        const keys = path.split('.');
        let value = this.config;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return defaultValue;
            }
        }

        return value;
    }

    async set(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let obj = this.config;

        for (const key of keys) {
            if (!obj[key] || typeof obj[key] !== 'object') {
                obj[key] = {};
            }
            obj = obj[key];
        }

        const oldValue = obj[lastKey];
        obj[lastKey] = value;

        // Save to storage
        await this.save();

        // Notify listeners
        this.notifyListeners(path, value, oldValue);
    }

    async update(updates) {
        const changes = [];

        const applyUpdates = (obj, updates, path = '') => {
            for (const [key, value] of Object.entries(updates)) {
                const currentPath = path ? `${path}.${key}` : key;
                
                if (value && typeof value === 'object' && !Array.isArray(value)) {
                    if (!obj[key] || typeof obj[key] !== 'object') {
                        obj[key] = {};
                    }
                    applyUpdates(obj[key], value, currentPath);
                } else {
                    const oldValue = obj[key];
                    obj[key] = value;
                    changes.push({ path: currentPath, value, oldValue });
                }
            }
        };

        applyUpdates(this.config, updates);
        await this.save();

        // Notify listeners for each change
        changes.forEach(({ path, value, oldValue }) => {
            this.notifyListeners(path, value, oldValue);
        });
    }

    async save() {
        try {
            await chrome.storage.sync.set({ config: this.config });
        } catch (error) {
            console.error('Config save error:', error);
        }
    }

    async reset(path = null) {
        if (path) {
            const keys = path.split('.');
            const defaultValue = this.getDefault(path);
            await this.set(path, defaultValue);
        } else {
            this.config = { ...Config.DEFAULTS };
            await this.save();
            this.notifyListeners('reset', this.config);
        }
    }

    getDefault(path) {
        const keys = path.split('.');
        let value = Config.DEFAULTS;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return undefined;
            }
        }

        return value;
    }

    // Event handling
    on(path, callback) {
        if (!this.listeners.has(path)) {
            this.listeners.set(path, new Set());
        }
        this.listeners.get(path).add(callback);

        // Return unsubscribe function
        return () => {
            const callbacks = this.listeners.get(path);
            if (callbacks) {
                callbacks.delete(callback);
                if (callbacks.size === 0) {
                    this.listeners.delete(path);
                }
            }
        };
    }

    notifyListeners(path, value, oldValue = undefined) {
        // Notify specific path listeners
        const callbacks = this.listeners.get(path);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(value, oldValue, path);
                } catch (error) {
                    console.error('Config listener error:', error);
                }
            });
        }

        // Notify wildcard listeners
        const wildcardCallbacks = this.listeners.get('*');
        if (wildcardCallbacks) {
            wildcardCallbacks.forEach(callback => {
                try {
                    callback(value, oldValue, path);
                } catch (error) {
                    console.error('Config wildcard listener error:', error);
                }
            });
        }
    }

    // Utility methods
    deepMerge(target, source) {
        const result = { ...target };

        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this.deepMerge(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }

        return result;
    }

    export() {
        return JSON.stringify(this.config, null, 2);
    }

    async import(configString) {
        try {
            const imported = JSON.parse(configString);
            this.config = this.deepMerge(Config.DEFAULTS, imported);
            await this.save();
            this.notifyListeners('import', this.config);
        } catch (error) {
            throw new Error('Invalid configuration format');
        }
    }
}

// Create singleton instance
const config = new Config();

// Export for use across extension
if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
} else {
    window.contextlyConfig = config;
}