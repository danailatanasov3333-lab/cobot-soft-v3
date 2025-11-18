class AdaptiveMovementConfig:
    def __init__(self,min_step_mm,max_step_mm,target_error_mm,max_error_ref,k,derivative_scaling):

        self.min_step_mm = min_step_mm # minimum movement (for very small errors)
        self.max_step_mm = max_step_mm # maximum movement for very large misalignment's
        self.target_error_mm = target_error_mm # desired error to reach
        self.max_error_ref = max_error_ref # error at which we reach max step
        self.k = k # responsiveness (1.0 = smooth, 2.0 = faster reaction)
        self.derivative_scaling = derivative_scaling # how strongly derivative term reduces step

        # # New: define mapping from image axes to robot axes
        # # Example: {'robot_x': ('image_y', 1), 'robot_y': ('image_x', -1)}
        # # Meaning: robot_x comes from image_y with positive direction, robot_y comes from image_x inverted
        # self.image_to_robot_axis = image_to_robot_axis or {
        #     'robot_x': ('image_x', 1),
        #     'robot_y': ('image_y', 1)
        # }

class RobotCalibrationEventsConfig:
    def __init__(self,broker,
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
    def __init__(self,vision_system,robot_service,
                     required_ids,
                    z_target,
                     debug=False,
                     step_by_step=False,
                     live_visualization=False):
        self.vision_system = vision_system
        self.robot_service = robot_service
        self.required_ids = required_ids
        self.z_target=z_target
        self.debug = debug
        self.step_by_step = step_by_step
        self.live_visualization = live_visualization