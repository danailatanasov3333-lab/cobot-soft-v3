"""
Looking for ArUco Markers State Handler

Handles the state where the system is looking for all required ArUco markers
in the camera feed to proceed with calibration.
"""

import cv2
from modules.utils.custom_logging import log_debug_message
from modules.robot_calibration.states.robot_calibration_states import RobotCalibrationStates


def handle_looking_for_aruco_markers_state(context) -> RobotCalibrationStates:
    """
    Handle the LOOKING_FOR_ARUCO_MARKERS state.
    
    This state captures frames and looks for all required ArUco markers
    to proceed with the calibration process.
    
    Args:
        context: RobotCalibrationContext containing all calibration state
        
    Returns:
        Next state to transition to
    """
    # Flush camera buffer to get stable frame
    context.flush_camera_buffer()

    # Capture frame for ArUco detection
    all_aruco_detection_frame = None
    while all_aruco_detection_frame is None:
        log_debug_message(context.logger_context, "Capturing frame for ArUco detection...")
        all_aruco_detection_frame = context.system.getLatestFrame()

    # Show live feed if visualization is enabled
    if context.live_visualization:
        show_live_feed(context, all_aruco_detection_frame, 0, broadcast_image=context.broadcast_events)

    # Find required ArUco markers
    result = context.calibration_vision.find_required_aruco_markers(all_aruco_detection_frame)
    frame = result.frame
    all_found = result.found

    # Save debug image
    if context.debug:
        cv2.imwrite("new_development/NewCalibrationMethod/aruco_detection_frame.png", frame)

    if all_found:
        return RobotCalibrationStates.ALL_ARUCO_FOUND
    else:
        # Stay in current state if not all markers found
        return RobotCalibrationStates.LOOKING_FOR_ARUCO_MARKERS


def show_live_feed(context, frame, current_error_mm=None, window_name="Calibration Live Feed", draw_overlay=True, broadcast_image=False):
    """Show live camera feed with overlays"""
    
    if broadcast_image and context.broker and context.CALIBRATION_IMAGE_TOPIC:
        context.broker.publish(context.CALIBRATION_IMAGE_TOPIC, frame)

    if not context.live_visualization:
        return False

    # Apply overlays if enabled
    if draw_overlay:
        display_frame = draw_live_overlay(context, frame.copy(), current_error_mm)
    else:
        display_frame = frame.copy()
    
    # Show frame
    cv2.imshow(window_name, display_frame)

    # Check for exit key
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        log_debug_message(context.logger_context, "Live feed stopped by user (q pressed)")
        return True  # Signal to exit
    elif key == ord('s'):
        # Save current frame
        import time
        cv2.imwrite(f"live_capture_{time.time():.0f}.png", display_frame)
    elif key == ord('p'):
        # Pause/resume
        cv2.waitKey(0)

    return False  # Continue


def draw_live_overlay(context, frame, current_error_mm=None):
    """Draw comprehensive live visualization overlay"""
    if not context.live_visualization:
        return frame

    from modules.robot_calibration import visualizer

    # Get current state name
    state_name = context.get_current_state_name()

    # Draw image center (always visible)
    if hasattr(context, 'debug_draw') and context.debug_draw:
        context.debug_draw.draw_image_center(frame)

    # Draw progress bar
    progress = (context.current_marker_id / len(context.required_ids)) * 100 if context.required_ids else 0
    visualizer.draw_progress_bar(frame, progress)
    visualizer.draw_status_text(frame, state_name)

    # Current marker info
    if hasattr(context, 'current_marker_id') and context.required_ids:
        required_ids_list = sorted(list(context.required_ids))
        if context.current_marker_id < len(required_ids_list):
            current_marker = required_ids_list[context.current_marker_id]
            visualizer.draw_current_marker_info(frame, current_marker, context.current_marker_id, required_ids_list)

    # Iteration info (during iterative alignment)
    current_state = getattr(context.state_machine, 'current_state', None) if context.state_machine else None
    if current_state == RobotCalibrationStates.ITERATE_ALIGNMENT:
        visualizer.draw_iteration_info(frame, context.iteration_count, context.max_iterations)
        
        if current_error_mm is not None:
            visualizer.draw_current_error_mm(frame, current_error_mm, context.alignment_threshold_mm)

    visualizer.draw_progress_text(frame, progress)
    return frame