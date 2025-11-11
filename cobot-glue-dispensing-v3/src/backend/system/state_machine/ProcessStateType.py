"""
Process State Types

This module defines the common state categories that all robot application
processes share. These provide a standard vocabulary for process states
across different applications (glue dispensing, painting, pick-and-place, etc.).
"""

from enum import Enum, auto
from typing import Dict, Set


class ProcessStateCategory(Enum):
    """
    High-level categories that all process states belong to.
    
    These categories help organize states and provide common patterns
    across different applications.
    """
    LIFECYCLE = "lifecycle"          # Initialization, shutdown states
    PREPARATION = "preparation"      # Setup, calibration, configuration states  
    EXECUTION = "execution"         # Active processing states
    CONTROL = "control"             # Pause, resume, stop states
    COMPLETION = "completion"       # Success, cleanup, finalization states
    ERROR = "error"                 # Error and recovery states


class ProcessStateType(Enum):
    """
    Common process state types that apply across all robot applications.
    
    These are the fundamental states that every application process should support.
    Application-specific states should inherit from or map to these base types.
    """
    
    # === LIFECYCLE STATES ===
    INITIALIZING = auto()           # Starting up, loading configuration
    READY = auto()                  # Initialized and ready for operations
    SHUTTING_DOWN = auto()          # Graceful shutdown in progress
    
    # === PREPARATION STATES ===
    PREPARING = auto()              # General preparation phase
    CALIBRATING = auto()            # Calibration in progress
    CONFIGURING = auto()            # Configuration setup
    LOADING = auto()                # Loading data, workpieces, etc.
    VALIDATING = auto()             # Validation checks
    
    # === EXECUTION STATES ===
    EXECUTING = auto()              # Active execution/processing
    PROCESSING = auto()             # Data/workpiece processing
    MOVING = auto()                 # Robot movement operations
    WAITING = auto()                # Waiting for external events
    
    # === CONTROL STATES ===
    IDLE = auto()                   # Idle, waiting for commands
    STARTING = auto()               # Starting an operation
    PAUSED = auto()                 # Temporarily paused
    RESUMING = auto()               # Resuming from pause
    STOPPING = auto()               # Stopping operation
    STOPPED = auto()                # Completely stopped
    
    # === COMPLETION STATES ===
    COMPLETING = auto()             # Finishing up operations
    COMPLETED = auto()              # Successfully completed
    FINALIZING = auto()             # Final cleanup operations
    
    # === ERROR STATES ===
    ERROR = auto()                  # General error state
    RECOVERING = auto()             # Attempting error recovery
    FAILED = auto()                 # Unrecoverable failure


