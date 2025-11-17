"""
Main Application Plugin Integration Example

Shows how to integrate the plugin system into the main application.
"""

import os
import sys
from typing import Dict, Any

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))  # Add parent for plugins
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))  # Add src

from plugins.base.plugin_manager import PluginManager
from frontend.core.services.ControllerService import ControllerService


class PluginizedMainApplication:
    """
    Example of how to integrate plugins into your main application.
    
    This replaces the hard-coded appWidgets with a dynamic plugin system.
    """
    
    def __init__(self, controller):
        self.controller = controller
        self.controller_service = ControllerService(controller)
        self.plugin_manager = PluginManager(self.controller_service)
        self.loaded_plugins: Dict[str, Any] = {}
        
        # Configure plugin directories
        self._setup_plugin_directories()
        
        # Set up event callbacks
        self.plugin_manager.set_event_callbacks(
            on_loaded=self._on_plugin_loaded,
            on_failed=self._on_plugin_failed
        )
    
    def _setup_plugin_directories(self):
        """Configure plugin search directories"""
        base_dir = os.path.dirname(__file__)
        
        # Add core plugins
        self.plugin_manager.add_plugin_directory(
            os.path.join(base_dir, 'core')
        )
        
        # Add feature plugins
        self.plugin_manager.add_plugin_directory(
            os.path.join(base_dir, 'features')
        )
        
        # Add extension plugins
        self.plugin_manager.add_plugin_directory(
            os.path.join(base_dir, 'extensions')
        )
    
    def start_application(self):
        """Start the application and load all plugins"""
        print("🚀 Starting Plugin-based Application...")
        
        try:
            # Load all plugins automatically
            results = self.plugin_manager.discover_and_load_all()
            
            print(f"Plugin loading results:")
            for plugin_name, success in results.items():
                status = "✅" if success else "❌"
                print(f"  {status} {plugin_name}")
            
            # Display system status
            status = self.plugin_manager.get_system_status()
            print(f"\\nSystem Status:")
            print(f"  Total plugins: {status['registry_stats']['total_plugins']}")
            print(f"  Loaded plugins: {status['registry_stats']['loaded_plugins']}")
            print(f"  Failed plugins: {status['registry_stats']['failed_plugins']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start application: {e}")
            return False
    
    def get_available_apps(self) -> Dict[str, str]:
        """
        Get list of available apps/plugins for the main menu.
        
        This replaces the hard-coded app widget list.
        
        Returns:
            Dictionary mapping app names to display names
        """
        apps = {}
        
        # Get all loaded plugins
        for plugin_name in self.plugin_manager.get_loaded_plugin_names():
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if plugin:
                # Use plugin metadata for display
                apps[plugin_name] = plugin.metadata.description
        
        return apps
    
    def create_app_widget(self, app_name: str, parent=None):
        """
        Create an app widget by plugin name.
        
        This replaces the switch statement in MainWindow.
        
        Args:
            app_name: Name of the plugin/app to create
            parent: Parent widget
            
        Returns:
            Widget instance or None if plugin not found
        """
        plugin = self.plugin_manager.get_plugin(app_name)
        if not plugin:
            print(f"❌ Plugin '{app_name}' not found")
            return None
        
        try:
            widget = plugin.create_widget(parent)
            print(f"✅ Created widget for plugin: {app_name}")
            return widget
        except Exception as e:
            print(f"❌ Failed to create widget for plugin '{app_name}': {e}")
            return None
    
    def get_plugin_icon_path(self, app_name: str) -> str:
        """
        Get icon path for a plugin.
        
        Args:
            app_name: Name of the plugin
            
        Returns:
            Path to plugin icon or empty string
        """
        plugin = self.plugin_manager.get_plugin(app_name)
        if plugin:
            return plugin.icon_path
        return ""
    
    def shutdown_application(self):
        """Shutdown application and cleanup all plugins"""
        print("🔄 Shutting down application...")
        self.plugin_manager.cleanup_all()
        print("✅ Application shutdown complete")
    
    def _on_plugin_loaded(self, plugin_name: str, plugin):
        """Callback when a plugin is successfully loaded"""
        print(f"🔌 Plugin loaded: {plugin_name}")
        self.loaded_plugins[plugin_name] = plugin
    
    def _on_plugin_failed(self, plugin_name: str, error: Exception):
        """Callback when a plugin fails to load"""
        print(f"⚠️  Plugin failed: {plugin_name} - {error}")


def demonstrate_plugin_integration():
    """Demonstrate how the plugin system integrates with main app"""
    print("🎯 Plugin Integration Demonstration")
    print("=" * 50)
    
    # Mock controller for demonstration
    class MockController:
        def __init__(self):
            self.requestSender = None
            
        def updateSettings(self, key, value, component_type):
            print(f"Mock: Update setting {key} = {value} ({component_type})")
            
        def handleGetSettings(self):
            return {}, {}, {}  # Mock camera, robot, glue settings
    
    # Create plugin-based application
    app = PluginizedMainApplication(MockController())
    
    # Start the application
    if not app.start_application():
        return False
    
    print("\\n" + "=" * 50)
    print("📱 Available Apps/Plugins:")
    print("=" * 50)
    
    # Show available apps
    apps = app.get_available_apps()
    for app_name, description in apps.items():
        icon_path = app.get_plugin_icon_path(app_name)
        print(f"📌 {app_name}")
        print(f"   Description: {description}")
        print(f"   Icon: {icon_path}")
        print()
    
    print("🎮 Creating Settings Widget...")
    settings_widget = app.create_app_widget("Settings")
    if settings_widget:
        print(f"✅ Settings widget created: {type(settings_widget).__name__}")
    
    # Cleanup
    app.shutdown_application()
    
    return True


if __name__ == "__main__":
    demonstrate_plugin_integration()