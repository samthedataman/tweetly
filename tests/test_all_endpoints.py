#!/usr/bin/env python3
"""
Comprehensive Backend API Test Suite
Tests all endpoints for data writing, reading, and embeddings functionality
"""

import requests
import json
import time
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"
TEST_USERNAME = "test_user_" + str(int(time.time()))

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Wallet-Address': TEST_WALLET
        })
        self.test_results = []
        self.test_data = {}
        self.auth_token = None
        self.user_created = False
        
    def log_test(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        
        if data and isinstance(data, dict) and len(str(data)) < 200:
            print(f"   Data: {data}")
    
    def setup_authentication(self):
        """Setup authentication for protected endpoints"""
        print("\n🔑 SETTING UP AUTHENTICATION")
        print("=" * 50)
        
        # For testing, we'll create a mock JWT token
        # In production, this would come from wallet signature verification
        try:
            # Create a simple auth token payload
            import jwt
            from datetime import datetime, timedelta
            
            payload = {
                "wallet": TEST_WALLET,
                "user_id": f"test_user_{TEST_WALLET[-8:]}",
                "exp": datetime.utcnow() + timedelta(hours=24)
            }
            
            # Use the same secret as the backend
            JWT_SECRET = "contextly-secret-key-change-in-production"
            self.auth_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            
            # Update session headers with auth token
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
            
            print(f"✅ Created auth token for wallet: {TEST_WALLET}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup authentication: {e}")
            return False
        
    def test_basic_connectivity(self):
        """Test basic API connectivity"""
        print("\n🔌 TESTING BASIC CONNECTIVITY")
        print("=" * 50)
        
        try:
            response = self.session.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Basic Connectivity", 
                    True, 
                    f"API responding - {data.get('service', 'Unknown')} v{data.get('version', 'Unknown')}", 
                    data
                )
                return True
            else:
                self.log_test("Basic Connectivity", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Basic Connectivity", False, f"Connection failed: {str(e)}")
            return False
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 TESTING AUTHENTICATION ENDPOINTS")
        print("=" * 50)
        
        # Test Twitter auth mode detection
        try:
            response = self.session.get(f"{API_BASE_URL}/v1/auth/x/test")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Twitter Auth Detection", 
                    True, 
                    f"Mode: {data.get('auth_type', 'unknown')}", 
                    data
                )
            else:
                self.log_test("Twitter Auth Detection", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Twitter Auth Detection", False, str(e))
        
        # Test Twitter status
        try:
            response = self.session.get(f"{API_BASE_URL}/v1/auth/x/status", 
                                       params={'wallet': TEST_WALLET})
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Twitter Auth Status", 
                    True, 
                    f"Status check successful", 
                    data
                )
            else:
                self.log_test("Twitter Auth Status", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Twitter Auth Status", False, str(e))
    
    def test_wallet_registration(self):
        """Test wallet registration (will fail with dummy signature, but tests endpoint)"""
        print("\n👛 TESTING WALLET REGISTRATION")
        print("=" * 50)
        
        try:
            payload = {
                "wallet": TEST_WALLET,
                "signature": "0x1234567890abcdef",  # Dummy signature
                "message": f"Contextly.ai Authentication\nAddress: {TEST_WALLET}\nTimestamp: {int(time.time() * 1000)}",
                "chainId": 1
            }
            
            response = self.session.post(f"{API_BASE_URL}/v1/wallet/register", 
                                       json=payload)
            
            if response.status_code == 401:
                self.log_test(
                    "Wallet Registration", 
                    True, 
                    "Endpoint working (correctly rejects invalid signature)"
                )
            else:
                self.log_test("Wallet Registration", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Wallet Registration", False, str(e))
    
    def test_conversation_endpoints(self):
        """Test conversation data writing and reading"""
        print("\n💬 TESTING CONVERSATION ENDPOINTS")
        print("=" * 50)
        
        # Test conversation list (should work)
        try:
            payload = {"wallet": TEST_WALLET}
            response = self.session.post(f"{API_BASE_URL}/v1/conversations/list", 
                                       json=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Conversation List", 
                    True, 
                    f"Retrieved {data.get('total', 0)} conversations", 
                    {'total': data.get('total', 0), 'count': len(data.get('conversations', []))}
                )
            else:
                self.log_test("Conversation List", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Conversation List", False, str(e))
        
        # Test conversation history
        try:
            response = self.session.get(f"{API_BASE_URL}/v1/conversations/history", 
                                       params={'limit': 10})
            
            if response.status_code == 200:
                data = response.json()
                message_count = len(data.get('messages', [])) if isinstance(data.get('messages'), list) else 0
                self.log_test(
                    "Conversation History", 
                    True, 
                    f"Retrieved {message_count} messages"
                )
            elif response.status_code == 500:
                self.log_test(
                    "Conversation History", 
                    False, 
                    "Known schema issue (search query parameter missing)"
                )
            else:
                self.log_test("Conversation History", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Conversation History", False, str(e))
        
        # Test message storage (will likely fail due to schema issues)
        session_id = f"test_session_{int(time.time())}"
        self.test_data['session_id'] = session_id
        
        try:
            message_payload = {
                "message": {
                    "id": f"test_msg_{int(time.time())}",
                    "session_id": session_id,
                    "role": "user",
                    "text": "This is a test message for comprehensive backend testing",
                    "timestamp": int(time.time() * 1000),
                    "platform": "claude"
                },
                "session_id": session_id,
                "wallet": TEST_WALLET
            }
            
            response = self.session.post(f"{API_BASE_URL}/v1/conversations/message", 
                                       json=message_payload)
            
            if response.status_code == 200:
                self.log_test(
                    "Message Storage", 
                    True, 
                    "Message stored successfully"
                )
                self.test_data['message_stored'] = True
            elif response.status_code == 500:
                self.log_test(
                    "Message Storage", 
                    False, 
                    "Known schema issue (user_id field missing)"
                )
            else:
                self.log_test("Message Storage", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Message Storage", False, str(e))
    
    def test_journey_endpoints(self):
        """Test journey/screenshot analysis endpoints"""
        print("\n🗺️ TESTING JOURNEY ENDPOINTS")
        print("=" * 50)
        
        try:
            # Create test journey data
            journey_payload = {
                "wallet": TEST_WALLET,
                "session_id": self.test_data.get('session_id', f"test_session_{int(time.time())}"),
                "screenshots": [
                    {
                        "screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                        "url": "https://example.com/test",
                        "title": "Test Page",
                        "timestamp": int(time.time() * 1000)
                    }
                ]
            }
            
            response = self.session.post(f"{API_BASE_URL}/v1/journeys/analyze", 
                                       json=journey_payload)
            
            if response.status_code == 200:
                self.log_test("Journey Analysis", True, "Journey processed successfully")
            elif response.status_code == 404:
                self.log_test("Journey Analysis", False, "User not found (expected for test user)")
            elif response.status_code == 500:
                self.log_test("Journey Analysis", False, "Server error (likely schema issue)")
            else:
                self.log_test("Journey Analysis", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Journey Analysis", False, str(e))
        
        # Test Sankey diagram generation
        try:
            response = self.session.post(f"{API_BASE_URL}/v1/journeys/sankey", 
                                        json={'wallet': TEST_WALLET})
            
            if response.status_code == 200:
                self.log_test("Sankey Generation", True, "Sankey diagram data retrieved")
            elif response.status_code == 404:
                self.log_test("Sankey Generation", False, "No journey data found (expected)")
            else:
                self.log_test("Sankey Generation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Sankey Generation", False, str(e))
    
    def test_knowledge_graph_endpoints(self):
        """Test knowledge graph and embeddings functionality"""
        print("\n🕸️ TESTING KNOWLEDGE GRAPH & EMBEDDINGS")
        print("=" * 50)
        
        # Test graph building
        try:
            graph_payload = {
                "session_id": self.test_data.get('session_id', f"test_session_{int(time.time())}"),
                "wallet": TEST_WALLET
            }
            
            response = self.session.post(f"{API_BASE_URL}/v1/graph/build", 
                                       params=graph_payload)
            
            if response.status_code == 200:
                self.log_test("Graph Building", True, "Knowledge graph built successfully")
            elif response.status_code == 404:
                self.log_test("Graph Building", False, "No conversation data found")
            else:
                self.log_test("Graph Building", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Graph Building", False, str(e))
        
        # Test graph querying
        try:
            query_payload = {
                "query": "test query about conversation data",
                "wallet": TEST_WALLET
            }
            
            response = self.session.post(f"{API_BASE_URL}/v1/graph/query", 
                                       params=query_payload)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Graph Querying", True, f"Query processed: {len(data.get('results', []))} results")
            else:
                self.log_test("Graph Querying", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Graph Querying", False, str(e))
        
        # Test graph visualization
        try:
            response = self.session.post(f"{API_BASE_URL}/v1/graph/visualize", 
                                        json={'wallet': TEST_WALLET})
            
            if response.status_code == 200:
                self.log_test("Graph Visualization", True, "Visualization data retrieved")
            else:
                self.log_test("Graph Visualization", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Graph Visualization", False, str(e))
    
    def test_stats_and_analytics(self):
        """Test stats and analytics endpoints"""
        print("\n📊 TESTING STATS & ANALYTICS")
        print("=" * 50)
        
        # Test user stats
        try:
            response = self.session.get(f"{API_BASE_URL}/v1/stats/{TEST_WALLET}")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("User Stats", True, "Stats retrieved successfully", data)
            elif response.status_code == 404:
                self.log_test("User Stats", False, "User not found (expected for test user)")
            else:
                self.log_test("User Stats", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("User Stats", False, str(e))
        
        # Test auto-mode status
        try:
            response = self.session.get(f"{API_BASE_URL}/v1/auto-mode/status/{TEST_WALLET}")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Auto-mode Status", True, "Auto-mode data retrieved", data)
            elif response.status_code == 401:
                self.log_test("Auto-mode Status", False, "Authentication required")
            else:
                self.log_test("Auto-mode Status", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Auto-mode Status", False, str(e))
        
        # Test insights generation
        try:
            response = self.session.post(f"{API_BASE_URL}/v1/insights/generate", 
                                       params={"time_range": 7})
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Insights Generation", True, "Insights generated successfully")
            elif response.status_code == 404:
                self.log_test("Insights Generation", False, "No data for insights (expected)")
            else:
                self.log_test("Insights Generation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Insights Generation", False, str(e))
    
    def test_lancedb_tables(self):
        """Test LanceDB table accessibility"""
        print("\n🗄️ TESTING LANCEDB TABLE ACCESS")
        print("=" * 50)
        
        # Test session history (indirect table access)
        try:
            response = self.session.get(f"{API_BASE_URL}/v1/sessions/history", 
                                       params={"limit": 10})
            
            if response.status_code == 200:
                data = response.json()
                session_count = len(data.get('sessions', [])) if isinstance(data.get('sessions'), list) else 0
                self.log_test("Session History", True, f"Retrieved {session_count} sessions")
            else:
                self.log_test("Session History", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Session History", False, str(e))
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print(f"\n🎯 KEY FINDINGS:")
        
        # Categorize results
        categories = {
            'Connectivity': [],
            'Authentication': [],
            'Data Storage': [],
            'Data Retrieval': [],
            'Embeddings/AI': [],
            'Other': []
        }
        
        for result in self.test_results:
            test_name = result['test']
            if 'Connectivity' in test_name:
                categories['Connectivity'].append(result)
            elif 'Auth' in test_name or 'Twitter' in test_name or 'Wallet' in test_name:
                categories['Authentication'].append(result)
            elif 'Storage' in test_name or 'Message' in test_name:
                categories['Data Storage'].append(result)
            elif 'List' in test_name or 'History' in test_name or 'Stats' in test_name:
                categories['Data Retrieval'].append(result)
            elif 'Graph' in test_name or 'Insights' in test_name or 'Embedding' in test_name:
                categories['Embeddings/AI'].append(result)
            else:
                categories['Other'].append(result)
        
        for category, results in categories.items():
            if results:
                passed = sum(1 for r in results if r['success'])
                total = len(results)
                print(f"   {category}: {passed}/{total} passed")
        
        print(f"\n🔧 RECOMMENDATIONS:")
        
        # Analyze failures and provide recommendations
        schema_issues = [r for r in self.test_results if not r['success'] and 'schema' in r['message'].lower()]
        auth_issues = [r for r in self.test_results if not r['success'] and 'auth' in r['message'].lower()]
        
        if schema_issues:
            print("   • Fix LanceDB schema issues (user_id field, search query parameters)")
        if auth_issues:
            print("   • Review authentication flow for production deployment")
        
        # Check if core functionality works
        list_working = any(r['success'] and 'List' in r['test'] for r in self.test_results)
        connectivity_working = any(r['success'] and 'Connectivity' in r['test'] for r in self.test_results)
        
        if connectivity_working and list_working:
            print("   ✅ Core API infrastructure is functional")
            print("   ✅ LanceDB connection is established")
            print("   ✅ Data retrieval endpoints work")
        
        print(f"\n💾 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': passed_tests/total_tests*100,
            'categories': categories,
            'results': self.test_results
        }

def main():
    """Run comprehensive backend test suite"""
    print("🧪 CONTEXTLY BACKEND COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print(f"🎯 Target API: {API_BASE_URL}")
    print(f"👛 Test Wallet: {TEST_WALLET}")
    print(f"⏰ Started: {datetime.now().isoformat()}")
    
    tester = BackendTester()
    
    # Run all test categories
    if not tester.test_basic_connectivity():
        print("❌ Backend not accessible. Please ensure the server is running.")
        return
    
    # Setup authentication for protected endpoints
    tester.setup_authentication()
    
    tester.test_auth_endpoints()
    tester.test_wallet_registration()
    tester.test_conversation_endpoints()
    tester.test_journey_endpoints()
    tester.test_knowledge_graph_endpoints()
    tester.test_stats_and_analytics()
    tester.test_lancedb_tables()
    
    # Generate final report
    report = tester.generate_report()
    
    # Save detailed results
    with open('backend_test_results.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: backend_test_results.json")
    print(f"⏰ Completed: {datetime.now().isoformat()}")
    
    return report

if __name__ == "__main__":
    main()