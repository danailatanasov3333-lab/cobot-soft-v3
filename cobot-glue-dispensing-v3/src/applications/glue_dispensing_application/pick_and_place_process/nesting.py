# Configuration
import math
import os
from dataclasses import dataclass
from datetime import datetime

from applications.glue_dispensing_application.pick_and_place_process.calculate_drop_off_position import \
    calculate_drop_off_position
from applications.glue_dispensing_application.pick_and_place_process.calculate_pickup_positions import \
    calculate_pickup_positions
from applications.glue_dispensing_application.pick_and_place_process.debug import save_nesting_debug_plot
from applications.glue_dispensing_application.pick_and_place_process.execute_pick_and_place_sequence import \
    execute_pick_and_place_sequence
from applications.glue_dispensing_application.pick_and_place_process.logging_utils import log_match_details, \
    log_drop_pos_calculated
from applications.glue_dispensing_application.pick_and_place_process.measure_height import measure_height_at_position, \
    HeightMeasureContext
from applications.glue_dispensing_application.pick_and_place_process.utils import rotate_offsets
from communication_layer.api.v1.topics import VisionTopics
from core.services.robot_service.impl.base_robot_service import RobotService
from modules.VisionSystem.heightMeasuring.LaserTracker import LaserTrackService
from modules.contour_matching import CompareContours
from modules.shared.MessageBroker import MessageBroker
from modules.shared.core.ContourStandartized import Contour
from modules.shared.localization.enums.Message import Message
from modules.shared.tools.enums.Gripper import Gripper
from modules.utils import utils
from modules.utils.contours import is_contour_inside_polygon
from modules.utils.custom_logging import setup_logger, LoggerContext, log_info_message
import time
# import logging
import cv2
import numpy as np

from applications.glue_dispensing_application.pick_and_place_process.Plane import Plane

# Import matplotlib for debug plotting
try:
    import matplotlib

    matplotlib.use('Agg')  # Use non-interactive backend for threading safety
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Debug plotting will be disabled.")

# Global logger variable
ENABLE_LOGGING = True  # Enable or disable logging

GRIPPER_X_OFFSET = 100.429  # mm, between transducer and gripper tip measured at rz = 0
GRIPPER_Y_OFFSET = 1.991  # mm, between transducer and gripper tip measured at rz = 0
DOUBLE_GRIPPER_Z_OFFSET = 14  # mm, between transducer and gripper tip
SINGLE_GRIPPER_Z_OFFSET = 19  # mm, between transducer and gripper tip
RZ_ORIENTATION = 90  # degrees
ROTATION_OFFSET_BETWEEN_PICKUP_AND_DROP_PLACE = 90  # degrees
DELAY_BETWEEN_CAPTURING_NEW_IMAGE = 1  # seconds ensuring robot is stationary and camera is stable

# Initialize logger if enabled
if ENABLE_LOGGING:
    nesting_logger = setup_logger("nesting")
else:
    nesting_logger = None

logger_context = LoggerContext(enabled=ENABLE_LOGGING, logger=nesting_logger)

@dataclass
class NestingResult:
    success: bool
    message: str


def move_to_nesting_capture_position(application,laser) -> int:
    ret = application.move_to_nesting_capture_position()
    if ret != 0:
        laser.turnOff()
        return False

    broker = MessageBroker()
    broker.publish(VisionTopics.THRESHOLD_REGION, {"region": "pickup"})

    time.sleep(DELAY_BETWEEN_CAPTURING_NEW_IMAGE)
    return True

def get_contours_with_retries(visionService, logger_context, max_retries=10, retry_delay=1) -> tuple[bool,any]:
    """
    Try multiple times to get contours from the vision system.
    Returns:
        contours (list) or None if no contours found after retries.
    """
    for attempt in range(1, max_retries + 1):
        contours = visionService.contours

        # SUCCESS: contours available
        if contours and len(contours) > 0:
            return True,contours

        # Not found yet → attempt retry
        if attempt < max_retries:
            log_info_message(logger_context, f"No contours detected (attempt {attempt}/{max_retries}), retrying...")
            time.sleep(retry_delay)

    # FAILED after all retries
    return False,None

