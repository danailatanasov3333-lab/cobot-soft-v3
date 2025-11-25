from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QScrollArea,
    QListWidget, QComboBox, QDialog, QDialogButtonBox, QTabWidget, QListWidgetItem
)

from core.model.settings.robotConfig.SafetyLimits import SafetyLimits
from core.model.settings.robotConfig.robotConfigModel import RobotConfig
from frontend.core.utils.localization import get_app_translator
from frontend.virtualKeyboard.VirtualKeyboard import FocusLineEdit
from frontend.widgets.robotManualControl.RobotJogWidget import RobotJogWidget
from plugins.core.settings.ui.BaseSettingsTabLayout import BaseSettingsTabLayout
from plugins.core.settings.ui.robot_settings_tab.robot_config_groups.global_motion import GlobalMotionSettings
from plugins.core.settings.ui.robot_settings_tab.robot_config_groups.robot_info import RobotInfo
from plugins.core.settings.ui.robot_settings_tab.translate import translate
from plugins.core.settings.ui.robot_settings_tab.signals import RobotConfigSignals
from plugins.core.settings.ui.robot_settings_tab.sub_tabs.general_settings import GeneralRobotSettingsTab, \
    GeneralSettings
from plugins.core.settings.ui.robot_settings_tab.sub_tabs.movement_groups import get_movement_groups_sub_tab
from plugins.core.settings.ui.robot_settings_tab.sub_tabs.safety import SafetySettingsTab

