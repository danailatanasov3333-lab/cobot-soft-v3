import os
from typing import Optional

from PyQt6.QtWidgets import QWidget

from plugins import IPlugin
from plugins.base.plugin_interface import PluginMetadata, PluginCategory, PluginPermission
from plugins.core.calibration.ui.CalibrationAppWidget import CalibrationAppWidget


class CalibrationPlugin(IPlugin):
    """Calibration Plugin Implementation"""

    def __init__(self):
        super().__init__()
        self._widget_instance = None

    @property
    def metadata(self):
        """Plugin metadata and information"""

        return PluginMetadata(
            name="Calibration",
            version="1.0.0",
            author="PL Team",
            description="Camera calibration tools for accurate measurements",
            category=PluginCategory.CORE,
            dependencies=[],
            permissions=[
                PluginPermission.CAMERA_ACCESS,
                PluginPermission.FILE_SYSTEM
            ],
            auto_load=True,
            min_app_version="1.0.0"
        )

    @property
    def icon_path(self) -> str:
        """Path to plugin icon"""
        return os.path.join(os.path.dirname(__file__), "icons", "calibration.png")

    def initialize(self, controller_service) -> bool:
        """
        Initialize the calibration plugin.

        Args:
            controller_service: Main controller service for backend operations
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.controller_service = controller_service
            self._mark_initialized(True)
            return True
        except Exception as e:
            print(f"Calibration plugin initialization failed: {e}")
            self._mark_initialized(False)
            return False

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create the calibration widget.

        Args:
            parent: Parent widget for the calibration interface

        Returns:
            QWidget representing the calibration interface
        """
        if not self._is_initialized:
            raise RuntimeError("Plugin not initialized")

        # Always create a fresh widget instance - don't cache to avoid Qt parent/child issues
        widget = CalibrationAppWidget(controller_service=self.controller_service, parent=parent)

        # Store weak reference for cleanup purposes
        self._widget_instance = widget

        return widget

    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        try:
            # Check if widget still exists and hasn't been deleted by Qt
            if self._widget_instance is not None:
                try:
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
            print(f"Error during calibration plugin cleanup: {e}")

    def can_load(self) -> bool:
        """Check if plugin can be loaded"""
        # Gallery plugin should always be available
        return True

    def get_status(self) -> dict:
        """Get plugin status"""
        status = super().get_status()
        status.update({
            "widget_created": self._widget_instance is not None,
            "controller_service_available": self.controller_service is not None
        })
        return status