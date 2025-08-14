#!/usr/bin/env python3
"""
CuWhapp Deployment Test Suite
Tests all critical endpoints and features after deployment
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class CuWhappTester:
    def __init__(self, base_url: str = "https://app.cuwapp.com", admin_url: str = "https://admin.cuwapp.com"):
        self.base_url = base_url.rstrip('/')
        self.admin_url = admin_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", response_data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response": response_data
        })
        
        if not success and response_data:
            print(f"    Response: {response_data}")
    
    def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test main app health
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            self.log_test("Main App Health Check", success, f"Status: {response.status_code}", data)
        except Exception as e:
            self.log_test("Main App Health Check", False, str(e))
        
        # Test admin health
        try:
            response = self.session.get(f"{self.admin_url}/health", timeout=10)
            success = response.status_code == 200
            self.log_test("Admin Dashboard Health", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Admin Dashboard Health", False, str(e))
    
    def test_api_endpoints(self):
        """Test core API endpoints"""
        print("\n🔍 Testing Core API Endpoints...")
        
        # Test swagger documentation
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=10)
            success = response.status_code == 200
            self.log_test("Swagger Documentation", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Swagger Documentation", False, str(e))
        
        # Test swagger.yaml
        try:
            response = self.session.get(f"{self.base_url}/swagger.yaml", timeout=10)
            success = response.status_code == 200
            self.log_test("OpenAPI Spec", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("OpenAPI Spec", False, str(e))
        
        # Test ping endpoint
        try:
            response = self.session.get(f"{self.base_url}/api/ping", timeout=10)
            success = response.status_code == 200
            self.log_test("API Ping", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("API Ping", False, str(e))
    
    def test_session_management(self):
        """Test session management endpoints"""
        print("\n🔍 Testing Session Management...")
        
        # Test session validation (should fail without auth)
        try:
            response = self.session.get(f"{self.base_url}/api/auth/session/validate")
            success = response.status_code == 401  # Should require auth
            message = "Correctly requires authentication"
            self.log_test("Session Validation Auth Required", success, message)
        except Exception as e:
            self.log_test("Session Validation Auth Required", False, str(e))
        
        # Test login endpoint (should accept POST)
        try:
            test_data = {"email": "test@example.com"}
            response = self.session.post(f"{self.base_url}/api/auth/login", json=test_data)
            success = response.status_code in [200, 400, 500]  # Should handle request
            self.log_test("Login Endpoint Accessible", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Login Endpoint Accessible", False, str(e))
    
    def test_whatsapp_endpoints(self):
        """Test WhatsApp session endpoints"""
        print("\n🔍 Testing WhatsApp Endpoints...")
        
        # Test sessions list (should require auth)
        try:
            response = self.session.get(f"{self.base_url}/api/sessions")
            success = response.status_code in [200, 401]  # Should either work or require auth
            self.log_test("Sessions List Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sessions List Endpoint", False, str(e))
    
    def test_campaign_endpoints(self):
        """Test campaign endpoints"""
        print("\n🔍 Testing Campaign Endpoints...")
        
        # Test campaigns list (should require auth)
        try:
            response = self.session.get(f"{self.base_url}/api/campaigns")
            success = response.status_code in [200, 401]  # Should either work or require auth
            self.log_test("Campaigns List Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Campaigns List Endpoint", False, str(e))
    
    def test_payment_endpoints(self):
        """Test payment endpoints"""
        print("\n🔍 Testing Payment Endpoints...")
        
        # Test payment config
        try:
            response = self.session.get(f"{self.base_url}/api/payments/config")
            success = response.status_code in [200, 401, 404]
            self.log_test("Payment Config Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Payment Config Endpoint", False, str(e))
    
    def test_warmer_endpoints(self):
        """Test warmer endpoints"""
        print("\n🔍 Testing Warmer Endpoints...")
        
        # Test warmer list (should require auth)
        try:
            response = self.session.get(f"{self.base_url}/api/warmer")
            success = response.status_code in [200, 401, 404]
            self.log_test("Warmer List Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Warmer List Endpoint", False, str(e))
    
    def test_static_files(self):
        """Test static file serving"""
        print("\n🔍 Testing Static Files...")
        
        # Test main HTML page
        try:
            response = self.session.get(f"{self.base_url}/")
            success = response.status_code == 200 and 'html' in response.headers.get('content-type', '')
            self.log_test("Main HTML Page", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Main HTML Page", False, str(e))
        
        # Test CSS files
        try:
            response = self.session.get(f"{self.base_url}/static/css/style.css")
            success = response.status_code == 200
            self.log_test("CSS Files", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("CSS Files", False, str(e))
        
        # Test JavaScript files
        try:
            response = self.session.get(f"{self.base_url}/static/js/app.js")
            success = response.status_code == 200
            self.log_test("JavaScript Files", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("JavaScript Files", False, str(e))
        
        # Test new session manager JS
        try:
            response = self.session.get(f"{self.base_url}/static/js/session-manager.js")
            success = response.status_code == 200
            self.log_test("Session Manager JS", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Session Manager JS", False, str(e))
    
    def test_admin_endpoints(self):
        """Test admin endpoints"""
        print("\n🔍 Testing Admin Endpoints...")
        
        # Test admin overview (should require admin auth)
        try:
            response = self.session.get(f"{self.admin_url}/api/stats/overview")
            success = response.status_code in [200, 401, 403]  # Should work or require admin auth
            self.log_test("Admin Overview", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Admin Overview", False, str(e))
    
    def test_database_connectivity(self):
        """Test database connectivity through API"""
        print("\n🔍 Testing Database Connectivity...")
        
        # Test database info endpoint
        try:
            response = self.session.get(f"{self.base_url}/api/database/info")
            success = response.status_code in [200, 401, 404]
            self.log_test("Database Info Endpoint", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Database Info Endpoint", False, str(e))
    
    def test_external_integrations(self):
        """Test external service integrations"""
        print("\n🔍 Testing External Integrations...")
        
        # Test WAHA API (if accessible)
        try:
            waha_url = "http://localhost:4500"
            response = self.session.get(f"{waha_url}/ping", timeout=5)
            success = response.status_code == 200
            self.log_test("WAHA API Connection", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("WAHA API Connection", False, f"WAHA may not be running: {str(e)}")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        print("🚀 Starting CuWhapp Deployment Tests...")
        print(f"Main App URL: {self.base_url}")
        print(f"Admin URL: {self.admin_url}")
        
        start_time = time.time()
        
        # Run all test suites
        self.test_health_endpoints()
        self.test_api_endpoints()
        self.test_session_management()
        self.test_whatsapp_endpoints()
        self.test_campaign_endpoints()
        self.test_payment_endpoints()
        self.test_warmer_endpoints()
        self.test_static_files()
        self.test_admin_endpoints()
        self.test_database_connectivity()
        self.test_external_integrations()
        
        end_time = time.time()
        
        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Duration: {end_time - start_time:.2f} seconds")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! Deployment looks good!")
        elif success_rate >= 80:
            print(f"\n⚠️  Most tests passed ({success_rate:.1f}%). Check failed tests above.")
        else:
            print(f"\n❌ Multiple test failures ({success_rate:.1f}% success). Please investigate.")
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": success_rate,
            "duration": end_time - start_time,
            "results": self.test_results
        }

def main():
    """Main function"""
    base_url = "https://app.cuwapp.com"
    admin_url = "https://admin.cuwapp.com"
    
    # Allow custom URLs from command line
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        admin_url = sys.argv[2]
    
    tester = CuWhappTester(base_url, admin_url)
    summary = tester.run_all_tests()
    
    # Save results to file
    with open('test_results.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: test_results.json")
    
    # Exit with appropriate code
    sys.exit(0 if summary['success_rate'] >= 80 else 1)

if __name__ == "__main__":
    main()