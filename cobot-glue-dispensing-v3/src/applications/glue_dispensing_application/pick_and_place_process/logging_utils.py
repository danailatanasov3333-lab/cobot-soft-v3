import math

from modules.utils.custom_logging import log_if_enabled, LoggingLevel, log_info_message


def log_pickup_position_calculation_result(params,log_enabled,logger,gripper_x_offset,gripper_y_offset):
    flat_centroid, pickup_x_rotated, pickup_y_rotated, orientation_radians, gripper_x_offset_rotated, gripper_y_offset_rotated, final_pickup_x, final_pickup_y, z_min, descent_height, pickup_height, pickup_positions = params
    # === LOGGING ===
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO, f"COORDINATE TRANSFORMATION:")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Before 90° rotation: ({flat_centroid[0]:.2f}, {flat_centroid[1]:.2f}) mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  └─ After 90° rotation:  ({pickup_x_rotated:.2f}, {pickup_y_rotated:.2f}) mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO, f"GRIPPER OFFSET TRANSFORMATION:")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Original offsets: ({gripper_x_offset}, {gripper_y_offset}) mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  └─ Rotated offsets:  ({gripper_x_offset_rotated:.2f}, {gripper_y_offset_rotated:.2f}) mm (rotated by {math.degrees(orientation_radians):.2f}°)")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO, f"FINAL PICKUP CALCULATION:")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Rotated position: ({pickup_x_rotated:.2f}, {pickup_y_rotated:.2f}) mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Applied offsets:  ({gripper_x_offset_rotated:.2f}, {gripper_y_offset_rotated:.2f}) mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"  └─ Final position:   ({final_pickup_x:.2f}, {final_pickup_y:.2f}) mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.DEBUG, f"HEIGHT CALCULATIONS:")
    log_if_enabled(log_enabled, logger, LoggingLevel.DEBUG, f"  ├─ Z minimum:     {z_min} mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.DEBUG, f"  ├─ Descent height: {descent_height} mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.DEBUG, f"  └─ Pickup height:  {pickup_height} mm")
    log_if_enabled(log_enabled, logger, LoggingLevel.INFO,
                   f"Generated {len(pickup_positions)} pickup positions (descent → pickup → lift)")
    log_if_enabled(log_enabled, logger, LoggingLevel.DEBUG, f"Pickup sequence: {pickup_positions}")


def log_match_details(logger_context,match_height,gripper,centroid,flat_centroid,orientations,match_i):
    log_info_message(logger_context, f"Match details: height={match_height}mm, gripper={gripper}")
    log_info_message(logger_context, "Applying homography transformation...")
    log_info_message(logger_context, f"HOMOGRAPHY TRANSFORMATION:")
    log_info_message(logger_context, f"  ├─ Camera coordinates: {centroid} pixels")
    log_info_message(logger_context, f"  ├─ Robot coordinates:  {flat_centroid} mm")
    log_info_message(logger_context, f"  ├─ Object orientation: {orientations[match_i]:.2f}°")
    log_info_message(logger_context, f"  └─ Assigned gripper:   {gripper}")


def log_drop_pos_calculated(logger_context,drop_off_position1,width,height):
    log_info_message(logger_context, f"📍 DROP-OFF: Position calculated at {drop_off_position1[:2]} mm (Z: {drop_off_position1[2]} mm)")
    log_info_message(logger_context, f"Drop-off position: {drop_off_position1}")
    log_info_message(logger_context,f"Workpiece dimensions: {width:.1f} x {height:.1f} mm")