class ProcessStateMetadata:
    """
    Metadata about process states including categories, descriptions, and properties.
    """
    
    # State category mapping
    STATE_CATEGORIES: Dict[ProcessStateType, ProcessStateCategory] = {
        # Lifecycle
        ProcessStateType.INITIALIZING: ProcessStateCategory.LIFECYCLE,
        ProcessStateType.READY: ProcessStateCategory.LIFECYCLE,
        ProcessStateType.SHUTTING_DOWN: ProcessStateCategory.LIFECYCLE,
        
        # Preparation
        ProcessStateType.PREPARING: ProcessStateCategory.PREPARATION,
        ProcessStateType.CALIBRATING: ProcessStateCategory.PREPARATION,
        ProcessStateType.CONFIGURING: ProcessStateCategory.PREPARATION,
        ProcessStateType.LOADING: ProcessStateCategory.PREPARATION,
        ProcessStateType.VALIDATING: ProcessStateCategory.PREPARATION,
        
        # Execution
        ProcessStateType.EXECUTING: ProcessStateCategory.EXECUTION,
        ProcessStateType.PROCESSING: ProcessStateCategory.EXECUTION,
        ProcessStateType.MOVING: ProcessStateCategory.EXECUTION,
        ProcessStateType.WAITING: ProcessStateCategory.EXECUTION,
        
        # Control
        ProcessStateType.IDLE: ProcessStateCategory.CONTROL,
        ProcessStateType.STARTING: ProcessStateCategory.CONTROL,
        ProcessStateType.PAUSED: ProcessStateCategory.CONTROL,
        ProcessStateType.RESUMING: ProcessStateCategory.CONTROL,
        ProcessStateType.STOPPING: ProcessStateCategory.CONTROL,
        ProcessStateType.STOPPED: ProcessStateCategory.CONTROL,
        
        # Completion
        ProcessStateType.COMPLETING: ProcessStateCategory.COMPLETION,
        ProcessStateType.COMPLETED: ProcessStateCategory.COMPLETION,
        ProcessStateType.FINALIZING: ProcessStateCategory.COMPLETION,
        
        # Error
        ProcessStateType.ERROR: ProcessStateCategory.ERROR,
        ProcessStateType.RECOVERING: ProcessStateCategory.ERROR,
        ProcessStateType.FAILED: ProcessStateCategory.ERROR,
    }
    
    # State descriptions
    STATE_DESCRIPTIONS: Dict[ProcessStateType, str] = {
        # Lifecycle
        ProcessStateType.INITIALIZING: "System is starting up and initializing",
        ProcessStateType.READY: "System is initialized and ready for operations",
        ProcessStateType.SHUTTING_DOWN: "System is shutting down gracefully",
        
        # Preparation
        ProcessStateType.PREPARING: "Preparing for operation execution",
        ProcessStateType.CALIBRATING: "Performing calibration procedures", 
        ProcessStateType.CONFIGURING: "Setting up configuration parameters",
        ProcessStateType.LOADING: "Loading data, workpieces, or resources",
        ProcessStateType.VALIDATING: "Validating setup and prerequisites",
        
        # Execution
        ProcessStateType.EXECUTING: "Actively executing the main operation",
        ProcessStateType.PROCESSING: "Processing data or workpieces",
        ProcessStateType.MOVING: "Robot movement operations in progress",
        ProcessStateType.WAITING: "Waiting for external events or conditions",
        
        # Control
        ProcessStateType.IDLE: "Idle, waiting for commands or operations",
        ProcessStateType.STARTING: "Starting a new operation",
        ProcessStateType.PAUSED: "Operation temporarily paused",
        ProcessStateType.RESUMING: "Resuming from a paused state",
        ProcessStateType.STOPPING: "Stopping current operation",
        ProcessStateType.STOPPED: "Operation has been stopped",
        
        # Completion
        ProcessStateType.COMPLETING: "Finishing up current operations",
        ProcessStateType.COMPLETED: "Operation completed successfully",
        ProcessStateType.FINALIZING: "Performing final cleanup operations",
        
        # Error
        ProcessStateType.ERROR: "An error has occurred",
        ProcessStateType.RECOVERING: "Attempting to recover from error",
        ProcessStateType.FAILED: "Unrecoverable failure has occurred",
    }
    
    # States that can be interrupted (e.g., by pause/stop commands)
    INTERRUPTIBLE_STATES: Set[ProcessStateType] = {
        ProcessStateType.PREPARING,
        ProcessStateType.CALIBRATING,
        ProcessStateType.CONFIGURING,
        ProcessStateType.LOADING,
        ProcessStateType.VALIDATING,
        ProcessStateType.EXECUTING,
        ProcessStateType.PROCESSING,
        ProcessStateType.MOVING,
        ProcessStateType.STARTING,
        ProcessStateType.COMPLETING,
        ProcessStateType.FINALIZING,
    }
    
    # States that represent active operations
    ACTIVE_STATES: Set[ProcessStateType] = {
        ProcessStateType.INITIALIZING,
        ProcessStateType.PREPARING,
        ProcessStateType.CALIBRATING,
        ProcessStateType.CONFIGURING,
        ProcessStateType.LOADING,
        ProcessStateType.VALIDATING,
        ProcessStateType.EXECUTING,
        ProcessStateType.PROCESSING,
        ProcessStateType.MOVING,
        ProcessStateType.STARTING,
        ProcessStateType.RESUMING,
        ProcessStateType.STOPPING,
        ProcessStateType.COMPLETING,
        ProcessStateType.FINALIZING,
        ProcessStateType.RECOVERING,
        ProcessStateType.SHUTTING_DOWN,
    }
    
    # Terminal states (process ends in these states)
    TERMINAL_STATES: Set[ProcessStateType] = {
        ProcessStateType.COMPLETED,
        ProcessStateType.FAILED,
        ProcessStateType.STOPPED,
    }
    
    # Error states
    ERROR_STATES: Set[ProcessStateType] = {
        ProcessStateType.ERROR,
        ProcessStateType.RECOVERING,
        ProcessStateType.FAILED,
    }
    
    @classmethod
    def get_category(cls, state: ProcessStateType) -> ProcessStateCategory:
        """Get the category for a given state."""
        return cls.STATE_CATEGORIES.get(state, ProcessStateCategory.EXECUTION)
    
    @classmethod
    def get_description(cls, state: ProcessStateType) -> str:
        """Get the description for a given state."""
        return cls.STATE_DESCRIPTIONS.get(state, "Unknown state")
    
    @classmethod
    def is_interruptible(cls, state: ProcessStateType) -> bool:
        """Check if a state can be interrupted by pause/stop commands."""
        return state in cls.INTERRUPTIBLE_STATES
    
    @classmethod
    def is_active(cls, state: ProcessStateType) -> bool:
        """Check if a state represents an active operation."""
        return state in cls.ACTIVE_STATES
    
    @classmethod
    def is_terminal(cls, state: ProcessStateType) -> bool:
        """Check if a state is terminal (process ends)."""
        return state in cls.TERMINAL_STATES
    
    @classmethod
    def is_error_state(cls, state: ProcessStateType) -> bool:
        """Check if a state represents an error condition."""
        return state in cls.ERROR_STATES
    
    @classmethod
    def get_states_by_category(cls, category: ProcessStateCategory) -> Set[ProcessStateType]:
        """Get all states in a specific category."""
        return {state for state, cat in cls.STATE_CATEGORIES.items() if cat == category}


