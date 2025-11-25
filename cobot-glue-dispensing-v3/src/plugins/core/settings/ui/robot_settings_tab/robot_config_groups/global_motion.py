from dataclasses import dataclass

from PyQt6.QtWidgets import QGroupBox, QGridLayout, QLabel

from frontend.virtualKeyboard.VirtualKeyboard import FocusSpinBox
from plugins.core.settings.ui.robot_settings_tab.robot_config_groups.base import SettingGroupBox

@dataclass
class GlobalMotionSettings:
    velocity: int
    acceleration: int

    def to_dict(self):
        return {
            "velocity": self.velocity,
            "acceleration": self.acceleration
        }

class GlobalMotionSettingsGroup(SettingGroupBox):
    def __init__(self):
        super().__init__("Global Motion Settings")
        self.layout = self.build_layout()
        self.build_ui()

    def build_layout(self):
        from PyQt6.QtWidgets import QGridLayout
        layout = QGridLayout()
        return layout

    def build_ui(self):
        # Global Velocity and Acceleration Settings
        self.global_group = QGroupBox("Global Motion Settings")
        global_layout = QGridLayout()

        # Global velocity
        self.global_velocity_label = QLabel("Global Velocity:")
        global_layout.addWidget(self.global_velocity_label, 0, 0)
        self.global_velocity = FocusSpinBox()
        self.global_velocity.setRange(1, 1000)
        self.global_velocity.setValue(100)
        self.global_velocity.setSuffix(" mm/s")
        global_layout.addWidget(self.global_velocity, 0, 1)

        # Global acceleration
        self.global_acceleration_label = QLabel("Global Acceleration:")
        global_layout.addWidget(self.global_acceleration_label, 1, 0)
        self.global_acceleration = FocusSpinBox()
        self.global_acceleration.setRange(1, 1000)
        self.global_acceleration.setValue(100)
        self.global_acceleration.setSuffix(" mm/s²")
        global_layout.addWidget(self.global_acceleration, 1, 1)

        self.global_group.setLayout(global_layout)

    def get_settings(self)->GlobalMotionSettings:
        return GlobalMotionSettings(
            velocity=self.global_velocity.value(),
            acceleration=self.global_acceleration.value()
        )

    def update_values(self, settings:GlobalMotionSettings):
        self.global_velocity.setValue(settings.velocity)
        self.global_acceleration.setValue(settings.acceleration)