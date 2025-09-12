#!/usr/bin/env python3
"""
Basic setup test for The E and Me voice interface system.

This script tests that the basic project structure and imports work correctly.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all core modules can be imported."""
    print("🧪 Testing Basic Imports")
    print("=" * 40)
    
    try:
        # Core imports
        print("1. Testing core imports...")
        from core.config_manager import ConfigManager
        from core.system_manager import SystemManager
        print("   ✅ Core modules imported successfully")
        
        # LLM imports
        print("2. Testing LLM imports...")
        from llm.local_llm import LocalLLM, LLMService
        print("   ✅ LLM modules imported successfully")
        
        # Utility imports
        print("3. Testing utility imports...")
        from utils.logger import setup_logging
        print("   ✅ Utility modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_config_loading():
    """Test configuration loading."""
    print("\n4. Testing configuration loading...")
    
    try:
        from core.config_manager import ConfigManager
        
        config_path = Path(__file__).parent.parent / "config" / "config.example.json"
        config_manager = ConfigManager(config_path)
        
        config = config_manager.load_config()
        print(f"   ✅ Configuration loaded: {len(config)} sections")
        
        # Test validation
        config_manager.validate_config(config)
        print("   ✅ Configuration validation passed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False


def test_logging():
    """Test logging setup."""
    print("\n5. Testing logging setup...")
    
    try:
        from utils.logger import setup_logging
        import logging
        
        setup_logging(level=logging.INFO)
        logger = logging.getLogger("test")
        logger.info("Test log message")
        
        print("   ✅ Logging setup successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Logging test failed: {e}")
        return False


def main():
    """Main test function."""
    print("🤖 The E and Me - Basic Setup Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_loading,
        test_logging
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All basic setup tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())