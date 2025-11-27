import math

from applications.glue_dispensing_application.pick_and_place_process.logging_utils import \
    log_pickup_position_calculation_result
from applications.glue_dispensing_application.pick_and_place_process.utils import rotate_offsets
from modules.shared.tools.enums.Gripper import Gripper
from modules.utils.custom_logging import log_if_enabled, LoggingLevel

def calculate_pickup_height_based_on_gripper(gripper,z_min,double_gripper_z_offset,single_gripper_z_offset,match_height):
    if gripper == Gripper.DOUBLE:
        pickup_height = z_min + double_gripper_z_offset + match_height
    elif gripper == Gripper.SINGLE:
        pickup_height = z_min + single_gripper_z_offset + match_height
    else:
        raise ValueError(f"Unknown gripper type: {gripper}")

    return pickup_height

def calculate_pickup_positions(flat_centroid,
                               match_height,
                               robotService,
                               orientation,
                               gripper,
                               logging_enabled,
                               logger,
                               gripper_x_offset,
                               gripper_y_offset,
                               rz_orientation,
                               double_gripper_z_offset,
                               single_gripper_z_offset):
    """
    Calculate pickup positions with coordinate transformation and gripper offsets.

    Args:
        flat_centroid: Transformed centroid coordinates from homography
        match_height: Height of the workpiece to pick up
        robotService: Robot service for accessing config

    Returns:
        list: List of pickup positions [descent, pickup, lift]
    """


    # === LOGGING ===
    log_if_enabled(logging_enabled,logger,LoggingLevel.INFO, f"Starting pickup position calculation for centroid: {flat_centroid}")
    log_if_enabled(logging_enabled,logger,LoggingLevel.DEBUG, f"Input parameters: match_height={match_height}mm")

    # === FUNCTIONALITY ===
    # Apply 90° coordinate transformation
    pickup_x_rotated = -flat_centroid[1]  # 90° rotation: x' = -y
    pickup_y_rotated = flat_centroid[0]  # 90° rotation: y' = x

    if gripper == Gripper.DOUBLE:
        rz = rz_orientation - 90
    else:
        rz = rz_orientation

    orientation_radians = math.radians(rz-orientation) # convert to radians
    gripper_x_offset_rotated, gripper_y_offset_rotated = rotate_offsets(
        gripper_x_offset,
        gripper_y_offset,
        orientation_radians
    )

    # Apply rotated offsets to rotated position
    final_pickup_x = pickup_x_rotated + gripper_x_offset_rotated
    final_pickup_y = pickup_y_rotated + gripper_y_offset_rotated

    # Calculate heights
    z_min = robotService.robot_config.safety_limits.z_min
    descent_height = z_min + 150  # Safe descent height above minimum

    pickup_height = calculate_pickup_height_based_on_gripper(gripper,z_min,double_gripper_z_offset,single_gripper_z_offset,match_height)


    # Create pickup sequence: descent -> pickup -> lift

    # choose angle
    # compute candidate angles
    angle1 = rz - orientation
    angle2 = rz + orientation

    # normalize to [-180, 180] then pick the one closer to 0
    def _norm_deg(a):
        return ((a + 180) % 360) - 180

    angle1 = _norm_deg(angle1)
    angle2 = _norm_deg(angle2)
    angle_closer_to_zero = angle1 if abs(angle1) <= abs(angle2) else angle2

    height_measure_position = [pickup_x_rotated, pickup_y_rotated, descent_height, 180, 0, rz-orientation]

    pickup_positions = [
        [final_pickup_x, final_pickup_y, descent_height, 180, 0, rz-orientation],  # Descent
        [final_pickup_x, final_pickup_y, pickup_height, 180, 0, rz-orientation],  # Pickup
        [final_pickup_x, final_pickup_y, descent_height, 180, 0, rz-orientation] # Lift
    ]
    params = flat_centroid, pickup_x_rotated, pickup_y_rotated, orientation_radians, gripper_x_offset_rotated, gripper_y_offset_rotated, final_pickup_x, final_pickup_y, z_min, descent_height, pickup_height, pickup_positions
    # log_pickup_position_calculation_result(params)

    return pickup_positions, height_measure_position,pickup_height

