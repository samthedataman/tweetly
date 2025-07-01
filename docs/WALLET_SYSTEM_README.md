# Contextly Wallet System Architecture

This document explains how the Contextly wallet system works, including the walletConnector, wallet brands, popup integration, and the communication flow between all components.

## Overview

The Contextly wallet system is a multi-layered architecture that supports connection to various wallet brands through a unified interface. It consists of three main layers:

1. **Content Script Layer** (`walletConnector.js`) - Handles direct wallet detection and communication
2. **Bridge Layer** (`walletBridge.js`) - Manages communication between popup and content scripts
3. **Adapter Layer** (`walletAdapter.js`) - Provides a unified interface for different wallet types
4. **UI Layer** (`popup.html` + `popup_merged.js`) - User interface for wallet interactions

## Architecture Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Popup UI      │◄──►│  WalletBridge    │◄──►│  WalletConnector    │
│  (popup.html)   │    │  (Bridge Layer)  │    │ (Content Script)    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         ▲                       ▲                        ▲
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ WalletAdapter   │    │  Chrome APIs     │    │   Wallet Providers  │
│ (Unified API)   │    │  (Messaging)     │    │   (window.ethereum) │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## Core Components

### 1. WalletConnector (Content Script)
**File**: `src/extension/content/walletConnector.js`

The walletConnector is injected into web pages and acts as the bridge between the extension and wallet providers installed in the browser.

#### Key Features:
- **Multi-wallet Detection**: Detects and supports 9+ wallet types
- **Cross-chain Support**: Handles Ethereum, Solana, and Tron wallets
- **Event Handling**: Listens for account and network changes
- **Message Protocol**: Communicates with extension via Chrome messaging API

#### Supported Wallet Brands:
```javascript
const supportedWallets = {
  // Ethereum-based wallets
  metamask: { name: 'MetaMask', icon: '🦊' },
  coinbase: { name: 'Coinbase Wallet', icon: '🔵' },
  trust: { name: 'Trust Wallet', icon: '🛡️' },
  brave: { name: 'Brave Wallet', icon: '🦁' },
  rainbow: { name: 'Rainbow', icon: '🌈' },
  okx: { name: 'OKX Wallet', icon: '⭕' },
  rabby: { name: 'Rabby', icon: '🐰' },
  
  // Cross-chain wallets
  phantom: { name: 'Phantom', icon: '👻' }, // Solana
  tronlink: { name: 'TronLink', icon: '🔷' }, // Tron
  
  // Generic fallback
  injected: { name: 'Injected Wallet', icon: '👛' }
};
```

#### Detection Logic:
```javascript
// Ethereum wallet detection
if (window.ethereum?.isMetaMask) {
  // MetaMask detected
}

// Solana wallet detection  
if (window.solana?.isPhantom) {
  // Phantom detected
}

// Tron wallet detection
if (window.tronWeb?.defaultAddress?.base58) {
  // TronLink detected
}
```

#### Message Handling:
The connector listens for five main message types:
- `WALLET_DETECT` - Returns list of available wallets
- `WALLET_CONNECT` - Connects to specified wallet
- `WALLET_SIGN_MESSAGE` - Signs messages with connected wallet
- `WALLET_GET_CHAIN_ID` - Gets current network chain ID
- `WALLET_SWITCH_NETWORK` - Switches to different network

### 2. WalletBridge (Extension Bridge)
**File**: `src/extension/utils/walletBridge.js`

The WalletBridge manages communication between the popup UI and content scripts, handling the async nature of wallet operations.

#### Key Features:
- **Tab Management**: Ensures content script injection on active tabs
- **Request Queuing**: Manages pending wallet requests with timeouts
- **Error Handling**: Provides detailed error messages for failed operations
- **URL Validation**: Prevents wallet operations on restricted pages

#### Core Methods:
```javascript
class WalletBridge {
  async detectWallets()     // Discover available wallets
  async connect(walletType) // Connect to specific wallet
  async signMessage(msg)    // Sign messages
  async getChainId()        // Get current network
  async switchNetwork(id)   // Switch networks
}
```

#### Content Script Injection:
```javascript
// Inject wallet connector into active tab
await chrome.scripting.executeScript({
  target: { tabId: activeTab.id },
  files: ['src/extension/content/walletConnector.js']
});
```

### 3. WalletAdapter (Unified Interface)
**File**: `src/extension/adapters/walletAdapter.js`

The WalletAdapter provides a unified interface for different wallet connection methods, supporting both injected wallets and embedded solutions.

#### Supported Connection Types:
- **Injected Wallets**: MetaMask, Coinbase, Trust, Rainbow, etc.
- **WalletConnect**: Mobile wallet connections
- **Privy**: Embedded wallet creation
- **Base Integration**: Base network specific wallets

#### Auto-Detection & Fallback:
```javascript
async connectBestAvailable() {
  const preferenceOrder = ['metamask', 'coinbase', 'rainbow', 'trust', 'injected'];
  
  for (const walletType of preferenceOrder) {
    try {
      return await this.connect(walletType);
    } catch (error) {
      continue; // Try next wallet
    }
  }
  
  // Fallback to WalletConnect or embedded wallet
  return await this.connectWalletConnect() || await this.connectPrivy();
}
```

#### Base Network Integration:
The adapter automatically switches connected wallets to Base network:
```javascript
async switchToBaseNetwork() {
  const baseChainId = '0x2105'; // 8453 in hex
  
  try {
    await this.wallet.provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: baseChainId }]
    });
  } catch (switchError) {
    // Add Base network if not present
    if (switchError.code === 4902) {
      await this.wallet.provider.request({
        method: 'wallet_addEthereumChain',
        params: [{ /* Base network config */ }]
      });
    }
  }
}
```

