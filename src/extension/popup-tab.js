// popup-tab.js - Tab-based popup script
// Debug functionality
document.getElementById('debugToggle').addEventListener('click', (e) => {
    e.preventDefault();
    const debugInfo = document.getElementById('debugInfo');
    debugInfo.style.display = debugInfo.style.display === 'none' ? 'block' : 'none';
});

// Update debug info
function updateDebugInfo() {
    if (window.contextlyPopup) {
        const popup = window.contextlyPopup;
        const debugWallet = document.getElementById('debugWallet');
        const debugMode = document.getElementById('debugMode');
        const debugLanceDB = document.getElementById('debugLanceDB');
        const debugLastAction = document.getElementById('debugLastAction');
        
        if (debugWallet) {
            debugWallet.textContent = popup.wallet?.address ? 
                popup.wallet.address.slice(0, 8) + '...' : 'Not connected';
        }
        if (debugMode) {
            debugMode.textContent = popup.currentMode || 'Free';
        }
        if (debugLanceDB) {
            debugLanceDB.textContent = popup.authToken ? 
                'Authenticated' : 'Not authenticated';
        }
        if (debugLastAction) {
            debugLastAction.textContent = new Date().toLocaleTimeString();
        }
    }
}

// Update debug info every 2 seconds
setInterval(updateDebugInfo, 2000);

// Log all console messages to debug
const originalLog = console.log;
const originalError = console.error;

console.log = function(...args) {
    originalLog.apply(console, args);
    const debugLastAction = document.getElementById('debugLastAction');
    if (debugLastAction) {
        debugLastAction.textContent = args.join(' ');
    }
};

console.error = function(...args) {
    originalError.apply(console, args);
    const debugLastAction = document.getElementById('debugLastAction');
    if (debugLastAction) {
        debugLastAction.textContent = 'ERROR: ' + args.join(' ');
        debugLastAction.parentElement.classList.add('error');
        setTimeout(() => {
            debugLastAction.parentElement.classList.remove('error');
        }, 3000);
    }
};

console.log('🎉 Tab-based popup loaded - DevTools will persist!');