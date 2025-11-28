"""
Clean entry point for nesting operations using the new layered architecture.
This module provides the main interface that replaces the old monolithic start_nesting function.
"""

from typing import List
from core.services.robot_service.impl.base_robot_service import RobotService
from .nesting_controller import NestingController
from .workflows import NestingResult


def start_nesting(application, vision_service, robot_service: RobotService, 
                 preselected_workpiece: List) -> NestingResult:
    """
    Start the nesting operation using the new layered architecture.
    
    This function provides a clean interface that replaces the old monolithic start_nesting
    function while maintaining the same signature for backward compatibility.
    
    Args:
        application: Application instance with movement methods
        vision_service: Vision service for image processing
        robot_service: Robot service for robot operations
        preselected_workpiece: List of workpiece templates to match against
        
    Returns:
        NestingResult with operation status and message
    """
    # Create controller and execute nesting
    controller = NestingController(application, vision_service, robot_service)
    return controller.start_nesting(preselected_workpiece)


# For backward compatibility, also export the old class if needed
class NestingResult:
    """Legacy NestingResult class for backward compatibility."""
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message