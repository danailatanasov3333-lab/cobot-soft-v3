"""
Decoupled RobotService Implementation

This module provides a refactored RobotService that is decoupled from 
application-specific state machines. Instead of directly accessing state 
machine states, it uses MessageBroker for communication and cancellation tokens
for operation control.

Key Changes:
- Removed direct state_machine dependency
- Added MessageBroker-based control
- Implemented cancellation token pattern
- Made robot service application-agnostic
"""

import threading
import time
from typing import Optional, List, Dict, Any, Callable

from modules.shared.MessageBroker import MessageBroker
from modules.shared.shared.settings.robotConfig.robotConfigModel import RobotConfig
from modules.robot.FairinoRobot import Axis, Direction
from modules.robot.RobotUtils import calculate_distance_between_points
from modules.robot.robotService.RobotServiceMessagePublisher import RobotServiceMessagePublisher
from modules.robot.robotService.RobotServiceStateManager import RobotServiceStateManager
from modules.robot.robotService.RobotServiceSubscriptionManager import RobotServiceSubscriptionManager
from modules.robot.robotService.RobotStateManager import RobotStateManager
from modules.robot.robotService.enums.RobotServiceState import RobotServiceState
from src.robot_application.glue_dispensing_application.tools.Laser import Laser
from src.robot_application.glue_dispensing_application.tools.ToolChanger import ToolChanger
from src.robot_application.glue_dispensing_application.tools.VacuumPump import VacuumPump
from src.backend.system.utils.custom_logging import setup_logger, LoggerContext, log_info_message, log_debug_message, log_error_message
from src.backend.system.state_machine.ProcessMessageTopics import RobotControlTopics, RobotStatusTopics


class CancellationToken:
    """
    Cancellation token for controlling robot operations.
    
    This provides a clean way to cancel robot operations without
    directly coupling to state machines.
    """
    
    def __init__(self):
        self._cancelled = threading.Event()
        self._reason = None
        self._timestamp = None
    
    def cancel(self, reason: str = "cancelled"):
        """Cancel the operation."""
        self._cancelled.set()
        self._reason = reason
        self._timestamp = time.time()
    
    def is_cancelled(self) -> bool:
        """Check if the operation has been cancelled."""
        return self._cancelled.is_set()
    
    def reset(self):
        """Reset the cancellation token."""
        self._cancelled.clear()
        self._reason = None
        self._timestamp = None
    
    def get_cancellation_reason(self) -> Optional[str]:
        """Get the reason for cancellation."""
        return self._reason
    
    def get_cancellation_timestamp(self) -> Optional[float]:
        """Get the timestamp when cancellation occurred."""
        return self._timestamp


