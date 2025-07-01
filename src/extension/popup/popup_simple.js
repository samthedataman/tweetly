// popup_enhanced.js - Direct wallet connection with better UX
class EnhancedPopup {
  constructor() {
    this.wallet = null;
    this.authToken = null;
    this.isConnecting = false;
    this.metaMaskConnector = null;
    this.stats = {
      conversationCount: 0,
      ctxtBalance: 0,
      dayStreak: 0
    };
    
    // Backend configuration
    this.API_BASE = 'http://localhost:8000';
    
    this.init();
  }

  async init() {
    console.log('🚀 Enhanced popup initializing...');
    
    // Initialize MetaMaskConnector
    if (typeof window.MetaMaskConnector !== 'undefined') {
      this.metaMaskConnector = new window.MetaMaskConnector();
      console.log('✅ MetaMaskConnector initialized');
    } else {
      console.error('❌ MetaMaskConnector not found on window');
    }
    
    // Load saved state
    await this.loadState();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Update UI
    this.updateUI();
    
    // Load stats if connected
    if (this.wallet?.connected) {
      await this.loadUserStats();
      
      // Notify background of existing connection
      console.log('📤 Notifying background of existing wallet connection');
      chrome.runtime.sendMessage({
        action: 'wallet_connected',
        data: {
          address: this.wallet.address,
          chainId: this.wallet.chainId,
          connected: true,
          earnMode: true,
          token: this.authToken,
          walletType: 'metamask'
        }
      });
    }
    
    console.log('✅ Enhanced popup ready');
  }

  async loadState() {
    try {
      // Load wallet and auth data
      const data = await chrome.storage.local.get(['wallet', 'authToken', 'earnMode']);
      
      if (data.wallet?.connected && data.authToken) {
        this.wallet = data.wallet;
        this.authToken = data.authToken;
        
        // Log token for testing
        console.log('🔑 ===========================================');
        console.log('🔑 LOADED AUTH TOKEN:', this.authToken);
        console.log('📋 COPY TOKEN FOR TESTING:', this.authToken);
        console.log('🏠 WALLET ADDRESS:', this.wallet.address);
        console.log('🔑 ===========================================');
      }
      
      // Load local stats
      const statsData = await chrome.storage.local.get(['stats', 'conversations']);
      this.stats = {
        conversationCount: statsData.conversations?.length || 0,
        ctxtBalance: statsData.stats?.ctxtBalance || 0,
        dayStreak: statsData.stats?.dayStreak || 0
      };
      
    } catch (error) {
      console.error('Failed to load state:', error);
    }
  }

