// AI Chat to Twitter Extension - Full Content Script
// Works on Claude.ai, ChatGPT, and Google AI Studio

// Immediate test to verify script injection
(function () {
  console.log('🚀 AI Chat to Twitter Extension loaded!');
  console.log('Current URL:', window.location.href);
  console.log('Current hostname:', window.location.hostname);
  console.log('Script injected at:', new Date().toISOString());
  console.log('Document ready state:', document.readyState);
  console.log('Body element exists:', !!document.body);
})();

class AITwitterExtension {
  constructor() {
    console.log('🏗️ AITwitterExtension constructor called!');
    this.apiUrl = 'http://localhost:8000';
    this.platform = this.detectPlatform();
    this.processedMessages = new Set();
    this.observerActive = false;
    this.messageCount = 0;
    console.log('🔧 Extension configured:', {
      apiUrl: this.apiUrl,
      platform: this.platform
    });
    this.createStatusIndicator();
    this.init();
  }
  
  createStatusIndicator() {
    // Create persistent status indicator
    this.indicator = document.createElement('div');
    this.indicator.id = 'ai-twitter-status';
    this.indicator.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 8px 16px;
      border-radius: 20px;
      z-index: 9999;
      font-size: 12px;
      font-family: system-ui, -apple-system, sans-serif;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.3s ease;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
    `;
    
    // Add status dot
    const statusDot = document.createElement('span');
    statusDot.style.cssText = `
      width: 8px;
      height: 8px;
      background: #4CAF50;
      border-radius: 50%;
      display: inline-block;
    `;
    
    const statusText = document.createElement('span');
    statusText.textContent = 'AI Twitter Active';
    
    this.indicator.appendChild(statusDot);
    this.indicator.appendChild(statusText);
    
    // Wait for body to be ready
    if (document.body) {
      document.body.appendChild(this.indicator);
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        document.body.appendChild(this.indicator);
      });
    }
  }
  
  updateStatus(status, isProcessing = false) {
    if (!this.indicator) return;
    
    const statusDot = this.indicator.querySelector('span:first-child');
    const statusText = this.indicator.querySelector('span:last-child');
    
    if (isProcessing) {
      statusDot.style.background = '#ff9800';
      statusDot.style.animation = 'pulse 1s infinite';
    } else {
      statusDot.style.background = '#4CAF50';
      statusDot.style.animation = 'none';
    }
    
    statusText.textContent = status;
  }

  detectPlatform() {
    const hostname = window.location.hostname;
    if (hostname.includes('claude.ai')) return 'claude';
    if (hostname.includes('chat.openai.com') || hostname.includes('chatgpt.com')) return 'chatgpt';
    if (hostname.includes('aistudio.google.com')) return 'google';
    return 'unknown';
  }

  init() {
    console.log(`🎯 Platform detected: ${this.platform}`);
    console.log('📍 Current URL:', window.location.href);
    console.log('🔍 Starting extension initialization...');

    // Add platform class to body for platform-specific styling
    document.body.classList.add(`platform-${this.platform}`);

    // Load settings from storage if available
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
      console.log('📦 Loading settings from Chrome storage...');
      chrome.storage.sync.get(['apiUrl', 'enabled'], (result) => {
        if (result.apiUrl) {
          this.apiUrl = result.apiUrl;
        }
        if (result.enabled !== undefined) {
          this.enabled = result.enabled;
        }
        console.log('✅ Settings loaded, setting up observer...');
        this.setupObserver();
      });
    } else {
      // If chrome storage is not available, just setup observer
      console.log('⚠️ Chrome storage not available, using defaults...');
      this.enabled = true;
      this.setupObserver();
    }

    // Listen for settings changes if runtime is available
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
      chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'updateApiUrl') {
          this.apiUrl = request.apiUrl;
        }
        if (request.action === 'toggleEnabled') {
          this.enabled = request.enabled;
          this.updateUI();
        }
      });
    }
  }

  setupObserver() {
    console.log('🔄 Setting up observer...');
    
    // Set up a more frequent check specifically for Claude streaming
    if (this.platform === 'claude') {
      setInterval(() => {
        // Look for messages that just finished streaming
        const streamingMessages = document.querySelectorAll('div[data-is-streaming="false"]:not([data-twitter-processed])');
        if (streamingMessages.length > 0) {
          console.log('🏁 Found finished streaming messages:', streamingMessages.length);
          this.updateStatus('Processing new messages...', true);
          this.attachButtons();
          setTimeout(() => {
            this.updateStatus(`AI Twitter Active (${this.processedMessages.size} messages)`, false);
          }, 500);
        }
      }, 500); // Check every 500ms for faster response
    } else {
      // For other platforms, check less frequently
      setInterval(() => {
        this.attachButtons();
      }, 2000);
    }

    // Platform-specific container selectors
    const containerSelectors = {
      claude: [
        'body',  // Start with body to catch everything
        'main',
        '.conversation-container',
        '#root',
        'div[class*="flex-1"]',
        // More specific Claude containers
        'div[class*="flex"][class*="flex-col"][class*="overflow-hidden"]',
        'div[class*="relative"][class*="flex-1"]'
      ],
      chatgpt: ['main', '#__next', '.flex-1', '[role="main"]'],
      google: ['main', '.conversation-container', '.chat-container']
    };

    const selectors = containerSelectors[this.platform] || containerSelectors.claude;
    console.log('📋 Container selectors for platform:', selectors);

    // Try to find container and start observing
    const findAndObserve = () => {
      console.log('🔍 Looking for container...');

      for (const selector of selectors) {
        const container = document.querySelector(selector);
        console.log(`Checking selector "${selector}":`, container ? 'Found' : 'Not found');

        if (container && !this.observerActive) {
          console.log(`✅ Found container: ${selector}`);
          console.log('Container element:', container);
          console.log('Container classes:', container.className);
          console.log('Container ID:', container.id);
          this.observerActive = true;

          // Debounce function to prevent excessive calls
          let debounceTimer;
          const debouncedAttachButtons = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
              this.attachButtons();
            }, 200); // Wait 200ms after last mutation
          };

          const observer = new MutationObserver((mutations) => {
            // Check for new nodes or streaming status changes
            let shouldUpdate = false;
            
            for (const mutation of mutations) {
              // Check for new nodes
              if (mutation.addedNodes.length > 0) {
                shouldUpdate = true;
              }
              
              // Check for streaming status changes (Claude specific)
              if (mutation.type === 'attributes' && 
                  mutation.attributeName === 'data-is-streaming' &&
                  mutation.target.getAttribute('data-is-streaming') === 'false') {
                console.log('🏁 Message finished streaming!');
                shouldUpdate = true;
              }
              
              // Check for new message containers
              if (mutation.target.nodeType === 1) { // Element node
                const element = mutation.target;
                if (element.matches && (
                    element.matches('div[data-is-streaming]') ||
                    element.matches('div[class*="font-claude-message"]') ||
                    element.matches('div[class*="group"][class*="relative"]')
                )) {
                  shouldUpdate = true;
                }
              }
            }
            
            if (shouldUpdate) {
              console.log('🔄 Content change detected, updating buttons...');
              debouncedAttachButtons();
            }
          });

          observer.observe(container, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-is-streaming', 'class']
          });

          // Initial attachment
          console.log('🎯 Running initial button attachment...');
          this.updateStatus('Scanning for messages...', true);
          this.attachButtons();
          setTimeout(() => {
            this.updateStatus(`AI Twitter Active (${this.processedMessages.size} messages)`, false);
          }, 1000);
          return true;
        }
      }
      console.log('❌ No container found yet');
      return false;
    };

    // Keep trying until we find the container
    if (!findAndObserve()) {
      console.log('⏳ Container not found, will retry every second...');
      const interval = setInterval(() => {
        console.log('🔄 Retrying container search...');
        if (findAndObserve()) {
          console.log('✅ Container found on retry!');
          clearInterval(interval);
        }
      }, 1000);
    }
  }

  getMessageSelectors() {
    const selectors = {
      claude: [
        // Claude.ai selectors - look for any streaming div
        'div[data-is-streaming]',
        'div[data-is-streaming="false"]',
        'div[data-is-streaming="true"]',
        'div[class*="font-claude-message"]',
        // Message containers
        'div[class*="group"][class*="relative"]',
        'div[class*="whitespace-pre-wrap"]',
        // Artifact containers
        'iframe[title*="artifact"]',
        'iframe[src*="artifact"]',
        '.artifact-container'
      ],
      chatgpt: [
        // ChatGPT selectors with wildcards
        'div[class*="group/conversation-turn"][class*="agent-turn"]',
        'div[class*="conversation-turn"][data-message-author-role="assistant"]',
        // Pattern matching for message containers
        'div[class*="relative"][class*="flex"][class*="agent-turn"]',
        'div[class*="text-message"][data-message-id]',
        // Button container patterns
        'div[class*="agent-turn"]:has(button[aria-label*="Copy"])',
        'div[data-message-author-role="assistant"]:has(div[class*="flex"]:has(button))',
        // Generic patterns
        '[data-message-author-role="assistant"]',
        '[data-testid*="conversation"]',
        'div[class*="markdown"][class*="prose"]',
        'div[class*="text-token"]'
      ],
      google: [
        // Google AI Studio selectors with wildcards
        'div[class*="chat-turn-container"][class*="model"]:has(.turn-footer)',
        'div[class*="chat-turn"]:has(.turn-footer):has(button[aria-label*="response"])',
        // Pattern matching for messages with feedback
        'div[class*="render"]:has(.turn-footer):has(.model-prompt-container)',
        'div[data-turn-role]:has(.turn-footer)',
        // Exclude input areas
        'div[class*="chat-turn"]:has(.turn-footer):not(:has([contenteditable]))',
        'div[class*="model"]:has(button[aria-label*="Good response"])',
        // Container patterns
        'div:has(> .model-prompt-container):has(> .turn-footer)',
        'div[class*="chat"]:has(.turn-footer[class*="ng-star-inserted"])'
      ]
    };

    return selectors[this.platform] || [...selectors.claude, ...selectors.chatgpt];
  }

  attachButtons() {
    console.log('🚀 attachButtons called!');
    console.log('🔍 Platform:', this.platform);
    console.log('🔍 Enabled:', this.enabled);
    console.log('🔍 Current URL:', window.location.href);

    if (this.enabled === false) {
      console.log('❌ Extension is disabled, returning...');
      return;
    }

    const selectors = this.getMessageSelectors();
    console.log('📋 Got selectors:', selectors.length, 'selectors for platform:', this.platform);

    const foundMessages = new Set();

    // Try each selector
    selectors.forEach((selector, index) => {
      try {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
          // Special handling for iframes (artifacts)
          if (el.tagName === 'IFRAME') {
            this.handleArtifactIframe(el);
            return;
          }

          // Check if element has substantial text content
          const text = el.textContent || '';
          if (text.length > 30 && text.length < 10000) {
            foundMessages.add(el);
          }
        });
      } catch (e) {
        console.error(`❌ Error with selector:`, e.message || e);
      }
    });

    // Process found messages
    console.log(`📊 Processing ${foundMessages.size} messages on ${this.platform}`);

    foundMessages.forEach(msg => {
      // Skip if this message or any parent already has our controls
      if (msg.querySelector('.ai-twitter-controls') || 
          msg.querySelector('.ai-twitter-x-btn') ||
          msg.closest('[data-twitter-processed="true"]')) {
        return;
      }

      // Create unique identifier for this message
      const messageId = this.getMessageId(msg);

      // Skip if already processed
      if (this.processedMessages.has(messageId)) {
        return;
      }

      // Mark as processed
      this.processedMessages.add(messageId);
      msg.dataset.twitterProcessed = 'true';

      // Ensure relative positioning for button placement
      const currentPosition = window.getComputedStyle(msg).position;
      if (currentPosition === 'static') {
        msg.style.position = 'relative';
      }

      // Create X button and hover panel
      const xButton = this.createPlatformXButton();

      // Create hover panel
      const controlsDiv = document.createElement('div');
      controlsDiv.className = 'ai-twitter-controls';
      controlsDiv.innerHTML = `
        <div class="control-buttons">
          <button class="twitter-control-btn tweet-btn">
            <span class="btn-icon">🐦</span>
            <span class="btn-label">Tweet</span>
          </button>
          <button class="twitter-control-btn sms-btn">
            <span class="btn-icon">💬</span>
            <span class="btn-label">SMS</span>
          </button>
          <button class="twitter-control-btn condense-btn">
            <span class="btn-icon">📝</span>
            <span class="btn-label">Condense</span>
          </button>
          <button class="twitter-control-btn style-btn">
            <span class="btn-icon">✨</span>
            <span class="btn-label">Style</span>
          </button>
          <button class="twitter-control-btn substack-btn">
            <span class="btn-icon">📰</span>
            <span class="btn-label">Substack</span>
          </button>
          <button class="twitter-control-btn medium-btn">
            <span class="btn-icon">📄</span>
            <span class="btn-label">Medium</span>
          </button>
        </div>
        <div class="style-dropdown hidden">
          <select class="style-select">
            <option value="">Select style...</option>
            <option value="professional">Professional</option>
            <option value="casual">Casual</option>
            <option value="humorous">Humorous</option>
            <option value="concise">Concise</option>
            <option value="creative">Creative</option>
            <option value="technical">Technical</option>
          </select>
          <button class="apply-style-btn">Apply</button>
        </div>
      `;

      // Add event handlers for hover panel buttons
      const tweetBtn = controlsDiv.querySelector('.tweet-btn');
      const smsBtn = controlsDiv.querySelector('.sms-btn');
      const condenseBtn = controlsDiv.querySelector('.condense-btn');
      const styleBtn = controlsDiv.querySelector('.style-btn');
      const substackBtn = controlsDiv.querySelector('.substack-btn');
      const mediumBtn = controlsDiv.querySelector('.medium-btn');
      const styleDropdown = controlsDiv.querySelector('.style-dropdown');
      const styleSelect = controlsDiv.querySelector('.style-select');
      const applyStyleBtn = controlsDiv.querySelector('.apply-style-btn');

      // Helper function to extract text
      const getText = () => {
        let text = this.extractText(msg);
        if (text.length < 50) {
          const claudeMessage = msg.querySelector('.font-claude-message') ||
            msg.querySelector('div[class*="whitespace-normal"][class*="break-words"]');
          if (claudeMessage) {
            text = this.extractText(claudeMessage);
          }
        }
        return text;
      };

      // Tweet button handler
      tweetBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const text = getText();
        this.showDialog(text, 'Share on X', 'Select a style to condense', text);
      });

      // SMS button handler
      smsBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const text = getText();
        const smsText = encodeURIComponent(text.substring(0, 160));
        window.open(`sms:?&body=${smsText}`, '_blank');
      });

      // Condense button handler
      condenseBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const text = getText();
        try {
          const condensed = await this.processText(text, 'condense');
          this.showDialog(condensed, 'Condensed Text', 'AI-condensed version');
        } catch (error) {
          console.error('Error condensing:', error);
          this.showDialog(text, 'Share on X');
        }
      });

      // Style button handler - toggle dropdown
      styleBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        styleDropdown.classList.toggle('hidden');
      });
      
      // Apply style button handler
      applyStyleBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const selectedStyle = styleSelect.value;
        if (selectedStyle) {
          const text = getText();
          try {
            const styled = await this.processText(text, 'restyle', selectedStyle);
            this.showDialog(styled, `${selectedStyle.charAt(0).toUpperCase() + selectedStyle.slice(1)} Style`, 'AI-styled version', text);
          } catch (error) {
            console.error('Error applying style:', error);
            this.showDialog(text, 'Share on X');
          }
          styleDropdown.classList.add('hidden');
          styleSelect.value = '';
        }
      });
      
      // Substack button handler
      substackBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const text = getText();
        this.showArticleDialog(text, 'substack');
      });
      
      // Medium button handler
      mediumBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const text = getText();
        this.showArticleDialog(text, 'medium');
      });

      // Add click handler for X button
      xButton.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();

        // Show loading state
        const originalContent = xButton.innerHTML;
        const loadingHtml = this.platform === 'claude' ?
          '<svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.25"></circle><path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="2"></path></svg>' :
          '<div class="loading-spinner" style="width: 14px; height: 14px;"></div>';
        xButton.innerHTML = loadingHtml;
        xButton.disabled = true;

        try {
          // Extract text from the message element
          let text = this.extractText(msg);

          // If text is too short, try to find the actual message content
          if (text.length < 50) {
            // For Claude, look for the font-claude-message content
            const claudeMessage = msg.querySelector('.font-claude-message') ||
              msg.querySelector('div[class*="whitespace-normal"][class*="break-words"]');
            if (claudeMessage) {
              text = this.extractText(claudeMessage);
            }
          }

          // Show dialog immediately with original text
          this.showDialog(text, 'Share on X', 'Select a style to condense', text);
        } catch (error) {
          console.error('Error extracting text:', error);
          // Fallback
          const text = this.extractText(msg);
          this.showDialog(text, 'Share on X', '', text);
        } finally {
          xButton.innerHTML = originalContent;
          xButton.disabled = false;
        }
      });

      // Platform-specific X button placement
      this.attachXButtonToPlatform(msg, xButton);

      // Append hover panel to message
      msg.appendChild(controlsDiv);
    });

    // Also attach floating button for general Claude interface
    this.attachFloatingButton();
  }

  getMessageId(element) {
    // Create a unique identifier based on content and position
    const text = element.textContent || '';
    const position = Array.from(element.parentNode?.children || []).indexOf(element);
    return `${text.substring(0, 50)}_${position}_${text.length}`;
  }


  createPlatformXButton() {
    let button;

    if (this.platform === 'claude') {
      // Claude style button
      button = document.createElement('button');
      button.className = 'inline-flex items-center justify-center relative shrink-0 ring-offset-2 ring-offset-bg-300 ring-accent-main-100 focus-visible:outline-none focus-visible:ring-1 disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:drop-shadow-none text-text-200 transition-all font-styrene active:bg-bg-400 hover:bg-bg-400 hover:text-text-100 h-8 w-8 rounded-md active:scale-95 ai-twitter-x-btn';
      button.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      `;
      button.title = 'Post to X';
    } else if (this.platform === 'chatgpt') {
      // ChatGPT style button
      button = document.createElement('button');
      button.className = 'flex items-center justify-center text-token-text-secondary transition hover:text-token-text-primary radix-state-open:text-token-text-secondary ai-twitter-x-btn';
      button.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" fill="currentColor" stroke="none"/>
        </svg>
      `;
      button.title = 'Post to X';
    } else if (this.platform === 'google') {
      // Google AI Studio style button
      button = document.createElement('button');
      button.className = 'mat-mdc-icon-button mat-icon-button mat-icon-button-base ai-twitter-x-btn';
      button.innerHTML = `
        <span class="mat-mdc-button-persistent-ripple mdc-icon-button__ripple"></span>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" opacity="0.7">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      `;
      button.title = 'Post to X';
    } else {
      // Generic fallback
      button = document.createElement('button');
      button.className = 'ai-twitter-x-btn';
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      `;
      button.title = 'Post to X';
    }

    return button;
  }

  attachXButtonToPlatform(messageElement, xButton) {
    console.log('🎯 attachXButtonToPlatform called for platform:', this.platform);

    // First check if this message already has an X button anywhere
    if (messageElement.querySelector('.ai-twitter-x-btn')) {
      console.log('⚠️ Message already has an X button, skipping attachment...');
      return;
    }

    if (this.platform === 'claude') {
      // Claude: Find the action buttons container (copy, thumbs, retry)
      const actionSelectors = [
        // Look for the action buttons container - NOT the footer
        'div[class*="rounded-lg"]:has(button[aria-label*="Copy"]):not(:has(svg path[d*="m19.6 66.5"]))',
        'div[class*="rounded-lg"]:has(button[aria-label*="Good response"])',
        'div[class*="rounded-lg"]:has(button[aria-label*="Bad response"])',
        'div[class*="rounded-lg"]:has(button[aria-label*="Retry"])',
        // Primary selector for the exact container
        'div[class*="rounded-lg"][class*="transition"][class*="pointer-events-auto"]:has(button)',
        'div[class*="rounded-lg"][class*="min-w-max"][class*="pointer-events-auto"]:has(button)',
        // More specific patterns
        'div[class*="rounded-lg"][class*="translate-x-"][class*="translate-y-"]:has(button)',
        // Fallback patterns
        'div[class*="pointer-events-auto"]:has(button[data-testid*="action-bar"])',
        'div[class*="rounded-lg"]:has(button[data-testid="action-bar-copy"])'
      ];

      // Check if this is the entire Claude footer section (we want to process it)
      const hasClaudeFooter = messageElement.querySelector('a[href*="support.anthropic.com"]') ||
        messageElement.querySelector('svg path[d*="m19.6 66.5"]');

      // Find the rounded-lg container
      for (const selector of actionSelectors) {
        const roundedContainers = messageElement.querySelectorAll(selector);

        for (const roundedContainer of roundedContainers) {

          // Skip if this is the Claude footer with logo
          const claudeLogo = roundedContainer.querySelector('svg path[d*="m19.6 66.5"]');
          const supportLink = roundedContainer.querySelector('a[href*="support.anthropic.com"]');
          const isClaudeFooter = claudeLogo || supportLink;

          if (isClaudeFooter) {
            continue;
          }

          // Check if this container has the action buttons (existing logic)
          const copyButton = roundedContainer.querySelector('button[data-testid*="action-bar"]') ||
            roundedContainer.querySelector('button[aria-label*="Copy"]');
          const retryButton = roundedContainer.querySelector('button[aria-label*="Retry"]');
          const closedButton = roundedContainer.querySelector('button[data-state="closed"]');
          const hasActionButtons = copyButton || closedButton || retryButton;

          console.log('Copy button found:', !!copyButton);
          console.log('Retry button found:', !!retryButton);
          console.log('Closed button found:', !!closedButton);

          if (!hasActionButtons && !isClaudeFooter) {
            console.log('❌ No action buttons or Claude footer found in this container, skipping...');
            continue;
          }

          console.log('✅ Action buttons found!');

          // Find the inner flex container that holds the buttons
          const flexSelectors = [
            'div[class*="text-text-"][class*="flex"]',
            'div[class*="flex"][class*="items-stretch"]',
            'div[class*="flex"][class*="gap"]:has(button)',
            'div[class*="flex"]:has(button[aria-label])',
            'div[class*="flex"]:has(button)'
          ];

          let buttonContainer = null;
          for (const flexSelector of flexSelectors) {
            buttonContainer = roundedContainer.querySelector(flexSelector);
            if (buttonContainer) {
              console.log(`✅ Found button container with selector: ${flexSelector}`);
              break;
            }
          }

          if (buttonContainer) {
            console.log('🎯 Button container found:', buttonContainer);
            console.log('Button container classes:', buttonContainer.className);
            console.log('Existing buttons in container:', buttonContainer.querySelectorAll('button').length);

            // Check if X button already exists in this container
            if (buttonContainer.querySelector('.ai-twitter-x-btn')) {
              console.log('⚠️ X button already exists in this container, skipping...');
              return;
            }

            // Style the X button to match Claude's design
            xButton.style.marginRight = '0.25rem'; // Add margin to the right since it's on the left now

            // Find action buttons to determine insertion point
            const copyButton = buttonContainer.querySelector('button[aria-label*="Copy"]');
            const thumbsUpButton = buttonContainer.querySelector('button[aria-label*="Good response"]');
            const thumbsDownButton = buttonContainer.querySelector('button[aria-label*="Bad response"]');
            const retryButton = buttonContainer.querySelector('button[aria-label*="Retry"]');

            console.log('Action buttons found:');
            console.log('- Copy:', !!copyButton);
            console.log('- Thumbs up:', !!thumbsUpButton);
            console.log('- Thumbs down:', !!thumbsDownButton);
            console.log('- Retry:', !!retryButton);

            // Insert X button at the beginning (left side) of the button container
            if (copyButton) {
              // Insert before copy button (leftmost position)
              console.log('📍 Inserting X button before copy button (left side)');
              copyButton.parentElement.insertBefore(xButton, copyButton);
            } else if (buttonContainer.firstChild) {
              // Insert as first child
              console.log('📍 Inserting X button as first child (left side)');
              buttonContainer.insertBefore(xButton, buttonContainer.firstChild);
            } else {
              // Fallback: append to button container
              console.log('📍 Appending X button to button container');
              buttonContainer.appendChild(xButton);
            }

            console.log('✅ X button added to Claude message!');
            return;
          } else {
            console.log('❌ Could not find button container within rounded container');
          }
        }
      }

      // Fallback: Try to find any button in the message and insert X button next to it
      console.log('🔎 Trying fallback approach...');
      const anyButton = messageElement.querySelector('button[aria-label*="Copy"]') ||
        messageElement.querySelector('button[aria-label*="Retry"]') ||
        messageElement.querySelector('button[data-testid*="action-bar"]');

      if (anyButton && anyButton.parentElement) {
        console.log('✅ Found a button via fallback, inserting X button');

        // Check if X button already exists in this parent
        if (anyButton.parentElement.querySelector('.ai-twitter-x-btn')) {
          console.log('⚠️ X button already exists via fallback, skipping...');
          return;
        }

        xButton.classList.add('ml-1');
        anyButton.parentElement.appendChild(xButton);
        console.log('✅ X button added via fallback method!');
        return;
      }

      console.log('❌ Could not find suitable container for X button after trying all selectors and fallback');
    } else if (this.platform === 'chatgpt') {
      // ChatGPT: Find the copy/edit button container
      const actionSelectors = [
        // Wildcard selectors for button containers
        'div[class*="flex"][class*="items"]:has(button[aria-label*="Copy"])',
        'div[class*="flex"]:has(button[data-testid*="copy"])',
        'div[class*="gap"]:has(button[class*="text-token"])',
        // Pattern matching for action areas
        'div[class*="justify-"]:has(button[aria-label])',
        'div[class*="items-center"]:has(button[data-state])',
        // Direct button patterns
        'button[aria-label*="Copy"]',
        'button[data-testid*="action"]',
        'button[class*="hover:bg-token"]',
        // Parent container patterns
        'div:has(> button[aria-label*="Copy"])',
        'div:has(> button[class*="rounded-lg"])'
      ];

      // Look for action buttons container
      let actionContainer = null;
      for (const selector of actionSelectors) {
        const elements = messageElement.querySelectorAll(selector);
        for (const element of elements) {
          // Check if this is the action buttons container
          if (element.querySelector('button[aria-label*="Copy"]') ||
            element.querySelector('button[data-testid="copy-turn-action-button"]')) {
            actionContainer = element;
            break;
          } else if (element.tagName === 'BUTTON' &&
            (element.getAttribute('aria-label')?.includes('Copy') ||
              element.getAttribute('data-testid') === 'copy-turn-action-button')) {
            actionContainer = element.parentElement;
            break;
          }
        }
        if (actionContainer) break;
      }

      if (actionContainer) {
        // Check if X button already exists
        if (actionContainer.querySelector('.ai-twitter-x-btn')) {
          console.log('⚠️ X button already exists in ChatGPT container, skipping...');
          return;
        }

        // Match ChatGPT's button styling
        xButton.classList.add('ml-1'); // Add spacing
        actionContainer.appendChild(xButton);
        return;
      }
    } else if (this.platform === 'google') {
      // Google AI Studio: Find the thumbs up/down buttons on messages (not input area)

      // First check if this is actually a message element and not an input
      const isInputArea = messageElement.closest('.chat-input') ||
        messageElement.closest('.input-container') ||
        messageElement.closest('[contenteditable="true"]') ||
        messageElement.querySelector('textarea') ||
        messageElement.querySelector('input[type="text"]') ||
        messageElement.querySelector('[contenteditable="true"]') ||
        messageElement.classList.contains('rounded-lg') && !messageElement.querySelector('.turn-footer');

      if (isInputArea) {
        console.log('Skipping input area element');
        return;
      }

      // Check if this element has the turn-footer with thumbs buttons
      const hasTurnFooter = messageElement.querySelector('.turn-footer:has(button[aria-label*="Good response"])') ||
        messageElement.querySelector('.turn-footer:has(button[aria-label*="Bad response"])');

      if (!hasTurnFooter) {
        console.log('Not a message element with feedback buttons');
        return;
      }

      const actionSelectors = [
        // Wildcard selectors for Google AI Studio
        'div[class*="turn-footer"]',
        'div[class*="footer"]:has(button[aria-label*="response"])',
        // Button patterns
        'button[aria-label*="response"]',
        'button[class*="feedback"]',
        'button:has(mat-icon[fonticon*="thumb"])',
        // Container patterns
        'div[class*="footer"]:has(button:has(mat-icon))',
        'div[class*="actions"]:has(button[aria-label*="Good"])',
        'div:has(> button[aria-label*="response"])',
        // Generic patterns
        'div[class*="flex"]:has(button[class*="mat-"])',
        'div[class*="justify"]:has(button[aria-label*="Bad"])'
      ];

      for (const selector of actionSelectors) {
        const elements = messageElement.querySelectorAll(selector);
        if (elements.length > 0) {
          let targetContainer = null;

          // Find the container that has the thumbs buttons
          for (const element of elements) {
            // Skip if in input area
            if (element.closest('.chat-input') || element.closest('.input-container')) {
              continue;
            }

            if (element.classList.contains('turn-footer')) {
              // This is the footer container, perfect!
              targetContainer = element;
            } else if (element.tagName === 'BUTTON' && element.classList.contains('response-feedback-button')) {
              // Found a feedback button, get its parent (turn-footer)
              targetContainer = element.parentElement;
            } else if (element.tagName === 'BUTTON') {
              // Get the parent that contains multiple buttons
              targetContainer = element.parentElement;
            } else if (element.tagName === 'DIV' && element.querySelector('button')) {
              targetContainer = element;
            }

            if (targetContainer) break;
          }

          if (targetContainer) {
            // Check if X button already exists
            if (targetContainer.querySelector('.ai-twitter-x-btn')) {
              console.log('⚠️ X button already exists in Google container, skipping...');
              return;
            }

            // Simply append the X button to the action container
            xButton.style.marginLeft = '4px';
            targetContainer.appendChild(xButton);
            return;
          }
        }
      }
    }

    // Fallback: Don't add if we can't find the right container
    console.log('Could not find appropriate container for X button');
  }

  extractText(element) {
    // Platform-specific extraction logic
    let targetElement = element;

    if (this.platform === 'claude') {
      // For Claude, find the message content specifically
      const messageContent = element.querySelector('.font-claude-message') ||
        element.querySelector('div[class*="whitespace-normal"][class*="break-words"]') ||
        element.querySelector('[data-is-streaming="false"] > div');

      if (messageContent) {
        targetElement = messageContent;
      }
    } else if (this.platform === 'chatgpt') {
      // For ChatGPT, find the markdown content
      const messageContent = element.querySelector('.markdown.prose') ||
        element.querySelector('div[class*="text-message"]') ||
        element.querySelector('[data-message-author-role="assistant"] .flex-col');

      if (messageContent) {
        targetElement = messageContent;
      }
    } else if (this.platform === 'google') {
      // For Google AI Studio, find the turn content
      const messageContent = element.querySelector('.turn-content') ||
        element.querySelector('.model-prompt-container') ||
        element.querySelector('ms-text-chunk');

      if (messageContent) {
        targetElement = messageContent;
      }
    }

    // Clone to avoid modifying original
    const clone = targetElement.cloneNode(true);

    // Remove action buttons and controls
    const selectorsToRemove = [
      '.ai-twitter-controls',
      '.ai-twitter-x-btn',
      'div[class*="rounded-lg"][class*="pointer-events-auto"]',
      'button[data-testid*="action"]',
      'div[class*="text-text-"][class*="flex"][class*="items-stretch"]',
      '.turn-footer',
      'a[href*="support.anthropic.com"]'
    ];

    selectorsToRemove.forEach(selector => {
      clone.querySelectorAll(selector).forEach(el => el.remove());
    });

    // Handle code blocks
    clone.querySelectorAll('pre, code').forEach(el => {
      const codeText = el.textContent || '';
      if (codeText.length > 100) {
        el.textContent = '[code snippet]';
      }
    });

    // Get clean text
    let text = clone.textContent || '';

    // Clean up whitespace while preserving paragraph breaks
    text = text.trim()
      .replace(/\n\s*\n\s*\n/g, '\n\n') // Multiple newlines to double
      .replace(/[ \t]+/g, ' ') // Multiple spaces to single
      .replace(/\n[ \t]+/g, '\n') // Remove spaces after newlines
      .trim();

    // Limit length for processing
    return text.substring(0, 2000);
  }

  async processText(text, action, style = null) {
    console.log('🌐 processText called!');
    console.log('📡 API URL:', this.apiUrl);
    console.log('📝 Action:', action);
    console.log('🎨 Style:', style);
    console.log('📏 Text length:', text.length);

    try {
      const requestBody = { text, action, style };
      console.log('📤 Sending request to backend:', requestBody);

      const response = await fetch(`${this.apiUrl}/api/process-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      console.log('📥 Response status:', response.status);
      console.log('📥 Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API error response:', errorText);
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Response data:', data);
      console.log('📏 Processed text length:', data.processed_text?.length);

      return data.processed_text;
    } catch (error) {
      console.error('❌ Process text error:', error);
      console.error('❌ Error details:', error.message);
      console.error('❌ Error stack:', error.stack);

      // Fallback processing
      console.log('⚠️ Using fallback processing...');
      if (action === 'condense') {
        // Simple fallback condensing
        const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
        return sentences.slice(0, 2).join(' ').substring(0, 250) + '...';
      } else {
        // Simple fallback styling
        return text.substring(0, 250) + '...';
      }
    }
  }

  showDialog(text, title = 'Share on X', subtitle = '', originalText = null) {
    // Remove any existing dialog
    const existingDialog = document.getElementById('ai-twitter-dialog');
    if (existingDialog) existingDialog.remove();

    // Store original text if provided
    this.dialogOriginalText = originalText || text;

    // Get platform colors
    const platformColors = {
      claude: { primary: '#d97757', secondary: '#f5f4f0', accent: '#eb7954' },
      chatgpt: { primary: '#10a37f', secondary: '#f7f7f8', accent: '#0d9373' },
      google: { primary: '#4285f4', secondary: '#f8f9fa', accent: '#1a73e8' }
    };
    const colors = platformColors[this.platform] || platformColors.claude;

    // Create overlay and dialog
    const overlay = document.createElement('div');
    overlay.className = 'ai-twitter-overlay';

    const dialog = document.createElement('div');
    dialog.id = 'ai-twitter-dialog';
    dialog.className = `ai-twitter-dialog ai-twitter-dialog-${this.platform}`;
    dialog.innerHTML = `
      <div class="dialog-header" style="border-bottom-color: ${colors.primary}20;">
        <h3>${title}</h3>
        ${subtitle ? `<p class="dialog-subtitle">${subtitle}</p>` : ''}
      </div>
      
      ${originalText ? `
        <div class="original-message-preview">
          <div class="preview-label">Original message:</div>
          <div class="preview-content">${this.truncatePreview(originalText, 150)}</div>
        </div>
      ` : ''}
      
      <div class="style-selector">
        <div class="style-label">Quick styles:</div>
        <div class="style-buttons">
          <button class="style-quick-btn" data-style="concise" title="Make it concise">
            <span class="style-icon">📝</span>
            <span class="style-name">Concise</span>
          </button>
          <button class="style-quick-btn" data-style="professional" title="Professional tone">
            <span class="style-icon">👔</span>
            <span class="style-name">Professional</span>
          </button>
          <button class="style-quick-btn" data-style="casual" title="Casual tone">
            <span class="style-icon">😊</span>
            <span class="style-name">Casual</span>
          </button>
          <button class="style-quick-btn" data-style="humorous" title="Add humor">
            <span class="style-icon">😄</span>
            <span class="style-name">Funny</span>
          </button>
        </div>
      </div>
      
      <textarea id="tweet-text" maxlength="280" placeholder="What's happening?">${text}</textarea>
      
      <div class="dialog-footer">
        <div class="char-count">
          <span id="char-current" style="color: ${text.length > 260 ? '#e0245e' : colors.primary};">${text.length}</span>/280
        </div>
        <div class="dialog-buttons">
          <button class="dialog-btn cancel-btn">Cancel</button>
          <button class="dialog-btn tweet-btn" style="background: ${colors.primary};">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            <span>Post</span>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(dialog);

    // Get elements
    const textarea = dialog.querySelector('#tweet-text');
    const charCurrent = dialog.querySelector('#char-current');
    const cancelBtn = dialog.querySelector('.cancel-btn');
    const tweetBtn = dialog.querySelector('.tweet-btn');
    const styleButtons = dialog.querySelectorAll('.style-quick-btn');

    // Update character count
    textarea.addEventListener('input', () => {
      const length = textarea.value.length;
      charCurrent.textContent = length;
      charCurrent.style.color = length > 280 ? '#e0245e' : length > 260 ? '#ffad1f' : colors.primary;
    });

    // Style button handlers
    styleButtons.forEach(btn => {
      btn.addEventListener('click', async () => {
        const style = btn.dataset.style;

        // Show loading state
        btn.classList.add('loading');
        btn.disabled = true;

        try {
          // Use original text for restyling
          const restyled = await this.processText(this.dialogOriginalText, 'restyle', style);
          textarea.value = restyled;

          // Update character count
          const length = restyled.length;
          charCurrent.textContent = length;
          charCurrent.style.color = length > 280 ? '#e0245e' : length > 260 ? '#ffad1f' : colors.primary;
        } catch (error) {
          console.error('Style error:', error);
        } finally {
          btn.classList.remove('loading');
          btn.disabled = false;
        }
      });
    });

    // Button handlers
    const closeDialog = () => {
      overlay.remove();
      dialog.remove();
    };

    cancelBtn.addEventListener('click', closeDialog);
    overlay.addEventListener('click', closeDialog);

    tweetBtn.addEventListener('click', () => {
      const tweetText = textarea.value;
      const platform = this.platform === 'claude' ? 'Claude.ai' :
        this.platform === 'chatgpt' ? 'ChatGPT' :
          this.platform === 'google' ? 'Google AI Studio' : 'AI Chat';

      // Add attribution if there's room
      let finalText = tweetText;
      const attribution = `\n\n(via ${platform})`;
      if (tweetText.length + attribution.length <= 280) {
        finalText = tweetText + attribution;
      }

      const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(finalText)}`;
      window.open(url, '_blank', 'width=550,height=420');
      closeDialog();

      // Track usage if chrome runtime is available
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        try {
          chrome.runtime.sendMessage({ action: 'tweetSent' });
        } catch (e) {
          // Ignore if sendMessage fails
        }
      }
    });

    // Focus and select text
    textarea.focus();
    textarea.select();

    // ESC key to close
    document.addEventListener('keydown', function escHandler(e) {
      if (e.key === 'Escape') {
        closeDialog();
        document.removeEventListener('keydown', escHandler);
      }
    });
  }

  // Helper to truncate preview text
  truncatePreview(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }
  
  // Show article generation dialog
  async showArticleDialog(text, platform) {
    // Remove any existing dialog
    const existingDialog = document.getElementById('ai-twitter-dialog');
    if (existingDialog) existingDialog.remove();
    
    const existingOverlay = document.querySelector('.ai-twitter-overlay');
    if (existingOverlay) existingOverlay.remove();

    // Create overlay and dialog
    const overlay = document.createElement('div');
    overlay.className = 'ai-twitter-overlay';

    const dialog = document.createElement('div');
    dialog.id = 'ai-twitter-dialog';
    dialog.className = `ai-twitter-dialog ai-twitter-dialog-${this.platform}`;
    
    const platformName = platform === 'substack' ? 'Substack' : 'Medium';
    const platformIcon = platform === 'substack' ? '📰' : '📄';
    
    dialog.innerHTML = `
      <div class="dialog-header">
        <h3>${platformIcon} Generate ${platformName} Article</h3>
        <p class="dialog-subtitle">Transform this content into a ${platformName} article</p>
      </div>
      
      <div class="original-message-preview">
        <div class="preview-label">Original content:</div>
        <div class="preview-content">${this.truncatePreview(text, 200)}</div>
      </div>
      
      <div class="article-options">
        <div class="style-label">Article title:</div>
        <input type="text" id="article-title" class="article-title-input" placeholder="Enter article title..." />
        
        <div class="style-label" style="margin-top: 12px;">Article style:</div>
        <div class="style-buttons">
          <button class="style-quick-btn" data-style="informative" title="Informative article">
            <span class="style-icon">📚</span>
            <span class="style-name">Informative</span>
          </button>
          <button class="style-quick-btn" data-style="tutorial" title="How-to guide">
            <span class="style-icon">🎯</span>
            <span class="style-name">Tutorial</span>
          </button>
          <button class="style-quick-btn" data-style="opinion" title="Opinion piece">
            <span class="style-icon">💭</span>
            <span class="style-name">Opinion</span>
          </button>
          <button class="style-quick-btn" data-style="story" title="Story format">
            <span class="style-icon">📖</span>
            <span class="style-name">Story</span>
          </button>
        </div>
      </div>
      
      <textarea id="article-content" placeholder="Article will appear here..." style="min-height: 200px; margin-top: 16px;"></textarea>
      
      <div class="dialog-footer">
        <div class="char-count">
          <span id="word-count">0</span> words
        </div>
        <div class="dialog-buttons">
          <button class="dialog-btn cancel-btn">Cancel</button>
          <button class="dialog-btn generate-btn" style="background: ${platform === 'substack' ? '#FF6719' : '#00ab6c'};">
            Generate Article
          </button>
          <button class="dialog-btn post-btn" style="background: ${platform === 'substack' ? '#FF6719' : '#00ab6c'}; display: none;">
            ${platformIcon} Open in ${platformName}
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(dialog);

    // Get elements
    const titleInput = dialog.querySelector('#article-title');
    const contentArea = dialog.querySelector('#article-content');
    const wordCount = dialog.querySelector('#word-count');
    const cancelBtn = dialog.querySelector('.cancel-btn');
    const generateBtn = dialog.querySelector('.generate-btn');
    const postBtn = dialog.querySelector('.post-btn');
    const styleButtons = dialog.querySelectorAll('.style-quick-btn');

    let selectedStyle = 'informative';

    // Style button handlers
    styleButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        styleButtons.forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedStyle = btn.dataset.style;
      });
    });

    // Select first style by default
    styleButtons[0].classList.add('selected');

    // Update word count
    contentArea.addEventListener('input', () => {
      const words = contentArea.value.trim().split(/\s+/).length;
      wordCount.textContent = words;
    });

    // Generate button handler
    generateBtn.addEventListener('click', async () => {
      const title = titleInput.value || 'Untitled Article';
      
      generateBtn.disabled = true;
      generateBtn.innerHTML = 'Generating...';
      
      try {
        // Process text as article
        const prompt = `Convert this into a ${selectedStyle} ${platformName} article with the title "${title}". Format it with proper headings, paragraphs, and structure suitable for ${platformName}.`;
        const article = await this.processText(text + '\n\n' + prompt, 'restyle', 'article');
        
        contentArea.value = `# ${title}\n\n${article}`;
        
        // Update word count
        const words = contentArea.value.trim().split(/\s+/).length;
        wordCount.textContent = words;
        
        // Show post button
        generateBtn.style.display = 'none';
        postBtn.style.display = 'inline-flex';
      } catch (error) {
        console.error('Article generation error:', error);
        contentArea.value = `# ${title}\n\n${text}`;
        generateBtn.style.display = 'none';
        postBtn.style.display = 'inline-flex';
      }
    });

    // Post button handler
    postBtn.addEventListener('click', () => {
      const content = contentArea.value;
      const title = titleInput.value || 'Untitled Article';
      
      if (platform === 'substack') {
        // Open Substack with pre-filled content
        const url = `https://substack.com/new/post?title=${encodeURIComponent(title)}&body=${encodeURIComponent(content)}`;
        window.open(url, '_blank');
      } else {
        // Open Medium with pre-filled content
        const url = `https://medium.com/new-story?title=${encodeURIComponent(title)}&body=${encodeURIComponent(content)}`;
        window.open(url, '_blank');
      }
      
      closeDialog();
    });

    // Button handlers
    const closeDialog = () => {
      overlay.remove();
      dialog.remove();
    };

    cancelBtn.addEventListener('click', closeDialog);
    overlay.addEventListener('click', closeDialog);

    // Focus title input
    titleInput.focus();

    // ESC key to close
    document.addEventListener('keydown', function escHandler(e) {
      if (e.key === 'Escape') {
        closeDialog();
        document.removeEventListener('keydown', escHandler);
      }
    });
  }

  showLoadingOverlay(element, message = 'Processing...') {
    const overlay = document.createElement('div');
    overlay.className = 'ai-twitter-loading';
    overlay.innerHTML = `
      <div class="loading-spinner"></div>
      <div class="loading-text">${message}</div>
    `;
    element.appendChild(overlay);
    return overlay;
  }

  async handleTweet(element) {
    const text = this.extractText(element);
    this.showDialog(text);
  }

  async handleSMS(element) {
    const text = this.extractText(element);
    // Condense for SMS (160 char limit)
    const condensed = await this.processText(text, 'condense');
    const smsText = condensed.substring(0, 160);

    // Detect platform and create appropriate SMS link
    const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);

    if (isIOS) {
      // iOS Messages app
      window.open(`sms:&body=${encodeURIComponent(smsText)}`);
    } else if (isAndroid) {
      // Android SMS
      window.open(`sms:?body=${encodeURIComponent(smsText)}`);
    } else {
      // Desktop fallback - show dialog with SMS text
      this.showDialog(smsText, 'SMS Message', 'Copy this text to send via SMS', text);
    }
  }

  async handleCondense(element) {
    const loadingOverlay = this.showLoadingOverlay(element, 'Condensing message...');

    try {
      const text = this.extractText(element);
      const condensed = await this.processText(text, 'condense');
      this.showDialog(condensed, 'Condensed Message', 'AI-powered summary', text);
    } catch (error) {
      console.error('Condense error:', error);
      this.showDialog(
        'Failed to condense message. Please try again.',
        'Error'
      );
    } finally {
      loadingOverlay.remove();
    }
  }

  async handleRestyle(element, style) {
    const loadingOverlay = this.showLoadingOverlay(element, `Applying ${style} style...`);

    try {
      const text = this.extractText(element);
      const restyled = await this.processText(text, 'restyle', style);
      const styleLabel = style.charAt(0).toUpperCase() + style.slice(1);
      this.showDialog(restyled, `${styleLabel} Style`, 'AI-powered restyle', text);
    } catch (error) {
      console.error('Restyle error:', error);
      this.showDialog(
        'Failed to restyle message. Please try again.',
        'Error'
      );
    } finally {
      loadingOverlay.remove();
    }
  }

  updateUI() {
    const controls = document.querySelectorAll('.ai-twitter-controls');
    controls.forEach(control => {
      control.style.display = this.enabled ? 'block' : 'none';
    });
  }

  // Handle Claude artifact iframes
  handleArtifactIframe(iframe) {
    if (iframe.dataset.twitterProcessed) return;
    iframe.dataset.twitterProcessed = 'true';

    // Wait for iframe to load
    const attachToIframe = () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (!iframeDoc) return;

        // Inject bottom button into iframe
        const bottomBtn = document.createElement('div');
        bottomBtn.className = 'ai-twitter-iframe-bottom';
        bottomBtn.innerHTML = `
          <button class="ai-twitter-iframe-post" title="Condense & post to X">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            <span>Post to X</span>
          </button>
        `;

        // Add styles to iframe
        const style = document.createElement('style');
        style.textContent = `
          .ai-twitter-iframe-bottom {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 12px;
            background: rgba(255, 255, 255, 0.95);
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            z-index: 9999;
            display: flex;
            justify-content: center;
          }
          
          .ai-twitter-iframe-post {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: #000;
            color: white;
            border: none;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: system-ui, -apple-system, sans-serif;
          }
          
          .ai-twitter-iframe-post:hover {
            background: #111;
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          }
          
          .ai-twitter-iframe-post:active {
            transform: translateY(0);
          }
          
          .ai-twitter-iframe-post svg {
            width: 14px;
            height: 14px;
          }
        `;

        iframeDoc.head.appendChild(style);
        iframeDoc.body.appendChild(bottomBtn);

        // Add click handler
        bottomBtn.addEventListener('click', async () => {
          const btn = bottomBtn.querySelector('button');
          const originalContent = btn.innerHTML;
          btn.innerHTML = '<span>Processing...</span>';
          btn.disabled = true;

          try {
            const text = this.extractArtifactText(iframeDoc);
            const condensed = await this.processText(text, 'condense');
            this.showDialog(condensed, 'Share Artifact on X', 'AI-condensed content');
          } catch (error) {
            const text = this.extractArtifactText(iframeDoc);
            this.showDialog(text, 'Share Artifact on X');
          } finally {
            btn.innerHTML = originalContent;
            btn.disabled = false;
          }
        });
      } catch (e) {
        // Cross-origin iframe, skip
      }
    };

    if (iframe.contentDocument?.readyState === 'complete') {
      attachToIframe();
    } else {
      iframe.addEventListener('load', attachToIframe);
    }
  }

  // Extract text from artifact iframe
  extractArtifactText(doc) {
    // Try to find the main content area
    const root = doc.getElementById('artifacts-component-root-html') || doc.body;

    // Clone and clean
    const clone = root.cloneNode(true);

    // Remove scripts and styles
    clone.querySelectorAll('script, style, .ai-twitter-floating-btn').forEach(el => el.remove());

    // Get text content
    let text = clone.textContent || '';

    // Clean up
    text = text.trim()
      .replace(/\s+/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .substring(0, 2000);

    return text || 'Check out this Claude artifact!';
  }

  // Attach floating button for selection-based posting
  attachFloatingButton() {
    if (document.getElementById('ai-twitter-selection-btn')) return;

    const floatingBtn = document.createElement('div');
    floatingBtn.id = 'ai-twitter-selection-btn';
    floatingBtn.className = 'ai-twitter-selection-floating';
    floatingBtn.innerHTML = `
      <button title="Post selected text to X">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      </button>
    `;

    document.body.appendChild(floatingBtn);

    // Hide by default
    floatingBtn.style.display = 'none';

    // Track text selection
    let selectedText = '';

    // Store reference on the extension instance for access in other methods
    this.floatingBtnState = { selectedElement: null };

    document.addEventListener('mouseup', (e) => {
      const selection = window.getSelection();
      selectedText = selection.toString().trim();

      if (selectedText.length > 10) {
        // Position button near selection
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        floatingBtn.style.display = 'block';
        floatingBtn.style.position = 'fixed';
        floatingBtn.style.left = `${rect.left + rect.width / 2 - 20}px`;
        floatingBtn.style.top = `${rect.bottom + 10}px`;
        floatingBtn.style.zIndex = '10000';
        this.floatingBtnState.selectedElement = null;
      } else {
        floatingBtn.style.display = 'none';
      }
    });

    // Add hover detection for non-text elements
    this.attachNonTextElementHandlers();

    // Hide on click elsewhere
    document.addEventListener('mousedown', (e) => {
      if (!floatingBtn.contains(e.target)) {
        floatingBtn.style.display = 'none';
      }
    });

    // Handle click
    floatingBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      if (selectedText) {
        this.showDialog(selectedText, 'Share Selection on X');
        floatingBtn.style.display = 'none';
        window.getSelection().removeAllRanges();
      } else if (this.floatingBtnState.selectedElement) {
        await this.handleNonTextElement(this.floatingBtnState.selectedElement);
        floatingBtn.style.display = 'none';
        this.floatingBtnState.selectedElement = null;
      }
    });
  }

  // Handle non-text elements like images, canvas, SVG, video
  attachNonTextElementHandlers() {
    const nonTextSelectors = ['img', 'canvas', 'svg', 'video', 'figure', '.math', '.chart', '.diagram'];
    let hoverTimeout;

    document.addEventListener('mouseover', (e) => {
      const target = e.target;

      // Check if element matches our non-text selectors
      const isNonTextElement = nonTextSelectors.some(selector => {
        if (target.matches && target.matches(selector)) return true;
        if (target.closest && target.closest(selector)) return true;
        return false;
      });

      if (isNonTextElement) {
        clearTimeout(hoverTimeout);

        hoverTimeout = setTimeout(() => {
          const floatingBtn = document.getElementById('ai-twitter-selection-btn');
          if (floatingBtn) {
            const rect = target.getBoundingClientRect();
            floatingBtn.style.display = 'block';
            floatingBtn.style.position = 'fixed';
            floatingBtn.style.left = `${rect.right - 40}px`;
            floatingBtn.style.top = `${rect.top + 10}px`;
            floatingBtn.style.zIndex = '10000';

            // Store reference to the element
            this.floatingBtnState.selectedElement = target;
          }
        }, 500); // Show after 500ms hover
      }
    });

    document.addEventListener('mouseout', () => {
      clearTimeout(hoverTimeout);
    });
  }

  // Handle different types of non-text elements
  async handleNonTextElement(element) {
    const tagName = element.tagName.toLowerCase();

    try {
      switch (tagName) {
        case 'img':
          await this.handleImage(element);
          break;
        case 'canvas':
          await this.handleCanvas(element);
          break;
        case 'svg':
          await this.handleSVG(element);
          break;
        case 'video':
          await this.handleVideo(element);
          break;
        default:
          // For other elements, try to extract meaningful content
          await this.handleGenericElement(element);
      }
    } catch (error) {
      console.error('Error handling non-text element:', error);
      this.showDialog('Unable to process this element. Try selecting text instead.', 'Error');
    }
  }

  // Handle image elements
  async handleImage(img) {
    const altText = img.alt || '';
    const title = img.title || '';
    const src = img.src || '';

    let text = '';
    if (altText) text += `Image: ${altText}\n`;
    if (title && title !== altText) text += `${title}\n`;

    // If no alt text, try to describe the image
    if (!text.trim()) {
      const imageName = src.split('/').pop().split('?')[0];
      text = `Image: ${imageName}`;
    }

    // Add context if available
    const caption = img.closest('figure')?.querySelector('figcaption')?.textContent;
    if (caption) text += `\nCaption: ${caption}`;

    this.showDialog(text.trim() || 'Check out this image!', 'Share Image on X');
  }

  // Handle canvas elements
  async handleCanvas(canvas) {
    // Try to get canvas title or nearby description
    let text = canvas.title || '';

    // Look for nearby labels or descriptions
    const label = canvas.getAttribute('aria-label');
    if (label) text = label;

    // Check for nearby text that might describe the canvas
    const parent = canvas.closest('div, section, article');
    if (parent) {
      const heading = parent.querySelector('h1, h2, h3, h4, h5, h6');
      if (heading) text = heading.textContent + '\n' + text;
    }

    this.showDialog(text.trim() || 'Check out this visualization!', 'Share Canvas on X');
  }

  // Handle SVG elements
  async handleSVG(svg) {
    // Try to extract title and description from SVG
    const title = svg.querySelector('title')?.textContent || '';
    const desc = svg.querySelector('desc')?.textContent || '';

    let text = '';
    if (title) text += title + '\n';
    if (desc) text += desc;

    // If no title/desc, try aria-label
    if (!text.trim()) {
      text = svg.getAttribute('aria-label') || 'Check out this diagram!';
    }

    this.showDialog(text.trim(), 'Share Diagram on X');
  }

  // Handle video elements
  async handleVideo(video) {
    const title = video.title || '';
    const currentTime = video.currentTime;
    const duration = video.duration;

    let text = title || 'Check out this video!';

    // Add timestamp if video is playing
    if (currentTime > 0 && duration) {
      const timestamp = this.formatTime(currentTime);
      const totalTime = this.formatTime(duration);
      text += `\n[${timestamp} / ${totalTime}]`;
    }

    this.showDialog(text, 'Share Video on X');
  }

  // Handle generic elements (math, charts, etc.)
  async handleGenericElement(element) {
    // Try various methods to extract meaningful content
    let text = '';

    // Check for aria-label
    const ariaLabel = element.getAttribute('aria-label');
    if (ariaLabel) {
      text = ariaLabel;
    }

    // Check for title attribute
    else if (element.title) {
      text = element.title;
    }

    // Check for math content
    else if (element.classList.contains('math') || element.querySelector('math')) {
      text = 'Mathematical expression';
      const mathEl = element.querySelector('annotation[encoding="application/x-tex"]');
      if (mathEl) text = mathEl.textContent;
    }

    // Fall back to text content
    else {
      text = element.textContent?.trim().substring(0, 280) || 'Check out this content!';
    }

    this.showDialog(text, 'Share on X');
  }

  // Format time in seconds to MM:SS
  formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  // Attach button to Claude's chat input
  attachClaudeChatButton() {
    // Watch for Claude's input area
    const observer = new MutationObserver(() => {
      this.tryAttachChatButton();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Initial attempt
    this.tryAttachChatButton();
  }

  tryAttachChatButton() {
    // Claude input selectors
    const inputSelectors = [
      'div[contenteditable="true"]',
      'textarea[placeholder*="Message"]',
      'div[data-placeholder*="Message"]',
      '.ProseMirror',
      'div[class*="composer"]',
      'div[class*="input-container"]'
    ];

    for (const selector of inputSelectors) {
      const inputArea = document.querySelector(selector);
      if (inputArea && !inputArea.dataset.twitterButtonAdded) {
        // Find the parent container that has the send button
        let container = inputArea.parentElement;
        while (container && !container.querySelector('button[aria-label*="Send"], button[aria-label*="send"], button svg')) {
          container = container.parentElement;
        }

        if (container) {
          this.addChatButton(container, inputArea);
          inputArea.dataset.twitterButtonAdded = 'true';
          break;
        }
      }
    }
  }

  addChatButton(container, inputArea) {
    // Create button that matches Claude's style
    const twitterBtn = document.createElement('button');
    twitterBtn.className = 'ai-twitter-chat-btn';
    twitterBtn.setAttribute('aria-label', 'Condense and post to X');
    twitterBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" opacity="0.6">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    `;

    // Style to match Claude's buttons
    const style = document.createElement('style');
    style.textContent = `
      .ai-twitter-chat-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        padding: 0;
        margin: 0 4px;
        background: transparent;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
      }
      
      .ai-twitter-chat-btn:hover {
        background: rgba(0, 0, 0, 0.05);
      }
      
      .ai-twitter-chat-btn:hover svg {
        opacity: 1 !important;
      }
      
      .ai-twitter-chat-btn:active {
        transform: scale(0.95);
      }
      
      .ai-twitter-chat-btn-tooltip {
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        margin-bottom: 8px;
        padding: 6px 12px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        font-size: 12px;
        border-radius: 4px;
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
      }
      
      .ai-twitter-chat-btn:hover .ai-twitter-chat-btn-tooltip {
        opacity: 1;
      }
    `;

    // Add style if not already added
    if (!document.getElementById('ai-twitter-chat-styles')) {
      style.id = 'ai-twitter-chat-styles';
      document.head.appendChild(style);
    }

    // Add tooltip
    const tooltip = document.createElement('span');
    tooltip.className = 'ai-twitter-chat-btn-tooltip';
    tooltip.textContent = 'Condense & post to X';
    twitterBtn.appendChild(tooltip);

    // Find the send button to position our button next to it
    const sendButton = container.querySelector('button[aria-label*="Send"], button[aria-label*="send"], button:has(svg)');
    if (sendButton && sendButton.parentElement) {
      sendButton.parentElement.insertBefore(twitterBtn, sendButton);
    } else {
      // Fallback: append to container
      container.appendChild(twitterBtn);
    }

    // Add click handler
    twitterBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      // Get the input text
      let text = '';
      if (inputArea.tagName === 'TEXTAREA') {
        text = inputArea.value;
      } else {
        text = inputArea.textContent || inputArea.innerText || '';
      }

      if (!text.trim()) {
        this.showDialog('Please type a message first!', 'No Message');
        return;
      }

      // Show loading state
      const originalHTML = twitterBtn.innerHTML;
      twitterBtn.innerHTML = `
        <div class="loading-spinner" style="width: 16px; height: 16px;"></div>
      `;
      twitterBtn.disabled = true;

      try {
        // Process the text (condense it)
        const condensed = await this.processText(text, 'condense');

        // Show dialog with condensed text
        this.showDialog(condensed, 'Share Message on X', 'AI-condensed from your draft');
      } catch (error) {
        console.error('Error processing text:', error);
        // Fallback to original text if condensing fails
        const truncated = text.length > 280 ? text.substring(0, 277) + '...' : text;
        this.showDialog(truncated, 'Share Message on X');
      } finally {
        // Restore button
        twitterBtn.innerHTML = originalHTML;
        twitterBtn.disabled = false;
      }
    });
  }

  // Attach button to Google AI Studio's chat input
  attachGoogleChatButton() {
    // Watch for Google AI Studio's input area
    const observer = new MutationObserver(() => {
      this.tryAttachGoogleChatButton();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Initial attempt
    this.tryAttachGoogleChatButton();
  }

  tryAttachGoogleChatButton() {
    // Google AI Studio input selectors
    const inputSelectors = [
      'textarea[placeholder*="Enter a prompt"]',
      'textarea[placeholder*="Type something"]',
      'textarea[placeholder*="Ask"]',
      'textarea[placeholder*="Message"]',
      'div[contenteditable="true"][role="textbox"]',
      'div[contenteditable="true"][class*="input"]',
      '.input-container textarea',
      'mat-form-field textarea',
      '[class*="prompt-input"] textarea',
      '[class*="chat-input"] textarea'
    ];

    for (const selector of inputSelectors) {
      const inputArea = document.querySelector(selector);
      if (inputArea && !inputArea.dataset.twitterButtonAdded) {
        // Find the parent container that might have the send button
        let container = inputArea.parentElement;
        let attempts = 0;
        while (container && attempts < 5) {
          // Look for send button or action area
          const hasButton = container.querySelector('button[aria-label*="Send"], button[aria-label*="send"], button:has(svg), button mat-icon, [class*="actions"], [class*="toolbar"]');
          if (hasButton) {
            this.addGoogleChatButton(container, inputArea);
            inputArea.dataset.twitterButtonAdded = 'true';
            return;
          }
          container = container.parentElement;
          attempts++;
        }

        // Fallback: add to input's parent if no button area found
        if (inputArea.parentElement) {
          this.addGoogleChatButton(inputArea.parentElement, inputArea);
          inputArea.dataset.twitterButtonAdded = 'true';
        }
      }
    }
  }

  addGoogleChatButton(container, inputArea) {
    // Create button that matches Google AI Studio's style
    const twitterBtn = document.createElement('button');
    twitterBtn.className = 'ai-twitter-google-chat-btn';
    twitterBtn.setAttribute('aria-label', 'Condense and post to X');
    twitterBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    `;

    // Style to match Google AI Studio's Material Design
    const style = document.createElement('style');
    style.textContent = `
      .ai-twitter-google-chat-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        padding: 0;
        margin: 0 8px;
        background: transparent;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
        color: #5f6368;
      }
      
      .ai-twitter-google-chat-btn:hover {
        background: rgba(0, 0, 0, 0.04);
        color: #202124;
      }
      
      .ai-twitter-google-chat-btn:active {
        background: rgba(0, 0, 0, 0.08);
        transform: scale(0.95);
      }
      
      .ai-twitter-google-chat-btn svg {
        width: 20px;
        height: 20px;
      }
      
      .ai-twitter-google-chat-btn-tooltip {
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        margin-bottom: 8px;
        padding: 6px 12px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        font-size: 12px;
        font-family: 'Google Sans', Roboto, sans-serif;
        border-radius: 4px;
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
      }
      
      .ai-twitter-google-chat-btn:hover .ai-twitter-google-chat-btn-tooltip {
        opacity: 1;
      }
    `;

    // Add style if not already added
    if (!document.getElementById('ai-twitter-google-styles')) {
      style.id = 'ai-twitter-google-styles';
      document.head.appendChild(style);
    }

    // Add tooltip
    const tooltip = document.createElement('span');
    tooltip.className = 'ai-twitter-google-chat-btn-tooltip';
    tooltip.textContent = 'Condense & post to X';
    twitterBtn.appendChild(tooltip);

    // Find where to insert the button
    const actionArea = container.querySelector('[class*="actions"], [class*="toolbar"], [class*="button-container"]');
    if (actionArea) {
      actionArea.insertBefore(twitterBtn, actionArea.firstChild);
    } else {
      // Try to find send button and insert before it
      const sendButton = container.querySelector('button');
      if (sendButton && sendButton.parentElement) {
        sendButton.parentElement.insertBefore(twitterBtn, sendButton);
      } else {
        container.appendChild(twitterBtn);
      }
    }

    // Add click handler
    twitterBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      // Get the input text
      let text = '';
      if (inputArea.tagName === 'TEXTAREA') {
        text = inputArea.value;
      } else {
        text = inputArea.textContent || inputArea.innerText || '';
      }

      if (!text.trim()) {
        this.showDialog('Please type a message first!', 'No Message');
        return;
      }

      // Show loading state
      const originalHTML = twitterBtn.innerHTML;
      twitterBtn.innerHTML = `
        <div class="loading-spinner" style="width: 16px; height: 16px;"></div>
      `;
      twitterBtn.disabled = true;

      try {
        // Process the text (condense it)
        const condensed = await this.processText(text, 'condense');

        // Show dialog with condensed text
        this.showDialog(condensed, 'Share on X', 'AI-condensed from Google AI Studio');
      } catch (error) {
        console.error('Error processing text:', error);
        // Fallback to original text if condensing fails
        const truncated = text.length > 280 ? text.substring(0, 277) + '...' : text;
        this.showDialog(truncated, 'Share on X');
      } finally {
        // Restore button
        twitterBtn.innerHTML = originalHTML;
        twitterBtn.disabled = false;
      }
    });
  }

  // Attach button to ChatGPT's chat input
  attachChatGPTButton() {
    // Watch for ChatGPT's input area
    const observer = new MutationObserver(() => {
      this.tryAttachChatGPTButton();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Initial attempt
    this.tryAttachChatGPTButton();
  }

  tryAttachChatGPTButton() {
    // ChatGPT input selectors based on the screenshot
    const inputSelectors = [
      'textarea[data-id="root"]',
      'textarea#prompt-textarea',
      'textarea[placeholder*="Message"]',
      'textarea[placeholder*="Send a message"]',
      'textarea[placeholder*="Type a message"]',
      'div[contenteditable="true"][data-placeholder]',
      'div.relative.flex textarea',
      'form textarea',
      '[class*="composer"] textarea',
      '[class*="prompt"] textarea'
    ];

    for (const selector of inputSelectors) {
      const inputArea = document.querySelector(selector);
      if (inputArea && !inputArea.dataset.twitterButtonAdded) {
        // Find the form or parent container
        let container = inputArea.closest('form') || inputArea.parentElement;
        let attempts = 0;

        // Look for the button container
        while (container && attempts < 5) {
          const buttonContainer = container.querySelector('button[data-testid], button[aria-label*="Send"], button:has(svg), [class*="flex"]:has(button)');
          if (buttonContainer) {
            this.addChatGPTButton(container, inputArea);
            inputArea.dataset.twitterButtonAdded = 'true';
            return;
          }
          container = container.parentElement;
          attempts++;
        }

        // Fallback: add to form if found
        const form = inputArea.closest('form');
        if (form) {
          this.addChatGPTButton(form, inputArea);
          inputArea.dataset.twitterButtonAdded = 'true';
        }
      }
    }
  }

  addChatGPTButton(container, inputArea) {
    // Create button that matches ChatGPT's style
    const twitterBtn = document.createElement('button');
    twitterBtn.className = 'ai-twitter-chatgpt-btn';
    twitterBtn.type = 'button'; // Prevent form submission
    twitterBtn.setAttribute('aria-label', 'Condense and post to X');
    twitterBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    `;

    // Style to match ChatGPT's design
    const style = document.createElement('style');
    style.textContent = `
      .ai-twitter-chatgpt-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        padding: 0;
        margin: 0 4px;
        background: transparent;
        border: none;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: all 0.15s ease;
        position: relative;
        color: #6b7280;
      }
      
      .ai-twitter-chatgpt-btn:hover {
        background: rgba(0, 0, 0, 0.05);
        color: #374151;
      }
      
      .ai-twitter-chatgpt-btn:active {
        transform: scale(0.95);
      }
      
      .ai-twitter-chatgpt-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      
      .ai-twitter-chatgpt-btn svg {
        width: 18px;
        height: 18px;
      }
      
      .ai-twitter-chatgpt-tooltip {
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        margin-bottom: 8px;
        padding: 6px 12px;
        background: #1f2937;
        color: white;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        border-radius: 6px;
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.15s ease;
      }
      
      .ai-twitter-chatgpt-btn:hover .ai-twitter-chatgpt-tooltip {
        opacity: 1;
      }
    `;

    // Add style if not already added
    if (!document.getElementById('ai-twitter-chatgpt-styles')) {
      style.id = 'ai-twitter-chatgpt-styles';
      document.head.appendChild(style);
    }

    // Add tooltip
    const tooltip = document.createElement('span');
    tooltip.className = 'ai-twitter-chatgpt-tooltip';
    tooltip.textContent = 'Condense & post to X';
    twitterBtn.appendChild(tooltip);

    // Find the send button to position our button correctly
    const sendButton = container.querySelector('button[data-testid="send-button"], button[aria-label*="Send"], button:has(svg path[d*="M4.5"]), button:last-child');

    if (sendButton && sendButton.parentElement) {
      // Insert before the send button
      sendButton.parentElement.insertBefore(twitterBtn, sendButton);
    } else {
      // Try to find a flex container with buttons
      const buttonContainer = container.querySelector('[class*="flex"]:has(button), [class*="absolute"]:has(button)');
      if (buttonContainer) {
        buttonContainer.insertBefore(twitterBtn, buttonContainer.firstChild);
      } else {
        // Fallback: append to container
        container.appendChild(twitterBtn);
      }
    }

    // Add click handler
    twitterBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      // Get the input text
      const text = inputArea.value || inputArea.textContent || '';

      if (!text.trim()) {
        this.showDialog('Please type a message first!', 'No Message');
        return;
      }

      // Show loading state
      const originalHTML = twitterBtn.innerHTML;
      twitterBtn.innerHTML = `
        <svg class="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3"></path>
        </svg>
      `;
      twitterBtn.disabled = true;

      // Add spinning animation
      const spinStyle = document.createElement('style');
      spinStyle.textContent = `
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `;
      if (!document.getElementById('ai-twitter-spin-styles')) {
        spinStyle.id = 'ai-twitter-spin-styles';
        document.head.appendChild(spinStyle);
      }

      try {
        // Process the text (condense it)
        const condensed = await this.processText(text, 'condense');

        // Show dialog with condensed text
        this.showDialog(condensed, 'Share on X', 'AI-condensed from ChatGPT');
      } catch (error) {
        console.error('Error processing text:', error);
        // Fallback to original text if condensing fails
        const truncated = text.length > 280 ? text.substring(0, 277) + '...' : text;
        this.showDialog(truncated, 'Share on X');
      } finally {
        // Restore button
        twitterBtn.innerHTML = originalHTML;
        twitterBtn.disabled = false;
      }
    });
  }
}

// Initialize extension when DOM is ready
console.log('🔧 Checking document ready state:', document.readyState);

if (document.readyState === 'loading') {
  console.log('⏳ Document still loading, waiting for DOMContentLoaded...');
  document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOMContentLoaded fired, initializing extension...');
    const extension = new AITwitterExtension();
    console.log('✅ Extension initialized:', extension);
  });
} else {
  console.log('📄 Document already loaded, initializing extension immediately...');
  const extension = new AITwitterExtension();
  console.log('✅ Extension initialized:', extension);
}