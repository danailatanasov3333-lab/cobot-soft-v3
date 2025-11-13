import threading

from modules.robot.calibration.config_helpers import AdaptiveMovementConfig, RobotCalibrationEventsConfig, \
    RobotCalibrationConfig
from modules.robot.calibration.newRobotCalibUsingTopLeftCornersOfArucoMarkers import RobotCalibrationPipeline
from modules.shared.MessageBroker import MessageBroker
from modules.shared.v1.topics import RobotTopics

def calibrate_robot(application):

        required_ids = [0,1, 2,3,4,5, 6,8]
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

            robot_calib_pipeline = RobotCalibrationPipeline(config=config,
                                                            events_config=robot_events_config,
                                                            adaptive_movement_config=adaptive_movement_config)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Failed to initialize calibration pipeline: {e}", None

        application.visionService.drawContours = False
        
        # Add debug print and ensure thread execution
        print("About to start calibration thread...")
        calibration_thread = threading.Thread(target=robot_calib_pipeline.run, daemon=False)  # Change to non-daemon
        print(f"Created thread: {calibration_thread}")
        calibration_thread.start()
        print(f"Thread started: {calibration_thread.is_alive()}")
        
        message = "Calibration started in background thread"
        image = None
        return True, message, image
