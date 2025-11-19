from applications.glue_dispensing_application.services.robot_service.glue_robot_service import GlueRobotService
from core.controllers.robot.base_robot_controller import BaseRobotController


class GlueRobotController(BaseRobotController):
    """
    RobotController handles high-level robot actions based on API-style or legacy requests.

    It interprets actions like jogging, calibration, homing, moving to positions, and resetting errors,
    delegating the actual execution to GlueRobotService.
    """

    def __init__(self, robot_service: GlueRobotService):
        self.robot_service = robot_service
        self._dynamic_handler_resolver = self._resolve_dynamic_handler
        super().__init__(robot_service=self.robot_service)
        self._initialize_handlers()

