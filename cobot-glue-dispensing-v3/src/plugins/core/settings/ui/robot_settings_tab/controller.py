# Controller
import copy
import json
import os

from PyQt6.QtWidgets import QListWidget, QMessageBox, QInputDialog, QListWidgetItem

from communication_layer.api.v1 import Constants
from communication_layer.api.v1.Response import Response
from communication_layer.api.v1.endpoints import robot_endpoints
from core.application.ApplicationContext import get_core_settings_path
from core.model.settings.robotConfig.GlobalMotionSettings import GlobalMotionSettings
from core.model.settings.robotConfig.MovementGroup import MovementGroup
from core.model.settings.robotConfig.SafetyLimits import SafetyLimits
from core.model.settings.robotConfig.robotConfigModel import RobotConfig, get_default_config
from frontend.virtualKeyboard.VirtualKeyboard import FocusLineEdit
from plugins.core.settings.ui.helpers.commands import ConfigChangeCommand, CommandHistory


class RobotConfigController:
    """Controller class to handle all robot configuration logic"""

    def __init__(self, requestSender):
        self.ui = None  # Will be set by the UI after initialization
        self.requestSender = requestSender
        # Use application context for core settings path
        self.config_file = get_core_settings_path("robot_config.json")
        self.command_history = CommandHistory()
        self.is_loading = False  # Flag to prevent undo tracking during load

    def set_ui(self, ui):
        """Set the UI reference and initialize"""
        self.ui = ui
        self.connect_signals()
        self.load_config()

    def connect_signals(self):
        """Connect all UI signals to controller methods"""
        signals = self.ui.signals

        # Robot info signals
        signals.robot_ip_changed.connect(self.on_robot_ip_changed)
        signals.robot_tool_changed.connect(self.on_robot_tool_changed)
        signals.robot_user_changed.connect(self.on_robot_user_changed)
        signals.tcp_x_offset_changed.connect(self.on_tcp_x_offset_changed)
        signals.tcp_y_offset_changed.connect(self.on_tcp_y_offset_changed)

        # Movement signals
        signals.velocity_changed.connect(self.on_velocity_changed)
        signals.acceleration_changed.connect(self.on_acceleration_changed)

        # Position management signals
        signals.add_point_requested.connect(self.on_add_point)
        signals.remove_point_requested.connect(self.on_remove_point)
        signals.edit_point_requested.connect(self.on_edit_point)
        signals.move_to_point_requested.connect(self.on_move_to_point)

        # Single position signals
        signals.edit_single_position_requested.connect(self.on_edit_single_position)
        signals.set_current_position_requested.connect(self.on_set_current_position)
        signals.move_to_single_position_requested.connect(self.on_move_to_single_position)

        # File operations
        signals.save_requested.connect(self.on_save)
        signals.reset_requested.connect(self.on_reset)

        # Undo/Redo operations
        signals.undo_requested.connect(self.on_undo)
        signals.redo_requested.connect(self.on_redo)

        # Jog operations
        signals.jog_requested.connect(self.on_jog_requested)
        signals.jog_started.connect(self.on_jog_started)
        signals.jog_stopped.connect(self.on_jog_stopped)
        signals.save_current_position_as_point.connect(self.on_save_current_position_as_point)

        # Trajectory execution
        signals.execute_trajectory_requested.connect(self.on_execute_trajectory)

        # Safety limit signals
        signals.safety_limit_changed.connect(self.on_safety_limit_changed)

        # Nozzle clean iterations signal
        signals.nozzle_clean_iterations_changed.connect(self.on_nozzle_clean_iterations_changed)

        # Global motion settings signals
        signals.global_velocity_changed.connect(self.on_global_velocity_changed)
        signals.global_acceleration_changed.connect(self.on_global_acceleration_changed)

    def on_safety_limit_changed(self, limit_name, value):
        """Handle safety limit change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)

            # Update the specific safety limit
            safety_limits = new_config.safety_limits
            if limit_name == "X_MIN":
                safety_limits.x_min = value
            elif limit_name == "X_MAX":
                safety_limits.x_max = value
            elif limit_name == "Y_MIN":
                safety_limits.y_min = value
            elif limit_name == "Y_MAX":
                safety_limits.y_max = value
            elif limit_name == "Z_MIN":
                safety_limits.z_min = value
            elif limit_name == "Z_MAX":
                safety_limits.z_max = value
            elif limit_name == "RX_MIN":
                safety_limits.rx_min = value
            elif limit_name == "RX_MAX":
                safety_limits.rx_max = value
            elif limit_name == "RY_MIN":
                safety_limits.ry_min = value
            elif limit_name == "RY_MAX":
                safety_limits.ry_max = value
            elif limit_name == "RZ_MIN":
                safety_limits.rz_min = value
            elif limit_name == "RZ_MAX":
                safety_limits.rz_max = value

            command = ConfigChangeCommand(self, old_config, new_config, f"Change {limit_name} to {value}")
            self.execute_command_with_history(command)

    # Signal handlers
    def on_robot_ip_changed(self, value):
        """Handle robot IP change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            new_config.robot_ip = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change Robot IP to {value}")
            self.execute_command_with_history(command)

    def on_robot_tool_changed(self, value):
        """Handle robot tool change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            new_config.robot_tool = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change Robot Tool to {value}")
            self.execute_command_with_history(command)

    def on_robot_user_changed(self, value):
        """Handle robot user change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            new_config.robot_user = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change Robot User to {value}")
            self.execute_command_with_history(command)

    def on_tcp_x_offset_changed(self, value):
        """Handle TCP X offset change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            new_config.tcp_x_offset = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change TCP X Offset to {value}")
            self.execute_command_with_history(command)

    def on_tcp_y_offset_changed(self, value):
        """Handle TCP Y offset change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            new_config.tcp_y_offset = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change TCP Y Offset to {value}")
            self.execute_command_with_history(command)

    def on_velocity_changed(self, group_name, value):
        """Handle velocity change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            if group_name not in new_config.movement_groups:
                new_config.movement_groups[group_name] = MovementGroup()
            new_config.movement_groups[group_name].velocity = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change {group_name} velocity to {value}")
            self.execute_command_with_history(command)

    def on_acceleration_changed(self, group_name, value):
        """Handle acceleration change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            if group_name not in new_config.movement_groups:
                new_config.movement_groups[group_name] = MovementGroup()
            new_config.movement_groups[group_name].acceleration = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change {group_name} acceleration to {value}")
            self.execute_command_with_history(command)

    def on_add_point(self, group_name):
        """Handle add point request"""
        old_config = self.get_current_config()
        mock_position = [0, 0, 0, 0, 0, 0]

        list_widget = self.ui.position_lists[group_name]
        item = QListWidgetItem(str(mock_position))
        list_widget.addItem(item)

        new_config = self.get_current_config()
        command = ConfigChangeCommand(self, old_config, new_config, f"Add point to {group_name}")
        self.execute_command_with_history(command)

    def on_remove_point(self, group_name):
        """Handle remove point request"""
        list_widget = self.ui.position_lists[group_name]
        current_item = list_widget.currentItem()

        if current_item:
            old_config = self.get_current_config()
            row = list_widget.row(current_item)
            removed_point = current_item.text()
            list_widget.takeItem(row)

            new_config = self.get_current_config()
            command = ConfigChangeCommand(self, old_config, new_config, f"Remove point from {group_name}")
            self.execute_command_with_history(command)
        else:
            QMessageBox.information(self.ui, "No Selection", "Please select a point to remove.")

    def on_edit_point(self, group_name):
        """Handle edit point request"""
        list_widget = self.ui.position_lists[group_name]
        current_item = list_widget.currentItem()

        if current_item:
            old_config = self.get_current_config()
            old_text = current_item.text()

            success = self._edit_position_dialog(current_item.text(), group_name, current_item)
            if success:
                new_config = self.get_current_config()
                command = ConfigChangeCommand(self, old_config, new_config, f"Edit point in {group_name}")
                self.execute_command_with_history(command)
        else:
            QMessageBox.information(self.ui, "No Selection", "Please select a point to edit.")  # TODO TRANSLATE

    def on_move_to_point(self, group_name):
        """Handle move to point request"""
        list_widget = self.ui.position_lists[group_name]
        current_item = list_widget.currentItem()

        if current_item:
            point_name = current_item.text()
            x, y, z, rx, ry, rz = [s.strip() for s in point_name.strip('[]').split(',')]
            print(f"Parsed coordinates: x={x}, y={y}, z={z}, rx={rx}, ry={ry}, rz={rz}")
            req = robot_endpoints.ROBOT_MOVE_TO_POSITION.format(position=f"{x}/{y}/{z}/{rx}/{ry}/{rz}")
            vel_acc_info = self._get_velocity_acceleration_info(group_name)
            print(f"Moving to point: {point_name} in group: {group_name}{vel_acc_info}")
            self.requestSender.send_request(req, "")
        else:
            QMessageBox.information(self.ui, "No Selection", "Please select a point to move to.")  # TODO TRANSLATE

    def on_edit_single_position(self, group_name):
        """Handle edit single position request"""
        position_widget = self.ui.position_lists[group_name]
        old_config = self.get_current_config()
        old_text = position_widget.text()

        dummy_item = type('Item', (), {'setText': lambda self, text: position_widget.setText(text)})()
        success = self._edit_position_dialog(old_text, group_name, dummy_item)
        if success:
            new_config = self.get_current_config()
            command = ConfigChangeCommand(self, old_config, new_config, f"Edit {group_name}")
            self.execute_command_with_history(command)

    def on_set_current_position(self, group_name):
        """Handle set current position request"""
        old_config = self.get_current_config()
        mock_position = [0, 0, 0, 0, 0, 0]

        position_widget = self.ui.position_lists[group_name]
        position_widget.setText(str(mock_position))

        new_config = self.get_current_config()
        command = ConfigChangeCommand(self, old_config, new_config, f"Set current position for {group_name}")
        self.execute_command_with_history(command)

    def on_move_to_single_position(self, group_name):
        """Handle move to single position request"""
        position_widget = self.ui.position_lists[group_name]
        position_text = position_widget.text()

        if position_text.strip():
            vel_acc_info = self._get_velocity_acceleration_info(group_name)
            print(f"Moving to {group_name}: {position_text}{vel_acc_info}")

            # Send appropriate movement request based on group name
            if self.requestSender:
                if group_name == "HOME_POS":
                    self.requestSender.send_request(robot_endpoints.ROBOT_MOVE_TO_HOME_POS, position_text)
                    print(f"🤖 ROBOT_MOVE_TO_HOME_POS request sent: {position_text}")
                elif group_name == "LOGIN_POS":
                    self.requestSender.send_request(robot_endpoints.ROBOT_MOVE_TO_LOGIN_POS, position_text)
                    print(f"🤖 ROBOT_MOVE_TO_LOGIN_POS request sent: {position_text}")
                elif group_name == "CALIBRATION_POS":
                    self.requestSender.send_request(robot_endpoints.ROBOT_MOVE_TO_CALIB_POS, position_text)
                    print(f"🤖 ROBOT_MOVE_TO_CALIB_POS request sent: {position_text}")
                else:
                    # For other positions, just print the movement info
                    print(f"Moving to {group_name} (no specific request constant defined)")
        else:
            QMessageBox.information(self.ui, "No Position", f"No position set for {group_name}.")  # TODO TRANSLATE

    def on_save(self):
        """Handle save request"""
        config = self.get_current_config()
        self.save_config_to_file(config.to_dict())
        QMessageBox.information(self.ui, "Current Configuration",  # TODO TRANSLATE
                                f"Configuration saved to {self.config_file}\n\n" +  # TODO TRANSLATE
                                json.dumps(config.to_dict(), indent=2))

    def on_reset(self):
        """Handle reset request"""
        old_config = self.get_current_config()
        default_config = get_default_config()

        command = ConfigChangeCommand(self, old_config, default_config, "Reset configuration to defaults")
        self.execute_command_with_history(command)

        QMessageBox.information(self.ui, "Reset Complete",
                                "Configuration has been reset to defaults and saved.")  # TODO TRANSLATE

    def on_jog_requested(self, command, axis, direction, step):
        """Handle jog request from jog widget"""
        print(f"Jog request: {command} {axis} {direction} {step}")
        request = f"robot/jog/{axis}/{direction}/{step}"
        self.requestSender.send_request(request)

    def on_jog_started(self, direction):
        """Handle jog start"""
        print(f"Jog started: {direction}")

    def on_jog_stopped(self, direction):
        """Handle jog stop"""
        print(f"Jog stopped: {direction}")

    def on_save_current_position_as_point(self, group_name):
        """Handle saving current robot position to a specific group"""
        print(f"Saving current position to {group_name}")
        response = self.requestSender.send_request(robot_endpoints.ROBOT_GET_CURRENT_POSITION)
        response = Response.from_dict(response)
        status = response.status
        if status == Constants.RESPONSE_STATUS_ERROR:
            message = response.message
            # show error message
            QMessageBox.critical(self.ui, "Error", f"Failed to get current position: {message}")  # TODO TRANSLATE
            return

        current_position = response.data.get("position", None)
        # current_position = [100, 200, 300, 180, 0, 90]  # Mock current position

        if group_name in self.ui.position_lists:
            widget = self.ui.position_lists[group_name]

            if isinstance(widget, FocusLineEdit):
                old_config = self.get_current_config()
                widget.setText(str(current_position))
                new_config = self.get_current_config()
                command = ConfigChangeCommand(self, old_config, new_config, f"Save current position to {group_name}")
                self.execute_command_with_history(command)

            elif isinstance(widget, QListWidget):
                old_config = self.get_current_config()
                item = QListWidgetItem(str(current_position))
                widget.addItem(item)
                new_config = self.get_current_config()
                command = ConfigChangeCommand(self, old_config, new_config, f"Add current position to {group_name}")
                self.execute_command_with_history(command)

        QMessageBox.information(self.ui, "Position Saved", f"Current position saved to {group_name}")  # TODO TRANSLATE

    def on_execute_trajectory(self, group_name):
        """Handle trajectory execution request"""
        print(f"\n🚀 EXECUTING TRAJECTORY: {group_name}")
        print("=" * 50)

        # Get the trajectory points
        if group_name in self.ui.position_lists:
            widget = self.ui.position_lists[group_name]

            if isinstance(widget, QListWidget):
                points = []
                for i in range(widget.count()):
                    item = widget.item(i)
                    points.append(item.text())

                if not points:
                    print("❌ No points defined for trajectory!")
                    QMessageBox.warning(self.ui, "Empty Trajectory",
                                        f"No points defined for {group_name} trajectory.")  # TODO TRANSLATE
                    return

                request = None
                if group_name == "SLOT 1 PICKUP":
                    request = robot_endpoints.ROBOT_SLOT_1_PICKUP
                elif group_name == "SLOT 1 DROPOFF":
                    request = robot_endpoints.ROBOT_SLOT_1_DROP
                elif group_name == "SLOT 4 PICKUP":
                    request = robot_endpoints.ROBOT_SLOT_4_PICKUP
                elif group_name == "SLOT 4 DROPOFF":
                    request = robot_endpoints.ROBOT_SLOT_4_DROP
                elif group_name == "SLOT 0 PICKUP":
                    request = robot_endpoints.ROBOT_SLOT_0_PICKUP
                elif group_name == "SLOT 0 DROPOFF":
                    request = robot_endpoints.ROBOT_SLOT_0_DROP
                elif group_name == "NOZZLE CLEAN":
                    request = robot_endpoints.ROBOT_EXECUTE_NOZZLE_CLEAN

                self.requestSender.send_request(request)

        else:
            print(f"❌ Group {group_name} not found!")

    def on_nozzle_clean_iterations_changed(self, value):
        """Handle nozzle clean iterations change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            if "NOZZLE CLEAN" not in new_config.movement_groups:
                new_config.movement_groups["NOZZLE CLEAN"] = MovementGroup()
            new_config.movement_groups["NOZZLE CLEAN"].iterations = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change NOZZLE CLEAN iterations to {value}")
            self.execute_command_with_history(command)

    def on_global_velocity_changed(self, value):
        """Handle global velocity change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            if "GLOBAL" not in new_config.movement_groups:
                new_config.movement_groups["GLOBAL"] = MovementGroup()
            new_config.movement_groups["GLOBAL"].velocity = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change GLOBAL velocity to {value}")
            self.execute_command_with_history(command)

    def on_global_acceleration_changed(self, value):
        """Handle global acceleration change"""
        if not self.is_loading:
            old_config = self.get_current_config()
            new_config = copy.deepcopy(old_config)
            if "GLOBAL" not in new_config.movement_groups:
                new_config.movement_groups["GLOBAL"] = MovementGroup()
            new_config.movement_groups["GLOBAL"].acceleration = value
            command = ConfigChangeCommand(self, old_config, new_config, f"Change GLOBAL acceleration to {value}")
            self.execute_command_with_history(command)

    def on_undo(self):
        """Handle undo request"""
        description = self.command_history.undo()
        if description:
            print(f"Undid: {description}")
            self.update_undo_redo_buttons()
        else:
            QMessageBox.information(self.ui, "Nothing to Undo", "No actions available to undo.")  # TODO TRANSLATE

    def on_redo(self):
        """Handle redo request"""
        description = self.command_history.redo()
        if description:
            print(f"Redid: {description}")
            self.update_undo_redo_buttons()
        else:
            QMessageBox.information(self.ui, "Nothing to Redo", "No actions available to redo.")  # TODO TRANSLATE

    def execute_command_with_history(self, command):
        """Execute command and add to history"""
        self.command_history.execute_command(command)
        self.update_undo_redo_buttons()
        print(f"Executed: {command.get_description()}")

    def update_undo_redo_buttons(self):
        """Update undo/redo button states"""
        if hasattr(self.ui, 'undo_btn'):
            self.ui.undo_btn.setEnabled(self.command_history.can_undo())
        if hasattr(self.ui, 'redo_btn'):
            self.ui.redo_btn.setEnabled(self.command_history.can_redo())

    # Helper methods
    def _edit_position_dialog(self, current_text, group_name, item):
        """Show position edit dialog"""
        try:
            position_str = current_text.strip("[]")
            position_values = [float(x.strip()) for x in position_str.split(",")]
            formatted_position = "\n".join([f"{i}: {val}" for i, val in enumerate(position_values)])
        except:
            formatted_position = current_text

        new_text, ok = QInputDialog.getMultiLineText(
            self.ui,
            f"Edit Position in {group_name}",
            "Edit position values (format: 0: x, 1: y, 2: z, 3: rx, 4: ry, 5: rz):",
            formatted_position
        )

        if ok and new_text.strip():
            try:
                lines = new_text.strip().split('\n')
                new_values = []

                for line in lines:
                    if ':' in line:
                        value = float(line.split(':', 1)[1].strip())
                        new_values.append(value)
                    else:
                        new_values.append(float(line.strip()))

                item.setText(str(new_values))
                print(f"Updated position in {group_name}: {new_values}")
                return True

            except ValueError as e:
                QMessageBox.warning(
                    self.ui,
                    "Invalid Input",  # TODO TRANSLATE
                    f"Could not parse the position values. Please ensure all values are valid numbers.\nError: {str(e)}"
                    # TODO TRANSLATE
                )
        return False

    def _get_velocity_acceleration_info(self, group_name):
        """Get velocity/acceleration info string for a group"""
        if group_name in self.ui.velocity_acceleration_widgets:
            vel = self.ui.velocity_acceleration_widgets[group_name]["velocity"].value()
            acc = self.ui.velocity_acceleration_widgets[group_name]["acceleration"].value()
            return f" (Velocity: {vel}, Acceleration: {acc})"
        return ""

    # Configuration management
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    config = RobotConfig.from_dict(data)
            else:
                config = get_default_config()
                self.save_config_to_file(config.to_dict())

            self.apply_config_to_ui(config)

        except Exception as e:
            QMessageBox.warning(self.ui, "Config Load Error",
                                f"Failed to load config: {str(e)}\nUsing defaults.")  # TODO TRANSLATE
            config = get_default_config()
            self.apply_config_to_ui(config)

    def apply_config_to_ui(self, config):
        """Apply configuration to UI elements"""
        self.is_loading = True

        self.ui.ip_edit.setText(config.robot_ip)
        self.ui.tool_edit.setValue(config.robot_tool)
        self.ui.user_edit.setValue(config.robot_user)
        self.ui.tcp_x_offset_edit.setValue(config.tcp_x_offset)
        self.ui.tcp_y_offset_edit.setValue(config.tcp_y_offset)

        # Apply safety limits
        if hasattr(self.ui, 'safety_limits'):
            self.ui.safety_limits['X_MIN'].setValue(config.safety_limits.x_min)
            self.ui.safety_limits['X_MAX'].setValue(config.safety_limits.x_max)
            self.ui.safety_limits['Y_MIN'].setValue(config.safety_limits.y_min)
            self.ui.safety_limits['Y_MAX'].setValue(config.safety_limits.y_max)
            self.ui.safety_limits['Z_MIN'].setValue(config.safety_limits.z_min)
            self.ui.safety_limits['Z_MAX'].setValue(config.safety_limits.z_max)
            self.ui.safety_limits['RX_MIN'].setValue(config.safety_limits.rx_min)
            self.ui.safety_limits['RX_MAX'].setValue(config.safety_limits.rx_max)
            self.ui.safety_limits['RY_MIN'].setValue(config.safety_limits.ry_min)
            self.ui.safety_limits['RY_MAX'].setValue(config.safety_limits.ry_max)
            self.ui.safety_limits['RZ_MIN'].setValue(config.safety_limits.rz_min)
            self.ui.safety_limits['RZ_MAX'].setValue(config.safety_limits.rz_max)

        # Apply global motion settings
        if hasattr(self.ui, 'global_velocity'):
            self.ui.global_velocity.setValue(config.global_motion_settings.global_velocity)
        if hasattr(self.ui, 'global_acceleration'):
            self.ui.global_acceleration.setValue(config.global_motion_settings.global_acceleration)
        if hasattr(self.ui, 'emergency_decel'):
            self.ui.emergency_decel.setValue(config.global_motion_settings.emergency_decel)
        if hasattr(self.ui, 'max_jog_step'):
            self.ui.max_jog_step.setValue(config.global_motion_settings.max_jog_step)

        for group_name, group_data in config.movement_groups.items():
            if group_name in self.ui.position_lists:
                widget = self.ui.position_lists[group_name]

                if isinstance(widget, FocusLineEdit):
                    widget.setText(group_data.position or "")
                elif isinstance(widget, QListWidget):
                    widget.clear()
                    for point in group_data.points:
                        item = QListWidgetItem(point)
                        widget.addItem(item)

            if group_name in self.ui.velocity_acceleration_widgets:
                widgets = self.ui.velocity_acceleration_widgets[group_name]
                widgets["velocity"].setValue(group_data.velocity)
                widgets["acceleration"].setValue(group_data.acceleration)

            # Load iterations value for NOZZLE CLEAN group
            if group_name == "NOZZLE CLEAN" and hasattr(self.ui, 'nozzle_clean_iterations'):
                self.ui.nozzle_clean_iterations.setValue(group_data.iterations)

        self.is_loading = False
        self.update_undo_redo_buttons()

    def get_current_config(self):
        """Get current configuration from UI"""
        movement_groups = {}

        for group_name, widget in self.ui.position_lists.items():
            group_data = MovementGroup()

            if isinstance(widget, FocusLineEdit):
                position_text = widget.text().strip()
                if position_text:
                    group_data.position = position_text
            elif isinstance(widget, QListWidget):
                points = []
                for i in range(widget.count()):
                    item = widget.item(i)
                    points.append(item.text())
                group_data.points = points

            movement_groups[group_name] = group_data

        for group_name, widgets in self.ui.velocity_acceleration_widgets.items():
            if group_name not in movement_groups:
                movement_groups[group_name] = MovementGroup()

            movement_groups[group_name].velocity = widgets["velocity"].value()
            movement_groups[group_name].acceleration = widgets["acceleration"].value()

        # Get iterations value for NOZZLE CLEAN group
        if hasattr(self.ui, 'nozzle_clean_iterations'):
            if "NOZZLE CLEAN" not in movement_groups:
                movement_groups["NOZZLE CLEAN"] = MovementGroup()
            movement_groups["NOZZLE CLEAN"].iterations = self.ui.nozzle_clean_iterations.value()

        # Get safety limits from UI

        safety_limits = SafetyLimits()
        if hasattr(self.ui, 'safety_limits'):
            safety_limits.x_min = self.ui.safety_limits['X_MIN'].value()
            safety_limits.x_max = self.ui.safety_limits['X_MAX'].value()
            safety_limits.y_min = self.ui.safety_limits['Y_MIN'].value()
            safety_limits.y_max = self.ui.safety_limits['Y_MAX'].value()
            safety_limits.z_min = self.ui.safety_limits['Z_MIN'].value()
            safety_limits.z_max = self.ui.safety_limits['Z_MAX'].value()
            safety_limits.rx_min = self.ui.safety_limits['RX_MIN'].value()
            safety_limits.rx_max = self.ui.safety_limits['RX_MAX'].value()
            safety_limits.ry_min = self.ui.safety_limits['RY_MIN'].value()
            safety_limits.ry_max = self.ui.safety_limits['RY_MAX'].value()
            safety_limits.rz_min = self.ui.safety_limits['RZ_MIN'].value()
            safety_limits.rz_max = self.ui.safety_limits['RZ_MAX'].value()

        # Get global motion settings from UI
        global_motion_settings = GlobalMotionSettings()
        if hasattr(self.ui, 'global_velocity'):
            global_motion_settings.global_velocity = self.ui.global_velocity.value()
        if hasattr(self.ui, 'global_acceleration'):
            global_motion_settings.global_acceleration = self.ui.global_acceleration.value()
        if hasattr(self.ui, 'emergency_decel'):
            global_motion_settings.emergency_decel = self.ui.emergency_decel.value()
        if hasattr(self.ui, 'max_jog_step'):
            global_motion_settings.max_jog_step = self.ui.max_jog_step.value()

        return RobotConfig(
            robot_ip=self.ui.ip_edit.text(),
            robot_tool=self.ui.tool_edit.value(),
            robot_user=self.ui.user_edit.value(),
            tcp_x_offset=self.ui.tcp_x_offset_edit.value(),
            tcp_y_offset=self.ui.tcp_y_offset_edit.value(),
            movement_groups=movement_groups,
            safety_limits=safety_limits,
            global_motion_settings=global_motion_settings
        )

    def save_config_to_file(self, config_data):
        """Save configuration to JSON file and send ROBOT_UPDATE_CONFIG request"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)

            # Send UPDATE_CONFIG request after successful save
            if self.requestSender:
                self.requestSender.send_request(robot_endpoints.ROBOT_UPDATE_CONFIG)
                print(f"🔄 ROBOT_UPDATE_CONFIG request sent for file: {self.config_file}")
                print(f"   └── Configuration has been updated and saved")
            else:
                print("⚠️ RequestSender not available. Cannot send ROBOT_UPDATE_CONFIG request.")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.ui, "Save Error", f"Failed to save config: {str(e)}")
