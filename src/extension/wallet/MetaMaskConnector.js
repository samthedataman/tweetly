// MetaMask Connector using metamask-extension-provider
const createMetaMaskProvider = require('metamask-extension-provider');

class MetaMaskConnector {
    constructor() {
        this.provider = null;
        this.account = null;
        this.chainId = null;
    }

    async activate() {
        console.log('🔗 Activating MetaMask connection...');
        
        const provider = createMetaMaskProvider();
        if (!provider) {
            console.error("MetaMask provider not detected.");
            throw new Error("MetaMask provider not detected.");
        }

        console.log('✅ MetaMask provider created successfully');

        try {
            const [accounts, chainId] = await Promise.all([
                provider.request({
                    method: 'eth_requestAccounts',
                }),
                provider.request({ method: 'eth_chainId' }),
            ]);

            console.log('📋 Accounts:', accounts);
            console.log('🔗 Chain ID:', chainId);

            const account = accounts[0] ? accounts[0].toLowerCase() : null;

            if (!account) {
                throw new Error('No accounts found in MetaMask');
            }

            this.chainId = chainId;
            this.account = account;
            this.provider = provider;

            console.log('✅ MetaMask connection successful');
            console.log('Account:', this.account);
            console.log('Chain ID:', this.chainId);

            this.subscribeToEvents(provider);

            return { 
                provider, 
                chainId: parseInt(chainId, 16), 
                account,
                address: account // alias for compatibility
            };
        } catch (error) {
            console.error('❌ MetaMask connection failed:', error);
            throw error;
        }
    }

    subscribeToEvents(provider) {
        console.log('🎧 Subscribing to MetaMask events...');
        
        provider.on('accountsChanged', (accounts) => {
            console.log('👛 Accounts changed:', accounts);
            this.account = accounts[0] ? accounts[0].toLowerCase() : null;
        });

        provider.on('chainChanged', (chainId) => {
            console.log('🔗 Chain changed:', chainId);
            this.chainId = chainId;
        });

        provider.on('error', (error) => {
            console.error('❌ MetaMask provider error:', error);
        });

        provider.on('connect', (connectInfo) => {
            console.log('✅ MetaMask connected:', connectInfo);
        });

        provider.on('disconnect', (error) => {
            console.log('🔌 MetaMask disconnected:', error);
        });
    }

    async signMessage(message) {
        if (!this.provider || !this.account) {
            throw new Error('MetaMask not connected');
        }

        try {
            const signature = await this.provider.request({
                method: 'personal_sign',
                params: [message, this.account]
            });

            return { signature };
        } catch (error) {
            console.error('❌ Message signing failed:', error);
            throw error;
        }
    }

    isConnected() {
        return !!(this.provider && this.account);
    }

    getAccount() {
        return this.account;
    }

    getChainId() {
        return this.chainId;
    }

    getProvider() {
        return this.provider;
    }
}

// Export for both Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetaMaskConnector;
}

// Make available globally for browser
if (typeof window !== 'undefined') {
    window.MetaMaskConnector = MetaMaskConnector;
}