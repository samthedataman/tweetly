// connect.js - Simple FastAPI wallet authentication
console.log('🔗 Connect page loaded');

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Simple wallet connection state
let walletConnection = {
    address: null,
    chainId: null,
    walletType: null,
    connected: false,
    token: null
};

// Elements
const status = document.getElementById('status');
const walletSelection = document.getElementById('walletSelection');
const connectedInfo = document.getElementById('connectedInfo');
const walletAddress = document.getElementById('walletAddress');
const networkName = document.getElementById('networkName');
const walletType = document.getElementById('walletType');

// Show status message
function showStatus(message, type = 'loading') {
    status.textContent = message;
    status.className = `status ${type}`;
    status.classList.remove('hidden');
}

// Hide status
function hideStatus() {
    status.classList.add('hidden');
}

// Update UI for connected state
function updateConnectedUI(connection) {
    walletSelection.classList.add('hidden');
    connectedInfo.classList.remove('hidden');
    
    walletAddress.textContent = connection.address;
    walletType.textContent = connection.walletType || 'Unknown';
    
    // Get network name
    const networks = {
        1: 'Ethereum Mainnet',
        8453: 'Base',
        84531: 'Base Goerli',
        84532: 'Base Sepolia'
    };
    networkName.textContent = networks[connection.chainId] || `Chain ${connection.chainId}`;
}

// Update UI for disconnected state
function updateDisconnectedUI() {
    walletSelection.classList.remove('hidden');
    connectedInfo.classList.add('hidden');
    hideStatus();
}

