"""
Robot Factory

This module provides a factory for creating robot instances based on robot type.
The factory abstracts the creation logic and allows easy extension for new robot types.
Handles ROS2 initialization for robots that require it.
"""

import logging
import threading

from .robot_types import RobotType
from .IRobot import IRobot
from .fairino_robot import FairinoRobot
# ZeroErrRobot is imported lazily after ROS2 initialization to avoid import order issues

logger = logging.getLogger(__name__)

# ROS2 initialization state
_ros2_initialized = False
_ros2_lock = threading.Lock()


class RobotCreationError(Exception):
    """Raised when robot creation fails"""
    pass


class RobotFactory:
    """
    Factory for creating robot instances based on type.
    
    This factory provides a centralized way to create different robot implementations
    while maintaining a consistent interface. Handles ROS2 initialization for robots
    that require it (e.g., ZeroErrRobot).
    """

    @staticmethod
    def _ensure_ros2_initialized():
        """
        Ensure ROS2 is initialized. Only initializes once per process.
        Thread-safe. Handles case where ROS2 might already be initialized.
        """
        global _ros2_initialized

        with _ros2_lock:
            if not _ros2_initialized:
                try:
                    import rclpy
                    # Check if context is already initialized
                    try:
                        if not rclpy.ok():
                            rclpy.init()
                            logger.info("ROS2 initialized successfully")
                        else:
                            logger.info("ROS2 already initialized")
                    except RuntimeError as e:
                        # If we get "must only be called once", it's already initialized
                        if "must only be called once" in str(e):
                            logger.info("ROS2 already initialized (caught RuntimeError)")
                        else:
                            raise
                    _ros2_initialized = True
                except ImportError:
                    logger.warning("rclpy not available - ROS2 robots will not work")
                    raise RobotCreationError("rclpy not installed - cannot create ROS2 robots")
                except Exception as e:
                    logger.error(f"Failed to initialize ROS2: {e}")
                    raise RobotCreationError(f"ROS2 initialization failed: {e}")

    @staticmethod
    def _start_ros2_spinning(robot, robot_type: RobotType):
        """
        Start ROS2 node spinning in a background thread for ROS2-based robots.

        Args:
            robot: Robot instance to spin
            robot_type: Type of robot
        """
        # Only spin for robots that are ROS2 nodes
        if hasattr(robot, 'subscriptions'):
            def spin_ros2():
                try:
                    import rclpy
                    rclpy.spin(robot)
                except Exception as e:
                    logger.error(f"ROS2 spin error for {robot_type.value}: {e}")

            ros2_thread = threading.Thread(target=spin_ros2, daemon=True)
            ros2_thread.start()
            logger.info(f"ROS2 node spinning in background thread for {robot_type.value}")

    @staticmethod
    def _requires_ros2(robot_type: RobotType) -> bool:
        """
        Check if a robot type requires ROS2.

        Args:
            robot_type: Type of robot to check

        Returns:
            True if robot requires ROS2, False otherwise
        """
        return robot_type == RobotType.ZERO_ERROR

    @staticmethod
    def create_robot(robot_type: RobotType, ip: str, **kwargs) -> IRobot:
        """
        Create a robot instance based on the specified type.
        Handles ROS2 initialization for robots that require it.

        Args:
            robot_type: Type of robot to create
            ip: IP address of the robot controller
            **kwargs: Additional arguments for robot initialization
            
        Returns:
            IRobot: Instance of the requested robot type
            
        Raises:
            RobotCreationError: If robot creation fails
        """
        try:
            logger.info(f"Creating robot of type: {robot_type.value} with IP: {ip}")
            
            # Initialize ROS2 if needed for this robot type
            if RobotFactory._requires_ros2(robot_type):
                RobotFactory._ensure_ros2_initialized()

            # Create robot instance
            robot = None
            if robot_type == RobotType.FAIRINO:
                robot = FairinoRobot(ip, **kwargs)

            elif robot_type == RobotType.ZERO_ERROR:
                # Import ZeroErrRobot only after ROS2 is initialized
                from .ZeroErrRobot import ZeroErrRobot
                robot = ZeroErrRobot(ip, **kwargs)

            elif robot_type == RobotType.TEST:
                # Import here to avoid circular dependencies
                from . import TestRobotWrapper
                robot = TestRobotWrapper(**kwargs)

            else:
                raise RobotCreationError(
                    f"Unsupported robot type: {robot_type.value}. "
                    f"Available types: {[t.value for t in RobotType]}"
                )

            # Start ROS2 spinning if this is a ROS2 robot
            if RobotFactory._requires_ros2(robot_type):
                RobotFactory._start_ros2_spinning(robot, robot_type)

            return robot

        except RobotCreationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create robot {robot_type.value}: {e}")
            raise RobotCreationError(f"Failed to create {robot_type.value} robot: {e}") from e
    
    @staticmethod
    def get_supported_types() -> list[RobotType]:
        """
        Get list of supported robot types.
        
        Returns:
            List of supported RobotType enum values
        """
        return list(RobotType)
    
    @staticmethod
    def is_supported(robot_type: RobotType) -> bool:
        """
        Check if a robot type is supported by this factory.
        
        Args:
            robot_type: Robot type to check
            
        Returns:
            True if supported, False otherwise
        """
        return robot_type in RobotType

    @staticmethod
    def shutdown_ros2():
        """
        Shutdown ROS2 if it was initialized.
        Should be called on application shutdown.
        """
        global _ros2_initialized

        with _ros2_lock:
            if _ros2_initialized:
                try:
                    import rclpy
                    logger.info("Shutting down ROS2...")
                    rclpy.shutdown()
                    _ros2_initialized = False
                    logger.info("ROS2 shutdown complete")
                except Exception as e:
                    logger.error(f"Error during ROS2 shutdown: {e}")


# Convenience function for direct use
def create_robot(robot_type: RobotType, ip: str, **kwargs) -> IRobot:
    """
    Convenience function to create a robot instance.
    
    Args:
        robot_type: Type of robot to create
        ip: IP address of the robot controller
        **kwargs: Additional arguments for robot initialization
        
    Returns:
        IRobot: Instance of the requested robot type
    """
    return RobotFactory.create_robot(robot_type, ip, **kwargs)