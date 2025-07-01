// content-wallet.js - Handles wallet interactions from the content script context
console.log('🔌 Content wallet script loaded');

// Listen for messages from the background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('📨 Content wallet received message:', request.action);
    
    // Handle ping to check if script is loaded
    if (request.action === 'ping') {
        console.log('🏓 Responding to ping');
        sendResponse({ pong: true });
        return;
    }
    
    // Handle wallet connection
    if (request.action === 'connect_metamask') {
        console.log('🔗 Handling MetaMask connection request');
        handleMetaMaskConnection()
            .then(result => {
                console.log('✅ Connection successful, sending response:', result);
                sendResponse(result);
            })
            .catch(error => {
                console.error('❌ Connection failed:', error);
                sendResponse({ error: error.message });
            });
        return true; // Keep channel open for async response
    }
    
    // Handle message signing
    if (request.action === 'sign_message') {
        console.log('✍️ Handling message signing request');
        handleMessageSigning(request.message, request.address)
            .then(result => {
                console.log('✅ Signing successful, sending response:', result);
                sendResponse(result);
            })
            .catch(error => {
                console.error('❌ Signing failed:', error);
                sendResponse({ error: error.message });
            });
        return true; // Keep channel open for async response
    }
    
    // Unknown action
    console.warn('⚠️ Unknown action:', request.action);
    sendResponse({ error: 'Unknown action: ' + request.action });
});

// Inject script to access window.ethereum
function injectScript() {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('src/extension/content/inject-wallet.js');
    script.onload = function() {
        this.remove();
    };
    (document.head || document.documentElement).appendChild(script);
}

// Inject immediately and wait for it to load
injectScript();

// Listen for responses from inject script
window.addEventListener('message', (event) => {
    if (event.data?.type === 'METAMASK_PONG') {
        console.log('🏓 Received pong from inject script:', event.data);
        if (!event.data.metamaskAvailable) {
            console.warn('⚠️ MetaMask not available in inject script');
        }
    }
});

// Wait for inject script to be ready with retry logic
let pingCount = 0;
const maxPings = 10;

function checkInjectScript() {
    pingCount++;
    console.log(`🔍 Checking if inject script is ready (${pingCount}/${maxPings})...`);
    window.postMessage({ type: 'METAMASK_PING' }, '*');
    
    if (pingCount < maxPings) {
        setTimeout(checkInjectScript, 1000);
    } else {
        console.warn('⚠️ Inject script did not respond after maximum attempts');
    }
}

// Start checking after initial delay
setTimeout(checkInjectScript, 500);

// Handle MetaMask connection through injected script
async function handleMetaMaskConnection() {
    console.log('🔗 Initiating MetaMask connection...');
    
    // Quick check: Does window.ethereum exist?
    if (typeof window.ethereum === 'undefined') {
        console.error('❌ MetaMask not detected in page context');
        console.log('🔍 Checking for common MetaMask indicators...');
        console.log('window.ethereum:', window.ethereum);
        console.log('window.web3:', window.web3);
        console.log('document.getElementById("metamask-inpage-provider"):', document.getElementById('metamask-inpage-provider'));
        
        // Wait a bit longer for MetaMask to load
        console.log('⏳ Waiting for MetaMask to initialize...');
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        if (typeof window.ethereum === 'undefined') {
            throw new Error('MetaMask is not installed or not accessible. Please install MetaMask browser extension and refresh the page.');
        }
    }
    
    return new Promise((resolve, reject) => {
        // Generate unique request ID
        const requestId = 'connect_' + Date.now();
        
        // Set up one-time listener for response
        const handleResponse = (event) => {
            if (event.data && event.data.type === 'METAMASK_RESPONSE' && event.data.requestId === requestId) {
                window.removeEventListener('message', handleResponse);
                
                if (event.data.error) {
                    console.error('❌ MetaMask error:', event.data.error);
                    reject(new Error(event.data.error));
                } else {
                    console.log('✅ MetaMask connected:', event.data.result);
                    resolve(event.data.result);
                }
            }
        };
        
        window.addEventListener('message', handleResponse);
        
        // Send request to injected script
        window.postMessage({
            type: 'METAMASK_REQUEST',
            action: 'connect',
            requestId: requestId
        }, '*');
        
        // Timeout after 10 seconds for faster debugging
        setTimeout(() => {
            window.removeEventListener('message', handleResponse);
            console.error('❌ Connection timeout - no response from inject script');
            reject(new Error('Connection timeout'));
        }, 10000);
    });
}

// Handle message signing through injected script
async function handleMessageSigning(message, address) {
    console.log('✍️ Initiating message signing...');
    
    return new Promise((resolve, reject) => {
        // Generate unique request ID
        const requestId = 'sign_' + Date.now();
        
        // Set up one-time listener for response
        const handleResponse = (event) => {
            if (event.data && event.data.type === 'METAMASK_RESPONSE' && event.data.requestId === requestId) {
                window.removeEventListener('message', handleResponse);
                
                if (event.data.error) {
                    console.error('❌ Signing error:', event.data.error);
                    reject(new Error(event.data.error));
                } else {
                    console.log('✅ Message signed');
                    resolve(event.data.result);
                }
            }
        };
        
        window.addEventListener('message', handleResponse);
        
        // Send request to injected script
        window.postMessage({
            type: 'METAMASK_REQUEST',
            action: 'sign',
            message: message,
            address: address,
            requestId: requestId
        }, '*');
        
        // Timeout after 30 seconds
        setTimeout(() => {
            window.removeEventListener('message', handleResponse);
            reject(new Error('Signing timeout'));
        }, 30000);
    });
}

console.log('✅ Content wallet script ready');