class RobotOperationResult:
    """
    Result of a robot operation.
    
    This provides structured feedback about operation outcomes.
    """
    
    def __init__(self, success: bool, message: str = "", data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = time.time()
    
    def __bool__(self):
        return self.success
    
    def __str__(self):
        return f"RobotOperationResult(success={self.success}, message='{self.message}')"


class DecoupledRobotService:
    """
    Decoupled RobotService implementation that is independent of application-specific state machines.
    
    Key Features:
    - MessageBroker-based communication
    - Cancellation token pattern for operation control
    - Application-agnostic design
    - Event-driven architecture
    """
    
    RX_VALUE = 180
    RY_VALUE = 0
    RZ_VALUE = 0
    
    def __init__(self, robot, settingsService, broker: MessageBroker = None):
        """
        Initialize the decoupled robot service.
        
        Args:
            robot: The robot instance
            settingsService: Settings service
            broker: MessageBroker instance for communication
        """
        # Logging setup
        self.robot_service_logger_context = LoggerContext("DecoupledRobotService", setup_logger("DecoupledRobotService"))
        
        # Robot and settings (no state machine dependency!)
        self.robot = robot
        self.robot.printSdkVersion()
        self.settingsService = settingsService
        self.robot_config: RobotConfig = self.settingsService.robot_config
        
        # MessageBroker for decoupled communication
        self.broker = broker or MessageBroker()
        
        # Robot state monitoring
        self.robot_state_manager_cycle_time = 0.03  # 30ms cycle time
        self.robotStateManager = RobotStateManager(
            robot_ip=self.robot_config.robot_ip,
            cycle_time=self.robot_state_manager_cycle_time
        )
        self.robotStateManager.start_monitoring()
        
        # Message handling
        self.message_publisher = RobotServiceMessagePublisher(self.broker)
        self.state_manager = RobotServiceStateManager(
            RobotServiceState.INITIALIZING, 
            self.message_publisher, 
            self
        )
        self.subscription_manager = RobotServiceSubscriptionManager(self, self.broker)
        
        self.state_manager.start_state_publisher_thread()
        self.subscription_manager.subscribe_robot_state_topic()
        self.state_topic = self.message_publisher.state_topic
        
        # Tools and peripherals
        self.pump = VacuumPump()
        self.laser = Laser()
        self.toolChanger = ToolChanger()
        self.currentGripper = None
        
        # Thread safety
        self._operation_lock = threading.Lock()
        self._stop_thread = threading.Event()
        
        # Control state (replaces direct state machine access)
        self._is_paused = threading.Event()
        self._is_stopped = threading.Event()
        self._emergency_stop = threading.Event()
        self._cancellation_token = CancellationToken()
        
        # Operation tracking
        self._current_operation = None
        self._operation_start_time = None
        
        # Setup MessageBroker subscriptions
        self._setup_control_subscriptions()
        
        # Backward compatibility: add state_machine attribute for legacy code
        self.state_machine = None  # Will be set by application if needed
        
        log_info_message(
            self.robot_service_logger_context,
            "Decoupled RobotService initialized"
        )
    
    # === MESSAGE BROKER SETUP ===
    
    def _setup_control_subscriptions(self):
        """Set up MessageBroker subscriptions for robot control."""
        # Subscribe to robot control messages
        self.broker.subscribe(RobotControlTopics.PAUSE, self._handle_pause_command)
        self.broker.subscribe(RobotControlTopics.RESUME, self._handle_resume_command)
        self.broker.subscribe(RobotControlTopics.STOP, self._handle_stop_command)
        self.broker.subscribe(RobotControlTopics.EMERGENCY_STOP, self._handle_emergency_stop_command)
        self.broker.subscribe(RobotControlTopics.RESET, self._handle_reset_command)
        
        log_debug_message(
            self.robot_service_logger_context,
            "Robot control subscriptions established"
        )
    
    # === CONTROL MESSAGE HANDLERS ===
    
    def _handle_pause_command(self, message: Dict[str, Any]):
        """Handle pause command from MessageBroker."""
        log_info_message(
            self.robot_service_logger_context,
            "Received pause command"
        )
        self._is_paused.set()
        self._cancellation_token.cancel("paused")
        
        # Publish status update
        self._publish_robot_status("paused", {"reason": "external_command"})
    
    def _handle_resume_command(self, message: Dict[str, Any]):
        """Handle resume command from MessageBroker."""
        log_info_message(
            self.robot_service_logger_context,
            "Received resume command"
        )
        self._is_paused.clear()
        
        # Reset cancellation token if it was cancelled due to pause
        if self._cancellation_token.get_cancellation_reason() == "paused":
            self._cancellation_token.reset()
        
        # Publish status update
        self._publish_robot_status("resumed", {"reason": "external_command"})
    
    def _handle_stop_command(self, message: Dict[str, Any]):
        """Handle stop command from MessageBroker."""
        log_info_message(
            self.robot_service_logger_context,
            "Received stop command"
        )
        self._is_stopped.set()
        self._cancellation_token.cancel("stopped")
        
        # Stop robot motion
        self._stop_robot_motion()
        
        # Publish status update
        self._publish_robot_status("stopped", {"reason": "external_command"})
    
    def _handle_emergency_stop_command(self, message: Dict[str, Any]):
        """Handle emergency stop command from MessageBroker."""
        log_info_message(
            self.robot_service_logger_context,
            "Received EMERGENCY STOP command"
        )
        self._emergency_stop.set()
        self._is_stopped.set()
        self._cancellation_token.cancel("emergency_stop")
        
        # Immediately stop robot motion
        self._stop_robot_motion()
        
        # Publish status update
        self._publish_robot_status("emergency_stopped", {
            "reason": "emergency_command",
            "severity": "high"
        })
    
    def _handle_reset_command(self, message: Dict[str, Any]):
        """Handle reset command from MessageBroker."""
        log_info_message(
            self.robot_service_logger_context,
            "Received reset command"
        )
        
        # Reset all control flags
        self._is_paused.clear()
        self._is_stopped.clear()
        self._emergency_stop.clear()
        self._cancellation_token.reset()
        
        # Publish status update
        self._publish_robot_status("reset", {"reason": "external_command"})
    
    # === ROBOT CONTROL METHODS ===
    
    def _stop_robot_motion(self) -> RobotOperationResult:
        """Stop robot motion safely."""
        with self._operation_lock:
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    result = self.robot.stopMotion()
                    log_info_message(
                        self.robot_service_logger_context,
                        f"Robot motion stopped, result: {result}"
                    )
                    return RobotOperationResult(True, "Motion stopped successfully")
                except Exception as e:
                    if "Request-sent" in str(e) and attempt < max_attempts - 1:
                        time.sleep(0.1)  # Wait and retry
                        continue
                    else:
                        error_msg = f"Failed to stop robot motion: {e}"
                        log_error_message(self.robot_service_logger_context, error_msg)
                        return RobotOperationResult(False, error_msg)
            
            return RobotOperationResult(False, "Failed to stop robot motion after max attempts")
    
    def wait_for_robot_to_reach_position(self, 
                                        end_point: List[float], 
                                        threshold: float,
                                        delay: float = 0.01, 
                                        timeout: float = 30.0,
                                        cancellation_token: Optional[CancellationToken] = None) -> RobotOperationResult:
        """
        Wait for robot to reach target position with cancellation support.
        
        This method replaces the problematic _waitForRobotToReachPosition method
        by using cancellation tokens instead of direct state machine access.
        
        Args:
            end_point: Target position [x, y, z, rx, ry, rz]
            threshold: Distance threshold in mm
            delay: Polling delay in seconds
            timeout: Maximum wait time in seconds
            cancellation_token: Optional cancellation token for this operation
            
        Returns:
            RobotOperationResult: Result of the operation
        """
        start_time = time.time()
        effective_token = cancellation_token or self._cancellation_token
        
        log_info_message(
            self.robot_service_logger_context,
            f"Waiting for robot to reach position {end_point}, threshold={threshold}mm, timeout={timeout}s"
        )
        
        while True:
            # Check cancellation (replaces state machine checks)
            if effective_token.is_cancelled():
                reason = effective_token.get_cancellation_reason()
                log_debug_message(
                    self.robot_service_logger_context,
                    f"Operation cancelled: {reason}"
                )
                return RobotOperationResult(False, f"Operation cancelled: {reason}")
            
            # Check robot control flags
            if self._is_stopped.is_set():
                log_debug_message(
                    self.robot_service_logger_context,
                    "Robot is stopped, exiting wait loop"
                )
                return RobotOperationResult(False, "Robot is stopped")
            
            if self._is_paused.is_set():
                log_debug_message(
                    self.robot_service_logger_context,
                    "Robot is paused, waiting for resume..."
                )
                # Wait for resume or cancellation
                while self._is_paused.is_set() and not effective_token.is_cancelled():
                    time.sleep(0.1)
                continue
            
            # Check timeout
            if time.time() - start_time > timeout:
                error_msg = f"Timeout reached while waiting for robot position {end_point}"
                log_debug_message(self.robot_service_logger_context, error_msg)
                return RobotOperationResult(False, error_msg)
            
            # Check position
            current_position = self.getCurrentPosition()
            if current_position is None:
                time.sleep(delay)
                continue
            
            distance = calculate_distance_between_points(current_position, end_point)
            
            if distance < threshold:
                success_msg = f"Robot reached target position {end_point} within threshold {threshold}mm"
                log_debug_message(self.robot_service_logger_context, success_msg)
                return RobotOperationResult(True, success_msg, {
                    "final_position": current_position,
                    "final_distance": distance,
                    "time_taken": time.time() - start_time
                })
            
            time.sleep(delay)
    
    def move_to_nesting_capture_position(self, z_offset: float = 0) -> RobotOperationResult:
        """
        Move to nesting capture position with cancellation support.
        
        Args:
            z_offset: Z-axis offset in mm
            
        Returns:
            RobotOperationResult: Result of the operation
        """
        log_info_message(
            self.robot_service_logger_context,
            f"Moving to nesting capture position with z_offset={z_offset}"
        )
        
        # Create operation-specific cancellation token
        operation_token = CancellationToken()
        
        try:
            ret = self.moveToStartPosition(z_offset=z_offset)
            
            if ret != 0:
                return RobotOperationResult(False, f"Failed to move to start position, error code: {ret}")
            
            target_pose = self.robot_config.getHomePositionParsed()
            target_pose[2] += z_offset  # apply z_offset
            
            # Use the new decoupled wait method
            result = self.wait_for_robot_to_reach_position(
                target_pose, 
                threshold=1.0, 
                delay=0.1,
                cancellation_token=operation_token
            )
            
            if result.success:
                return RobotOperationResult(True, "Successfully moved to nesting capture position", {
                    "target_position": target_pose,
                    "z_offset": z_offset
                })
            else:
                return RobotOperationResult(False, f"Failed to reach nesting capture position: {result.message}")
                
        except Exception as e:
            error_msg = f"Error moving to nesting capture position: {e}"
            log_error_message(self.robot_service_logger_context, error_msg)
            return RobotOperationResult(False, error_msg)
    
    def move_to_spray_capture_position(self, z_offset: float = 0) -> RobotOperationResult:
        """
        Move to spray capture position with cancellation support.
        
        Args:
            z_offset: Z-axis offset in mm
            
        Returns:
            RobotOperationResult: Result of the operation
        """
        log_info_message(
            self.robot_service_logger_context,
            f"Moving to spray capture position with z_offset={z_offset}"
        )
        
        # Implementation similar to nesting capture position
        # This would contain the actual spray position logic
        try:
            # Placeholder implementation - replace with actual logic
            target_pose = self.robot_config.getSprayPositionParsed()  # Assuming this exists
            target_pose[2] += z_offset
            
            result = self.wait_for_robot_to_reach_position(
                target_pose,
                threshold=1.0,
                delay=0.1
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error moving to spray capture position: {e}"
            log_error_message(self.robot_service_logger_context, error_msg)
            return RobotOperationResult(False, error_msg)
    
    # === STATUS PUBLISHING ===
    
    def _publish_robot_status(self, status_type: str, data: Dict[str, Any] = None):
        """
        Publish robot status updates via MessageBroker.
        
        Args:
            status_type: Type of status update
            data: Additional status data
        """
        try:
            status_data = {
                "robot_id": self.robot_config.robot_ip,
                "timestamp": time.time(),
                "current_operation": self._current_operation,
                **(data or {})
            }
            
            # Publish to appropriate status topic
            topic_map = {
                "paused": RobotStatusTopics.STATE,
                "resumed": RobotStatusTopics.STATE,
                "stopped": RobotStatusTopics.STATE,
                "emergency_stopped": RobotStatusTopics.ERROR,
                "reset": RobotStatusTopics.STATE,
                "position_reached": RobotStatusTopics.TARGET_REACHED,
                "motion_started": RobotStatusTopics.MOTION_STATE,
                "motion_stopped": RobotStatusTopics.MOTION_STATE,
            }
            
            topic = topic_map.get(status_type, RobotStatusTopics.STATE)
            self.broker.publish(topic, status_data)
            
        except Exception as e:
            log_error_message(
                self.robot_service_logger_context,
                f"Error publishing robot status: {e}"
            )
    
    # === UTILITY METHODS ===
    
    def getCurrentPosition(self) -> Optional[List[float]]:
        """Get current robot position"""
        return self.robotStateManager.position
    
    def moveToStartPosition(self, z_offset: float = 0) -> int:
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
    
    def moveToCalibrationPosition(self, z_offset: float = 0) -> int:
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

    def moveToLoginPosition(self) -> int:
        ret = None
        currentPos = self.getCurrentPosition()
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

    def get_current_velocity(self):
        """Get current robot velocity"""
        return self.robotStateManager.velocity

    def get_current_acceleration(self):
        """Get current robot acceleration"""
        return self.robotStateManager.acceleration
    
    def enableRobot(self):
        """Enable robot motion"""
        self.robot.enable()
        print("Robot enabled")
    
    def disableRobot(self):
        """Disable robot motion"""
        self.robot.disable()
        print("Robot disabled")
    
    def stopRobot(self):
        """Stop robot motion"""
        return self.robot.stopMotion()

    def is_within_safety_limits(self, position):
        """Check if position is within safety limits"""
        safety_config = self.robot_config.safety_limits
        pos_x, pos_y, pos_z = position[0], position[1], position[2]
        
        if pos_z > safety_config.z_max:
            print(f"Position Z {pos_z} exceeds maximum limit of {safety_config.z_max}")
            return False
        
        if pos_z < safety_config.z_min:
            print(f"Position Z {pos_z} is below minimum limit of {safety_config.z_min}")
            return False
        
        return True

    def pickupGripper(self, gripperId, callBack=None):
        """Picks up a gripper from the tool changer."""
        # check if gripper is not already picked
        if self.currentGripper == gripperId:
            message = f"Gripper {gripperId} is already picked"
            print(message)
            return False, message

        slotId = self.toolChanger.getSlotIdByGrippedId(gripperId)
        self.toolChanger.setSlotAvailable(slotId)

        if gripperId == 0:
            config = self.robot_config.getSlot0PickupConfig()
            positions = self.robot_config.getSlot0PickupPointsParsed()
        elif gripperId == 1:
            config = self.robot_config.getSlot1PickupConfig()
            positions = self.robot_config.getSlot1PickupPointsParsed()
        elif gripperId == 4:
            config = self.robot_config.getSlot4PickupConfig()
            positions = self.robot_config.getSlot4PickupPointsParsed()
        else:
            raise ValueError("UNSUPPORTED GRIPPER ID: ", gripperId)

        try:
            for pos in positions:
                print("Moving to position: ", pos)
                self.robot.moveL(position=pos,
                                 tool=self.robot_config.robot_tool,
                                 user=self.robot_config.robot_tool,
                                 vel=config.velocity,
                                 acc=config.acceleration,
                                 blendR=1)
        except Exception as e:
            import traceback
            traceback.print_exc()

        self.moveToStartPosition()
        self.currentGripper = gripperId
        return True, None

    def dropOffGripper(self, gripperId, callBack=None):
        """Drops off the currently held gripper into a specified slot."""
        gripperId = int(gripperId)
        slotId = self.toolChanger.getSlotIdByGrippedId(gripperId)
        if self.toolChanger.isSlotOccupied(slotId):
            message = f"Slot {slotId} is taken"
            print(message)
            return False, message

        self.toolChanger.setSlotNotAvailable(slotId)

        if gripperId == 0:
            config = self.robot_config.getSlot0DropoffConfig()
            positions = self.robot_config.getSlot0DropoffPointsParsed()
        elif gripperId == 1:
            print("RobotService.dropOffGripper: Dropping off gripper 1")
            config = self.robot_config.getSlot1DropoffConfig()
            positions = self.robot_config.getSlot1DropoffPointsParsed()
        elif gripperId == 4:
            config = self.robot_config.getSlot4DropoffConfig()
            positions = self.robot_config.getSlot4DropoffPointsParsed()
        else:
            raise ValueError("UNSUPPORTED GRIPPER ID: ", gripperId)

        for pos in positions:
            ret = self.robot.moveL(position=pos,
                             tool=self.robot_config.robot_tool,
                             user=self.robot_config.robot_user,
                             vel=config.velocity,
                             acc=config.acceleration,
                             blendR=1)
            print("move before drop off: ", ret)

        self.currentGripper = None
        return True, None

    def startJog(self, axis, direction, step):
        step = float(step)
        # Set sign based on direction
        if direction == Direction.MINUS:
            temp_step = abs(step)
            print(f"Direction minus, step set to {temp_step}")
        else:
            temp_step = -abs(step)
            print(f"Direction plus, step set to {temp_step}")

        if axis == Axis.Z:
            currentPos = self.getCurrentPosition()
            proposedZ = currentPos[2] + temp_step
            print(f"RobotService: startJog: current Z: {currentPos[2]}, proposed Z: {proposedZ}")
            if proposedZ < self.robot_config.safety_limits.z_min:
                print(
                    f"Jog Z to {proposedZ}mm exceeds minimum limit of {self.robot_config.safety_limits.z_min}mm. Jog cancelled.")
                return -1
            if proposedZ > self.robot_config.safety_limits.z_max:
                print(
                    f"Jog Z to {proposedZ}mm exceeds maximum limit of {self.robot_config.safety_limits.z_max}mm. Jog cancelled.")
                return -1

        result = self.robot.startJog(axis=axis,
                                     direction=direction,
                                     step=step,
                                     vel=self.robot_config.getJogConfig().velocity,
                                     acc=self.robot_config.getJogConfig().acceleration)
        print(f"RobotService: startJog: result: {result}")
        return result

    def moveToPosition(self, position, tool, workpiece, velocity, acceleration, waitToReachPosition=False):
        """Moves the robot to a specified position with optional waiting."""
        # check if position is within safety limits
        result = self.is_within_safety_limits(position)
        if not result:
            return False

        ret = self.robot.moveCart(position, tool, workpiece, vel=velocity, acc=acceleration)

        if waitToReachPosition:  # TODO comment out when using test robot
            self.wait_for_robot_to_reach_position(position, 2, delay=0.1)

        return ret

    def loadConfig(self):
        try:
            self.robot_config = self.settingsService.load_robot_config()
            print("Robot Config reloaded in RobotService: ", self.robot_config)
            return True
        except:
            print("Failed to reload robot config in RobotService")
            return False
    
    def _waitForRobotToReachPosition(self, endPoint, threshold, delay, timeout=1):
        """Legacy method for backward compatibility"""
        result = self.wait_for_robot_to_reach_position(endPoint, threshold, delay, timeout)
        return result.success
    
    def stop(self):
        """Gracefully stop the service"""
        print("Stopping DecoupledRobotService...")
        self._stop_thread.set()
        if hasattr(self, 'robotStateManager'):
            self.robotStateManager.stop_monitoring()
        if hasattr(self, 'state_manager'):
            self.state_manager.stop_state_publisher_thread()
        print("DecoupledRobotService stopped")

    def __del__(self):
        """Cleanup when service is destroyed"""
        try:
            self.stop()
        except:
            pass
    
    def is_operational(self) -> bool:
        """Check if the robot service is operational."""
        return not (self._emergency_stop.is_set() or self._is_stopped.is_set())
    
    def is_paused(self) -> bool:
        """Check if the robot service is paused."""
        return self._is_paused.is_set()
    
    def get_cancellation_token(self) -> CancellationToken:
        """Get the current cancellation token."""
        return self._cancellation_token
    
    def create_operation_token(self) -> CancellationToken:
        """Create a new cancellation token for a specific operation."""
        return CancellationToken()
    
    # === CLEANUP ===
    
    def shutdown(self):
        """Shutdown the robot service and clean up resources."""
        log_info_message(
            self.robot_service_logger_context,
            "Shutting down DecoupledRobotService"
        )
        
        # Stop any ongoing operations
        self._cancellation_token.cancel("shutdown")
        self._is_stopped.set()
        
        # Stop robot motion
        self._stop_robot_motion()
        
        # Stop monitoring
        if hasattr(self.robotStateManager, 'stop_monitoring'):
            self.robotStateManager.stop_monitoring()
        
        # Stop state publisher
        if hasattr(self.state_manager, 'stop_state_publisher_thread'):
            self.state_manager.stop_state_publisher_thread()
    
    def __str__(self):
        return f"DecoupledRobotService(robot_ip={self.robot_config.robot_ip})"
    
    def __repr__(self):
        return (f"DecoupledRobotService(robot_ip={self.robot_config.robot_ip}, "
                f"operational={self.is_operational()}, paused={self.is_paused()})")


# === MIGRATION HELPER ===

class RobotServiceMigrationHelper:
    """
    Helper class to assist with migrating from coupled to decoupled RobotService.
    
    This can be used to gradually migrate existing code that depends on the
    old state machine coupling pattern.
    """
    
    @staticmethod
    def create_legacy_compatibility_wrapper(decoupled_service: DecoupledRobotService, 
                                           state_machine) -> 'LegacyCompatibilityWrapper':
        """
        Create a compatibility wrapper that maintains the old interface
        while using the new decoupled service underneath.
        
        Args:
            decoupled_service: The new decoupled robot service
            state_machine: The legacy state machine (for compatibility)
            
        Returns:
            LegacyCompatibilityWrapper: Wrapper that maintains old interface
        """
        return LegacyCompatibilityWrapper(decoupled_service, state_machine)


class LegacyCompatibilityWrapper:
    """
    Compatibility wrapper that maintains the old RobotService interface
    while using the new decoupled implementation underneath.
    
    This allows for gradual migration of existing code.
    """
    
    def __init__(self, decoupled_service: DecoupledRobotService, state_machine):
        self.decoupled_service = decoupled_service
        self.state_machine = state_machine  # Keep for compatibility
        
        # Delegate all attributes to the decoupled service
        for attr in ['robot', 'settingsService', 'robot_config', 'pump', 'laser', 'toolChanger']:
            if hasattr(decoupled_service, attr):
                setattr(self, attr, getattr(decoupled_service, attr))
    
    def _waitForRobotToReachPosition(self, endPoint, threshold, delay, timeout=1):
        """
        Legacy method that maintains the old interface.
        
        This method still exists for backward compatibility but now uses
        the decoupled implementation underneath.
        """
        result = self.decoupled_service.wait_for_robot_to_reach_position(
            endPoint, threshold, delay, timeout
        )
        
        # Return old-style boolean result for compatibility
        return result.success
    
    def __getattr__(self, name):
        """Delegate any other attribute access to the decoupled service."""
        return getattr(self.decoupled_service, name)