# === DEFAULT TRANSITION RULES ===

class CommonTransitionRules:
    """
    Common transition rules that apply to most process state machines.
    
    Applications can use these as a starting point and add their own specific rules.
    """
    
    @staticmethod
    def get_base_transitions() -> Dict[ProcessStateType, Set[ProcessStateType]]:
        """
        Get the base transition rules that most applications can use.
        
        Returns:
            Dict mapping states to their valid transition targets
        """
        return {
            # From INITIALIZING
            ProcessStateType.INITIALIZING: {
                ProcessStateType.READY,
                ProcessStateType.ERROR,
                ProcessStateType.FAILED,
            },
            
            # From READY  
            ProcessStateType.READY: {
                ProcessStateType.PREPARING,
                ProcessStateType.IDLE,
                ProcessStateType.SHUTTING_DOWN,
                ProcessStateType.ERROR,
            },
            
            # From IDLE
            ProcessStateType.IDLE: {
                ProcessStateType.STARTING,
                ProcessStateType.PREPARING,
                ProcessStateType.CALIBRATING,
                ProcessStateType.CONFIGURING,
                ProcessStateType.SHUTTING_DOWN,
                ProcessStateType.ERROR,
            },
            
            # From PREPARING
            ProcessStateType.PREPARING: {
                ProcessStateType.EXECUTING,
                ProcessStateType.VALIDATING,
                ProcessStateType.PAUSED,
                ProcessStateType.STOPPED,
                ProcessStateType.ERROR,
            },
            
            # From EXECUTING
            ProcessStateType.EXECUTING: {
                ProcessStateType.PROCESSING,
                ProcessStateType.MOVING,
                ProcessStateType.COMPLETING,
                ProcessStateType.PAUSED,
                ProcessStateType.STOPPING,
                ProcessStateType.ERROR,
            },
            
            # From PAUSED
            ProcessStateType.PAUSED: {
                ProcessStateType.RESUMING,
                ProcessStateType.STOPPING,
                ProcessStateType.STOPPED,
                ProcessStateType.ERROR,
            },
            
            # From COMPLETED
            ProcessStateType.COMPLETED: {
                ProcessStateType.IDLE,
                ProcessStateType.SHUTTING_DOWN,
            },
            
            # From ERROR
            ProcessStateType.ERROR: {
                ProcessStateType.RECOVERING,
                ProcessStateType.FAILED,
                ProcessStateType.STOPPED,
                ProcessStateType.IDLE,
            },
            
            # Add more transition rules as needed...
        }
    
    @staticmethod
    def get_emergency_transitions() -> Set[ProcessStateType]:
        """
        Get states that can be reached from any state in emergency situations.
        
        Returns:
            Set of states that can always be transitioned to
        """
        return {
            ProcessStateType.ERROR,
            ProcessStateType.STOPPING,
            ProcessStateType.STOPPED,
            ProcessStateType.FAILED,
        }