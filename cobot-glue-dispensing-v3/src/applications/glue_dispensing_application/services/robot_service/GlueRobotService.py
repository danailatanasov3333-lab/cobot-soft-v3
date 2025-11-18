"""
Decoupled RobotService implementation with cancellation token support
for robust pause/resume functionality and clean operation control.
No longer dependent on external state machines.
"""

from core.services.robot_service.RobotServiceSubscriptionManager import RobotServiceSubscriptionManager
from applications.glue_dispensing_application.services.robot_service.ToolManager import ToolManager

from modules.shared.tools.Laser import Laser
from modules.shared.tools.VacuumPump import VacuumPump

import threading
from modules.shared.tools.ToolChanger import ToolChanger
from core.services.robot_service.base_robot_service import BaseRobotService

class RobotService(BaseRobotService):
    """
    RobotService implementation with cancellation token support
    for decoupled pause/resume functionality and clean operation control.
    """
    
    RX_VALUE = 180
    RY_VALUE = 0
    RZ_VALUE = 0
    
    def __init__(self, robot, settingsService,robot_state_manager):
        """Initialize the robot service"""
        super().__init__(robot,settingsService,robot_state_manager)

        self.subscription_manager = RobotServiceSubscriptionManager(self,self.broker)
        self.state_manager.start_state_publisher_thread()
        self.subscription_manager.subscribe_robot_state_topic()
        self.subscription_manager.subscribe_glue_process_state_topic()
        self.state_topic = self.message_publisher.state_topic

        # Tools and peripherals
        self.pump = VacuumPump()
        self.laser = Laser()
        self.toolChanger = ToolChanger()
        self.tool_manager = ToolManager(self.toolChanger,self)
        # Thread safety

        self._stop_thread = threading.Event()

    @property
    def current_tool(self):
        return self.tool_manager.current_gripper

    def move_to_nesting_capture_position(self, z_offset=0):
        ret = self.moveToStartPosition(z_offset=z_offset)

        if ret != 0:
            return ret

        target_pose = self.robot_config.getHomePositionParsed()
        target_pose[2] += z_offset  # apply z_offset
        self._waitForRobotToReachPosition(target_pose, 1, 0.1)
        return  ret

    def move_to_spray_capture_position(self, z_offset=0):
        ret = self.moveToCalibrationPosition(z_offset=z_offset)

        if ret != 0:
            return ret

        target_pose = self.robot_config.getCalibrationPositionParsed()
        target_pose[2] += z_offset  # apply z_offset
        self._waitForRobotToReachPosition(target_pose, 1, 0.1)
        return ret
    # Movement methods
    def moveToCalibrationPosition(self,z_offset=0):
        """Move robot to calibration position"""
        try:
            position = self.robot_config.getCalibrationPositionParsed()
            # apply the z offset to account for the calibration pattern thickness
            position[2] += z_offset
            config = self.robot_config.getCalibrationPosConfig()
            
            ret = self.robot.moveCart(
                position=position,
                tool=self.robot_config.robot_tool,
                user=self.robot_config.robot_user,
                vel=config.velocity,
                acc=config.acceleration
            )

            self.message_publisher.publish_threshold_region_topic("spray")
            return ret
            
        except Exception as e:
            print(f"Error moving to calibration position: {e}")
            return -1

    def moveToLoginPosition(self):
        ret = None
        currentPos = self.get_current_position()
        x, y, z, rx, ry, rz = currentPos

        if y > 350:
            ret = self.moveToCalibrationPosition()
            if ret != 0:
                return ret

            ret = self.moveToStartPosition()
            if ret != 0:
                return ret
        else:
            ret = self.moveToStartPosition()
            if ret != 0:
                return ret

        position = self.robot_config.getLoginPositionParsed()  # This already handles None case
        loginPositionConfig = self.robot_config.getLoginPosConfig()
        velocity = loginPositionConfig.velocity
        acceleration = loginPositionConfig.acceleration
        ret = self.robot.moveCart(position=position,
                                  tool=self.robot_config.robot_tool,
                                  user=self.robot_config.robot_user,
                                  vel=velocity,
                                  acc=acceleration)
        return ret

    def moveToStartPosition(self,z_offset=0):
        """Move robot to start position"""
        try:
            position = self.robot_config.getHomePositionParsed()
            print(f"Position before z offset: {position}")
            # apply the z offset to account for the calibration pattern thickness
            position[2] += z_offset
            print(f"Position with z offset: {position}")
            config = self.robot_config.getHomePosConfig()
            
            ret = self.robot.moveCart(
                position=position,
                tool=self.robot_config.robot_tool,
                user=self.robot_config.robot_user,
                vel=config.velocity,
                acc=config.acceleration
            )
            
            print(f"Moving to start position, result: {ret}")
            self.message_publisher.publish_threshold_region_topic("pickup")
            return ret
            
        except Exception as e:
            print(f"Error moving to start position: {e}")
            return -1

    def pickupGripper(self, gripper_id, callback=None):
        """Delegate pickup to ToolManager"""
        success, message = self.tool_manager.pickup_gripper(gripper_id)
        if callback:
            callback(success, message)
        return success, message

    def dropOffGripper(self, gripper_id, callback=None):
        """Delegate dropoff to ToolManager"""
        success, message = self.tool_manager.drop_off_gripper(gripper_id)
        if callback:
            callback(success, message)
        return success, message

    def reload_config(self):
        self. robot_config = self.settings_service.reload_robot_config()

   


