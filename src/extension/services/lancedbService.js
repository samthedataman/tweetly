// lancedbService.js - LanceDB integration with wallet authentication
class LanceDBService {
  constructor() {
    this.apiUrl = 'http://localhost:8000'; // Your backend API
    this.walletService = null;
    this.userAddress = null;
    this.isAuthenticated = false;
  }

  // Initialize with wallet service
  async initialize(walletService) {
    this.walletService = walletService;
    
    // Check if wallet is connected
    if (walletService.address) {
      this.userAddress = walletService.address;
      await this.authenticateUser();
    }
  }

  // Authenticate user with wallet signature
  async authenticateUser() {
    if (!this.walletService || !this.userAddress) {
      throw new Error('Wallet not connected');
    }

    try {
      // Create authentication message
      const timestamp = Date.now();
      const message = `Contextly.ai Authentication\nAddress: ${this.userAddress}\nTimestamp: ${timestamp}`;
      
      // Sign the message
      const signature = await this.walletService.signMessage(message);
      
      // Send to backend for verification
      const response = await fetch(`${this.apiUrl}/v1/auth/wallet`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          address: this.userAddress,
          message: message,
          signature: signature,
          timestamp: timestamp
        })
      });

      if (response.ok) {
        const authData = await response.json();
        this.isAuthenticated = true;
        
        // Store auth token for future requests
        await chrome.storage.local.set({
          authToken: authData.token,
          authExpiry: authData.expiry
        });

        console.log('✅ User authenticated with LanceDB');
        return authData;
      } else {
        throw new Error(`Authentication failed: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Authentication error:', error);
      throw error;
    }
  }

  // Get auth headers for API requests
  async getAuthHeaders() {
    const data = await chrome.storage.local.get(['authToken', 'authExpiry']);
    
    if (!data.authToken || Date.now() > data.authExpiry) {
      // Token expired, re-authenticate
      await this.authenticateUser();
      const newData = await chrome.storage.local.get(['authToken']);
      return {
        'Authorization': `Bearer ${newData.authToken}`,
        'Content-Type': 'application/json',
        'X-Wallet-Address': this.userAddress
      };
    }

    return {
      'Authorization': `Bearer ${data.authToken}`,
      'Content-Type': 'application/json',
      'X-Wallet-Address': this.userAddress
    };
  }

  // Save conversation to LanceDB
  async saveConversation(conversationData) {
    if (!this.isAuthenticated || !this.userAddress) {
      throw new Error('User not authenticated');
    }

    try {
      const headers = await this.getAuthHeaders();
      
      // Prepare conversation data with wallet address
      const payload = {
        user_address: this.userAddress,
        conversation_id: conversationData.id || this.generateConversationId(),
        platform: conversationData.platform,
        title: conversationData.title,
        messages: conversationData.messages,
        metadata: {
          ...conversationData.metadata,
          wallet_address: this.userAddress,
          saved_at: new Date().toISOString(),
          chain_id: this.walletService.chainId
        },
        // Vector embeddings will be generated on the backend
        embedding_text: this.extractTextForEmbedding(conversationData)
      };

      const response = await fetch(`${this.apiUrl}/v1/conversations`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ Conversation saved to LanceDB:', result.conversation_id);
        
        // Update local storage with saved status
        await this.updateLocalConversation(result.conversation_id, { saved: true });
        
        return result;
      } else {
        throw new Error(`Failed to save conversation: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Failed to save conversation:', error);
      throw error;
    }
  }

  // Search conversations in LanceDB using vector similarity
  async searchConversations(query, options = {}) {
    if (!this.isAuthenticated || !this.userAddress) {
      throw new Error('User not authenticated');
    }

    try {
      const headers = await this.getAuthHeaders();
      
      const searchPayload = {
        query: query,
        user_address: this.userAddress,
        limit: options.limit || 10,
        filters: {
          platform: options.platform,
          date_range: options.dateRange,
          ...options.filters
        }
      };

      const response = await fetch(`${this.apiUrl}/v1/conversations/search`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(searchPayload)
      });

      if (response.ok) {
        const results = await response.json();
        console.log(`✅ Found ${results.conversations.length} conversations`);
        return results.conversations;
      } else {
        throw new Error(`Search failed: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Search error:', error);
      throw error;
    }
  }

  // Get user's conversation list
  async getConversationsList(options = {}) {
    if (!this.isAuthenticated || !this.userAddress) {
      throw new Error('User not authenticated');
    }

    try {
      const headers = await this.getAuthHeaders();
      
      const params = new URLSearchParams({
        user_address: this.userAddress,
        limit: options.limit || 50,
        offset: options.offset || 0,
        platform: options.platform || '',
        sort_by: options.sortBy || 'created_at',
        sort_order: options.sortOrder || 'desc'
      });

      const response = await fetch(`${this.apiUrl}/v1/conversations/list?${params}`, {
        method: 'GET',
        headers: headers
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`✅ Retrieved ${result.conversations.length} conversations`);
        return result;
      } else {
        throw new Error(`Failed to get conversations: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Failed to get conversations:', error);
      throw error;
    }
  }

  // Save user journey/navigation data
  async saveJourney(journeyData) {
    if (!this.isAuthenticated || !this.userAddress) {
      throw new Error('User not authenticated');
    }

    try {
      const headers = await this.getAuthHeaders();
      
      const payload = {
        user_address: this.userAddress,
        journey_id: journeyData.id,
        pages: journeyData.pages,
        start_time: journeyData.startTime,
        end_time: journeyData.endTime,
        duration: journeyData.duration,
        metadata: {
          wallet_address: this.userAddress,
          chain_id: this.walletService.chainId,
          page_count: journeyData.pageCount
        }
      };

      const response = await fetch(`${this.apiUrl}/v1/journeys`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ Journey saved to LanceDB:', result.journey_id);
        return result;
      } else {
        throw new Error(`Failed to save journey: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Failed to save journey:', error);
      throw error;
    }
  }

  // Get user stats and earnings
  async getUserStats() {
    if (!this.isAuthenticated || !this.userAddress) {
      throw new Error('User not authenticated');
    }

    try {
      const headers = await this.getAuthHeaders();
      
      const response = await fetch(`${this.apiUrl}/v1/users/${this.userAddress}/stats`, {
        method: 'GET',
        headers: headers
      });

      if (response.ok) {
        const stats = await response.json();
        console.log('✅ User stats retrieved:', stats);
        
        // Update local storage with stats
        await chrome.storage.local.set({
          userStats: stats,
          statsLastUpdated: Date.now()
        });
        
        return stats;
      } else {
        throw new Error(`Failed to get user stats: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Failed to get user stats:', error);
      throw error;
    }
  }

  // Helper methods
  generateConversationId() {
    return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  extractTextForEmbedding(conversationData) {
    // Extract meaningful text for vector embedding
    const texts = [];
    
    if (conversationData.title) {
      texts.push(conversationData.title);
    }
    
    if (conversationData.messages) {
      conversationData.messages.forEach(msg => {
        if (msg.text && msg.text.length > 10) {
          // Truncate very long messages to first 500 chars
          texts.push(msg.text.substring(0, 500));
        }
      });
    }
    
    return texts.join('\n\n');
  }

  async updateLocalConversation(conversationId, updates) {
    try {
      const data = await chrome.storage.local.get('conversations');
      const conversations = data.conversations || [];
      
      const index = conversations.findIndex(conv => conv.id === conversationId);
      if (index !== -1) {
        conversations[index] = { ...conversations[index], ...updates };
        await chrome.storage.local.set({ conversations });
      }
    } catch (error) {
      console.error('Failed to update local conversation:', error);
    }
  }

  // Sync local data with LanceDB
  async syncLocalData() {
    if (!this.isAuthenticated) {
      console.log('❌ Not authenticated, skipping sync');
      return;
    }

    try {
      console.log('🔄 Syncing local data with LanceDB...');
      
      // Get local conversations that haven't been saved
      const localData = await chrome.storage.local.get('conversations');
      const conversations = localData.conversations || [];
      
      const unsavedConversations = conversations.filter(conv => !conv.saved);
      
      console.log(`📤 Uploading ${unsavedConversations.length} unsaved conversations`);
      
      for (const conversation of unsavedConversations) {
        try {
          await this.saveConversation(conversation);
          await new Promise(resolve => setTimeout(resolve, 100)); // Rate limiting
        } catch (error) {
          console.error(`Failed to sync conversation ${conversation.id}:`, error);
        }
      }
      
      console.log('✅ Data sync completed');
      
    } catch (error) {
      console.error('Sync failed:', error);
    }
  }

  // Check if user is authenticated
  isUserAuthenticated() {
    return this.isAuthenticated && this.userAddress;
  }

  // Get current user address
  getUserAddress() {
    return this.userAddress;
  }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LanceDBService;
} else {
  window.LanceDBService = LanceDBService;
}