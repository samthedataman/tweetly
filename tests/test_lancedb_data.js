// Test script to send sample conversation data to LanceDB via FastAPI
const API_BASE_URL = 'http://localhost:8000';

// Demo user wallet (for testing)
const DEMO_WALLET = '0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d';

// Sample conversation data
const sampleConversations = [
    {
        session_id: 'demo_session_1_' + Date.now(),
        messages: [
            {
                id: 'msg_1_' + Date.now(),
                role: 'user',
                text: 'How do I implement a binary search algorithm in Python?',
                platform: 'claude',
                timestamp: Date.now() - 3600000 // 1 hour ago
            },
            {
                id: 'msg_2_' + Date.now(),
                role: 'assistant', 
                text: 'Here\'s a clean implementation of binary search in Python:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    \n    return -1  # Element not found\n```\n\nThis algorithm has O(log n) time complexity and works on sorted arrays.',
                platform: 'claude',
                timestamp: Date.now() - 3590000,
                artifacts: [
                    {
                        type: 'code',
                        language: 'python',
                        title: 'Binary Search Implementation'
                    }
                ]
            },
            {
                id: 'msg_3_' + Date.now(),
                role: 'user',
                text: 'Can you explain the time complexity analysis?',
                platform: 'claude',
                timestamp: Date.now() - 3580000
            },
            {
                id: 'msg_4_' + Date.now(),
                role: 'assistant',
                text: 'Absolutely! The time complexity of binary search is O(log n) because:\n\n1. **Each iteration halves the search space** - we eliminate half of the remaining elements\n2. **Maximum iterations needed** - log₂(n) where n is the array size\n3. **Example**: For 1000 elements, max 10 iterations (2¹⁰ = 1024)\n\nThis makes binary search much faster than linear search O(n) for large datasets.',
                platform: 'claude',
                timestamp: Date.now() - 3570000
            }
        ]
    },
    {
        session_id: 'demo_session_2_' + Date.now(),
        messages: [
            {
                id: 'msg_5_' + Date.now(),
                role: 'user',
                text: 'What are the best practices for React state management?',
                platform: 'chatgpt',
                timestamp: Date.now() - 7200000 // 2 hours ago
            },
            {
                id: 'msg_6_' + Date.now(),
                role: 'assistant',
                text: 'Here are the key React state management best practices:\n\n## Local State\n- Use `useState` for component-specific data\n- Keep state as close to where it\'s needed as possible\n\n## Global State\n- **Context API**: For simple global state (theme, user auth)\n- **Redux Toolkit**: For complex apps with many state interactions\n- **Zustand**: Lightweight alternative to Redux\n\n## State Structure\n- Normalize nested data\n- Avoid duplicating state\n- Use derived state when possible\n\n## Performance\n- Use `useCallback` and `useMemo` sparingly\n- Consider state colocation\n- Split large state objects',
                platform: 'chatgpt',
                timestamp: Date.now() - 7190000,
                metadata: {
                    topic: 'react',
                    difficulty: 'intermediate'
                }
            }
        ]
    },
    {
        session_id: 'demo_session_3_' + Date.now(),
        messages: [
            {
                id: 'msg_7_' + Date.now(),
                role: 'user',
                text: 'Explain the difference between machine learning and deep learning',
                platform: 'gemini',
                timestamp: Date.now() - 10800000 // 3 hours ago
            },
            {
                id: 'msg_8_' + Date.now(),
                role: 'assistant',
                text: '**Machine Learning** is a broader field where algorithms learn patterns from data to make predictions without explicit programming.\n\n**Deep Learning** is a subset of ML that uses artificial neural networks with multiple layers (hence "deep") to model complex patterns.\n\n## Key Differences:\n\n### Machine Learning\n- Uses algorithms like linear regression, decision trees, SVM\n- Requires manual feature engineering\n- Works well with smaller datasets\n- More interpretable results\n\n### Deep Learning  \n- Uses neural networks with many hidden layers\n- Automatic feature extraction\n- Requires large datasets\n- Superior performance on complex tasks (images, speech, NLP)\n- Less interpretable ("black box")\n\n**Think of it this way**: All deep learning is machine learning, but not all machine learning is deep learning.',
                platform: 'gemini',
                timestamp: Date.now() - 10790000,
                metadata: {
                    topic: 'machine-learning',
                    category: 'comparison'
                }
            }
        ]
    }
];

