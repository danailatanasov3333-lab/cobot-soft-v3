"""
Robot Monitor Factory

This module provides a factory for creating robot monitor instances based on robot type.
The factory abstracts the creation logic and allows easy extension for new robot monitor types.
"""

from typing import Optional
import logging

from core.model.robot.robot_types import RobotType
from core.services.robot_service.interfaces.IRobotMonitor import IRobotMonitor
from .fairino_monitor import FairinoRobotMonitor
from .zero_error_monitor import ZeroErrorRobotMonitor

logger = logging.getLogger(__name__)


class RobotMonitorCreationError(Exception):
    """Raised when robot monitor creation fails"""
    pass


class RobotMonitorFactory:
    """
    Factory for creating robot monitor instances based on robot type.
    
    This factory provides a centralized way to create different robot monitor implementations
    while maintaining a consistent interface.
    """
    
    @staticmethod
    def create_monitor(robot_type: RobotType, robot_ip: str, cycle_time: float = 0.03, **kwargs) -> IRobotMonitor:
        """
        Create a robot monitor instance based on the specified robot type.
        
        Args:
            robot_type: Type of robot to monitor
            robot_ip: IP address of the robot controller
            cycle_time: Monitoring cycle time in seconds (default: 0.03)
            **kwargs: Additional arguments for monitor initialization
            
        Returns:
            IRobotMonitor: Instance of the requested robot monitor type
            
        Raises:
            RobotMonitorCreationError: If monitor creation fails
        """
        try:
            logger.info(f"Creating robot monitor for type: {robot_type.value} with IP: {robot_ip}")
            
            if robot_type == RobotType.FAIRINO:
                return FairinoRobotMonitor(robot_ip, cycle_time, **kwargs)
            
            elif robot_type == RobotType.ZERO_ERROR:
                return ZeroErrorRobotMonitor(robot_ip, cycle_time, **kwargs)
            
            elif robot_type == RobotType.TEST:
                # For test robots, we can create a mock monitor or return a basic one
                # For now, we'll use the Fairino monitor as a fallback
                logger.warning(f"Using Fairino monitor for test robot type")
                return FairinoRobotMonitor(robot_ip, cycle_time, **kwargs)
            
            else:
                raise RobotMonitorCreationError(
                    f"Unsupported robot type for monitoring: {robot_type.value}. "
                    f"Available types: {[t.value for t in RobotType]}"
                )
                
        except Exception as e:
            logger.error(f"Failed to create robot monitor for {robot_type.value}: {e}")
            raise RobotMonitorCreationError(f"Failed to create {robot_type.value} robot monitor: {e}") from e
    
    @staticmethod
    def get_supported_types() -> list[RobotType]:
        """
        Get list of supported robot types for monitoring.
        
        Returns:
            List of supported RobotType enum values
        """
        return list(RobotType)
    
    @staticmethod
    def is_supported(robot_type: RobotType) -> bool:
        """
        Check if a robot type is supported for monitoring.
        
        Args:
            robot_type: Robot type to check
            
        Returns:
            True if supported, False otherwise
        """
        return robot_type in RobotType


# Convenience function for direct use
def create_robot_monitor(robot_type: RobotType, robot_ip: str, cycle_time: float = 0.03, **kwargs) -> IRobotMonitor:
    """
    Convenience function to create a robot monitor instance.
    
    Args:
        robot_type: Type of robot to monitor
        robot_ip: IP address of the robot controller
        cycle_time: Monitoring cycle time in seconds
        **kwargs: Additional arguments for monitor initialization
        
    Returns:
        IRobotMonitor: Instance of the requested robot monitor type
    """
    return RobotMonitorFactory.create_monitor(robot_type, robot_ip, cycle_time, **kwargs)