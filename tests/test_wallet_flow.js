// Test script to verify wallet authentication flow
// This simulates what connect.js does

const API_BASE_URL = 'http://localhost:8000';

// Test wallet data (for testing purposes only)
const testWallet = '0x742d35cc6634c0532925a3b8d0a'
const testMessage = `Contextly.ai Authentication\nAddress: ${testWallet}\nTimestamp: ${Date.now()}`;

console.log('🧪 Testing wallet authentication flow...');
console.log('📝 Test message:', testMessage);

// Test 1: Wallet registration with invalid signature
async function testWalletRegistration() {
    try {
        console.log('\n1️⃣ Testing wallet registration endpoint...');
        
        const response = await fetch(`${API_BASE_URL}/v1/wallet/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                wallet: testWallet,
                signature: 'invalid_signature_for_testing',
                message: testMessage,
                chainId: 1
            })
        });
        
        const result = await response.text();
        console.log('📊 Response status:', response.status);
        console.log('📊 Response:', result);
        
        if (response.status === 401) {
            console.log('✅ Endpoint correctly rejects invalid signatures');
        } else {
            console.log('❌ Unexpected response');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Test 2: Stats endpoint
async function testStatsEndpoint() {
    try {
        console.log('\n2️⃣ Testing stats endpoint...');
        
        const response = await fetch(`${API_BASE_URL}/v1/stats/${testWallet}`, {
            headers: {
                'Authorization': 'Bearer fake_token_for_testing',
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.text();
        console.log('📊 Response status:', response.status);
        console.log('📊 Response:', result);
        
        if (response.status === 404) {
            console.log('✅ Endpoint correctly returns 404 for non-existent user');
        } else {
            console.log('❌ Unexpected response');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Test 3: Auto-mode endpoint
async function testAutoModeEndpoint() {
    try {
        console.log('\n3️⃣ Testing auto-mode status endpoint...');
        
        const response = await fetch(`${API_BASE_URL}/v1/auto-mode/status/${testWallet}`, {
            headers: {
                'Authorization': 'Bearer fake_token_for_testing',
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.text();
        console.log('📊 Response status:', response.status);
        console.log('📊 Response:', result);
        
        if (response.status === 401) {
            console.log('✅ Endpoint correctly requires authentication');
        } else {
            console.log('❌ Unexpected response');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run all tests
async function runTests() {
    await testWalletRegistration();
    await testStatsEndpoint();
    await testAutoModeEndpoint();
    console.log('\n🎉 All endpoint tests completed!');
}

// Check if we're in Node.js environment
if (typeof fetch === 'undefined') {
    console.log('❌ This test requires a fetch-capable environment');
    console.log('💡 Please run this in a browser console or with Node.js + fetch polyfill');
} else {
    runTests();
}