// Function to send a single message to the API
async function sendMessage(message, session_id, wallet) {
    try {
        const payload = {
            message: {
                id: message.id,
                session_id: session_id,
                role: message.role,
                text: message.text,
                timestamp: message.timestamp,
                platform: message.platform,
                artifacts: message.artifacts || null,
                metadata: message.metadata || null
            },
            session_id: session_id,
            wallet: wallet
        };

        console.log(`📤 Sending message: ${message.role} - "${message.text.substring(0, 50)}..."`);

        const response = await fetch(`${API_BASE_URL}/v1/conversations/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': wallet
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const result = await response.json();
            console.log(`✅ Message stored successfully`);
            return result;
        } else {
            const error = await response.text();
            console.error(`❌ Failed to store message: ${response.status} - ${error}`);
            return null;
        }
    } catch (error) {
        console.error(`❌ Error sending message:`, error);
        return null;
    }
}

// Function to send all sample data
async function sendAllSampleData() {
    console.log('🚀 Starting LanceDB data test...');
    console.log(`👛 Demo wallet: ${DEMO_WALLET}`);
    console.log(`📊 Sending ${sampleConversations.length} conversations with ${sampleConversations.reduce((sum, conv) => sum + conv.messages.length, 0)} total messages`);
    
    let successCount = 0;
    let totalMessages = 0;

    for (const conversation of sampleConversations) {
        console.log(`\n📝 Processing conversation: ${conversation.session_id}`);
        
        for (const message of conversation.messages) {
            totalMessages++;
            const result = await sendMessage(message, conversation.session_id, DEMO_WALLET);
            if (result) {
                successCount++;
            }
            
            // Small delay between messages to avoid rate limiting
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }

    console.log(`\n🎉 Test completed!`);
    console.log(`✅ Successfully sent: ${successCount}/${totalMessages} messages`);
    
    // Test retrieval
    await testDataRetrieval();
}

// Function to test data retrieval
async function testDataRetrieval() {
    console.log(`\n🔍 Testing data retrieval...`);
    
    try {
        // Test conversations list
        const listResponse = await fetch(`${API_BASE_URL}/v1/conversations/list`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': DEMO_WALLET
            },
            body: JSON.stringify({
                wallet: DEMO_WALLET
            })
        });

        if (listResponse.ok) {
            const conversations = await listResponse.json();
            console.log(`📋 Retrieved ${conversations.total} conversations`);
            
            if (conversations.conversations.length > 0) {
                console.log(`📄 Sample conversation titles:`);
                conversations.conversations.slice(0, 3).forEach(conv => {
                    console.log(`  - ${conv.title || 'Untitled'} (${conv.message_count} messages)`);
                });
            }
        } else {
            console.error(`❌ Failed to retrieve conversations: ${listResponse.status}`);
        }

        // Test conversation history
        const historyResponse = await fetch(`${API_BASE_URL}/v1/conversations/history`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': DEMO_WALLET
            },
            body: JSON.stringify({
                wallet: DEMO_WALLET,
                limit: 10
            })
        });

        if (historyResponse.ok) {
            const history = await historyResponse.json();
            console.log(`📚 Retrieved conversation history with ${history.messages?.length || 0} recent messages`);
        } else {
            console.error(`❌ Failed to retrieve history: ${historyResponse.status}`);
        }

    } catch (error) {
        console.error(`❌ Error testing retrieval:`, error);
    }
}

// Check if we're in a fetch-capable environment and run the test
if (typeof fetch !== 'undefined') {
    sendAllSampleData().catch(console.error);
} else {
    console.log('❌ This test requires a fetch-capable environment');
    console.log('💡 Please run this in a browser console or with Node.js + fetch polyfill');
    
    // Export for Node.js if needed
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { sendAllSampleData, sampleConversations, DEMO_WALLET };
    }
}

console.log('🧪 LanceDB test script loaded');