### 4. Popup UI System
**Files**: `src/extension/popup/popup.html`, `src/extension/popup/popup_merged.js`

The popup provides the user interface for wallet interactions, featuring a modal-based wallet selection system.

#### Wallet Connection Flow:
1. User clicks "Connect Wallet" button (`walletConnectBtn`)
2. Wallet selection modal opens (`walletModal`)
3. User selects preferred wallet brand
4. WalletBridge initiates connection via content script
5. UI updates with connection status and wallet info

#### Wallet Selection Modal:
```html
<div class="wallet-options">
  <div class="wallet-option" data-wallet="coinbase">
    <div class="wallet-icon">🔵</div>
    <div class="wallet-name">Coinbase Wallet</div>
    <div class="wallet-desc">Recommended</div>
  </div>
  
  <div class="wallet-option" data-wallet="metamask">
    <div class="wallet-icon">🦊</div>
    <div class="wallet-name">MetaMask</div>
    <div class="wallet-desc">Browser extension</div>
  </div>
  
  <div class="wallet-option" data-wallet="walletconnect">
    <div class="wallet-icon">🔗</div>
    <div class="wallet-name">WalletConnect</div>
    <div class="wallet-desc">Mobile wallets</div>
  </div>
</div>
```

#### Real-time Updates:
The popup listens for wallet events and updates the UI accordingly:
```javascript
// Listen for account changes
window.ethereum?.on('accountsChanged', (accounts) => {
  this.updateWalletInfo(accounts[0]);
});

// Listen for network changes  
window.ethereum?.on('chainChanged', (chainId) => {
  this.updateNetworkInfo(parseInt(chainId, 16));
});
```

## Communication Protocol

### Message Flow
1. **Popup → WalletBridge**: User initiates wallet action
2. **WalletBridge → Content Script**: Bridge injects connector and sends message
3. **Content Script → Wallet Provider**: Connector calls wallet API
4. **Wallet Provider → Content Script**: Wallet responds with data/signature
5. **Content Script → WalletBridge**: Connector sends response back
6. **WalletBridge → Popup**: Bridge resolves promise with result

### Message Types
```javascript
// Detection
{ action: 'WALLET_DETECT' }
→ { success: true, wallets: [...] }

// Connection
{ action: 'WALLET_CONNECT', walletType: 'metamask' }
→ { success: true, data: { address, chainId, type } }

// Signing
{ action: 'WALLET_SIGN_MESSAGE', message: 'Hello World' }
→ { success: true, signature: '0x...' }

// Network Info
{ action: 'WALLET_GET_CHAIN_ID' }
→ { success: true, chainId: 1 }

// Network Switch
{ action: 'WALLET_SWITCH_NETWORK', chainId: '0x2105' }
→ { success: true }
```

## Error Handling

### Common Error Scenarios:
1. **No Wallet Detected**: User doesn't have any Web3 wallets installed
2. **Connection Rejected**: User cancels connection request
3. **Network Mismatch**: Wrong network selected
4. **Signature Rejected**: User cancels signing request
5. **Tab Restrictions**: Trying to connect on chrome:// or extension pages

### Error Messages:
```javascript
// User-friendly error messages
const errorMessages = {
  4001: 'Connection cancelled by user',
  4902: 'This network needs to be added to your wallet first',
  -32002: 'Connection request already pending. Please check your wallet.',
  'NO_WALLET': 'No wallet detected. Please install MetaMask or another Web3 wallet.',
  'INVALID_TAB': 'Please navigate to a website to connect your wallet.'
};
```

## Configuration

### Wallet Priorities:
Connection attempts follow this preference order:
1. MetaMask (most popular)
2. Coinbase Wallet (recommended for Base)
3. Rainbow (good UX)
4. Trust Wallet (mobile-friendly)
5. Generic injected wallet
6. WalletConnect (mobile fallback)
7. Privy embedded wallet (final fallback)

### Network Configuration:
```javascript
const networkConfig = {
  base: {
    chainId: 8453,
    name: 'Base',
    rpcUrl: 'https://mainnet.base.org',
    blockExplorerUrl: 'https://basescan.org'
  }
};
```

## Security Considerations

1. **Content Script Isolation**: Wallet connector runs in isolated environment
2. **Message Validation**: All messages are validated before processing
3. **URL Restrictions**: Wallet operations blocked on sensitive pages
4. **Timeout Protection**: Requests timeout after 30 seconds
5. **User Confirmation**: All signing operations require user approval

## Development Notes

### Adding New Wallet Support:
1. Add detection logic to `walletConnector.js`
2. Add wallet metadata to `walletAdapter.js`
3. Update popup UI with new wallet option
4. Test connection and signing flows

### Testing:
- Test on different websites (not chrome:// pages)
- Verify detection works for each wallet type
- Test connection, signing, and network switching
- Check error handling for edge cases

### Debugging:
- Check browser console for wallet connector logs
- Use Chrome DevTools to inspect message passing
- Monitor network requests in DevTools
- Check extension background script logs

## Future Enhancements

1. **Hardware Wallet Support**: Ledger, Trezor integration
2. **Multi-chain Support**: Ethereum, Polygon, Arbitrum
3. **Wallet Analytics**: Connection success rates, user preferences
4. **Enhanced UI**: Better wallet selection, connection status
5. **Mobile Support**: Responsive design for mobile browsers