def close_contours(newContours):
    # add first point to the end to close the contour
    for i, cnt in enumerate(newContours):
        if len(cnt) > 0:
            # Close the contour by adding first point to the end using numpy concatenation
            # Ensure dimensions match: cnt is (n, 1, 2), so reshape first point to (1, 1, 2)
            first_point = cnt[0].reshape(1, 1, 2)
            newContours[i] = np.vstack([cnt, first_point])

def filter_contours_in_pickup_area(pickup_area,newContours):
    if pickup_area is not None and len(pickup_area) >= 4:
        initial_count = len(newContours)
        filtered_contours = []
        for contour in newContours:
            if is_contour_inside_polygon(contour, pickup_area[0], pickup_area[1], pickup_area[2], pickup_area[3]):
                filtered_contours.append(contour)
        newContours = filtered_contours
        return newContours
    return None


def match_contours_to_workpieces(workpieces, newContours):
    try:
        matches_data, noMatches, _ = CompareContours.findMatchingWorkpieces(workpieces, newContours)
        return matches_data,noMatches
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None,None

def pickup_gripper(robotService: RobotService, target_gripper_id: int, laser) -> NestingResult:
    success, message = robotService.pickupGripper(target_gripper_id)
    if not success:
        log_info_message(logger_context, f"Failed to pick up gripper {target_gripper_id}: {message}")
        laser.turnOff()
        return NestingResult(success=False, message=f"Failed to pick up gripper {target_gripper_id}: {message}")

def change_gripper_if_needed(robotService: RobotService, target_gripper_id: int, laser) -> NestingResult:
    # if different, drop the current gripper (if any) and pick up the new one
    if robotService.current_tool is not None:
        log_info_message(logger_context, f"Dropping off current gripper: {robotService.current_tool}")
        success, message = robotService.dropOffGripper(robotService.current_tool)
        if not success:
            log_info_message(logger_context, f"Failed to drop off gripper {robotService.current_tool}: {message}")
            laser.turnOff()
            return NestingResult(success=False, message=f"Failed to drop off gripper {robotService.current_tool}: {message}")

    result = pickup_gripper(robotService, target_gripper_id, laser)
    if not result.success:
        return result

    result = robotService.tool_manager.verify_gripper_change(target_gripper_id)
    if not result:
        laser.turnOff()
        return NestingResult(success=False,
                             message=f"Gripper change verification failed. Expected: {target_gripper_id}, Current: {robotService.current_tool}")

    log_info_message(logger_context, f"Successfully switched to gripper: {target_gripper_id}")

    return NestingResult(success=True, message="Gripper changed successfully")


def finish_nesting(robotService, laser, workpiece_found: bool,
                   message_success: str, message_failure: str,
                   move_before_finish=False, application=None) -> NestingResult:
    """
    Handles ending the nesting operation based on whether workpieces were found before.

    Args:
        robotService: Robot service instance
        laser: Laser tool instance
        workpiece_found: True if some workpieces were processed before
        message_success: Message to return on successful nesting completion
        message_failure: Message to return if no workpieces were ever found
        move_before_finish: If True, move robot to capture position before finishing
        application: Application instance (required if move_before_finish is True)

    Returns:
        NestingResult with appropriate success flag and message
    """
    if workpiece_found:
        log_info_message(logger_context, "No more workpieces detected, completing nesting.")
        robotService.dropOffGripper(robotService.current_tool)
        if move_before_finish and application is not None:
            ret = application.move_to_nesting_capture_position()
            if ret != 0:
                laser.turnOff()
                return NestingResult(success=False, message="Failed to move to start position")
        laser.turnOff()
        return NestingResult(success=True, message=message_success)
    else:
        laser.turnOff()
        return NestingResult(success=False, message=message_failure)


def determine_pickup_point(match, cnt_obj):
    if match.pickupPoint is not None:
        centroid = match.pickupPoint
        log_info_message(logger_context, f"Using predefined pickup point: {centroid}")
    else:
        centroid = cnt_obj.getCentroid()
        log_info_message(logger_context, f"No predefined pickup point, using contour centroid: {centroid}")

