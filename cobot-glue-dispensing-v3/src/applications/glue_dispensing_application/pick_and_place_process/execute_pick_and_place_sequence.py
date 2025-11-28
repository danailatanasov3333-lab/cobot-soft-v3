from modules.shared.tools.enums.Gripper import Gripper
from modules.utils.custom_logging import log_if_enabled, LoggingLevel, log_info_message


def execute_pick_sequence(robot_service,
        pickup_positions,
        measured_height,
        gripper,
        logger_context,
        grippers_config):
    ret = True
    for i, pos in enumerate(pickup_positions):
        # Create a copy to avoid modifying the original
        adjusted_pos = pos.copy()

        # Update Z coordinate based on measured height for pickup position (index 1)
        if i == 1:  # Pickup position (descent=0, pickup=1, lift=2)
            z_min = robot_service.robot_config.safety_limits.z_min
            if gripper == Gripper.DOUBLE:
                adjusted_pos[2] = z_min + grippers_config.double_gripper_z_offset + measured_height
            elif gripper == Gripper.SINGLE:
                adjusted_pos[2] = z_min + grippers_config.single_gripper_z_offset + measured_height

        log_info_message(logger_context,f"Moving to pickup position {i}: {adjusted_pos} (original: {pos})")

        ret = move_to(robot_service, adjusted_pos)
        if ret != 0:
            ret = False
            break
    return ret


def execute_place_sequence(robot_service, drop_off_position1, drop_off_position2):
    # Execute drop-off sequence via waypoint
    descent_height = robot_service.robot_config.safety_limits.z_min + 100
    waypoint = [-317.997, 261.207, descent_height + 50, 180, 0, 0]

    ret = move_to(robot_service, waypoint)
    if ret != 0:
        return ret
    ret = move_to(robot_service, drop_off_position1)
    if ret != 0:
        return ret
    ret = move_to(robot_service, drop_off_position2)

    robot_service.tool_manager.pump.turnOff(robot_service.robot)
    return ret


def execute_pick_and_place_sequence(robot_service,
                                    pickup_positions,
                                    drop_off_position1,
                                    drop_off_position2,
                                    measured_height,
                                    gripper,
                                    logger_context,
                                    grippers_config):
    ret = execute_pick_sequence(
        robot_service,
        pickup_positions,
        measured_height,
        gripper,
        logger_context,
        grippers_config
    )
    if ret != 0:
        return ret
    ret = execute_place_sequence(robot_service, drop_off_position1, drop_off_position2)
    if ret != 0:
        return ret
    ret = robot_service.move_to_calibration_position()
    return ret


def move_to(robot_service, position):
    ret = robot_service.move_to_position(position=position,
                                         tool=robot_service.robot_config.robot_tool,
                                         workpiece=robot_service.robot_config.robot_user,
                                         velocity=robot_service.robot_config.global_motion_settings.global_velocity,
                                         acceleration=robot_service.robot_config.global_motion_settings.global_acceleration,
                                         waitToReachPosition=True)
    return ret