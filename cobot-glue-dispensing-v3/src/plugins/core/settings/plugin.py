"""
Settings Plugin Implementation

Main plugin class for the settings management system.
"""

import os
from typing import Optional
from PyQt6.QtWidgets import QWidget

# Import plugin base classes
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from plugins.base.plugin_interface import IPlugin, PluginMetadata, PluginCategory, PluginPermission

# Import the existing settings widget
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))
from plugins.core.settings.ui.SettingsAppWidget import SettingsAppWidget


class SettingsPlugin(IPlugin):
    """
    Settings plugin for system configuration management.
    
    Provides access to camera, robot, and glue settings through a
    unified interface with the new service architecture.
    """
    
    def __init__(self):
        super().__init__()
        self._widget_instance = None
    
    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata and information"""
        return PluginMetadata(
            name="Settings",
            version="1.0.0",
            author="PL Team",
            description="System settings management for camera, robot, and glue configurations",
            category=PluginCategory.CORE,
            dependencies=[],
            permissions=[
                PluginPermission.SETTINGS_READ,
                PluginPermission.SETTINGS_WRITE
            ],
            auto_load=True,
            min_app_version="1.0.0"
        )
    
    @property
    def icon_path(self) -> str:
        """Path to plugin icon"""
        return os.path.join(os.path.dirname(__file__), "icons", "settings.png")
    
    def initialize(self, controller_service) -> bool:
        """
        Initialize the settings plugin.
        
        Args:
            controller_service: Main controller service for backend operations
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.controller_service = controller_service
            self._mark_initialized(True)
            return True
        except Exception as e:
            print(f"Settings plugin initialization failed: {e}")
            self._mark_initialized(False)
            return False
    
    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create the settings widget.
        
        Args:
            parent: Parent widget for the settings interface
            
        Returns:
            QWidget representing the settings interface
        """
        if not self._is_initialized:
            raise RuntimeError("Plugin not initialized")
        
        # Always create a fresh widget instance - don't cache to avoid Qt parent/child issues
        # The old cached instance may have been deleted by Qt's parent-child cleanup
        widget = SettingsAppWidget(
            parent=parent,
            controller=self.controller_service.controller,
            controller_service=self.controller_service
        )

        # Store weak reference for cleanup purposes
        self._widget_instance = widget

        return widget

    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        try:
            # Check if widget still exists and hasn't been deleted by Qt
            if self._widget_instance is not None:
                try:
                    # Try to access the widget to see if it's still valid
                    if hasattr(self._widget_instance, 'clean_up'):
                        self._widget_instance.clean_up()
                except RuntimeError:
                    # Widget was already deleted by Qt's parent-child cleanup
                    pass
                finally:
                    self._widget_instance = None

            self.controller_service = None
            self._mark_initialized(False)
            
        except Exception as e:
            print(f"Error during settings plugin cleanup: {e}")
    
    def can_load(self) -> bool:
        """Check if plugin can be loaded"""
        # Settings plugin should always be available
        return True
    
    def get_status(self) -> dict:
        """Get plugin status"""
        status = super().get_status()
        status.update({
            "widget_created": self._widget_instance is not None,
            "controller_service_available": self.controller_service is not None
        })
        return status