  setupEventListeners() {
    // Wallet connect button - now handles connection directly
    document.getElementById('walletConnectBtn')?.addEventListener('click', async () => {
      if (this.wallet?.connected) {
        this.showWalletMenu();
      } else {
        await this.connectWallet();
      }
    });

    // Twitter/X connect button
    document.getElementById('xConnectBtn')?.addEventListener('click', async () => {
      await this.connectTwitter();
    });

    // Mode toggle
    document.getElementById('modeToggle')?.addEventListener('click', () => {
      this.toggleEarnMode();
    });

    // Action buttons
    document.querySelectorAll('.action-card').forEach(card => {
      card.addEventListener('click', () => {
        this.handleAction(card.dataset.action);
      });
    });

    // Listen for wallet events from background script
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.type === 'wallet_event') {
        this.handleWalletEvent(request.event, request.data);
      }
    });

    // Check platform status periodically
    this.updatePlatformStatus();
    setInterval(() => this.updatePlatformStatus(), 5000);
  }

  async connectWallet() {
    if (this.isConnecting) return;
    
    try {
      this.isConnecting = true;
      this.showConnectingState();
      
      console.log('🔗 Attempting wallet connection using MetaMaskConnector...');
      
      // Check if MetaMaskConnector is available
      if (!this.metaMaskConnector) {
        throw new Error('MetaMaskConnector not initialized. Please refresh the extension.');
      }
      
      // Use the MetaMaskConnector
      const connectionResult = await this.metaMaskConnector.activate();
      
      console.log('✅ MetaMask connection successful:', connectionResult);
      
      const { address, chainId } = connectionResult;
      
      // Generate message for signing
      const message = this.generateAuthMessage();
      
      // Sign message using MetaMaskConnector
      const signResult = await this.metaMaskConnector.signMessage(message);
      
      console.log('✅ Message signed successfully');
      
      // Register with backend (required for proper authentication)
      console.log('🚀 Starting backend registration...');
      console.log('📝 Registration data:', {
        wallet: address,
        message: message,
        signature: signResult.signature,
        chainId: chainId
      });
      
      let authData;
      try {
        authData = await this.registerWithBackend({
          wallet: address,
          signature: signResult.signature,
          message,
          chainId
        });
        console.log('✅ Backend registration successful');
        console.log('📦 Auth data received:', authData);
      } catch (error) {
        console.error('❌ Backend registration failed:', error.message);
        console.error('🔍 Full error:', error);
        
        // Don't store invalid tokens - show error instead
        this.showToast('Backend connection failed. Please try again.', 'error');
        this.isConnecting = false;
        this.updateWalletButton(false);
        
        // Clear any existing invalid tokens
        await chrome.storage.local.remove(['authToken']);
        
        return;
      }
      
      // Store connection data
      this.wallet = {
        address,
        chainId,
        connected: true,
        connectedAt: Date.now()
      };
      
      this.authToken = authData.token;
      
      // Log token for testing
      console.log('🔑 ===========================================');
      console.log('🔑 AUTH TOKEN STORED:', this.authToken);
      console.log('📋 COPY TOKEN FOR TESTING:', this.authToken);
      console.log('🏠 WALLET ADDRESS:', address);
      console.log('🔑 ===========================================');
      
      console.log('💾 Storing wallet data:', this.wallet);
      
      // Save to storage - always enable earn mode for new users
      await chrome.storage.local.set({
        wallet: this.wallet,
        authToken: this.authToken,
        earnMode: true  // Always enabled for new wallet connections
      });
      
      console.log('🎨 Updating UI after wallet connection...');
      
      // Update UI
      this.updateUI();
      await this.loadUserStats();
      
      console.log('✅ UI update complete. Wallet connected:', this.wallet?.connected);
      
      this.showToast('🎉 Wallet Connected! You\'re now earning CTXT tokens!', 'success');
      
      // Update mode section to show active state
      const modeSection = document.getElementById('modeSection');
      if (modeSection) {
        modeSection.classList.add('active');
      }
      
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
          console.log('✅ Background confirmed wallet connection:', response);
        }
      });
      
    } catch (error) {
      console.error('❌ Wallet connection failed:', error);
      console.error('Error details:', {
        message: error.message,
        stack: error.stack
      });
      
      // For debugging - show the exact error without trying to interpret it
      console.log('🔍 DEBUGGING - Full error details:', error);
      this.showToast(`DEBUGGING: ${error.message}`, 'error');
    } finally {
      this.isConnecting = false;
      this.hideConnectingState();
    }
  }

  async registerWithBackend(data) {
    const response = await fetch(`${this.API_BASE}/v1/wallet/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }
    
    const result = await response.json();
    
    // Log the token for testing
    console.log('🔑 AUTH TOKEN RECEIVED:', result.token);
    console.log('📋 COPY THIS TOKEN FOR TESTING:', result.token);
    console.log('🏠 Wallet Address:', data.wallet);
    
    return result;
  }

  async connectTwitter() {
    try {
      if (!this.wallet?.connected) {
        this.showToast('Please connect your wallet first', 'warning');
        await this.connectWallet();
        return;
      }
      
      // Check if already connected
      const twitterData = await chrome.storage.local.get('twitterConnection');
      if (twitterData.twitterConnection?.connected) {
        this.showToast(`Already connected: @${twitterData.twitterConnection.username}`, 'info');
        return;
      }
      
      // Initiate Twitter OAuth flow
      const response = await fetch(`${this.API_BASE}/v1/auth/x/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.authToken}`
        },
        body: JSON.stringify({
          wallet_address: this.wallet.address
        })
      });
      
      const data = await response.json();
      
      if (data.auth_url) {
        // Open OAuth URL in new tab
        chrome.tabs.create({ url: data.auth_url });
        
        // Listen for completion
        this.waitForTwitterAuth(data.session_id);
      }
      
    } catch (error) {
      console.error('Twitter connection failed:', error);
      this.showToast('Failed to connect Twitter', 'error');
    }
  }

  async waitForTwitterAuth(sessionId) {
    // Poll for Twitter auth completion
    const checkInterval = setInterval(async () => {
      try {
        const response = await fetch(`${this.API_BASE}/v1/auth/x/status?wallet=${this.wallet.address}`, {
          headers: {
            'Authorization': `Bearer ${this.authToken}`
          }
        });
        
        const data = await response.json();
        
        if (data.authenticated) {
          clearInterval(checkInterval);
          
          // Store Twitter connection
          await chrome.storage.local.set({
            twitterConnection: {
              connected: true,
              username: data.x_username,
              connectedAt: Date.now()
            }
          });
          
          this.updateUI();
          this.showToast(`✅ Connected @${data.x_username}`, 'success');
        }
      } catch (error) {
        console.error('Twitter status check failed:', error);
      }
    }, 2000);
    
    // Stop checking after 2 minutes
    setTimeout(() => clearInterval(checkInterval), 120000);
  }

  async loadUserStats() {
    if (!this.wallet?.connected || !this.authToken) return;
    
    try {
      const response = await fetch(`${this.API_BASE}/v1/stats/${this.wallet.address}`, {
        headers: {
          'Authorization': `Bearer ${this.authToken}`
        }
      });
      
      if (response.ok) {
        const stats = await response.json();
        this.stats = {
          conversationCount: stats.conversationCount || 0,
          ctxtBalance: stats.totalEarnings || 0,
          dayStreak: stats.dayStreak || 0
        };
        
        // Cache stats locally
        await chrome.storage.local.set({ stats: this.stats });
        
        this.updateStats();
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }

  showWalletMenu() {
    // Create dropdown menu
    const menu = document.createElement('div');
    menu.className = 'wallet-menu';
    menu.innerHTML = `
      <div class="wallet-menu-item" data-action="copy">
        <span>📋</span> Copy Address
      </div>
      <div class="wallet-menu-item" data-action="explorer">
        <span>🔍</span> View on Explorer
      </div>
      <div class="wallet-menu-item" data-action="switch">
        <span>🔄</span> Switch Wallet
      </div>
      <div class="wallet-menu-divider"></div>
      <div class="wallet-menu-item danger" data-action="disconnect">
        <span>🚪</span> Disconnect
      </div>
    `;
    
    // Position menu
    const btn = document.getElementById('walletConnectBtn');
    const rect = btn.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.top = `${rect.bottom + 5}px`;
    menu.style.right = '20px';
    menu.style.zIndex = '9999';
    
    // Add menu styles
    menu.style.cssText += `
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.1);
      padding: 8px;
      min-width: 200px;
    `;
    
    document.body.appendChild(menu);
    
    // Handle menu items
    menu.addEventListener('click', async (e) => {
      const item = e.target.closest('.wallet-menu-item');
      if (!item) return;
      
      const action = item.dataset.action;
      
      switch (action) {
        case 'copy':
          await navigator.clipboard.writeText(this.wallet.address);
          this.showToast('Address copied!', 'success');
          break;
          
        case 'explorer':
          const explorerUrl = this.getExplorerUrl(this.wallet.address, this.wallet.chainId);
          chrome.tabs.create({ url: explorerUrl });
          break;
          
        case 'switch':
          await this.disconnectWallet();
          await this.connectWallet();
          break;
          
        case 'disconnect':
          await this.disconnectWallet();
          break;
      }
      
      document.body.removeChild(menu);
    });
    
    // Close menu on outside click
    setTimeout(() => {
      const closeMenu = (e) => {
        if (!menu.contains(e.target)) {
          document.body.removeChild(menu);
          document.removeEventListener('click', closeMenu);
        }
      };
      document.addEventListener('click', closeMenu);
    }, 0);
  }

  async disconnectWallet() {
    try {
      // Clear storage
      await chrome.storage.local.remove(['wallet', 'authToken', 'earnMode']);
      
      // Reset state
      this.wallet = null;
      this.authToken = null;
      this.stats = {
        conversationCount: 0,
        ctxtBalance: 0,
        dayStreak: 0
      };
      
      // Update UI
      this.updateUI();
      
      // Notify background
      console.log('📤 Sending wallet disconnection message to background');
      chrome.runtime.sendMessage({ 
        action: 'wallet_disconnected',
        data: { connected: false }
      });
      
      this.showToast('Wallet disconnected', 'info');
      
    } catch (error) {
      console.error('Disconnect failed:', error);
      this.showToast('Failed to disconnect', 'error');
    }
  }

  toggleEarnMode() {
    if (!this.wallet?.connected) {
      this.showToast('Connect wallet to enable earn mode', 'warning');
      this.connectWallet();
      return;
    }
    
    const toggle = document.getElementById('modeToggle');
    const isEarnMode = toggle.classList.contains('active');
    
    if (isEarnMode) {
      toggle.classList.remove('active');
      chrome.storage.local.set({ earnMode: false });
      this.showToast('Earn mode disabled', 'info');
    } else {
      toggle.classList.add('active');
      chrome.storage.local.set({ earnMode: true });
      this.showToast('💰 Earn mode enabled!', 'success');
    }
  }

  updateUI() {
    this.updateWalletButton();
    this.updateStats();
    this.updateModeToggle();
    this.updateConnectionStatus();
  }

  updateConnectionStatus() {
    // Add a connection status indicator at the top
    let statusBar = document.getElementById('connectionStatusBar');
    
    if (!statusBar) {
      // Create status bar if it doesn't exist
      statusBar = document.createElement('div');
      statusBar.id = 'connectionStatusBar';
      statusBar.style.cssText = `
        padding: 8px 16px;
        text-align: center;
        font-size: 12px;
        font-weight: 600;
        border-bottom: 1px solid #e5e5e5;
      `;
      
      const container = document.querySelector('.popup-container');
      const header = document.querySelector('.popup-header');
      if (container && header) {
        container.insertBefore(statusBar, header.nextSibling);
      }
    }
    
    if (this.wallet?.connected) {
      const shortAddress = `${this.wallet.address.slice(0, 8)}...${this.wallet.address.slice(-6)}`;
      statusBar.innerHTML = `🟢 Connected: ${shortAddress} | Earning CTXT`;
      statusBar.style.backgroundColor = '#dcfce7';
      statusBar.style.color = '#059669';
      statusBar.style.display = 'block';
    } else {
      statusBar.style.display = 'none';
    }
  }

  updateWalletButton() {
    const btn = document.getElementById('walletConnectBtn');
    console.log('🎨 updateWalletButton called');
    console.log('Button found:', !!btn);
    console.log('Wallet state:', this.wallet);
    console.log('Wallet connected:', this.wallet?.connected);
    
    if (!btn) {
      console.log('❌ walletConnectBtn not found in DOM');
      return;
    }
    
    if (this.wallet?.connected) {
      const shortAddress = `${this.wallet.address.slice(0, 6)}...${this.wallet.address.slice(-4)}`;
      console.log('✅ Updating button to connected state:', shortAddress);
      
      btn.innerHTML = `
        <span class="status-dot connected"></span>
        <span class="wallet-connected-text">🟢 ${shortAddress}</span>
        <span class="dropdown-arrow">▼</span>
      `;
      btn.classList.add('connected');
      btn.style.backgroundColor = '#dcfce7';
      btn.style.borderColor = '#10b981';
      btn.style.color = '#059669';
      console.log('✅ Button classes after connect:', btn.className);
    } else {
      console.log('ℹ️ Updating button to disconnected state');
      btn.innerHTML = `
        <span class="wallet-icon">👛</span>
        <span>Connect Wallet</span>
      `;
      btn.classList.remove('connected');
      btn.style.backgroundColor = '';
      btn.style.borderColor = '';
      btn.style.color = '';
      console.log('ℹ️ Button classes after disconnect:', btn.className);
    }
  }

  updateStats() {
    document.getElementById('conversationCount').textContent = this.stats.conversationCount;
    document.getElementById('ctxtBalance').textContent = this.stats.ctxtBalance.toFixed(2);
    document.getElementById('dayStreak').textContent = this.stats.dayStreak;
  }

  updateModeToggle() {
    const toggle = document.getElementById('modeToggle');
    const label = document.getElementById('modeLabel');
    const modeSection = document.getElementById('modeSection');
    
    if (this.wallet?.connected && this.earnMode) {
      // Show earn mode active
      toggle?.classList.add('active');
      modeSection?.classList.add('active');
      if (label) {
        label.innerHTML = '💰 <strong>Earn Mode Active</strong>';
        label.style.color = 'var(--accent-secondary)';
      }
    } else if (this.wallet?.connected && !this.earnMode) {
      // Wallet connected but earn mode off
      toggle?.classList.remove('active');
      modeSection?.classList.remove('active');
      if (label) {
        label.innerHTML = 'Earn Mode Paused';
        label.style.color = 'var(--text-secondary)';
      }
    } else {
      // No wallet connected
      toggle?.classList.remove('active');
      modeSection?.classList.remove('active');
      if (label) {
        label.innerHTML = 'Free Mode';
        label.style.color = 'var(--text-secondary)';
      }
    }
  }

  async updatePlatformStatus() {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      const activeTab = tabs[0];
      
      const supportedPlatforms = [
        'claude.ai',
        'chat.openai.com',
        'chatgpt.com',
        'gemini.google.com',
        'aistudio.google.com'
      ];
      
      const statusBadge = document.getElementById('platformStatus');
      if (!statusBadge) return;
      
      const isSupported = supportedPlatforms.some(domain => 
        activeTab?.url?.includes(domain)
      );
      
      statusBadge.textContent = isSupported ? 'Active' : 'Inactive';
      statusBadge.className = `status-badge ${isSupported ? 'active' : 'inactive'}`;
      
    } catch (error) {
      console.error('Platform status update failed:', error);
    }
  }

  // UI Helper Methods
  showConnectingState() {
    const btn = document.getElementById('walletConnectBtn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <span class="spinner"></span>
        <span>Connecting...</span>
      `;
    }
  }

  hideConnectingState() {
    const btn = document.getElementById('walletConnectBtn');
    if (btn) {
      btn.disabled = false;
      this.updateWalletButton();
    }
  }

  async showMetaMaskAccountPrompt() {
    console.log('🦊 Showing MetaMask account setup prompt...');
    
    const modal = document.createElement('div');
    modal.className = 'metamask-prompt';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
    `;
    
    modal.innerHTML = `
      <div class="modal-content" style="
        background: white;
        padding: 24px;
        border-radius: 12px;
        max-width: 400px;
        text-align: center;
        margin: 20px;
      ">
        <div style="font-size: 48px; margin-bottom: 16px;">🦊</div>
        <h3 style="margin: 0 0 12px 0; color: #1a1a1a;">MetaMask Setup Required</h3>
        <p style="margin: 0 0 20px 0; color: #666; line-height: 1.5;">
          MetaMask is installed but has no accounts. Please follow these steps:
        </p>
        <div style="text-align: left; margin: 0 0 20px 0; color: #666; line-height: 1.6;">
          <div style="margin-bottom: 8px;"><strong>1.</strong> Click the MetaMask extension icon in your browser</div>
          <div style="margin-bottom: 8px;"><strong>2.</strong> Create a new wallet OR import existing wallet</div>
          <div style="margin-bottom: 8px;"><strong>3.</strong> Complete the setup process</div>
          <div><strong>4.</strong> Come back and try connecting again</div>
        </div>
        <div style="display: flex; gap: 12px; justify-content: center;">
          <button id="closeModal" style="
            padding: 12px 24px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
          ">Got it!</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    const closeBtn = document.getElementById('closeModal');
    
    if (closeBtn) {
      closeBtn.onclick = () => {
        document.body.removeChild(modal);
      };
    }
  }

  async showMetaMaskPrompt() {
    console.log('🦊 Checking MetaMask installation status...');
    
    // Try to detect if MetaMask is actually installed by checking for extension
    let isMetaMaskInstalled = false;
    try {
      // Check if we can query for MetaMask extension
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs[0]) {
        const response = await chrome.tabs.sendMessage(tabs[0].id, { action: 'ping' }).catch(() => null);
        // If we can communicate with content script, MetaMask might be loading
        isMetaMaskInstalled = true;
      }
    } catch (error) {
      console.log('Cannot determine MetaMask status via content script');
    }
    
    const modal = document.createElement('div');
    modal.className = 'metamask-prompt';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
    `;
    
    modal.innerHTML = `
      <div class="modal-content" style="
        background: white;
        padding: 24px;
        border-radius: 12px;
        max-width: 400px;
        text-align: center;
        margin: 20px;
      ">
        <div style="font-size: 48px; margin-bottom: 16px;">🦊</div>
        <h3 style="margin: 0 0 12px 0; color: #1a1a1a;">MetaMask Connection Issue</h3>
        <p style="margin: 0 0 20px 0; color: #666; line-height: 1.5;">
          ${isMetaMaskInstalled 
            ? 'MetaMask is installed but not responding. Please refresh the page and try again.'
            : 'MetaMask browser extension is required to connect your wallet.'
          }
        </p>
        <div style="display: flex; gap: 12px; justify-content: center;">
          ${isMetaMaskInstalled 
            ? `<button id="refreshPage" style="
                padding: 12px 24px;
                background: #f97316;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
              ">Refresh Page</button>`
            : `<button id="installMetaMask" style="
                padding: 12px 24px;
                background: #f97316;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
              ">Install MetaMask</button>`
          }
          <button id="closeModal" style="
            padding: 12px 24px;
            background: #e5e5e5;
            color: #333;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
          ">Cancel</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    const installBtn = document.getElementById('installMetaMask');
    const refreshBtn = document.getElementById('refreshPage');
    const closeBtn = document.getElementById('closeModal');
    
    if (installBtn) {
      installBtn.onclick = () => {
        chrome.tabs.create({ url: 'https://metamask.io/download/' });
        document.body.removeChild(modal);
      };
    }
    
    if (refreshBtn) {
      refreshBtn.onclick = async () => {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs[0]) {
          chrome.tabs.reload(tabs[0].id);
        }
        window.close(); // Close popup
      };
    }
    
    if (closeBtn) {
      closeBtn.onclick = () => {
        document.body.removeChild(modal);
      };
    }
  }

  handleWalletEvent(event, data) {
    switch (event) {
      case 'accountsChanged':
        if (data.accounts.length === 0) {
          this.disconnectWallet();
        } else if (data.accounts[0] !== this.wallet?.address) {
          // Account switched, reconnect
          this.connectWallet();
        }
        break;
        
      case 'chainChanged':
        if (this.wallet) {
          this.wallet.chainId = parseInt(data.chainId, 16);
          chrome.storage.local.set({ wallet: this.wallet });
          this.updateUI();
        }
        break;
    }
  }

  generateAuthMessage() {
    const timestamp = new Date().toISOString();
    return `Sign this message to authenticate with Contextly:\n\nTimestamp: ${timestamp}\nDomain: contextly.ai`;
  }

  getExplorerUrl(address, chainId) {
    const explorers = {
      1: `https://etherscan.io/address/${address}`,
      8453: `https://basescan.org/address/${address}`,
      84532: `https://sepolia.basescan.org/address/${address}`
    };
    return explorers[chainId] || `https://etherscan.io/address/${address}`;
  }

  handleAction(action) {
    const actions = {
      import: () => this.showImportDialog(),
      search: () => this.showSearchDialog(),
      export: () => this.exportConversations(),
      share: () => this.shareConversations()
    };
    
    const handler = actions[action];
    if (handler) {
      handler();
    } else {
      this.showToast(`${action} coming soon!`, 'info');
    }
  }

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    const styles = {
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      padding: '12px 20px',
      borderRadius: '8px',
      backgroundColor: {
        info: '#3b82f6',
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b'
      }[type],
      color: 'white',
      fontSize: '14px',
      fontWeight: '500',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      zIndex: '10000',
      opacity: '0',
      transform: 'translateY(20px)',
      transition: 'all 0.3s ease'
    };
    
    Object.assign(toast.style, styles);
    document.body.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
    });
    
    // Remove after 3 seconds
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(20px)';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
}

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
  window.contextlyPopup = new EnhancedPopup();
});