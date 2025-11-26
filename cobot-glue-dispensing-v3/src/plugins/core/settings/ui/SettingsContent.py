import os

from PyQt6 import QtCore
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy


from frontend.widgets.CustomWidgets import CustomTabWidget, BackgroundTabPage
from plugins.core.settings.ui.robot_settings_tab.RobotConfigUI import RobotConfigUI
from .CameraSettingsTabLayout import CameraSettingsTabLayout
from plugins.core.wight_cells_settings_plugin.ui.GlueSettingsTabLayout import GlueSettingsTabLayout
from communication_layer.api.v1.endpoints import glue_endpoints
from applications.glue_dispensing_application.settings.GlueSettings import GlueSettings

#
RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..", "icons")
BACKGROUND = os.path.join(RESOURCE_DIR, "Background_&_Logo.png")
CAMERA_SETTINGS_ICON_PATH = os.path.join(RESOURCE_DIR, "CAMERA_SETTINGS_BUTTON.png")
CONTOUR_SETTINGS_ICON_PATH = os.path.join(RESOURCE_DIR, "CONTOUR_SETTINGS_BUTTON_SQUARE.png")
ROBOT_SETTINGS_ICON_PATH = os.path.join(RESOURCE_DIR, "ROBOT_SETTINGS_BUTTON_SQUARE.png")
GLUE_SETTINGS_ICON_PATH = os.path.join(RESOURCE_DIR, "glue_qty.png")


class BackgroundWidget(CustomTabWidget):
    def __init__(self):
        super().__init__()

        # Load the background image
        self.background = QPixmap(BACKGROUND)  # Update with your image path
        if self.background.isNull():
            print("Error: Background image not loaded correctly!")

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background.isNull():
            painter.drawPixmap(self.rect(), self.background)  # Scale image to widget size
        else:
            print("Background image not loaded")
        super().paintEvent(event)  # Call the base class paintEvent to ensure proper widget rendering


