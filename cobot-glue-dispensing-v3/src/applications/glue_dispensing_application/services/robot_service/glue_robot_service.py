"""
Decoupled RobotService implementation with cancellation token support
for robust pause/resume functionality and clean operation control.
No longer dependent on external state machines.
"""
from applications.glue_dispensing_application.services.robot_service.glue_robot_service_state_manager import \
    GlueRobotServiceStateManager
from applications.glue_dispensing_application.services.robot_service.glue_robot_service_subscription_manager import \
    GlueRobotServiceSubscriptionManager
from core.model.robot.fairino_robot import FairinoRobot
from core.services.robot_service.enums.RobotServiceState import RobotServiceState
from core.services.robot_service.impl.RobotStateManager import RobotStateManager
from modules.shared.tools.Laser import Laser
from modules.shared.tools.VacuumPump import VacuumPump
import threading
from core.services.robot_service.impl.base_robot_service import BaseRobotService

class GlueRobotService(BaseRobotService):
    """
    RobotService implementation with cancellation token support
    for decoupled pause/resume functionality and clean operation control.
    """
    
    RX_VALUE = 180
    RY_VALUE = 0
    RZ_VALUE = 0
    
    def __init__(self, robot:FairinoRobot, settingsService,robot_state_manager:RobotStateManager):
        """Initialize the robot service"""
        super().__init__(robot,settingsService,robot_state_manager)

        self.subscription_manager = GlueRobotServiceSubscriptionManager(self,self.broker)
        self.state_manager.start_state_publisher_thread()
        self.subscription_manager.subscribe_robot_state_topic()
        self.subscription_manager.subscribe_glue_process_state_topic()
        self.state_topic = self.message_publisher.state_topic
        self.state_manager = GlueRobotServiceStateManager(RobotServiceState.INITIALIZING, self.message_publisher, self)
        # Tools and peripherals
        self.pump = VacuumPump()
        self.laser = Laser()

        # Thread safety
        self._stop_thread = threading.Event()

    def move_to_nesting_capture_position(self, z_offset=0):
        ret = self.moveToStartPosition(z_offset=z_offset)

        if ret != 0:
            return ret

        target_pose = self.robot_config.getHomePositionParsed()
        target_pose[2] += z_offset  # apply z_offset
        self._waitForRobotToReachPosition(target_pose, 1, 0.1)
        return  ret

    def move_to_spray_capture_position(self, z_offset=0):
        ret = self.move_to_calibration_position(z_offset=z_offset)

        if ret != 0:
            return ret

        target_pose = self.robot_config.getCalibrationPositionParsed()
        target_pose[2] += z_offset  # apply z_offset
        self._waitForRobotToReachPosition(target_pose, 1, 0.1)
        return ret




