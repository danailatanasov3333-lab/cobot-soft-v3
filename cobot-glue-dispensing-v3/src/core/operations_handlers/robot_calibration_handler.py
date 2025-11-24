"""
Robot Calibration Handler

This handler manages robot calibration operations using the refactored
ExecutableStateMachine-based calibration pipeline for improved modularity,
maintainability, and consistency with other system components.

Updated to use:
- RefactoredRobotCalibrationPipeline (with ExecutableStateMachine)
- Better error handling and state monitoring
- Enhanced logging and debugging capabilities
"""

import threading
import time

from communication_layer.api.v1.topics import RobotTopics
from modules.robot_calibration.newRobotCalibUsingExecutableStateMachine import RefactoredRobotCalibrationPipeline

from modules.shared.MessageBroker import MessageBroker
from modules.robot_calibration.config_helpers import AdaptiveMovementConfig, RobotCalibrationEventsConfig, \
    RobotCalibrationConfig


def calibrate_robot(application):

        required_ids = [0,1,2,3,4,5,6,8]
        print(f"Robot Calibration: Using required IDs: {required_ids}")
        try:

            adaptive_movement_config = AdaptiveMovementConfig(
                min_step_mm=0.1, # minimum movement (for very small errors)
                max_step_mm=25.0,# maximum movement for very large misalignment's
                target_error_mm=0.25, # desired error to reach
                max_error_ref=100.0, # error at which we reach max step
                k=2.0, # responsiveness (1.0 = smooth, 2.0 = faster reaction)
                derivative_scaling=0.5 # how strongly derivative term reduces step
            )

            robot_events_config = RobotCalibrationEventsConfig(
                broker=MessageBroker(),
                calibration_start_topic=RobotTopics.ROBOT_CALIBRATION_START,
                calibration_log_topic=RobotTopics.ROBOT_CALIBRATION_LOG,
                calibration_image_topic=RobotTopics.ROBOT_CALIBRATION_IMAGE,
                calibration_stop_topic=RobotTopics.ROBOT_CALIBRATION_STOP,
            )

            config = RobotCalibrationConfig(
                vision_system=application.visionService,
                robot_service=application.robotService,
                required_ids=required_ids,
                z_target=300,# height for refined marker search
                debug=False,
                step_by_step=False,
                live_visualization=False
            )

            robot_calib_pipeline = RefactoredRobotCalibrationPipeline(config=config,
                                                                      events_config=robot_events_config,
                                                                      adaptive_movement_config=adaptive_movement_config)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Failed to initialize calibration pipeline: {e}", None

        application.visionService.drawContours = False
        
        # Create a thread wrapper that handles the ExecutableStateMachine properly
        def calibration_thread_worker():
            """Worker function for calibration thread with proper error handling"""
            try:
                print("=== Starting ExecutableStateMachine-based Robot Calibration ===")
                success = robot_calib_pipeline.run()
                
                if success:
                    print("✅ Robot calibration completed successfully!")
                    # Get final state and context for debugging
                    final_state = robot_calib_pipeline.get_state_machine().current_state
                    context = robot_calib_pipeline.get_context()
                    print(f"Final state: {final_state}")
                    print(f"Processed {len(context.robot_positions_for_calibration)} markers")
                else:
                    print("❌ Robot calibration failed!")
                    
            except Exception as e:
                print(f"❌ Robot calibration thread error: {e}")
                import traceback
                traceback.print_exc()
        
        # Start calibration in background thread
        print("About to start ExecutableStateMachine calibration thread...")
        calibration_thread = threading.Thread(target=calibration_thread_worker, daemon=False)
        print(f"Created thread: {calibration_thread}")
        calibration_thread.start()
        print(f"Thread started: {calibration_thread.is_alive()}")
        
        # Store reference for potential monitoring/cancellation
        robot_calib_pipeline._calibration_thread = calibration_thread
        
        message = "ExecutableStateMachine-based calibration started in background thread"
        image = None
        return True, message, image


def get_calibration_status(robot_calib_pipeline):
    """
    Get the current status of the robot calibration process.
    
    This function leverages the ExecutableStateMachine to provide
    real-time status information about the calibration progress.
    
    Args:
        robot_calib_pipeline: RefactoredRobotCalibrationPipeline instance
        
    Returns:
        dict: Status information including current state, progress, and timing
    """
    try:
        state_machine = robot_calib_pipeline.get_state_machine()
        context = robot_calib_pipeline.get_context()
        
        # Calculate progress
        total_markers = len(context.required_ids) if context.required_ids else 0
        current_marker = context.current_marker_id
        markers_completed = len(context.robot_positions_for_calibration)
        progress_percentage = (markers_completed / total_markers * 100) if total_markers > 0 else 0
        
        # Get timing information
        total_time = 0
        if context.total_calibration_start_time:
            total_time = time.time() - context.total_calibration_start_time
        
        status = {
            "current_state": state_machine.current_state.name if state_machine.current_state else "UNKNOWN",
            "is_running": not state_machine._stop_requested,
            "total_markers": total_markers,
            "current_marker_id": current_marker,
            "markers_completed": markers_completed,
            "progress_percentage": round(progress_percentage, 1),
            "total_time_seconds": round(total_time, 2),
            "state_timings": context.state_timings,
            "has_error": state_machine.current_state.name == "ERROR" if state_machine.current_state else False,
            "thread_alive": getattr(robot_calib_pipeline, '_calibration_thread', None) and 
                           robot_calib_pipeline._calibration_thread.is_alive(),
        }
        
        return status
        
    except Exception as e:
        return {
            "error": f"Failed to get calibration status: {e}",
            "current_state": "UNKNOWN",
            "is_running": False,
        }


def stop_calibration(robot_calib_pipeline):
    """
    Stop the robot calibration process.
    
    This function uses the ExecutableStateMachine's stop mechanism
    to gracefully terminate the calibration process.
    
    Args:
        robot_calib_pipeline: RefactoredRobotCalibrationPipeline instance
        
    Returns:
        bool: True if stop was initiated successfully
    """
    try:
        state_machine = robot_calib_pipeline.get_state_machine()
        state_machine.stop_execution()
        
        print("🛑 Robot calibration stop requested")
        return True
        
    except Exception as e:
        print(f"❌ Failed to stop calibration: {e}")
        return False
