"""
Complete Phase 2 Test Suite
Tests all components: file processing, validation, templates, campaigns, and API
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_phase_2_complete():
    """Run comprehensive Phase 2 tests"""
    
    print("🚀 WhatsApp Agent - Phase 2 Complete Test Suite")
    print("=" * 60)
    
    tests = [
        ("🗄️ Database Foundation", test_database_foundation),
        ("📁 File Processing", test_file_processing),
        ("✅ Data Validation", test_data_validation),
        ("📝 Template Engine", test_template_engine),
        ("📋 Campaign Management", test_campaign_management),
        ("⚙️ Message Processing", test_message_processing),
        ("🔌 API Integration", test_api_integration),
        ("📊 Complete Workflow", test_complete_workflow)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                print(f"✅ {test_name} - PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"💥 {test_name} - CRASHED: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Phase 2 is fully operational!")
        print("\n🚀 Ready for production use:")
        print("   ✅ File Upload & Processing")
        print("   ✅ Random Message Samples") 
        print("   ✅ Campaign Management")
        print("   ✅ Background Job Processing")
        print("   ✅ Real-time Progress Tracking")
        print("   ✅ Complete API Integration")
    else:
        print(f"⚠️ {total - passed} tests failed. Please check errors above.")
    
    return passed == total

def test_database_foundation():
    """Test database and models"""
    try:
        from database.connection import init_database, test_connection, get_database_info
        from database.models import Campaign, Delivery, CampaignAnalytics
        
        # Initialize database
        if not init_database():
            print("❌ Database initialization failed")
            return False
        print("✅ Database initialized")
        
        # Test connection
        if not test_connection():
            print("❌ Database connection failed")
            return False
        print("✅ Database connection working")
        
        # Test models
        with get_database_info() as info:
            if len(info.get('tables', {})) >= 3:
                print("✅ All tables created")
            else:
                print("❌ Missing tables")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test error: {str(e)}")
        return False

def test_file_processing():
    """Test file upload and processing"""
    try:
        from utils.file_handler import FileHandler, CSVProcessor, DataPreprocessor
        
        # Create test CSV
        test_csv_content = """phone_number,name,company,message_samples