def transform_centroids(visionService, centroid):
    transformed_centroid = utils.applyTransformation(visionService.cameraToRobotMatrix, [centroid])
    centroid_for_height_measure = utils.applyTransformation(visionService.cameraToRobotMatrix, [centroid],
                                                            apply_transducer_offset=False)
    flat_centroid = transformed_centroid
    while isinstance(flat_centroid, (list, tuple)) and len(flat_centroid) == 1:
        flat_centroid = flat_centroid[0]

    return centroid_for_height_measure, flat_centroid

def apply_offsets_based_on_gripper(gripper, drop_off_position1, drop_off_position2):
    if gripper == Gripper.DOUBLE:
        # rotate the offsets by -90 degrees and apply them
        orientation_radians = math.radians(-90)
        rotated_x, rotated_y = rotate_offsets(GRIPPER_X_OFFSET, GRIPPER_Y_OFFSET, orientation_radians)
        # handle pos 1
        drop_off_position1[0] += rotated_x
        drop_off_position1[1] += rotated_y

        # handle pos 2
        drop_off_position2[0] += rotated_x
        drop_off_position2[1] += rotated_y
    else:
        # apply standard gripper offsets
        # handle pos 2
        drop_off_position1[0] += GRIPPER_X_OFFSET
        drop_off_position1[1] += GRIPPER_Y_OFFSET

        # handle pos 2
        drop_off_position2[0] += GRIPPER_X_OFFSET
        drop_off_position2[1] += GRIPPER_Y_OFFSET

