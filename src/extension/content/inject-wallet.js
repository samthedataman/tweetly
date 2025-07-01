// inject-wallet.js - Injected into the page context to access window.ethereum
(function() {
    console.log('💉 Wallet injector script loaded');
    
    let metamaskDetected = false;
    let retryCount = 0;
    const maxRetries = 10;
    
    // Function to check for MetaMask
    function checkForMetaMask() {
        console.log(`🔍 Checking for MetaMask (attempt ${retryCount + 1}/${maxRetries})...`);
        
        if (typeof window.ethereum !== 'undefined') {
            console.log('✅ MetaMask detected!');
            metamaskDetected = true;
            initializeWalletListeners();
            return true;
        }
        
        retryCount++;
        if (retryCount < maxRetries) {
            console.log(`⏳ MetaMask not detected yet, retrying in 100ms...`);
            setTimeout(checkForMetaMask, 100);
        } else {
            console.error('❌ MetaMask not detected after multiple attempts');
            console.log('🔍 Available ethereum providers:', window.ethereum);
        }
        return false;
    }
    
    // Start checking for MetaMask
    if (!checkForMetaMask()) {
        // Also listen for the ethereum provider to be injected
        window.addEventListener('ethereum#initialized', () => {
            console.log('🎯 MetaMask ethereum#initialized event received');
            if (!metamaskDetected) {
                checkForMetaMask();
            }
        });
        
        // Additional fallback - check periodically
        const intervalId = setInterval(() => {
            if (metamaskDetected || retryCount >= maxRetries) {
                clearInterval(intervalId);
                return;
            }
            checkForMetaMask();
        }, 500);
    }
    
    function initializeWalletListeners() {
        console.log('🎧 Initializing wallet listeners...');
        
        // Listen for requests from content script
        window.addEventListener('message', async (event) => {
            // Only accept messages from the same window
            if (event.source !== window) return;
        
        // Handle ping request
        if (event.data && event.data.type === 'METAMASK_PING') {
            console.log('🏓 Responding to ping from content script');
            window.postMessage({
                type: 'METAMASK_PONG',
                metamaskAvailable: typeof window.ethereum !== 'undefined'
            }, '*');
            return;
        }
        
        // Check for our message type
        if (event.data && event.data.type === 'METAMASK_REQUEST') {
            console.log('📨 Received MetaMask request:', event.data.action);
            
            const requestId = event.data.requestId;
            
            try {
                let result;
                
                switch (event.data.action) {
                    case 'connect':
                        result = await connectMetaMask();
                        break;
                        
                    case 'sign':
                        result = await signMessage(event.data.message, event.data.address);
                        break;
                        
                    default:
                        throw new Error('Unknown action: ' + event.data.action);
                }
                
                // Send success response
                window.postMessage({
                    type: 'METAMASK_RESPONSE',
                    requestId: requestId,
                    result: result
                }, '*');
                
            } catch (error) {
                console.error('❌ MetaMask operation failed:', error);
                
                // Send error response
                window.postMessage({
                    type: 'METAMASK_RESPONSE',
                    requestId: requestId,
                    error: error.message || 'Unknown error'
                }, '*');
            }
        }
    });
    
    // Connect to MetaMask
    async function connectMetaMask() {
        console.log('🔗 Connecting to MetaMask...');
        
        // Check if MetaMask is installed
        if (!window.ethereum) {
            throw new Error('MetaMask is not installed');
        }
        
        // Check if already connected
        const accounts = await window.ethereum.request({ 
            method: 'eth_accounts' 
        });
        
        let address;
        
        if (accounts.length > 0) {
            console.log('✅ Already connected:', accounts[0]);
            address = accounts[0];
        } else {
            console.log('🔐 Requesting wallet access...');
            // Request access
            const newAccounts = await window.ethereum.request({ 
                method: 'eth_requestAccounts' 
            });
            
            if (newAccounts.length === 0) {
                throw new Error('No accounts found');
            }
            
            address = newAccounts[0];
            console.log('✅ Connected:', address);
        }
        
        // Get chain ID
        const chainId = await window.ethereum.request({ 
            method: 'eth_chainId' 
        });
        
        // Convert hex chainId to number
        const chainIdNumber = parseInt(chainId, 16);
        
        console.log('🔗 Chain ID:', chainIdNumber);
        
        return {
            address: address,
            chainId: chainIdNumber,
            provider: 'metamask'
        };
    }
    
    // Sign a message with MetaMask
    async function signMessage(message, address) {
        console.log('✍️ Signing message with MetaMask...');
        console.log('📝 Message:', message);
        console.log('💳 Address:', address);
        
        if (!window.ethereum) {
            throw new Error('MetaMask is not installed');
        }
        
        // Ensure we're connected
        const accounts = await window.ethereum.request({ 
            method: 'eth_accounts' 
        });
        
        if (accounts.length === 0) {
            throw new Error('No accounts connected');
        }
        
        // Verify the address matches
        if (accounts[0].toLowerCase() !== address.toLowerCase()) {
            throw new Error('Address mismatch');
        }
        
        try {
            // Sign the message
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, address]
            });
            
            console.log('✅ Message signed successfully');
            
            return { signature };
            
        } catch (error) {
            if (error.code === 4001) {
                throw new Error('User rejected the signature request');
            }
            throw error;
        }
    }
    
        // Listen for account changes
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', (accounts) => {
                console.log('👛 Accounts changed:', accounts);
                
                // Notify content script
                window.postMessage({
                    type: 'WALLET_EVENT',
                    event: 'accountsChanged',
                    data: { accounts }
                }, '*');
            });
            
            window.ethereum.on('chainChanged', (chainId) => {
                console.log('🔗 Chain changed:', chainId);
                
                // Notify content script
                window.postMessage({
                    type: 'WALLET_EVENT',
                    event: 'chainChanged',
                    data: { chainId }
                }, '*');
            });
        }
        
        console.log('✅ Wallet injector ready');
    } // End of initializeWalletListeners
})();