class SettingsContent(BackgroundWidget):
    # Action signals
    update_camera_feed_requested = QtCore.pyqtSignal()
    raw_mode_requested = QtCore.pyqtSignal(bool)
    
    # Settings change signal - replaces callback pattern
    setting_changed = QtCore.pyqtSignal(str, object, str)  # key, value, component_type

    def __init__(self, controller=None, controller_service=None):
        super().__init__()

        # Store controller_service for passing to UI components
        # Prefer controller_service over raw controller
        self.controller_service = controller_service
        self.controller = controller  # Legacy fallback

        self.setStyleSheet(""" 
            QTabWidget {
                background-color: white; 
                padding: 10px; 
            }
            QTabBar::tab { 
                background: transparent; 
                border: none; 
            } 
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Initialize tab containers
        self.cameraSettingsTab = None
        self.robotSettingsTab = None
        self.glueSettingsTab = None
        
        # Initialize layout containers
        self.cameraSettingsTabLayout = None
        self.robotSettingsTabLayout = None
        self.glueSettingsTabLayout = None

        # Get needed tabs from application context
        needed_tabs = self._get_needed_settings_tabs()
        print(f"SettingsContent: Creating tabs for application: {needed_tabs}")
        
        # Create tabs dynamically based on application needs
        self._create_dynamic_tabs(needed_tabs)
        
        print(f"SettingsContent: Tabs created successfully. Glue tab exists: {self.glueSettingsTab is not None}")

        # Set icons for tabs (Initial)
        self.update_tab_icons()

        # Connect unified signals to settings callback
        self._connect_settings_signals()
        # self.hide()  # Hide settings content initially

    def _get_needed_settings_tabs(self):
        """Get the settings tabs needed by the current application."""
        try:
            from core.application.ApplicationContext import get_application_settings_tabs
            return get_application_settings_tabs()
        except Exception as e:
            print(f"Error getting needed settings tabs: {e}")
            return ["camera", "robot"]  # Fallback to default tabs

    def _create_dynamic_tabs(self, needed_tabs):
        """Create tabs dynamically based on application needs."""
        try:
            # Create camera tab if needed
            if "camera" in needed_tabs:
                self._create_camera_tab()
            
            # Create robot tab if needed  
            if "robot" in needed_tabs:
                self._create_robot_tab()
                
            # Create glue tab if needed
            if "glue" in needed_tabs:
                self._create_glue_tab()
                
        except Exception as e:
            print(f"Error creating dynamic tabs: {e}")
            # Fallback to creating default tabs
            self._create_camera_tab()
            self._create_robot_tab()

    def _create_camera_tab(self):
        """Create camera settings tab."""
        self.cameraSettingsTab = BackgroundTabPage()
        self.addTab(self.cameraSettingsTab, "")
        
        # Create camera settings layout
        self.cameraSettingsTabLayout = CameraSettingsTabLayout(self.cameraSettingsTab)
        self.connectCameraSettingSignals()
        self.cameraSettingsTabLayout.update_camera_feed_signal.connect(lambda: self.update_camera_feed_requested.emit())
        
        # Set the layout to the tab
        self.cameraSettingsTab.setLayout(self.cameraSettingsTabLayout)

    def _create_robot_tab(self):
        """Create robot settings tab."""
        self.robotSettingsTab = BackgroundTabPage()
        self.addTab(self.robotSettingsTab, "")

        # Create robot settings using controller_service (signal-based pattern)
        self.robotSettingsTabLayout = RobotConfigUI(self, self.controller_service)

        # For RobotConfigUI widget, we need to add it as a widget, not set it as layout
        robot_tab_layout = QVBoxLayout()
        robot_tab_layout.addWidget(self.robotSettingsTabLayout)
        self.robotSettingsTab.setLayout(robot_tab_layout)

    def _create_glue_tab(self):
        """Create glue settings tab."""
        self.glueSettingsTab = BackgroundTabPage()
        self.addTab(self.glueSettingsTab, "")
        
        # Create glue settings with initial data fetched from server
        initial_glue_settings = self._load_initial_glue_settings()
        self.glueSettingsTabLayout = GlueSettingsTabLayout(self.glueSettingsTab, initial_glue_settings)
        
        # Set the layout to the tab
        self.glueSettingsTab.setLayout(self.glueSettingsTabLayout)

    def _connect_settings_signals(self):
        """
        Connect all settings tab signals to emit the unified setting_changed signal.
        This replaces the old callback pattern with clean signal emission.
        """
        # Connect glue settings value changes if glue tab exists
        if self.glueSettingsTabLayout is not None:
            self.glueSettingsTabLayout.value_changed_signal.connect(self._emit_setting_change)

        # Connect camera settings value changes if camera tab exists
        if self.cameraSettingsTabLayout is not None:
            self.cameraSettingsTabLayout.value_changed_signal.connect(self._emit_setting_change)

        # Connect robot settings value changes if robot tab exists
        if self.robotSettingsTabLayout is not None:
            self.robotSettingsTabLayout.value_changed_signal.connect(self._emit_setting_change)

    def _load_initial_glue_settings(self):
        """Load initial glue settings from the server."""
        try:
            print("Loading initial glue settings from server...")
            response = self.controller.handle(glue_endpoints.SETTINGS_GLUE_GET)
            
            if response and response.get('status') == 'success':
                settings_data = response.get('data', {})
                print(f"Loaded glue settings: {settings_data}")
                return GlueSettings(settings_data)
            else:
                print(f"Failed to load glue settings: {response}")
                return GlueSettings()  # Return default settings
        except Exception as e:
            print(f"Error loading initial glue settings: {e}")
            import traceback
            traceback.print_exc()
            return GlueSettings()  # Return default settings on error
    
    def _emit_setting_change(self, key: str, value, component_type: str):
        """
        Emit the unified setting_changed signal and maintain backward compatibility.
        
        Args:
            key: The setting key
            value: The new value
            component_type: The component class name
        """
        # Emit the new signal for modern signal-based handling
        self.setting_changed.emit(key, value, component_type)
    
    def clean_up(self):
        """Clean up resources when closing the settings content"""
        if self.cameraSettingsTabLayout is not None:
            self.cameraSettingsTabLayout.clean_up()
        # TODO: Add cleanup for other tabs if needed
        # if self.robotSettingsTabLayout is not None:
        #     self.robotSettingsTabLayout.clean_up()
        # if self.glueSettingsTabLayout is not None:
        #     self.glueSettingsTabLayout.clean_up()

    def updateCameraFeed(self, frame):
        """Update the camera feed in the camera settings tab."""
        if self.cameraSettingsTabLayout is not None:
            self.cameraSettingsTabLayout.update_camera_feed(frame)

    def connectCameraSettingSignals(self):
        print("Connecting camera settings signals")
        self.cameraSettingsTabLayout.star_camera_requested.connect(self.onStartCameraRequested)
        self.cameraSettingsTabLayout.raw_mode_requested.connect(self.onRawModeRequested)

    def onStartCameraRequested(self):
        print("Camera start requested")

    def onRawModeRequested(self, state):
        print("Raw mode requested")
        # Emit a signal to update the camera feed
        self.raw_mode_requested.emit(state)

    def update_tab_icons(self):
        """Dynamically update tab icons based on window width and created tabs"""
        tab_icon_size = int(self.width() * 0.05)  # 5% of new window width for tabs
        
        # Set icons based on which tabs were actually created
        tab_index = 0
        if self.cameraSettingsTab is not None:
            self.setTabIcon(tab_index, QIcon(CAMERA_SETTINGS_ICON_PATH))
            tab_index += 1
        
        if self.robotSettingsTab is not None:
            self.setTabIcon(tab_index, QIcon(ROBOT_SETTINGS_ICON_PATH))
            tab_index += 1
            
        if self.glueSettingsTab is not None:
            self.setTabIcon(tab_index, QIcon(GLUE_SETTINGS_ICON_PATH))
            tab_index += 1
        
        self.tabBar().setIconSize(QSize(tab_icon_size, tab_icon_size))

    def resizeEvent(self, event):
        """Resize the tab widget dynamically on window resize"""
        new_width = self.width()

        # Resize the tab widget to be responsive to the window size
        self.setMinimumWidth(int(new_width * 0.3))  # 30% of the window width
        self.update_tab_icons()

        super().resizeEvent(event)

    def updateCameraSettings(self, cameraSettings):
        print("Updating camera settings in SettingsContent: ", cameraSettings)
        if self.cameraSettingsTabLayout is not None:
            self.cameraSettingsTabLayout.updateValues(cameraSettings)

    def updateRobotSettings(self, robotSettings):
        if self.robotSettingsTabLayout is not None:
            self.robotSettingsTabLayout.updateValues(robotSettings)

    def updateContourSettings(self, contourSettings):
        # TODO: Implement contour settings update if needed
        # if self.contourSettingsTabLayout is not None:
        #     self.contourSettingsTabLayout.updateValues(contourSettings)
        return

    def updateGlueSettings(self, glueSettings):
        if self.glueSettingsTabLayout is not None:
            self.glueSettingsTabLayout.updateValues(glueSettings)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QSizePolicy

    app = QApplication(sys.argv)
    window = SettingsContent()
    window.show()
    sys.exit(app.exec())
