"""
Quick test for Phase 1 WhatsApp Agent features
"""
import requests
import json
from colorama import init, Fore, Style

init()

BASE_URL = "https://app.cuwapp.com"

def test_api():
    """Test basic API functionality"""
    print(f"\n{Fore.CYAN}Testing WhatsApp Agent API...{Style.RESET_ALL}\n")
    
    # Test 1: Get sessions
    try:
        response = requests.get(f"{BASE_URL}/api/sessions")
        if response.status_code == 200:
            data = response.json()
            print(f"{Fore.GREEN}✅ API is working!{Style.RESET_ALL}")
            print(f"   Sessions found: {len(data.get('data', []))}")
            
            # Show session details
            for session in data.get('data', []):
                status = session.get('status', 'UNKNOWN')
                color = Fore.GREEN if status == 'WORKING' else Fore.YELLOW
                print(f"   {color}• {session['name']}: {status}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ API error: {response.status_code}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Connection error: {str(e)}{Style.RESET_ALL}")
    
    # Test 2: Check server info
    try:
        response = requests.get(f"{BASE_URL}/api/server/info")
        if response.status_code == 200:
            data = response.json()
            print(f"\n{Fore.GREEN}✅ Server info accessible{Style.RESET_ALL}")
            print(f"   Version: {data.get('data', {}).get('version', {})}")
    except:
        pass
    
    # Test 3: Check if Phase 2 is available
    try:
        response = requests.get(f"{BASE_URL}/api/campaigns")
        if response.status_code == 200:
            print(f"\n{Fore.GREEN}✅ Phase 2 features are available!{Style.RESET_ALL}")
        elif response.status_code == 503:
            print(f"\n{Fore.YELLOW}⚠️  Phase 2 features not available (expected){Style.RESET_ALL}")
    except:
        pass
    
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Dashboard available at: https://app.cuwapp.com{Style.RESET_ALL}")
    print(f"{Fore.CYAN}API docs available at: https://app.cuwapp.com/docs{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    test_api()