// Simple wallet connection using FastAPI backend
async function connectWallet(preferredType = null) {
    try {
        console.log('🔗 Attempting to connect wallet:', preferredType);
        showStatus('Checking for wallet...', 'loading');

        // Check if MetaMask is available
        if (typeof window.ethereum === 'undefined') {
            showStatus('MetaMask not detected. Please install MetaMask and refresh this page.', 'error');
            return;
        }

        console.log('✅ MetaMask detected, requesting connection...');
        showStatus('Connecting to MetaMask...', 'loading');

        // Request account access
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });

        if (!accounts || accounts.length === 0) {
            throw new Error('No accounts found');
        }

        // Get chain ID
        const chainId = await window.ethereum.request({
            method: 'eth_chainId'
        });

        // Detect wallet type
        let detectedWalletType = 'Unknown';
        if (window.ethereum.isMetaMask) {
            detectedWalletType = 'MetaMask';
        } else if (window.ethereum.isCoinbaseWallet) {
            detectedWalletType = 'Coinbase';
        }

        const walletAddr = accounts[0];
        const chainIdNum = parseInt(chainId, 16);

        console.log('🎉 Wallet connected:', { walletAddr, chainIdNum, detectedWalletType });
        
        // Create authentication message
        showStatus('Preparing authentication message...', 'loading');
        const timestamp = Date.now();
        const authMessage = `Contextly.ai Authentication\nAddress: ${walletAddr}\nTimestamp: ${timestamp}`;

        console.log('📝 Requesting signature...');
        showStatus('Please sign the message in MetaMask...', 'loading');

        // Sign the authentication message
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [authMessage, walletAddr]
        });

        console.log('✅ Message signed, authenticating with backend...');
        showStatus('Authenticating with backend...', 'loading');

        // Send to FastAPI backend for verification
        const response = await fetch(`${API_BASE_URL}/v1/wallet/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                wallet: walletAddr,
                signature: signature,
                message: authMessage,
                chainId: chainIdNum
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Authentication failed');
        }

        const authResult = await response.json();
        console.log('🎉 Backend authentication successful:', authResult);

        // Store the connection and token
        walletConnection = {
            address: walletAddr,
            chainId: chainIdNum,
            walletType: detectedWalletType,
            connected: true,
            token: authResult.token
        };

        // Store in extension storage
        await chrome.storage.local.set({
            walletConnection: walletConnection,
            authToken: authResult.token
        });

        // Update UI
        updateConnectedUI(walletConnection);
        showStatus('✅ Wallet connected and authenticated!', 'success');

        // Show Twitter auth section
        const twitterSection = document.getElementById('twitterSection');
        if (twitterSection) {
            twitterSection.classList.remove('hidden');
        }

        // Notify extension
        try {
            chrome.runtime.sendMessage({
                action: 'wallet_connected',
                data: {
                    address: walletAddr,
                    chainId: chainIdNum,
                    walletType: detectedWalletType,
                    token: authResult.token,
                    authenticated: true
                }
            });
            console.log('📨 Sent wallet_connected message to extension');
        } catch (messageError) {
            console.warn('Failed to send message:', messageError);
        }

        // Don't auto-close now - let user connect Twitter too
        console.log('✅ Wallet connected - you can now connect Twitter/X for enhanced features');

    } catch (error) {
        console.error('❌ Connection failed:', error);
        if (error.message.includes('User rejected')) {
            showStatus('Connection cancelled by user', 'error');
        } else {
            showStatus(`Connection failed: ${error.message}`, 'error');
        }
    }
}

// Disconnect wallet
async function disconnectWallet() {
    try {
        console.log('🔌 Disconnecting wallet...');
        
        // Clear local state
        walletConnection = {
            address: null,
            chainId: null,
            walletType: null,
            connected: false,
            token: null
        };

        // Clear extension storage
        await chrome.storage.local.remove(['walletConnection', 'authToken', 'twitterConnection']);

        // Update UI
        updateDisconnectedUI();
        showStatus('Wallet disconnected', 'success');

        // Hide Twitter section
        const twitterSection = document.getElementById('twitterSection');
        if (twitterSection) {
            twitterSection.classList.add('hidden');
        }

        // Notify extension
        chrome.runtime.sendMessage({
            action: 'wallet_disconnected'
        });

    } catch (error) {
        console.error('Disconnect error:', error);
        showStatus('Failed to disconnect', 'error');
    }
}

// Connect Twitter account
async function connectTwitter() {
    try {
        if (!walletConnection.connected) {
            showStatus('Please connect your wallet first', 'error');
            return;
        }

        console.log('𝕏 Attempting to connect Twitter...');
        showStatus('Connecting to Twitter/X...', 'loading');

        // Auto-detect development mode based on backend environment
        // This will check your .env file automatically:
        // - If TWITTER_CLIENT_ID is missing/dummy → Development mode
        // - If TWITTER_CLIENT_ID is real → Production mode
        console.log('🔍 Auto-detecting Twitter auth mode from backend...');
        const isDevelopmentMode = await checkIfBackendInDevMode();

        if (isDevelopmentMode) {
            // Development mode - simple username input
            const username = prompt('Enter your Twitter/X username for development testing:');
            if (!username) {
                showStatus('Twitter connection cancelled', 'error');
                return;
            }

            // Test the dev endpoint
            const response = await fetch(`${API_BASE_URL}/v1/auth/x/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': walletConnection.address
                },
                body: JSON.stringify({
                    wallet: walletConnection.address,
                    dev_mode: true,
                    username: username
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Twitter connected (dev mode):', result);
                
                // Store Twitter connection
                await chrome.storage.local.set({
                    twitterConnection: {
                        username: username,
                        connected: true,
                        devMode: true,
                        connectedAt: Date.now()
                    }
                });

                showStatus(`✅ Twitter connected: @${username} (dev mode)`, 'success');
                
                // Update UI to show connected state
                const connectBtn = document.getElementById('connectTwitter');
                if (connectBtn) {
                    connectBtn.innerHTML = `
                        <div class="wallet-icon">✅</div>
                        <div class="wallet-info">
                            <h3>Connected: @${username}</h3>
                            <p>Development mode</p>
                        </div>
                    `;
                    connectBtn.style.opacity = '0.7';
                    connectBtn.disabled = true;
                }

                // Auto-close after Twitter connection
                setTimeout(() => {
                    console.log('🔚 Closing connection window...');
                    window.close();
                }, 2000);

            } else {
                const error = await response.text();
                throw new Error(error);
            }

        } else {
            // Production mode - real Twitter OAuth
            const response = await fetch(`${API_BASE_URL}/v1/auth/x/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${walletConnection.token}`
                },
                body: JSON.stringify({
                    wallet: walletConnection.address
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Twitter OAuth URL received:', result);
                
                // Open Twitter OAuth in popup
                const authWindow = window.open(
                    result.auth_url,
                    'twitterAuth',
                    'width=600,height=600,scrollbars=yes,resizable=yes'
                );

                // Listen for OAuth completion
                const checkClosed = setInterval(() => {
                    if (authWindow.closed) {
                        clearInterval(checkClosed);
                        // Check if auth was successful
                        checkTwitterAuthStatus();
                    }
                }, 1000);

            } else {
                const error = await response.text();
                throw new Error(error);
            }
        }

    } catch (error) {
        console.error('❌ Twitter connection failed:', error);
        showStatus(`Twitter connection failed: ${error.message}`, 'error');
    }
}

