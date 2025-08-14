"""
Test script to verify Ollama model connectivity and functionality
"""

import os
import sys
import json
import requests
from litellm import completion

def test_ollama_direct():
    """Test direct connection to Ollama API"""
    print("Testing direct Ollama API connection...")
    
    base_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3:1b")
    
    try:
        # Test if Ollama is running
        response = requests.get(f"{base_url}/api/tags")
        if response.status_code == 200:
            print(f"✓ Ollama is running at {base_url}")
            models = response.json().get("models", [])
            print(f"  Available models: {[m['name'] for m in models]}")
            
            if not any(m['name'] == model for m in models):
                print(f"✗ Model '{model}' not found in Ollama")
                return False
        else:
            print(f"✗ Failed to connect to Ollama at {base_url}")
            return False
            
        # Test generation
        print(f"\nTesting generation with model '{model}'...")
        gen_response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": "Hello, how are you?",
                "stream": False
            }
        )
        
        if gen_response.status_code == 200:
            result = gen_response.json()
            print(f"✓ Direct API test successful")
            print(f"  Response: {result.get('response', '')[:100]}...")
            return True
        else:
            print(f"✗ Generation failed: {gen_response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_litellm_ollama():
    """Test Ollama through LiteLLM"""
    print("\n\nTesting Ollama through LiteLLM...")
    
    base_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3:1b")
    
    try:
        response = completion(
            model=f"ollama/{model}",
            messages=[{"role": "user", "content": "Say hello in one sentence"}],
            api_base=base_url,
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✓ LiteLLM test successful")
        print(f"  Model: ollama/{model}")
        print(f"  Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"✗ LiteLLM test failed: {e}")
        return False

def test_warmer_orchestrator():
    """Test the actual ConversationOrchestrator"""
    print("\n\nTesting ConversationOrchestrator...")
    
    try:
        from warmer.orchestrator import ConversationOrchestrator
        
        orchestrator = ConversationOrchestrator()
        print(f"✓ Orchestrator initialized")
        print(f"  Model: {orchestrator.ollama_model}")
        print(f"  API Base: {orchestrator.ollama_api_base}")
        
        # Test message generation
        if orchestrator.litellm_available:
            print("\nTesting message generation...")
            message = orchestrator._generate_message_with_ai("greeting")
            if message and message != orchestrator._get_fallback_message("greeting"):
                print(f"✓ AI message generation successful")
                print(f"  Generated: {message}")
                return True
            else:
                print(f"✗ AI generation failed, got fallback message")
                return False
        else:
            print("✗ LiteLLM not available in orchestrator")
            return False
            
    except Exception as e:
        print(f"✗ Orchestrator test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("OLLAMA MODEL TEST SUITE")
    print("=" * 60)
    
    # Display configuration
    print("\nConfiguration:")
    print(f"  OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'gemma3:1b')} (default: gemma3:1b)")
    print(f"  OLLAMA_API_BASE: {os.getenv('OLLAMA_API_BASE', 'http://localhost:11434')} (default: http://localhost:11434)")
    
    # Run tests
    results = []
    results.append(("Direct API", test_ollama_direct()))
    results.append(("LiteLLM", test_litellm_ollama()))
    results.append(("Orchestrator", test_warmer_orchestrator()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:20} {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✓ All tests passed!" if all_passed else "✗ Some tests failed!"))
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())