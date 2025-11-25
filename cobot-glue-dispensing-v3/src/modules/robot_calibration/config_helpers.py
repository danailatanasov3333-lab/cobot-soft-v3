class AdaptiveMovementConfig:
    def __init__(self, min_step_mm, max_step_mm, target_error_mm, max_error_ref, k, derivative_scaling):
        self.min_step_mm = min_step_mm  # minimum movement (for very small errors)
        self.max_step_mm = max_step_mm  # maximum movement for very large misalignment's
        self.target_error_mm = target_error_mm  # desired error to reach
        self.max_error_ref = max_error_ref  # error at which we reach max step
        self.k = k  # responsiveness (1.0 = smooth, 2.0 = faster reaction)
        self.derivative_scaling = derivative_scaling  # how strongly derivative term reduces step


class RobotCalibrationEventsConfig:
    def __init__(self, broker,
                 calibration_start_topic,
                 calibration_stop_topic,
                 calibration_image_topic,
                 calibration_log_topic):
        self.broker = broker
        self.calibration_start_topic = calibration_start_topic
        self.calibration_stop_topic = calibration_stop_topic
        self.calibration_image_topic = calibration_image_topic
        self.calibration_log_topic = calibration_log_topic


class RobotCalibrationConfig:
    def __init__(self, vision_system,
                 robot_service,
                 required_ids,
                 z_target,
                 axis_mapping_marker_id=4,
                 axis_mapping_move_mm=100.0,
                 axis_mapping_max_attempts=100,
                 axis_mapping_delay=1.0,
                 debug=False,
                 step_by_step=False,
                 live_visualization=False):
        self.vision_system = vision_system
        self.robot_service = robot_service
        self.required_ids = required_ids
        self.z_target = z_target
        self.axis_mapping_marker_id = axis_mapping_marker_id
        self.axis_mapping_move_mm = axis_mapping_move_mm
        self.axis_mapping_max_attempts = axis_mapping_max_attempts
        self.axis_mapping_delay = axis_mapping_delay
        self.debug = debug
        self.step_by_step = step_by_step
        self.live_visualization = live_visualization
