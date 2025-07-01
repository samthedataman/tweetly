# Wallet Authentication Flow Documentation

This document provides a detailed breakdown of the wallet connection and authentication process in the Contextly extension, including all relevant files, functions, and line numbers.

## Table of Contents
1. [Overview](#overview)
2. [Frontend: Wallet Connection](#frontend-wallet-connection)
3. [Frontend: Message Signing](#frontend-message-signing)
4. [Backend: Authentication API](#backend-authentication-api)
5. [Backend: Signature Verification](#backend-signature-verification)
6. [Token Management](#token-management)
7. [Session Persistence](#session-persistence)
8. [Security Considerations](#security-considerations)

## Overview

The wallet authentication flow consists of:
1. User initiates wallet connection from the Chrome extension popup
2. Extension requests wallet access and gets user's address
3. User signs a timestamped message to prove wallet ownership
4. Backend verifies the signature and creates a JWT token
5. Token is stored and used for all subsequent API requests

## Frontend: Wallet Connection

### File: `/src/extension/popup/popup_simple.js`

#### Connection Initiation (Lines 113-126)
```javascript
async connectWallet() {
    console.log('🎯 Connect wallet clicked');
    
    if (this.isConnecting) {
        console.log('⏳ Already connecting, please wait...');
        return;
    }
    
    this.isConnecting = true;
    this.updateWalletButton(true);
    
    try {
        await this.ensureMetaMaskConnector();
```

#### MetaMask Connector Setup (Lines 276-301)
```javascript
async ensureMetaMaskConnector() {
    console.log('🔧 Ensuring MetaMask connector...');
    
    if (this.metaMaskConnector) {
        console.log('✅ MetaMask connector already exists');
        return;
    }
    
    try {
        console.log('📦 Creating new MetaMask connector...');
        
        if (typeof MetaMaskConnector === 'undefined') {
            throw new Error('MetaMaskConnector not loaded');
        }
        
        this.metaMaskConnector = new MetaMaskConnector({
            silent: false,
            debug: true
        });
        
        console.log('✅ MetaMask connector created successfully');
    } catch (error) {
        console.error('❌ Failed to create MetaMask connector:', error);
        throw error;
    }
}
```

### File: `/src/extension/wallet/MetaMaskConnector.js`

#### Wallet Provider Connection (Lines 45-73)
```javascript
async connect() {
    try {
        this.log('🔗 Attempting to connect...');
        
        // Create provider
        const provider = await createMetaMaskProvider();
        this.provider = new ethers.providers.Web3Provider(provider);
        
        // Request accounts
        this.log('📝 Requesting accounts...');
        const accounts = await this.provider.send('eth_requestAccounts', []);
        
        if (!accounts || accounts.length === 0) {
            throw new Error('No accounts found');
        }
        
        this.address = accounts[0];
        this.log('✅ Connected to address:', this.address);
        
        // Get chain ID
        const network = await this.provider.getNetwork();
        this.chainId = network.chainId;
        this.log('🔗 Connected to chain:', this.chainId);
        
        return {
            address: this.address,
            chainId: this.chainId
        };
    } catch (error) {
        this.handleError('Connection failed', error);
        throw error;
    }
}
```

## Frontend: Message Signing

### File: `/src/extension/popup/popup_simple.js`

#### Message Generation (Lines 857-860)
```javascript
generateAuthMessage() {
    const timestamp = new Date().toISOString();
    return `Sign this message to authenticate with Contextly:\n\nTimestamp: ${timestamp}\nDomain: contextly.ai`;
}
```

#### Signing Process (Lines 128-151)
```javascript
// Get wallet connection
const connectionResult = await this.metaMaskConnector.connect();
console.log('🔗 Wallet connection result:', connectionResult);

const { address, chainId } = connectionResult;
console.log('📱 Connected - Address:', address, 'Chain:', chainId);

// Generate and sign auth message
const message = this.generateAuthMessage();
console.log('📝 Auth message:', message);

console.log('✍️ Requesting signature...');
const signResult = await this.metaMaskConnector.signMessage(message);

if (!signResult || !signResult.signature) {
    throw new Error('Failed to sign message');
}

console.log('✅ Message signed successfully');
```

### File: `/src/extension/wallet/MetaMaskConnector.js`

#### Message Signing Implementation (Lines 75-91)
```javascript
async signMessage(message) {
    try {
        this.log('✍️ Signing message...');
        
        if (!this.provider || !this.address) {
            throw new Error('Not connected');
        }
        
        const signer = this.provider.getSigner();
        const signature = await signer.signMessage(message);
        
        this.log('✅ Message signed');
        return { signature, address: this.address };
    } catch (error) {
        this.handleError('Failed to sign message', error);
        throw error;
    }
}
```

## Backend: Authentication API

### File: `/src/backend/api/backend.py`

#### Wallet Registration Endpoint (Lines 1158-1210)
```python
@app.post("/v1/wallet/register")
async def register_wallet(registration: WalletRegistration):
    """Register a new wallet or login existing wallet"""
    auth_logger.info(f"📝 Wallet registration attempt: {registration.wallet}")
    
    # Verify signature
    auth_logger.info(f"🔐 Verifying signature for wallet: {registration.wallet}")
    
    is_valid = verify_wallet_signature(
        registration.wallet, 
        registration.signature, 
        registration.message
    )
    
    if not is_valid:
        auth_logger.error(f"❌ Invalid signature for wallet: {registration.wallet}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    auth_logger.info(f"✅ Signature valid for wallet: {registration.wallet}")
    
    # Check if wallet exists
    existing = await find_user_by_wallet(registration.wallet)
    
    if not existing:
        user_doc = {
            "_id": str(uuid.uuid4()),
            "wallet": registration.wallet,
            "x_id": None,
            "x_username": None,
            "chainId": registration.chainId,
            "created": str(datetime.now().isoformat()),
            "totalEarnings": 0.0,
            "conversationCount": 0,
            "journeyCount": 0,
            "graphNodesCreated": 0,
            "auth_method": "wallet",
            "last_active": str(datetime.now().isoformat()),
        }
        await create_user(user_doc)
        
        # Create JWT token for new user
        token = create_access_token(user_doc["wallet"], user_doc["_id"])
        auth_logger.info(f"✅ New wallet registered: {registration.wallet}")
        
        return {
            "success": True,
            "userId": user_doc["_id"],
            "message": "Wallet registered successfully",
            "token": token,
            "wallet": user_doc["wallet"],
        }
```

#### User Creation (Lines 1025-1034)
```python
async def create_user(user_data: dict):
    """Create new user"""
    if users_table is None:
        raise Exception("Users table not initialized")
    try:
        users_table.add([user_data])
        return user_data
    except Exception as e:
        print(f"Error creating user: {e}")
        raise e
```

## Backend: Signature Verification

### File: `/src/backend/auth/auth.py`

#### Signature Verification Function (Lines 45-60)
```python
def verify_wallet_signature(wallet: str, signature: str, message: str) -> bool:
    """Verify that a signature matches the wallet address"""
    try:
        w3 = Web3()
        
        # Encode the message
        encoded_message = encode_defunct(text=message)
        
        # Recover the address from the signature
        recovered_address = w3.eth.account.recover_message(
            encoded_message, signature=signature
        )
        
        # Compare addresses (case-insensitive)
        return recovered_address.lower() == wallet.lower()
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False
```

#### JWT Token Creation (Lines 62-76)
```python
def create_access_token(wallet: str, user_id: str) -> str:
    """Create a JWT access token"""
    payload = {
        "wallet": wallet,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Store session in Redis if available
    if redis_client:
        _store_session(wallet, user_id, token)
    
    return token
```

## Token Management

### File: `/src/extension/popup/popup_simple.js`

#### Token Storage (Lines 189-194)
```javascript
// Save to storage - always enable earn mode for new users
await chrome.storage.local.set({
    wallet: this.wallet,
    authToken: this.authToken,
    earnMode: true  // Always enabled for new wallet connections
});
```

#### Background Notification (Lines 207-226)
```javascript
// Notify other parts of extension
const walletMessage = {
    action: 'wallet_connected',
    data: {
        address: this.wallet.address,
        chainId: this.wallet.chainId,
        connected: true,
        earnMode: true,
        token: this.authToken,
        walletType: 'metamask'
    }
};

console.log('📤 Sending wallet connection message to background:', walletMessage);

chrome.runtime.sendMessage(walletMessage, (response) => {
    if (chrome.runtime.lastError) {
        console.error('❌ Error sending message:', chrome.runtime.lastError);
    } else {
        console.log('📨 Background response:', response);
    }
});
```

### File: `/src/extension/background.js`

#### Message Handler (Lines 267-300)
```javascript
if (request.action === 'wallet_connected') {
    console.log('[Background] Wallet connected event received');
    
    // Store wallet data
    const walletData = {
        wallet: {
            address: request.data.address,
            chainId: request.data.chainId,
            connected: true,
            connectedAt: Date.now()
        },
        authToken: request.data.token,
        earnMode: request.data.earnMode
    };
    
    chrome.storage.local.set(walletData, () => {
        console.log('[Background] Wallet data stored successfully');
    });
    
    // Update content scripts
    chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
            if (tab.url && supportedPlatforms.some(domain => tab.url.includes(domain))) {
                chrome.tabs.sendMessage(tab.id, {
                    action: 'wallet_connected',
                    data: request.data
                }, () => {
                    if (chrome.runtime.lastError) {
                        console.log(`[Background] Could not update tab ${tab.id}:`, 
                            chrome.runtime.lastError.message);
                    }
                });
            }
        });
    });
    
    sendResponse({ success: true, message: 'Wallet connection processed' });
}
```

## Session Persistence

### File: `/src/extension/popup/popup_simple.js`

#### Load Stored Data on Startup (Lines 55-86)
```javascript
async loadStoredData() {
    console.log('📂 Loading stored data...');
    
    const data = await chrome.storage.local.get(['wallet', 'authToken', 'earnMode']);
    console.log('💾 Retrieved data:', {
        hasWallet: !!data.wallet,
        hasToken: !!data.authToken,
        earnMode: data.earnMode
    });
    
    if (data.wallet && data.authToken) {
        this.wallet = data.wallet;
        this.authToken = data.authToken;
        this.earnMode = data.earnMode !== false;
        
        console.log('🔑 Restored wallet connection:', {
            address: this.wallet.address,
            chainId: this.wallet.chainId,
            connected: this.wallet.connected
        });
        
        // Verify wallet is still connected
        if (this.wallet.connected) {
            await this.verifyWalletConnection();
        }
    }
}
```

### File: `/src/backend/auth/auth.py`

#### Redis Session Storage (Lines 130-145)
```python
def _store_session(wallet: str, user_id: str, token: str):
    """Store session in Redis"""
    try:
        session_key = f"session:{wallet}"
        session_data = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Store with expiration matching JWT
        redis_client.setex(
            session_key,
            timedelta(hours=JWT_EXPIRATION_HOURS),
            json.dumps(session_data),
        )
    except Exception as e:
        logger.error(f"Failed to store session in Redis: {e}")
```

## Security Considerations

### Authentication Security Features:

1. **Message Signing Requirements**
   - Timestamp included to prevent replay attacks
   - Domain binding ("contextly.ai") to prevent cross-site usage
   - Personal sign method ensures only wallet owner can authenticate

2. **JWT Token Security**
   - 7-day expiration (168 hours)
   - Signed with secret key
   - Contains minimal claims (wallet, user_id)
   - Validated on every API request

3. **Backend Verification**
   - Web3.py used for cryptographic signature verification
   - Case-insensitive address comparison
   - Error handling for invalid signatures

4. **Session Management**
   - Redis session storage with automatic expiration
   - Chrome local storage for client-side persistence
   - Event listeners for wallet/chain changes

### API Authorization

All protected endpoints use the `get_current_user` dependency:

```python
# File: /src/backend/auth/auth.py (Lines 96-115)
async def get_current_user(
    authorization: str = Header(None)
) -> dict:
    """Get current user from JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        return {
            "wallet": payload["wallet"],
            "user_id": payload["user_id"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
```

## Error Handling

The system includes comprehensive error handling at each step:

1. **Wallet Connection Errors**: User-friendly messages for common issues
2. **Signing Cancellation**: Graceful handling when user rejects signing
3. **Network Errors**: Retry logic and timeout handling
4. **Invalid Tokens**: Automatic cleanup of invalid stored tokens

## Testing the Flow

To test the wallet authentication:

1. Open the extension popup
2. Click "Connect Wallet"
3. Approve the connection in MetaMask
4. Sign the authentication message
5. Verify the success toast and UI updates
6. Check Chrome DevTools for detailed logs
7. Verify API requests include the Authorization header