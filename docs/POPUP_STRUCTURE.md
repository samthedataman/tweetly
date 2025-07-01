# Popup Structure Documentation

## Current Active Popup (as of manifest.json)
- **File**: `popup.html`
- **JavaScript**: `popup_merged.js`
- **Styles**: `styles.css`
- **Components**: `emptyState.js`, `emptyState.css`

## Features in Active Popup
1. **Wallet Connection**
   - Multiple wallet support (MetaMask, Coinbase, Rainbow, WalletConnect)
   - Wallet modal with close button
   - Dynamic API URL (localhost for dev, api.contextly.ai for prod)
   - Enhanced error messages

2. **X (Twitter) Authentication**
   - OAuth flow with popup window
   - Status polling
   - Proper API endpoint configuration

3. **Import Conversations**
   - Import section with copy/paste and bulk upload
   - Demo conversations with templates
   - Empty state with engaging UI

4. **Earnings System**
   - Free mode / Earn mode toggle
   - CTXT token balance
   - Earnings statistics
   - Leaderboard

5. **Conversation Management**
   - Search across all platforms
   - Filter by platform (Claude, ChatGPT, Gemini)
   - Export functionality
   - Transfer context between tabs

## Cleaned Up Structure
- All duplicate and unused popup files have been removed
- Only the active popup files remain:
  - `popup.html` - Main popup HTML
  - `popup_merged.js` - Unified JavaScript
  - `styles.css` - Main styles
  - Component files (emptyState.js, emptyState.css)

## Key Dependencies
- `simpleWallet.js` - Wallet connection utility
- `walletAdapter.js` - Unified wallet interface
- `baseIntegration.js` - Base blockchain integration
- `contractService.js` - Smart contract interactions
- `gaslessService.js` - Gasless transaction support
- `progressiveOnboarding.js` - User onboarding flow

## Important Notes
1. All API calls now use dynamic URL configuration
2. Error handling provides user-friendly messages
3. The popup supports both development and production environments
4. Role field is now properly captured and stored in LanceDB
5. Extensive logging is available in browser console