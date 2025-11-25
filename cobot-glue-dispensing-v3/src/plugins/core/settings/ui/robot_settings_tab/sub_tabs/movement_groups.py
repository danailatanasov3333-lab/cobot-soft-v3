from PyQt6.QtWidgets import QLabel, QHBoxLayout, QGroupBox, QVBoxLayout, QPushButton, QListWidget

from frontend.virtualKeyboard.VirtualKeyboard import FocusSpinBox, FocusLineEdit


def get_movement_groups_sub_tab(robot_config_ui):
    # Add Movement groups to scroll content
    movement_groups = {
        "LOGIN_POS": {"has_vel_acc": True, "single_position": True},
        "HOME_POS": {"has_vel_acc": True, "single_position": True},
        "CALIBRATION_POS": {"has_vel_acc": True, "single_position": True},
        "JOG": {"velocity": 20, "acceleration": 100, "has_positions": False},
        "NOZZLE CLEAN": {"velocity": 30, "acceleration": 30, "has_positions": True},
        "TOOL CHANGER": {"velocity": 100, "acceleration": 30, "has_positions": True},
        "SLOT 0 PICKUP": {"has_vel_acc": True, "has_positions": True},
        "SLOT 0 DROPOFF": {"has_vel_acc": True, "has_positions": True},
        "SLOT 1 PICKUP": {"has_vel_acc": True, "has_positions": True},
        "SLOT 1 DROPOFF": {"has_vel_acc": True, "has_positions": True},
        "SLOT 4 PICKUP": {"has_vel_acc": True, "has_positions": True},
        "SLOT 4 DROPOFF": {"has_vel_acc": True, "has_positions": True},
    }

    for group_name, config in movement_groups.items():
        group_box = QGroupBox(group_name)
        group_layout = QVBoxLayout()

        # Store group box reference for translation
        robot_config_ui._group_box_translation_map[group_box] = group_name

        # Velocity/acceleration controls
        if "velocity" in config and "acceleration" in config:
            vel_acc_layout = QHBoxLayout()
            vel_label = QLabel("Velocity:")  # TODO TRANSLATE
            vel_spin = FocusSpinBox()
            vel_spin.setRange(0, 1000)
            vel_spin.setValue(config["velocity"])
            acc_label = QLabel("Acceleration:")  # TODO TRANSLATE
            acc_spin = FocusSpinBox()
            acc_spin.setRange(0, 1000)
            acc_spin.setValue(config["acceleration"])

            vel_acc_layout.addWidget(vel_label)
            vel_acc_layout.addWidget(vel_spin)
            vel_acc_layout.addWidget(acc_label)
            vel_acc_layout.addWidget(acc_spin)
            vel_acc_layout.addStretch()
            group_layout.addLayout(vel_acc_layout)

            # Store label references for translation
            robot_config_ui._label_translation_map[vel_label] = "VELOCITY"
            robot_config_ui._label_translation_map[acc_label] = "ACCELERATION"

            robot_config_ui.velocity_acceleration_widgets[group_name] = {
                "velocity": vel_spin,
                "acceleration": acc_spin
            }
        elif config.get("has_vel_acc", False):
            vel_acc_layout = QHBoxLayout()
            vel_label = QLabel("Velocity:")  # TODO TRANSLATE
            vel_spin = FocusSpinBox()
            vel_spin.setRange(0, 1000)
            vel_spin.setValue(0)
            acc_label = QLabel("Acceleration:")  # TODO TRANSLATE
            acc_spin = FocusSpinBox()
            acc_spin.setRange(0, 1000)
            acc_spin.setValue(0)

            vel_acc_layout.addWidget(vel_label)
            vel_acc_layout.addWidget(vel_spin)
            vel_acc_layout.addWidget(acc_label)
            vel_acc_layout.addWidget(acc_spin)
            vel_acc_layout.addStretch()
            group_layout.addLayout(vel_acc_layout)

            # Store label references for translation
            robot_config_ui._label_translation_map[vel_label] = "VELOCITY"
            robot_config_ui._label_translation_map[acc_label] = "ACCELERATION"

            robot_config_ui.velocity_acceleration_widgets[group_name] = {
                "velocity": vel_spin,
                "acceleration": acc_spin
            }

        # Add iterations field specifically for NOZZLE CLEAN
        if group_name == "NOZZLE CLEAN":
            iterations_layout = QHBoxLayout()
            iterations_label = QLabel("Iterations:")
            iterations_spin = FocusSpinBox()
            iterations_spin.setRange(1, 100)
            iterations_spin.setValue(1)

            iterations_layout.addWidget(iterations_label)
            iterations_layout.addWidget(iterations_spin)
            iterations_layout.addStretch()
            group_layout.addLayout(iterations_layout)

            # Store for later access
            if not hasattr(robot_config_ui, 'nozzle_clean_iterations'):
                robot_config_ui.nozzle_clean_iterations = iterations_spin

        # Position controls
        if config.get("single_position", False):
            # Single position display
            position_layout = QHBoxLayout()
            position_label = QLabel(f"{group_name} Position:")  # TODO TRANSLATE
            position_display = FocusLineEdit()
            position_display.setReadOnly(True)
            edit_position_btn = QPushButton("Edit")  # TODO TRANSLATE
            set_current_btn = QPushButton("Set Current")  # TODO TRANSLATE
            move_to_btn = QPushButton("Move To")  # TODO TRANSLATE

            # Store button references for translation
            robot_config_ui._button_translation_map[edit_position_btn] = "EDIT"
            robot_config_ui._button_translation_map[set_current_btn] = "SAVE_CURRENT_POSITION"
            robot_config_ui._button_translation_map[move_to_btn] = "MOVE_TO"

            edit_position_btn.clicked.connect(
                lambda checked, gn=group_name: robot_config_ui.signals.edit_single_position_requested.emit(gn))
            set_current_btn.clicked.connect(
                lambda checked, gn=group_name: robot_config_ui.signals.set_current_position_requested.emit(gn))
            move_to_btn.clicked.connect(
                lambda checked, gn=group_name: robot_config_ui.signals.move_to_single_position_requested.emit(gn))

            position_layout.addWidget(position_display)
            position_layout.addWidget(edit_position_btn)
            position_layout.addWidget(set_current_btn)
            position_layout.addWidget(move_to_btn)

            group_layout.addWidget(position_label)
            group_layout.addLayout(position_layout)
            robot_config_ui.position_lists[group_name] = position_display

        elif config.get("has_positions", True):
            # Multiple positions
            position_list = QListWidget()
            position_list.setMaximumHeight(120)
            group_layout.addWidget(QLabel(f"{group_name} Points:"))  # TODO TRANSLATE
            group_layout.addWidget(position_list)

            button_layout = QHBoxLayout()
            add_btn = QPushButton("Add")  # TODO TRANSLATE
            remove_btn = QPushButton("Remove")  # TODO TRANSLATE
            edit_btn = QPushButton("Edit")  # TODO TRANSLATE
            move_btn = QPushButton("Move To")  # TODO TRANSLATE
            save_current_btn = QPushButton("Save Current")  # TODO TRANSLATE

            # Store button references for translation
            robot_config_ui._button_translation_map[add_btn] = "ADD"
            robot_config_ui._button_translation_map[remove_btn] = "REMOVE"
            robot_config_ui._button_translation_map[edit_btn] = "EDIT"
            robot_config_ui._button_translation_map[move_btn] = "MOVE_TO"
            robot_config_ui._button_translation_map[save_current_btn] = "SAVE_CURRENT_POSITION"

            add_btn.clicked.connect(lambda checked, gn=group_name: robot_config_ui.signals.add_point_requested.emit(gn))
            remove_btn.clicked.connect(lambda checked, gn=group_name: robot_config_ui.signals.remove_point_requested.emit(gn))
            edit_btn.clicked.connect(lambda checked, gn=group_name: robot_config_ui.signals.edit_point_requested.emit(gn))
            move_btn.clicked.connect(lambda checked, gn=group_name: robot_config_ui.signals.move_to_point_requested.emit(gn))
            save_current_btn.clicked.connect(
                lambda checked, gn=group_name: robot_config_ui.signals.save_current_position_as_point.emit(gn))

            button_layout.addWidget(add_btn)
            button_layout.addWidget(remove_btn)
            button_layout.addWidget(edit_btn)
            button_layout.addWidget(move_btn)
            button_layout.addWidget(save_current_btn)

            # Add Execute Trajectory button for trajectory groups
            trajectory_groups = ["NOZZLE CLEAN", "TOOL CHANGER", "SLOT 0 PICKUP", "SLOT 0 DROPOFF",
                                 "SLOT 1 PICKUP", "SLOT 1 DROPOFF", "SLOT 4 PICKUP", "SLOT 4 DROPOFF"]

            if group_name in trajectory_groups:
                execute_btn = QPushButton("Execute Trajectory")

                # Store button reference for translation
                robot_config_ui._button_translation_map[execute_btn] = "EXECUTE_TRAJECTORY"

                execute_btn.setStyleSheet("""
                         QPushButton {
                             background-color: #28a745;
                             color: white;
                             border: none;
                             border-radius: 4px;
                             padding: 6px 12px;
                             font-weight: bold;
                         }
                         QPushButton:hover {
                             background-color: #218838;
                         }
                         QPushButton:pressed {
                             background-color: #1e7e34;
                         }
                     """)
                execute_btn.clicked.connect(
                    lambda checked, gn=group_name: robot_config_ui.signals.execute_trajectory_requested.emit(gn))
                button_layout.addWidget(execute_btn)

            group_layout.addLayout(button_layout)

            robot_config_ui.position_lists[group_name] = position_list

        group_box.setLayout(group_layout)
        robot_config_ui.movement_group_tab_layout.addWidget(group_box)