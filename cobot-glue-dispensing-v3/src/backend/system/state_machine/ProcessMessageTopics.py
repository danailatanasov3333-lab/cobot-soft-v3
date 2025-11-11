"""
Process Message Topics

This module extends the existing topic structure defined in modules.shared.v1.topics
with process-specific topics for state machine communication and robot control.

This provides a standardized messaging interface that decouples components
and enables flexible, event-driven communication while integrating with the
existing topic hierarchy.
"""

from modules.shared.v1.topics import (
    SystemTopics, RobotTopics, VisionTopics, GlueTopics, 
    WorkpieceTopics, SettingsTopics, UITopics, TopicCategory
)
from typing import Dict, List


class ProcessControlTopics(TopicCategory):
    """
    Topics for process control across applications.
    
    These topics provide standardized process control that works
    across different robot applications, extending the existing topic structure.
    """
    
    # === GENERAL PROCESS CONTROL ===
    START_PROCESS = "process/control/start"          # Start process execution
    PAUSE_PROCESS = "process/control/pause"          # Pause process
    RESUME_PROCESS = "process/control/resume"        # Resume process
    STOP_PROCESS = "process/control/stop"            # Stop process
    RESET_PROCESS = "process/control/reset"          # Reset process to initial state
    
    # === PROCESS LIFECYCLE ===
    INITIALIZE = "process/control/initialize"        # Initialize process
    SHUTDOWN = "process/control/shutdown"            # Shutdown process
    CALIBRATE = "process/control/calibrate"          # Start calibration
    
    @staticmethod
    def get_app_specific_topic(base_topic: str, app_type: str) -> str:
        """
        Get an application-specific topic.
        
        Args:
            base_topic: Base topic name
            app_type: Application type ("glue", "paint", "pick_place")
            
        Returns:
            str: Application-specific topic
        """
        return f"process/{app_type}/control/{base_topic.split('/')[-1]}"


class ProcessStateTopics(TopicCategory):
    """
    Topics for process state updates.
    
    Process state machines publish their state changes to these topics
    so other components can react to process state changes.
    """
    
    # === GENERAL PROCESS STATE ===
    STATE_CHANGED = "process/state/changed"          # Process state changed
    STATE_HISTORY = "process/state/history"          # Process state transition history
    
    # === APPLICATION-SPECIFIC STATE TOPICS ===
    GLUE_STATE = "process/glue/state"               # Glue process state
    PAINT_STATE = "process/paint/state"             # Paint process state  
    PICK_PLACE_STATE = "process/pick_place/state"   # Pick-and-place process state
    
    # === PROCESS EVENTS ===
    PROCESS_STARTED = "process/events/started"       # Process started
    PROCESS_COMPLETED = "process/events/completed"   # Process completed
    PROCESS_FAILED = "process/events/failed"         # Process failed
    PROCESS_PAUSED = "process/events/paused"         # Process paused
    PROCESS_RESUMED = "process/events/resumed"       # Process resumed
    
    @staticmethod
    def get_app_state_topic(app_type: str) -> str:
        """
        Get the state topic for a specific application.
        
        Args:
            app_type: Application type ("glue", "paint", "pick_place")
            
        Returns:
            str: Application-specific state topic
        """
        return f"process/{app_type}/state"
    
    @staticmethod
    def get_app_event_topic(app_type: str, event: str) -> str:
        """
        Get an event topic for a specific application.
        
        Args:
            app_type: Application type ("glue", "paint", "pick_place")
            event: Event name
            
        Returns:
            str: Application-specific event topic
        """
        return f"process/{app_type}/events/{event}"