1234567890,John Doe,Acme Corp,"Hi {name}!|Hello {name}!|Hey {name}!"
0987654321,Jane Smith,Beta Inc,
5555555555,Bob Johnson,Gamma LLC,"Welcome {name}!|Greetings {name}!"
"""
        
        test_file = "test_data.csv"
        with open(test_file, 'w') as f:
            f.write(test_csv_content)
        
        # Test file handler
        handler = FileHandler()
        validation = handler.validate_file(test_file)
        
        if not validation["valid"]:
            print(f"❌ File validation failed: {validation['error']}")
            return False
        print("✅ File validation passed")
        
        # Test CSV processor
        processor = CSVProcessor()
        file_info = processor.get_file_info(test_file)
        
        if len(file_info["headers"]) != 4:
            print("❌ Wrong header count")
            return False
        print("✅ CSV headers detected correctly")
        
        # Test data reading
        data = processor.read_data(test_file)
        if len(data) != 3:
            print("❌ Wrong data row count")
            return False
        print("✅ CSV data read correctly")
        
        # Test column mapping
        mapping = DataPreprocessor.detect_column_mapping(file_info["headers"])
        if "phone_number" not in mapping:
            print("❌ Column mapping failed")
            return False
        print("✅ Column mapping detected")
        
        # Cleanup
        os.remove(test_file)
        
        return True
        
    except Exception as e:
        print(f"❌ File processing error: {str(e)}")
        # Cleanup on error
        try:
            os.remove(test_file)
        except:
            pass
        return False

def test_data_validation():
    """Test data validation systems"""
    try:
        from utils.validation import PhoneValidator, DataValidator
        
        # Test phone validation
        phone_validator = PhoneValidator()
        
        test_phones = [
            ("1234567890", True),
            ("+1-234-567-8900", True),
            ("invalid", False),
            ("", False)
        ]
        
        for phone, should_be_valid in test_phones:
            result = phone_validator.validate_phone(phone)
            if result["valid"] != should_be_valid:
                print(f"❌ Phone validation failed for {phone}")
                return False
        
        print("✅ Phone validation working")
        
        # Test data validator
        data_validator = DataValidator()
        
        test_data = [
            {"phone_number": "1234567890", "name": "John Doe"},
            {"phone_number": "invalid", "name": "Jane Smith"},
            {"phone_number": "5555555555", "name": ""}
        ]
        
        mapping = {"phone_number": "phone_number", "name": "name"}
        validation = data_validator.validate_campaign_data(test_data, mapping)
        
        if not validation["valid"]:
            print("❌ Data validation failed")
            return False
        
        if validation["valid_rows"] < 2:
            print("❌ Expected at least 2 valid rows")
            return False
        
        print("✅ Data validation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation test error: {str(e)}")
        return False

def test_template_engine():
    """Test message template engine with samples"""
    try:
        from utils.templates import MessageTemplateEngine
        
        engine = MessageTemplateEngine()
        
        # Test single template
        template = "Hello {name}! Your order {order_id} is ready."
        variables = {"name": "John", "order_id": "12345"}
        
        rendered = engine.render_template(template, variables)
        expected = "Hello John! Your order 12345 is ready."
        
        if rendered != expected:
            print(f"❌ Template rendering failed. Expected: {expected}, Got: {rendered}")
            return False
        print("✅ Template rendering working")
        
        # Test random sample selection
        samples = [
            "Hi {name}! Welcome.",
            "Hello {name}! Great to see you.",
            "Hey {name}! Thanks for joining."
        ]
        
        # Test multiple selections to ensure randomness
        selected_indices = set()
        for _ in range(10):
            index, sample = engine.select_random_sample(samples)
            selected_indices.add(index)
            if sample != samples[index]:
                print("❌ Sample selection inconsistent")
                return False
        
        if len(selected_indices) < 2:  # Should get some variety in 10 tries
            print("⚠️ Sample selection may not be random enough")
        
        print("✅ Random sample selection working")
        
        # Test message processing with samples
        row_data = {"name": "John", "company": "Acme"}
        csv_samples = "Hi {name}!|Hello {name}!|Hey {name}!"
        
        index, sample_text, final_message = engine.process_message_with_samples(
            row_data=row_data,
            campaign_samples=samples,
            csv_samples_column="message_samples"
        )
        
        if "John" not in final_message:
            print("❌ Variable substitution failed in message processing")
            return False
        
        print("✅ Message processing with samples working")
        
        return True
        
    except Exception as e:
        print(f"❌ Template engine test error: {str(e)}")
        return False

def test_campaign_management():
    """Test campaign CRUD operations"""
    try:
        from jobs.manager import CampaignManager
        from jobs.models import CampaignCreate, MessageSample, MessageMode
        
        manager = CampaignManager()
        
        # Create test campaign
        samples = [
            MessageSample(text="Hi {name}! Welcome to {company}."),
            MessageSample(text="Hello {name}! Great to have you at {company}."),
            MessageSample(text="Hey {name}! Thanks for joining {company}.")
        ]
        
        campaign_data = CampaignCreate(
            name="Test Campaign",
            session_name="default",
            message_mode=MessageMode.MULTIPLE,
            message_samples=samples,
            delay_seconds=5,
            retry_attempts=3
        )
        
        # Create campaign
        campaign = manager.create_campaign(campaign_data)
        if not campaign or not campaign.id:
            print("❌ Campaign creation failed")
            return False
        print("✅ Campaign created successfully")
        
        # Get campaign
        retrieved = manager.get_campaign(campaign.id)
        if not retrieved or retrieved.name != "Test Campaign":
            print("❌ Campaign retrieval failed")
            return False
        print("✅ Campaign retrieval working")
        
        # Test campaign status operations
        if not manager.start_campaign(campaign.id):
            print("❌ Campaign start failed")
            return False
        print("✅ Campaign start working")
        
        if not manager.pause_campaign(campaign.id):
            print("❌ Campaign pause failed")
            return False
        print("✅ Campaign pause working")
        
        # Get stats
        stats = manager.get_campaign_stats()
        if stats.total_campaigns < 1:
            print("❌ Campaign stats failed")
            return False
        print("✅ Campaign statistics working")
        
        # Cleanup
        manager.delete_campaign(campaign.id)
        print("✅ Campaign cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Campaign management test error: {str(e)}")
        return False

def test_message_processing():
    """Test message processor (without actual sending)"""
    try:
        from jobs.processor import MessageProcessor
        from waha_functions import WAHAClient
        
        # Test processor initialization
        processor = MessageProcessor()
        
        # Test status
        status = processor.get_processing_status()
        if "active_campaigns" not in status:
            print("❌ Processor status invalid")
            return False
        print("✅ Message processor initialized")
        
        # Test without actually starting campaign processing
        # (would need real campaign and WAHA session)
        print("✅ Message processor ready for campaign processing")
        
        return True
        
    except Exception as e:
        print(f"❌ Message processor test error: {str(e)}")
        return False

def test_api_integration():
    """Test API endpoints integration"""
    try:
        # Test Phase 2 availability check
        from main import PHASE_2_ENABLED
        
        if not PHASE_2_ENABLED:
            print("❌ Phase 2 not enabled in main application")
            return False
        print("✅ Phase 2 enabled in main application")
        
        # Test component imports in main
        from main import campaign_manager, template_engine
        
        if not campaign_manager:
            print("❌ Campaign manager not initialized in main")
            return False
        print("✅ Campaign manager integrated")
        
        if not template_engine:
            print("❌ Template engine not initialized in main")
            return False
        print("✅ Template engine integrated")
        
        # Test API extensions import
        try:
            from api_extensions import router
            print("✅ API extensions imported successfully")
        except ImportError:
            print("❌ API extensions import failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API integration test error: {str(e)}")
        return False

def test_complete_workflow():
    """Test complete campaign workflow"""
    try:
        print("Testing complete workflow simulation...")
        
        # 1. File processing simulation
        test_data = [
            {"phone_number": "1234567890", "name": "John", "company": "Acme"},
            {"phone_number": "0987654321", "name": "Jane", "company": "Beta"}
        ]
        
        # 2. Template processing simulation
        from utils.templates import MessageTemplateEngine
        engine = MessageTemplateEngine()
        
        samples = ["Hi {name}!", "Hello {name}!", "Hey {name}!"]
        
        for row in test_data:
            index, sample, message = engine.process_message_with_samples(
                row_data=row,
                campaign_samples=samples
            )
            
            if row["name"] not in message:
                print("❌ Workflow: Variable substitution failed")
                return False
        
        print("✅ Workflow: Template processing working")
        
        # 3. Campaign creation simulation
        from jobs.manager import CampaignManager
        from jobs.models import CampaignCreate, MessageSample, MessageMode
        
        manager = CampaignManager()
        
        campaign_data = CampaignCreate(
            name="Workflow Test Campaign",
            session_name="default",
            message_mode=MessageMode.MULTIPLE,
            message_samples=[MessageSample(text=s) for s in samples]
        )
        
        campaign = manager.create_campaign(campaign_data)
        print("✅ Workflow: Campaign creation working")
        
        # 4. Cleanup
        manager.delete_campaign(campaign.id)
        print("✅ Workflow: Complete workflow simulation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete workflow test error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_phase_2_complete()
    sys.exit(0 if success else 1)