def start_nesting(application, visionService, robotService: RobotService, preselected_workpiece) -> NestingResult:
    log_info_message(logger_context, "🤖 Starting Nesting Operation")

    workpieces = preselected_workpiece

    plane = Plane() # Initialize empty plane for nesting
    count = 0 # Count of placed workpieces
    workpiece_found = False # Track if any workpiece was found in any iteration
    placed_contours = []  # Track placed contours for debug plotting
    max_retries = 10 # maximum number of retries for contour detection
    retry_delay = 1  # seconds between retries
    measurement_height = 350  # initial height for measurement
    laser = robotService.tool_manager.get_tool("laser") # get laser tool
    laserTrackingService = LaserTrackService() # initialize laser tracking service

    height_measure_context= HeightMeasureContext(
                robot_service=robotService,
                vision_service=visionService,
                laser_tracking_service=laserTrackingService,
                laser=laser
            )

    while True:
        success = move_to_nesting_capture_position(application,laser)
        if not success:
            return NestingResult(success=False, message="Failed to move to start position")

        success,newContours = get_contours_with_retries(visionService, logger_context, max_retries, retry_delay)

        if not success:
            # NO CONTOURS FOUND
            log_info_message(logger_context, "Max retries reached, no contours found.")
            return finish_nesting(
                robotService,
                laser,
                workpiece_found,
                message_success="Nesting complete, no more workpieces to pick",
                message_failure="No contours found after retries",
                move_before_finish=False,
                application=None
            )

        close_contours(newContours)

        log_info_message(logger_context,f"Image captured, processing contours...")

        newContours = filter_contours_in_pickup_area(visionService.getPickupAreaPoints(),newContours)
        if newContours is None:
            log_info_message(logger_context, "No pickup area defined, processing all contours")
        else:
            log_info_message(logger_context, f"Pickup area defined, filtering contours...")

        # Match workpieces with detected contours
        matches_data, noMatches = match_contours_to_workpieces(workpieces, newContours)
        if matches_data is None:
            log_info_message(logger_context,"Error during contour matching.")
            laser.turnOff()
            return NestingResult(success=False, message="Error during contour matching")

        orientations = matches_data["orientations"]
        matches = matches_data["workpieces"]

        if matches is not None and len(matches) > 0:
            workpiece_found = True
        else:
            return finish_nesting(
                robotService,
                laser,
                workpiece_found,
                message_success="Nesting complete, no more workpieces to pick",
                message_failure="No workpieces matched detected contours",
                move_before_finish=True,
                application=application
            )

        log_info_message(logger_context,f"Found {len(matches)} matching workpieces, processing each match...")

        if not matches:
            log_info_message(logger_context,"No matching workpieces found, ending nesting operation.")
            laser.turnOff()
            return NestingResult(success=False, message=Message.NO_WORKPIECE_DETECTED.value)

        log_info_message(logger_context,f"Processing {len(matches)} matched workpieces...")

        # Process each matched workpiece
        for match_i, match in enumerate(matches):
            success = move_to_nesting_capture_position(application, laser)
            if not success:
                return NestingResult(success=False, message="Failed to move to start position")

            contour = match.get_main_contour()
            cnt_obj = Contour(contour)
            match_height = 3
            gripper = match.gripperID
            centroid = determine_pickup_point(match, cnt_obj)


            # Apply homography transformation
            centroid_for_height_measure,flat_centroid = transform_centroids(visionService, centroid)
            log_match_details(logger_context,match_height,gripper,centroid,flat_centroid,orientations,match_i)
            # Calculate pickup and drop-off positions
            pickup_positions, height_measure_position, pickup_height = calculate_pickup_positions(flat_centroid,
                                                                                                  match_height,
                                                                                                  robotService,
                                                                                                  orientations[match_i],
                                                                                                  gripper,ENABLE_LOGGING,nesting_logger,
                                                                                                  GRIPPER_X_OFFSET,
                                                                                                  GRIPPER_Y_OFFSET,
                                                                                                  RZ_ORIENTATION,
                                                                                                  DOUBLE_GRIPPER_Z_OFFSET,
                                                                                                  SINGLE_GRIPPER_Z_OFFSET)

            drop_off_result = calculate_drop_off_position(match,
                                                          centroid,
                                                          orientations[match_i],
                                                          plane,
                                                          pickup_height,
                                                          gripper,
                                                          ENABLE_LOGGING,
                                                          nesting_logger,
                                                          RZ_ORIENTATION,
                                                          ROTATION_OFFSET_BETWEEN_PICKUP_AND_DROP_PLACE)


            log_info_message(logger_context, "Calculating drop-off position...")


            if drop_off_result[0] is None:  # Plane is full

                log_info_message(logger_context,"⚠️  PLANE FULL: Cannot place more workpieces")
                plane.isFull = True
                break

            drop_off_position1, drop_off_position2, width, height, plane, placed_contour = drop_off_result

            # apply gripper offsets to drop-off position
            apply_offsets_based_on_gripper(gripper, drop_off_position1, drop_off_position2)

            count += 1

            # Add placed contour to tracking list for debug plotting
            placed_contours.append({
                'contour': placed_contour,
                'drop_position': drop_off_position1,
                'dimensions': (width, height),
                'match_index': match_i + 1
            })

            log_drop_pos_calculated(logger_context,drop_off_position1,width,height)
            save_nesting_debug_plot(plane, placed_contours, match_i + 1)

            target_gripper_id = int(gripper.value)
            if robotService.current_tool != target_gripper_id:
               result = change_gripper_if_needed(robotService, target_gripper_id, laser)
               if not result.success:
                   return result
            else:
                log_info_message(logger_context,f"Gripper {target_gripper_id} already attached, no change needed")

            # Extract raw centroid coordinates
            cx = centroid_for_height_measure[0][0][0][0]
            cy = centroid_for_height_measure[0][0][0][1]

            # --- Rotate centroid by 90 degrees counterclockwise around origin ---
            rotated_cx = -cy
            rotated_cy = cx

            # Assign rotated coordinates to height measure position
            height_measure_position[0] = rotated_cx
            height_measure_position[1] = rotated_cy

            height_measure_position[2] = measurement_height  # set a safe height for measurement
            height_measure_position[5] = RZ_ORIENTATION


            result, measured_height, value_in_pixels = measure_height_at_position(height_measure_context,height_measure_position)

            if not result:
                laser.turnOff()
                return NestingResult(success=False, message="Failed to measure height.")

            measured_height = measured_height + 2  # temp add 2 mm

            log_info_message(logger_context,message=f"Measured workpiece height: result={result} {value_in_pixels} mm")

            # robotService.pump.turnOn(robotService.robot)
            # 3. Execute pick and place sequence
            ret = execute_pick_and_place_sequence(robotService, pickup_positions,
                                                  drop_off_position1,
                                                  drop_off_position2,
                                                  measured_height, gripper)
            if ret != 0:
                robotService.tool_manager.pump.turnOff(robotService.robot)
                laser.turnOff()
                return NestingResult(success=False, message="Failed during pick and place sequence")