class RobotControlTopics(TopicCategory):
    """
    Topics for controlling robot operations.
    
    These topics extend the existing RobotTopics with specific control commands
    that allow process state machines to send control commands to robot services
    without direct coupling.
    """
    
    # === ROBOT CONTROL COMMANDS ===
    PAUSE = "robot/control/pause"                    # Pause all robot operations
    STOP = "robot/control/stop"                      # Stop all robot operations  
    RESUME = "robot/control/resume"                  # Resume paused operations
    EMERGENCY_STOP = "robot/control/emergency_stop"  # Emergency stop (immediate)
    RESET = "robot/control/reset"                    # Reset robot to initial state
    
    # === ROBOT MOVEMENT COMMANDS ===
    MOVE_TO_POSITION = "robot/control/move_to"       # Move to specific position
    MOVE_HOME = "robot/control/move_home"            # Move to home position
    JOG = "robot/control/jog"                        # Jog robot in direction
    
    # === ROBOT OPERATION COMMANDS ===
    START_PATH = "robot/control/start_path"          # Start path execution
    CANCEL_PATH = "robot/control/cancel_path"        # Cancel current path
    SET_SPEED = "robot/control/set_speed"            # Set robot speed
    SET_ACCELERATION = "robot/control/set_acceleration"  # Set acceleration


class RobotStatusTopics(TopicCategory):
    """
    Topics for robot status updates.
    
    These topics extend the existing RobotTopics with detailed status information
    that robot services can publish to inform other components about their state.
    """
    
    # === ROBOT STATE UPDATES (extends existing RobotTopics.ROBOT_STATUS) ===
    STATE = "robot/status/state"                     # Current robot state
    MOTION_STATE = "robot/status/motion"             # Motion status (moving, stopped)
    CONNECTION = "robot/status/connection"           # Connection status
    
    # === ROBOT OPERATION UPDATES ===
    PATH_PROGRESS = "robot/status/path_progress"     # Path execution progress
    PATH_COMPLETED = "robot/status/path_completed"   # Path execution completed
    TARGET_REACHED = "robot/status/target_reached"   # Target position reached
    
    # === ROBOT ERRORS ===
    ERROR = "robot/status/error"                     # Robot error occurred
    WARNING = "robot/status/warning"                 # Robot warning
    RECOVERY_STATUS = "robot/status/recovery"        # Error recovery status
    
    # === INTEGRATE WITH EXISTING TOPICS ===
    POSITION = RobotTopics.ROBOT_POSITION            # Use existing position topic
    STATUS = RobotTopics.ROBOT_STATUS                # Use existing status topic


class MessageFormats:
    """
    Standard message formats for different topic types.
    
    This ensures consistent message structure across the system.
    """
    
    @staticmethod
    def robot_control_message(command: str, parameters: Dict = None) -> Dict:
        """
        Create a robot control message.
        
        Args:
            command: The command to execute
            parameters: Optional command parameters
            
        Returns:
            Dict: Formatted message
        """
        return {
            "command": command,
            "parameters": parameters or {},
            "timestamp": None,  # Will be set by MessageBroker
        }
    
    @staticmethod
    def robot_status_message(status_type: str, data: Dict = None) -> Dict:
        """
        Create a robot status message.
        
        Args:
            status_type: Type of status update
            data: Status data
            
        Returns:
            Dict: Formatted message
        """
        return {
            "status_type": status_type,
            "data": data or {},
            "timestamp": None,  # Will be set by MessageBroker
        }
    
    @staticmethod
    def process_state_message(app_type: str, old_state: str, new_state: str, context: Dict = None) -> Dict:
        """
        Create a process state change message.
        
        Args:
            app_type: Application type
            old_state: Previous state
            new_state: New state
            context: Optional transition context
            
        Returns:
            Dict: Formatted message
        """
        return {
            "app_type": app_type,
            "old_state": old_state,
            "new_state": new_state,
            "context": context or {},
            "timestamp": None,  # Will be set by MessageBroker
        }
    
    @staticmethod
    def process_event_message(app_type: str, event: str, data: Dict = None) -> Dict:
        """
        Create a process event message.
        
        Args:
            app_type: Application type
            event: Event name
            data: Event data
            
        Returns:
            Dict: Formatted message
        """
        return {
            "app_type": app_type,
            "event": event,
            "data": data or {},
            "timestamp": None,  # Will be set by MessageBroker
        }


