"""
Quick verification script to check if all services are running
"""
import requests
import json
from colorama import init, Fore, Style

init()

def check_service(name, url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ {name} is running at {url}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}⚠️  {name} returned status {response.status_code}{Style.RESET_ALL}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}❌ {name} is not running at {url}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ {name} error: {str(e)}{Style.RESET_ALL}")
        return False

def check_waha_sessions():
    try:
        response = requests.get("http://localhost:4500/api/sessions")
        if response.status_code == 200:
            sessions = response.json()
            working_sessions = [s for s in sessions if s.get('status') == 'WORKING']
            print(f"\n{Fore.CYAN}📱 WhatsApp Sessions:{Style.RESET_ALL}")
            for session in sessions:
                status = session.get('status', 'UNKNOWN')
                color = Fore.GREEN if status == 'WORKING' else Fore.YELLOW
                print(f"   {color}• {session['name']}: {status}{Style.RESET_ALL}")
            return len(working_sessions) > 0
        return False
    except:
        return False

def main():
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"🔍 WhatsApp Agent Service Check")
    print(f"{'='*50}{Style.RESET_ALL}\n")
    
    # Check services
    waha_ok = check_service("WAHA Server", "http://localhost:4500/ping")
    api_ok = check_service("FastAPI Backend", "https://app.cuwapp.com/")
    
    # Check WAHA sessions
    if waha_ok:
        has_working = check_waha_sessions()
        if not has_working:
            print(f"\n{Fore.YELLOW}⚠️  No WORKING sessions found. You need at least one active session.{Style.RESET_ALL}")
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    if waha_ok and api_ok:
        print(f"{Fore.GREEN}✅ All services are running! You can now run test_phase3.py{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Some services are not running. Please start them first.{Style.RESET_ALL}")
        if not waha_ok:
            print(f"{Fore.YELLOW}   • Start WAHA with: docker-compose up{Style.RESET_ALL}")
        if not api_ok:
            print(f"{Fore.YELLOW}   • Start FastAPI with: python start.py{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
