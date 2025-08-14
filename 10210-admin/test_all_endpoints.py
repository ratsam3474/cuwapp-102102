#!/usr/bin/env python3
"""
CuWhapp API Endpoint Testing Script
Tests all API endpoints to ensure they're working correctly
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

class APITester:
    def __init__(self, base_url: str = "https://app.cuwapp.com", admin_url: str = "https://admin.cuwapp.com"):
        self.base_url = base_url
        self.admin_url = admin_url
        self.auth_token = None
        self.admin_token = "admin_secret_token_2024"
        self.test_results = []
        
    def test_endpoint(self, method: str, url: str, name: str, 
                     headers: Optional[Dict] = None, 
                     data: Optional[Dict] = None,
                     expected_status: int = 200) -> bool:
        """Test a single endpoint"""
        try:
            start_time = time.time()
            
            if headers is None:
                headers = {}
            
            if self.auth_token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=5
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == expected_status:
                print(f"{Fore.GREEN}✓ {name:<50} [{response.status_code}] {elapsed:.2f}s")
                self.test_results.append({
                    "name": name,
                    "status": "passed",
                    "code": response.status_code,
                    "time": elapsed
                })
                return True
            else:
                print(f"{Fore.RED}✗ {name:<50} [{response.status_code}] Expected: {expected_status}")
                self.test_results.append({
                    "name": name,
                    "status": "failed",
                    "code": response.status_code,
                    "expected": expected_status,
                    "time": elapsed
                })
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}✗ {name:<50} Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "status": "error",
                "error": str(e)
            })
            return False
    
    def run_tests(self):
        """Run all API endpoint tests"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}CuWhapp API Endpoint Testing")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        # Health Check
        print(f"{Fore.YELLOW}Testing Health Endpoints:")
        self.test_endpoint("GET", f"{self.base_url}/health", "Main App Health")
        self.test_endpoint("GET", f"{self.admin_url}/health", "Admin Dashboard Health")
        
        # Authentication Endpoints
        print(f"\n{Fore.YELLOW}Testing Authentication Endpoints:")
        self.test_endpoint("GET", f"{self.base_url}/api/auth/stats", "Auth Stats")
        self.test_endpoint(
            "POST", 
            f"{self.base_url}/api/auth/newsletter/subscribe",
            "Newsletter Subscribe",
            data={"email": "test@example.com"},
            expected_status=200
        )
        
        # Session Management (requires auth)
        print(f"\n{Fore.YELLOW}Testing Session Endpoints:")
        # Note: These will fail without proper auth token
        self.test_endpoint("GET", f"{self.base_url}/api/sessions", "Get Sessions", expected_status=401)
        
        # Campaign Management
        print(f"\n{Fore.YELLOW}Testing Campaign Endpoints:")
        self.test_endpoint("GET", f"{self.base_url}/api/campaigns", "Get Campaigns", expected_status=401)
        self.test_endpoint("GET", f"{self.base_url}/api/campaigns/stats", "Campaign Stats", expected_status=401)
        
        # Warmer Endpoints
        print(f"\n{Fore.YELLOW}Testing Warmer Endpoints:")
        self.test_endpoint("GET", f"{self.base_url}/api/warmer", "List Warmers", expected_status=401)
        
        # Admin Endpoints
        print(f"\n{Fore.YELLOW}Testing Admin Endpoints:")
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        self.test_endpoint(
            "GET", 
            f"{self.admin_url}/api/stats/overview",
            "Admin Overview Stats",
            headers=admin_headers
        )
        
        self.test_endpoint(
            "GET",
            f"{self.admin_url}/api/users?limit=5",
            "Admin Get Users",
            headers=admin_headers
        )
        
        self.test_endpoint(
            "GET",
            f"{self.admin_url}/api/analytics/revenue",
            "Admin Revenue Analytics",
            headers=admin_headers
        )
        
        self.test_endpoint(
            "GET",
            f"{self.admin_url}/api/analytics/usage",
            "Admin Usage Analytics",
            headers=admin_headers
        )
        
        self.test_endpoint(
            "GET",
            f"{self.admin_url}/api/analytics/warmer",
            "Admin Warmer Analytics",
            headers=admin_headers
        )
        
        self.test_endpoint(
            "GET",
            f"{self.admin_url}/api/containers",
            "Admin Docker Containers",
            headers=admin_headers
        )
        
        # Print Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}Test Summary")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "passed"])
        failed = len([r for r in self.test_results if r["status"] == "failed"])
        errors = len([r for r in self.test_results if r["status"] == "error"])
        
        print(f"Total Tests: {total}")
        print(f"{Fore.GREEN}Passed: {passed}")
        print(f"{Fore.RED}Failed: {failed}")
        print(f"{Fore.YELLOW}Errors: {errors}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        # Show failed tests
        if failed > 0 or errors > 0:
            print(f"\n{Fore.RED}Failed/Error Tests:")
            for result in self.test_results:
                if result["status"] in ["failed", "error"]:
                    if result["status"] == "failed":
                        print(f"  - {result['name']}: Got {result['code']}, Expected {result['expected']}")
                    else:
                        print(f"  - {result['name']}: {result.get('error', 'Unknown error')}")
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n{Fore.CYAN}Detailed results saved to test_results.json")

def main():
    """Main function"""
    tester = APITester()
    
    # Check if services are running
    print(f"{Fore.CYAN}Checking if services are running...")
    
    try:
        requests.get(f"{tester.base_url}/health", timeout=2)
        print(f"{Fore.GREEN}✓ Main app is running on port 8000")
    except:
        print(f"{Fore.RED}✗ Main app is not running on port 8000")
        print(f"{Fore.YELLOW}  Start it with: python main.py")
    
    try:
        requests.get(f"{tester.admin_url}/health", timeout=2)
        print(f"{Fore.GREEN}✓ Admin dashboard is running on port 8001")
    except:
        print(f"{Fore.RED}✗ Admin dashboard is not running on port 8001")
        print(f"{Fore.YELLOW}  Start it with: python admin_dashboard.py")
    
    # Run tests
    tester.run_tests()

if __name__ == "__main__":
    main()