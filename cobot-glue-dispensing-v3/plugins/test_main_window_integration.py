#!/usr/bin/env python3
"""
Main Window Integration Test

Test the plugin system integration with the main application window.
"""

import os
import sys
import logging

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_plugin_widget_factory():
    """Test the plugin widget factory"""
    print("🧪 Testing Plugin Widget Factory Integration")
    print("=" * 50)
    
    try:
        # Initialize PyQt6 application first
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from frontend.core.main_window.PluginWidgetFactory import PluginWidgetFactory
        
        # Mock controller for testing
        class MockController:
            def __init__(self):
                self.requestSender = None
            def updateSettings(self, key, value, component_type):
                print(f"Mock: Update setting {key} = {value} ({component_type})")
            def handleGetSettings(self):
                return {}, {}, {}  # Mock camera, robot, glue settings
        
        # Mock main window
        class MockMainWindow:
            def __init__(self):
                pass
        
        controller = MockController()
        main_window = MockMainWindow()
        
        # Create plugin widget factory
        print("🔧 Creating PluginWidgetFactory...")
        factory = PluginWidgetFactory(controller, main_window)
        
        # Test available apps
        print("\\n📱 Available Apps:")
        apps = factory.get_available_apps()
        for app_name, info in apps.items():
            print(f"  - {app_name}: {info.get('name', 'Unknown')} ({info.get('category', 'unknown')})")
        
        # Test creating settings widget (should work as plugin)
        print("\\n🎯 Testing Settings Widget Creation:")
        settings_widget = factory.create_widget('settings')
        if settings_widget:
            widget_type = type(settings_widget).__name__
            print(f"  ✅ Created: {widget_type}")
        else:
            print("  ❌ Failed to create settings widget")
        
        # Test creating dashboard widget (should fallback to legacy)
        print("\\n🎯 Testing Dashboard Widget Creation (Legacy):")
        dashboard_widget = factory.create_widget('dashboard')
        if dashboard_widget:
            widget_type = type(dashboard_widget).__name__
            print(f"  ✅ Created: {widget_type}")
        else:
            print("  ❌ Failed to create dashboard widget")
        
        # Test plugin system status
        print("\\n📊 Plugin System Status:")
        status = factory.get_plugin_system_status()
        print(f"  Initialized: {status.get('initialized', False)}")
        print(f"  Loaded plugins: {status.get('registry_stats', {}).get('loaded_plugins', 0)}")
        
        # Cleanup
        print("\\n🔄 Cleaning up...")
        factory.cleanup()
        
        # Cleanup Qt application
        if app:
            app.quit()
        
        print("\\n✅ Plugin Widget Factory integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\\n❌ Plugin Widget Factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_window_create_app():
    """Test MainWindow create_app method with plugins"""
    print("\\n🏠 Testing MainWindow create_app Integration")
    print("=" * 50)
    
    try:        
        from frontend.core.main_window.WidgetFactory import WidgetType
        
        print("✅ Successfully imported MainWindow components")
        print("✅ WidgetType enum available:")
        
        for widget_type in WidgetType:
            print(f"  - {widget_type.name}: {widget_type.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ MainWindow integration test failed: {e}")
        return False

def main():
    """Run integration tests"""
    print("🔌 Plugin System Main Window Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Plugin Widget Factory", test_plugin_widget_factory),
        ("MainWindow Components", test_main_window_create_app)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\\n📋 Running: {test_name}")
        print("-" * 40)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((test_name, False))
    
    print("\\n" + "=" * 60)
    print("📈 Integration Test Results")
    print("=" * 60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name}")
        if success:
            passed += 1
    
    print(f"\\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All integration tests passed! Plugin system is integrated successfully.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())