# Main UI Class
class RobotConfigUI(BaseSettingsTabLayout, QWidget):
    value_changed_signal = pyqtSignal(str, object, str)
    def __init__(self,parent_widget= None, robotConfigController=None):
        # super().__init__()
        BaseSettingsTabLayout.__init__(self,parent_widget)
        QWidget.__init__(self)
        self.setWindowTitle("Robot Config UI")
        self.resize(1200, 800)
        self.position_lists = {}
        self.velocity_acceleration_widgets = {}
        self.signals = RobotConfigSignals()
        # Initialize translation mapping for UI elements
        self._button_translation_map = {}
        self._group_box_translation_map = {}
        self._label_translation_map = {}
        self.init_ui()
        self.connect_ui_signals()
        self.controller = robotConfigController

        # Set UI reference in controller and initialize
        self.controller.set_ui(self)
        self.translator = get_app_translator()
        self.translator.language_changed.connect(lambda: translate(self))
        translate(self)

    def init_ui(self):
        # Main horizontal layout
        main_layout = QHBoxLayout()

        # Left side - Scrollable Configuration panel (2/3 width)
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create main scroll content widget and layout
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()

        self.general_settings_tab = GeneralRobotSettingsTab()
        self.general_settings_tab.general_settings_changed_signal.connect(self.on_settings_changed)
        self.tab_widget.addTab(self.general_settings_tab,"General")

        self.safety_settings_tab = SafetySettingsTab()
        # self.safety_settings_tab.safety_settings_changed_signal.connect(lambda k,v:self.value_changed_signal(k,v,self.className))
        self.tab_widget.addTab(self.safety_settings_tab,"Safety")

        self.movement_group_tab_layout = QVBoxLayout()
        get_movement_groups_sub_tab(self)
        self.tab_widget.addTab(QWidget(), "Movement Groups")
        self.tab_widget.widget(2).setLayout(self.movement_group_tab_layout)
        self.tab_widget.addTab(QWidget(),"Calibration")

        scroll_layout.addWidget(self.tab_widget)

        # Set the scroll content and add to main scroll area
        scroll_content.setLayout(scroll_layout)
        config_scroll.setWidget(scroll_content)
        main_layout.addWidget(config_scroll, 2)  # 2/3 width

        # Right side - Jog control panel (1/3 width)
        jog_panel = QWidget()
        jog_layout = QVBoxLayout()

        jog_title = QLabel("Robot Jog Control") # TODO TRANSLATE
        jog_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 10px;
            padding: 10px;
            background-color: #F0F0F0;
            border-radius: 4px;
        """)
        jog_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        jog_layout.addWidget(jog_title)

        self.jog_widget = RobotJogWidget()
        jog_layout.addWidget(self.jog_widget)
        jog_layout.addStretch()

        jog_panel.setLayout(jog_layout)
        main_layout.addWidget(jog_panel, 1)  # 1/3 width

        self.setLayout(main_layout)

    def on_settings_changed(self,k,v):
        self.value_changed_signal.emit(k,v,self.className)

    def connect_ui_signals(self):
        """Connect UI element signals to custom signals"""
        # Robot info signals
        self.general_settings_tab.robot_info_group.ip_edit.textChanged.connect(self.signals.robot_ip_changed.emit)
        self.general_settings_tab.robot_info_group.tool_edit.valueChanged.connect(self.signals.robot_tool_changed.emit)
        self.general_settings_tab.robot_info_group.user_edit.valueChanged.connect(self.signals.robot_user_changed.emit)
        self.general_settings_tab.robot_info_group.tcp_x_offset_edit.valueChanged.connect(self.signals.tcp_x_offset_changed.emit)
        self.general_settings_tab.robot_info_group.tcp_y_offset_edit.valueChanged.connect(self.signals.tcp_y_offset_changed.emit)

        # Velocity/acceleration signals
        for group_name, widgets in self.velocity_acceleration_widgets.items():
            widgets["velocity"].valueChanged.connect(
                lambda value, gn=group_name: self.signals.velocity_changed.emit(gn, value)
            )
            widgets["acceleration"].valueChanged.connect(
                lambda value, gn=group_name: self.signals.acceleration_changed.emit(gn, value)
            )

        # Safety limit signals
        for limit_name, spinbox in self.safety_settings_tab.safety_group.safety_limits.items():
            spinbox.valueChanged.connect(
                lambda value, ln=limit_name: self.signals.safety_limit_changed.emit(ln, value)
            )

        # Global motion settings signals
        self.general_settings_tab.global_group.global_velocity.valueChanged.connect(self.signals.global_velocity_changed.emit)
        self.general_settings_tab.global_group.global_acceleration.valueChanged.connect(self.signals.global_acceleration_changed.emit)

        # Connect jog widget signals
        self.jog_widget.jogRequested.connect(self.signals.jog_requested.emit)
        self.jog_widget.jogStarted.connect(self.signals.jog_started.emit)
        self.jog_widget.jogStopped.connect(self.signals.jog_stopped.emit)
        self.jog_widget.save_point_requested.connect(self.on_jog_save_point)

        # Connect nozzle clean iterations signal
        if hasattr(self, 'nozzle_clean_iterations'):
            self.nozzle_clean_iterations.valueChanged.connect(self.signals.nozzle_clean_iterations_changed.emit)

    def on_jog_save_point(self):
        """Handle save point request from jog widget"""
        # Create dialog to select target group
        dialog = QDialog(self)
        dialog.setWindowTitle("Save Current Position")
        dialog.setModal(True)
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Select target group to save current position:")) # TODO TRANSLATE

        combo = QComboBox()
        # Add groups that can accept new points (both single and multi-position groups)
        for group_name in self.position_lists.keys():
            widget = self.position_lists[group_name]
            if isinstance(widget, QListWidget):  # Multi-position groups
                combo.addItem(group_name)
            elif isinstance(widget, FocusLineEdit):  # Single-position groups (LOGIN_POS, HOME_POS, CALIBRATION_POS)
                combo.addItem(group_name)

        layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted and combo.currentText():
            selected_group = combo.currentText()
            self.signals.save_current_position_as_point.emit(selected_group)

    def updateValues(self,robot_settings:RobotConfig):
        self.update_general_settings_tab(robot_settings)
        self.update_safety_settings_tab(robot_settings)
        self.update_movement_groups_tab(robot_settings)
        print(f"[RobotConfigUI] UI values updated from RobotConfig model")

    def update_general_settings_tab(self,robot_settings:RobotConfig):
        robot_info = RobotInfo(
            robot_ip=robot_settings.robot_ip,
            robot_tool=robot_settings.robot_tool,
            robot_user=robot_settings.robot_user,
            tcp_x_offset=robot_settings.tcp_x_offset,
            tcp_y_offset = robot_settings.tcp_y_offset)
        global_motion_settings = GlobalMotionSettings(
            velocity=robot_settings.global_motion_settings.global_velocity,
            acceleration=robot_settings.global_motion_settings.global_acceleration
        )
        general_values = GeneralSettings(
            robot_info=robot_info,
            global_motion= global_motion_settings
        )

        self.general_settings_tab.update_values(general_values)

    def update_safety_settings_tab(self,robot_settings:RobotConfig):
        safety_limits = SafetyLimits(
            x_min=robot_settings.safety_limits.x_min,
            x_max=robot_settings.safety_limits.x_max,
            y_min=robot_settings.safety_limits.y_min,
            y_max=robot_settings.safety_limits.y_max,
            z_min=robot_settings.safety_limits.z_min,
            z_max=robot_settings.safety_limits.z_max,
            rx_min=robot_settings.safety_limits.rx_min,
            rx_max=robot_settings.safety_limits.rx_max,
            ry_min=robot_settings.safety_limits.ry_min,
            ry_max=robot_settings.safety_limits.ry_max,
            rz_min=robot_settings.safety_limits.rz_min,
            rz_max=robot_settings.safety_limits.rz_max
        )

        self.safety_settings_tab.update_values(safety_limits)

    def update_movement_groups_tab(self,robot_settings:RobotConfig):
        for group_name, group_data in robot_settings.movement_groups.items():
            if group_name in self.position_lists:
                widget = self.position_lists[group_name]

                if isinstance(widget, FocusLineEdit):
                    widget.setText(group_data.position or "")
                elif isinstance(widget, QListWidget):
                    widget.clear()
                    for point in group_data.points:
                        item = QListWidgetItem(point)
                        widget.addItem(item)
