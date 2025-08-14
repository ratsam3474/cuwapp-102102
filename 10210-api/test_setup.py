"""
Test script to verify the database and campaign system setup
Run with: python test_setup.py
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test database imports
        from database.connection import init_database, test_connection
        from database.models import Campaign, Delivery, CampaignAnalytics
        print("✅ Database modules imported successfully")
        
        # Test job imports
        from jobs.manager import CampaignManager
        from jobs.models import CampaignCreate, MessageMode, MessageSample
        print("✅ Job modules imported successfully")
        
        # Test utility imports
        from utils.templates import MessageTemplateEngine
        print("✅ Utility modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🗄️ Testing database...")
    
    try:
        from database.connection import init_database, test_connection, get_database_info
        
        # Initialize database
        if init_database():
            print("✅ Database initialized successfully")
        else:
            print("❌ Database initialization failed")
            return False
        
        # Test connection
        if test_connection():
            print("✅ Database connection test passed")
        else:
            print("❌ Database connection test failed")
            return False
        
        # Get database info
        info = get_database_info()
        print(f"✅ Database info: {info['database_size_mb']} MB, {len(info['tables'])} tables")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test error: {str(e)}")
        return False

def test_campaign_manager():
    """Test campaign manager basic functionality"""
    print("\n📋 Testing campaign manager...")
    
    try:
        from jobs.manager import CampaignManager
        from jobs.models import CampaignCreate, MessageMode, MessageSample
        
        manager = CampaignManager()
        
        # Test campaign creation
        sample_campaign = CampaignCreate(
            name="Test Campaign",
            session_name="default",
            message_mode=MessageMode.MULTIPLE,
            message_samples=[
                MessageSample(text="Hello {name}! Welcome."),
                MessageSample(text="Hi {name}! Great to see you.")
            ]
        )
        
        # Note: This would actually create a campaign in the database
        # For testing, we'll just validate the model
        print("✅ Campaign model validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Campaign manager test error: {str(e)}")
        return False

def test_template_engine():
    """Test message template engine"""
    print("\n📝 Testing template engine...")
    
    try:
        from utils.templates import MessageTemplateEngine
        
        engine = MessageTemplateEngine()
        
        # Test template validation
        template = "Hello {name}! Your order {order_id} is ready."
        validation = engine.validate_template(template)
        
        if validation["is_valid"]:
            print("✅ Template validation passed")
        else:
            print(f"❌ Template validation failed: {validation['error_message']}")
            return False
        
        # Test variable extraction
        variables = engine.extract_variables(template)
        expected_vars = ["name", "order_id"]
        
        if set(variables) == set(expected_vars):
            print("✅ Variable extraction passed")
        else:
            print(f"❌ Variable extraction failed. Expected {expected_vars}, got {variables}")
            return False
        
        # Test template rendering
        sample_data = {"name": "John", "order_id": "12345"}
        rendered = engine.render_template(template, sample_data)
        expected = "Hello John! Your order 12345 is ready."
        
        if rendered == expected:
            print("✅ Template rendering passed")
        else:
            print(f"❌ Template rendering failed. Expected '{expected}', got '{rendered}'")
            return False
        
        # Test random sample selection
        samples = [
            "Hi {name}! Welcome.",
            "Hello {name}! Great to see you.",
            "Hey {name}! Thanks for joining."
        ]
        
        index, selected = engine.select_random_sample(samples)
        if 0 <= index < len(samples) and selected == samples[index]:
            print("✅ Random sample selection passed")
        else:
            print("❌ Random sample selection failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Template engine test error: {str(e)}")
        return False

def test_file_structure():
    """Test that all required directories exist"""
    print("\n📁 Testing file structure...")
    
    required_dirs = [
        "database",
        "jobs", 
        "utils",
        "data",
        "static"
    ]
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ Directory '{dir_name}' exists")
        else:
            print(f"❌ Directory '{dir_name}' missing")
            return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 WhatsApp Agent - Phase 2 Setup Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("Database", test_database),
        ("Campaign Manager", test_campaign_manager),
        ("Template Engine", test_template_engine)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n❌ {test_name} test failed")
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 2 foundation is ready.")
        print("\n📝 Next steps:")
        print("1. Install new dependencies: pip install -r requirements.txt")
        print("2. Test the campaign creation in your main application")
        print("3. Build the frontend interface for campaign management")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main()