class TopicRegistry:
    """
    Registry of all available topics for easy reference and validation.
    """
    
    # All robot control topics
    ROBOT_CONTROL = [
        RobotControlTopics.PAUSE,
        RobotControlTopics.STOP,
        RobotControlTopics.RESUME,
        RobotControlTopics.EMERGENCY_STOP,
        RobotControlTopics.RESET,
        RobotControlTopics.MOVE_TO_POSITION,
        RobotControlTopics.MOVE_HOME,
        RobotControlTopics.JOG,
        RobotControlTopics.START_PATH,
        RobotControlTopics.CANCEL_PATH,
        RobotControlTopics.SET_SPEED,
        RobotControlTopics.SET_ACCELERATION,
    ]
    
    # All robot status topics
    ROBOT_STATUS = [
        RobotStatusTopics.STATE,
        RobotStatusTopics.POSITION,
        RobotStatusTopics.MOTION_STATE,
        RobotStatusTopics.CONNECTION,
        RobotStatusTopics.PATH_PROGRESS,
        RobotStatusTopics.PATH_COMPLETED,
        RobotStatusTopics.TARGET_REACHED,
        RobotStatusTopics.ERROR,
        RobotStatusTopics.WARNING,
        RobotStatusTopics.RECOVERY_STATUS,
    ]
    
    # All process control topics
    PROCESS_CONTROL = [
        ProcessControlTopics.START_PROCESS,
        ProcessControlTopics.PAUSE_PROCESS,
        ProcessControlTopics.RESUME_PROCESS,
        ProcessControlTopics.STOP_PROCESS,
        ProcessControlTopics.RESET_PROCESS,
        ProcessControlTopics.INITIALIZE,
        ProcessControlTopics.SHUTDOWN,
        ProcessControlTopics.CALIBRATE,
    ]
    
    # All process state topics
    PROCESS_STATE = [
        ProcessStateTopics.STATE_CHANGED,
        ProcessStateTopics.STATE_HISTORY,
        ProcessStateTopics.GLUE_STATE,
        ProcessStateTopics.PAINT_STATE,
        ProcessStateTopics.PICK_PLACE_STATE,
        ProcessStateTopics.PROCESS_STARTED,
        ProcessStateTopics.PROCESS_COMPLETED,
        ProcessStateTopics.PROCESS_FAILED,
        ProcessStateTopics.PROCESS_PAUSED,
        ProcessStateTopics.PROCESS_RESUMED,
    ]
    
    # All system topics
    SYSTEM = [
        SystemTopics.APPLICATION_STATE,
        SystemTopics.SYSTEM_HEALTH,
        # SystemTopics.SYSTEM_ALERTS,
        # SystemTopics.COMPONENT_READY,
        # SystemTopics.COMPONENT_ERROR,
        # SystemTopics.COMPONENT_SHUTDOWN,
        # SystemTopics.CALIBRATION_START,
        # SystemTopics.CALIBRATION_COMPLETE,
        # SystemTopics.CALIBRATION_FAILED,
    ]
    
    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Get all registered topics."""
        return (cls.ROBOT_CONTROL + cls.ROBOT_STATUS + 
                cls.PROCESS_CONTROL + cls.PROCESS_STATE + cls.SYSTEM)
    
    @classmethod
    def is_valid_topic(cls, topic: str) -> bool:
        """Check if a topic is valid/registered."""
        return topic in cls.get_all_topics()
    
    @classmethod
    def get_topics_by_category(cls, category: str) -> List[str]:
        """Get topics by category (robot_control, robot_status, process_control, process_state, system)."""
        category_map = {
            "robot_control": cls.ROBOT_CONTROL,
            "robot_status": cls.ROBOT_STATUS,
            "process_control": cls.PROCESS_CONTROL,
            "process_state": cls.PROCESS_STATE,
            "system": cls.SYSTEM,
        }
        return category_map.get(category, [])


# === CONVENIENCE FUNCTIONS ===

def get_robot_control_topic(command: str) -> str:
    """Get robot control topic for a command."""
    return f"robot/control/{command}"


def get_robot_status_topic(status_type: str) -> str:
    """Get robot status topic for a status type."""
    return f"robot/status/{status_type}"


def get_process_topic(app_type: str, topic_type: str) -> str:
    """Get process topic for an application and topic type."""
    return f"process/{app_type}/{topic_type}"


def get_system_topic(topic_type: str) -> str:
    """Get system topic for a topic type."""
    return f"system/{topic_type}"