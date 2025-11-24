#!/usr/bin/env python3
"""
Plugin System Test

Test script to verify the plugin system works correctly.
"""

import os
import sys
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, '..'))  # Add parent directory
sys.path.insert(0, os.path.join(project_root, '..', 'src'))  # Add src directory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_plugin_discovery():
    """Test plugin discovery functionality"""
    print("🔍 Testing Plugin Discovery...")
    
    from plugins.base.plugin_loader import PluginLoader
    
    loader = PluginLoader()
    
    # Test discovery
    plugin_dirs = [os.path.join(project_root, 'core')]
    discovered = loader.discover_plugins(plugin_dirs)
    
    print(f"Discovered {len(discovered)} plugins:")
    for plugin_path, metadata in discovered:
        print(f"  - {metadata['name']} v{metadata['version']} at {plugin_path}")
    
    return len(discovered) > 0

def test_plugin_loading():
    """Test plugin loading functionality"""
    print("🚀 Testing Plugin Loading...")
    
    from plugins.base.plugin_loader import PluginLoader
    
    loader = PluginLoader()
    
    # Discover settings plugin
    plugin_dirs = [os.path.join(project_root, 'core')]
    discovered = loader.discover_plugins(plugin_dirs)
    
    for plugin_path, metadata in discovered:
        if metadata['name'] == 'Settings':
            try:
                plugin = loader.load_plugin(plugin_path, metadata)
                print(f"✅ Successfully loaded plugin: {plugin.metadata.name}")
                print(f"   Category: {plugin.metadata.category.value}")
                print(f"   Description: {plugin.metadata.description}")
                return True
            except Exception as e:
                print(f"❌ Failed to load plugin: {e}")
                return False
    
    print("❌ Settings plugin not found")
    return False

def test_plugin_manager():
    """Test plugin manager functionality"""
    print("🎯 Testing Plugin Manager...")
    
    from plugins.base.plugin_manager import PluginManager
    
    # Create mock controller service
    class MockControllerService:
        def __init__(self):
            self.controller = None
    
    manager = PluginManager()
    manager.set_controller_service(MockControllerService())
    manager.add_plugin_directory(os.path.join(project_root, 'core'))
    
    try:
        results = manager.discover_and_load_all()
        
        print(f"Loading results:")
        for plugin_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {plugin_name}")
        
        # Get loaded plugins
        loaded_plugins = manager.get_loaded_plugin_names()
        print(f"Loaded plugins: {loaded_plugins}")
        
        # Test getting a specific plugin
        if 'Settings' in loaded_plugins:
            settings_plugin = manager.get_plugin('Settings')
            print(f"Settings plugin status: {settings_plugin.get_status()}")
        
        return len(loaded_plugins) > 0
        
    except Exception as e:
        print(f"❌ Plugin manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all plugin system tests"""
    print("🧪 Plugin System Test Suite")
    print("=" * 40)
    
    tests = [
        ("Plugin Discovery", test_plugin_discovery),
        ("Plugin Loading", test_plugin_loading),
        ("Plugin Manager", test_plugin_manager)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"Result: {'✅ PASSED' if success else '❌ FAILED'}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("📊 Test Results Summary")
    print("=" * 40)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Plugin system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())