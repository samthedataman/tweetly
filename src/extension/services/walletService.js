// walletService.js - Simple, robust wallet connection for Chrome extensions
class WalletService {
  constructor() {
    this.provider = null;
    this.address = null;
    this.chainId = null;
  }

  // Check if wallet is available
  isWalletInstalled() {
    return typeof window.ethereum !== 'undefined';
  }

  // Get installed wallet type
  getWalletType() {
    if (!window.ethereum) return null;
    
    if (window.ethereum.isMetaMask) return 'metamask';
    if (window.ethereum.isCoinbaseWallet) return 'coinbase';
    if (window.ethereum.isRabby) return 'rabby';
    if (window.ethereum.isBraveWallet) return 'brave';
    if (window.ethereum.isRainbow) return 'rainbow';
    if (window.ethereum.isTrust) return 'trust';
    
    return 'unknown';
  }

  // Connect wallet (works in popup, content script, or full page)
  async connect() {
    if (!this.isWalletInstalled()) {
      throw new Error('No wallet detected. Please install MetaMask or another Web3 wallet.');
    }

    try {
      // Request accounts
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts'
      });

      if (accounts.length === 0) {
        throw new Error('No accounts found');
      }

      // Get chain ID
      const chainId = await window.ethereum.request({
        method: 'eth_chainId'
      });

      // Store connection info
      this.provider = window.ethereum;
      this.address = accounts[0];
      this.chainId = parseInt(chainId, 16);

      // Set up event listeners
      this.setupEventListeners();

      // Save to extension storage
      await this.saveConnection();

      // Notify background script
      try {
        chrome.runtime.sendMessage({
          action: 'wallet_connected',
          data: {
            address: this.address,
            chainId: this.chainId,
            walletType: this.getWalletType()
          }
        });
      } catch (e) {
        // Ignore if no background script
      }

      return {
        address: this.address,
        chainId: this.chainId,
        walletType: this.getWalletType()
      };

    } catch (error) {
      if (error.code === 4001) {
        throw new Error('User rejected connection');
      }
      throw error;
    }
  }

  // Switch to specific chain (e.g., Base)
  async switchChain(chainId) {
    if (!this.provider) {
      throw new Error('Not connected to wallet');
    }

    const chainIdHex = `0x${chainId.toString(16)}`;
    
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: chainIdHex }]
      });
      
      this.chainId = chainId;
      await this.saveConnection();
      
    } catch (error) {
      // Chain not added yet
      if (error.code === 4902) {
        await this.addChain(chainId);
        this.chainId = chainId;
        await this.saveConnection();
      } else {
        throw error;
      }
    }
  }

  // Add new chain
  async addChain(chainId) {
    const chains = {
      8453: {
        chainName: 'Base',
        nativeCurrency: { name: 'ETH', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['https://mainnet.base.org'],
        blockExplorerUrls: ['https://basescan.org']
      },
      84531: {
        chainName: 'Base Goerli',
        nativeCurrency: { name: 'ETH', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['https://goerli.base.org'],
        blockExplorerUrls: ['https://goerli.basescan.org']
      },
      84532: {
        chainName: 'Base Sepolia',
        nativeCurrency: { name: 'ETH', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['https://sepolia.base.org'],
        blockExplorerUrls: ['https://sepolia.basescan.org']
      }
    };

    const chainInfo = chains[chainId];
    if (!chainInfo) throw new Error(`Chain ${chainId} not supported`);

    await window.ethereum.request({
      method: 'wallet_addEthereumChain',
      params: [{
        chainId: `0x${chainId.toString(16)}`,
        ...chainInfo
      }]
    });
  }

  // Sign message for authentication
  async signMessage(message) {
    if (!this.address) throw new Error('Not connected');
    if (!this.provider) throw new Error('No provider available');

    const signature = await window.ethereum.request({
      method: 'personal_sign',
      params: [message, this.address]
    });

    return signature;
  }

  // Set up event listeners
  setupEventListeners() {
    if (!window.ethereum) return;

    // Account changed
    window.ethereum.on('accountsChanged', async (accounts) => {
      if (accounts.length === 0) {
        await this.disconnect();
      } else {
        this.address = accounts[0];
        await this.saveConnection();
        
        // Notify background/popup
        try {
          chrome.runtime.sendMessage({
            action: 'wallet_account_changed',
            address: this.address
          });
        } catch (e) {
          // Ignore if no background script
        }
      }
    });

    // Chain changed
    window.ethereum.on('chainChanged', async (chainId) => {
      this.chainId = parseInt(chainId, 16);
      await this.saveConnection();
      
      try {
        chrome.runtime.sendMessage({
          action: 'wallet_chain_changed',
          chainId: this.chainId
        });
      } catch (e) {
        // Ignore if no background script
      }
    });

    // Disconnect
    window.ethereum.on('disconnect', async () => {
      await this.disconnect();
    });
  }

  // Save connection to extension storage
  async saveConnection() {
    try {
      await chrome.storage.local.set({
        wallet: {
          connected: true,
          address: this.address,
          chainId: this.chainId,
          walletType: this.getWalletType(),
          timestamp: Date.now()
        }
      });
    } catch (error) {
      console.error('Failed to save wallet connection:', error);
    }
  }

  // Restore connection from storage
  async restoreConnection() {
    try {
      const data = await chrome.storage.local.get('wallet');
      
      if (data.wallet && data.wallet.connected) {
        // Check if wallet still available
        if (!this.isWalletInstalled()) {
          await this.disconnect();
          return null;
        }

        // Check if still same account
        const accounts = await window.ethereum.request({
          method: 'eth_accounts'
        });

        if (accounts.length > 0 && accounts[0] === data.wallet.address) {
          this.address = data.wallet.address;
          this.chainId = data.wallet.chainId;
          this.provider = window.ethereum;
          this.setupEventListeners();
          return data.wallet;
        } else {
          // Account changed, clear old connection
          await this.disconnect();
        }
      }

      return null;
    } catch (error) {
      console.error('Failed to restore wallet connection:', error);
      return null;
    }
  }

  // Disconnect wallet
  async disconnect() {
    this.provider = null;
    this.address = null;
    this.chainId = null;
    
    try {
      await chrome.storage.local.remove('wallet');
      
      // Notify background/popup
      chrome.runtime.sendMessage({
        action: 'wallet_disconnected'
      });
    } catch (error) {
      console.error('Failed to disconnect wallet:', error);
    }
  }

  // Get balance
  async getBalance() {
    if (!this.address) throw new Error('Not connected');
    if (!this.provider) throw new Error('No provider available');

    const balance = await window.ethereum.request({
      method: 'eth_getBalance',
      params: [this.address, 'latest']
    });

    // Convert from hex to decimal
    return parseInt(balance, 16) / 1e18;
  }

  // Get connection status
  getConnectionStatus() {
    return {
      connected: !!this.address,
      address: this.address,
      chainId: this.chainId,
      walletType: this.getWalletType(),
      shortAddress: this.address ? 
        `${this.address.slice(0, 6)}...${this.address.slice(-4)}` : null
    };
  }

  // Check if on specific chain
  isOnChain(targetChainId) {
    return this.chainId === targetChainId;
  }

  // Auto-switch to Base if not already on it
  async ensureBaseNetwork() {
    const baseChainId = 8453;
    if (!this.isOnChain(baseChainId)) {
      await this.switchChain(baseChainId);
    }
  }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WalletService;
} else {
  window.WalletService = WalletService;
}''