// Check if backend is in development mode
async function checkIfBackendInDevMode() {
    try {
        // Check if backend has real Twitter keys or dummy ones
        const response = await fetch(`${API_BASE_URL}/v1/auth/x/test`, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            // Backend returns dev_mode: true when using dummy keys
            return result.dev_mode === true;
        }
        
        // Default to development mode if can't determine
        return true;
    } catch (error) {
        console.log('Could not determine backend mode, defaulting to development');
        return true;
    }
}

// Check Twitter auth status
async function checkTwitterAuthStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/v1/auth/x/status`, {
            headers: {
                'X-Wallet-Address': walletConnection.address,
                'Authorization': `Bearer ${walletConnection.token}`
            }
        });

        if (response.ok) {
            const result = await response.json();
            if (result.linked) {
                console.log('✅ Twitter auth confirmed:', result);
                showStatus(`✅ Twitter connected: @${result.x_username}`, 'success');
                
                // Store Twitter connection
                await chrome.storage.local.set({
                    twitterConnection: {
                        username: result.x_username,
                        connected: true,
                        devMode: false,
                        connectedAt: Date.now()
                    }
                });

                // Auto-close after successful connection
                setTimeout(() => {
                    window.close();
                }, 2000);
            }
        }
    } catch (error) {
        console.error('Error checking Twitter auth status:', error);
    }
}

// Initialize event listeners
function initEventListeners() {
    console.log('🎯 Setting up event listeners...');
    
    const connectMetaMask = document.getElementById('connectMetaMask');
    const connectCoinbase = document.getElementById('connectCoinbase');
    const connectAny = document.getElementById('connectAny');
    const connectTwitter = document.getElementById('connectTwitter');
    const disconnectBtn = document.getElementById('disconnectBtn');
    
    if (connectMetaMask) {
        connectMetaMask.addEventListener('click', () => {
            console.log('🦊 MetaMask button clicked');
            connectWallet('metamask');
        });
    }

    if (connectCoinbase) {
        connectCoinbase.addEventListener('click', () => {
            console.log('🔵 Coinbase button clicked');
            connectWallet('coinbase');
        });
    }

    if (connectAny) {
        connectAny.addEventListener('click', () => {
            console.log('🌐 Any wallet button clicked');
            connectWallet();
        });
    }

    if (connectTwitter) {
        connectTwitter.addEventListener('click', () => {
            console.log('𝕏 Twitter button clicked');
            connectTwitter();
        });
    }

    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', disconnectWallet);
    }
    
    console.log('✅ Event listeners set up');
}

// Check for existing connection
async function checkExistingConnection() {
    console.log('🔍 Checking for existing connection...');
    try {
        const result = await chrome.storage.local.get(['walletConnection', 'authToken']);
        
        if (result.walletConnection && result.authToken) {
            console.log('✅ Found stored connection:', result.walletConnection.address);
            walletConnection = result.walletConnection;
            updateConnectedUI(walletConnection);
            showStatus('Wallet already connected', 'success');
            
            // Show Twitter section if wallet is connected
            const twitterSection = document.getElementById('twitterSection');
            if (twitterSection) {
                twitterSection.classList.remove('hidden');
            }
            
            // If URL has #twitter, focus on Twitter connection
            if (window.location.hash === '#twitter') {
                showStatus('Now connect your Twitter/X account', 'loading');
                const twitterBtn = document.getElementById('connectTwitter');
                if (twitterBtn) {
                    twitterBtn.scrollIntoView({ behavior: 'smooth' });
                    twitterBtn.style.border = '3px solid #1DA1F2';
                    setTimeout(() => {
                        twitterBtn.style.border = '';
                    }, 3000);
                }
            }
        } else {
            console.log('ℹ️ No existing connection found');
        }
    } catch (error) {
        console.error('Error checking existing connection:', error);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('📄 DOM loaded');
        initEventListeners();
        checkExistingConnection();
    });
} else {
    console.log('📄 DOM already ready');
    initEventListeners();
    checkExistingConnection();
}

// Listen for wallet events
chrome.runtime.onMessage.addListener((request) => {
    console.log('📨 Received message:', request);
    if (request.action === 'wallet_account_changed') {
        if (walletConnection.connected) {
            updateConnectedUI(walletConnection);
        }
    } else if (request.action === 'wallet_disconnected') {
        disconnectWallet();
    }
});

console.log('🎉 Connect script initialized with FastAPI backend');