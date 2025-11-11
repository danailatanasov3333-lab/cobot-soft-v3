"""
Process State Machine Interface

This module defines the abstract interface for all process state machines
in the robot applications. It provides a contract that all application-specific
state machines must implement, ensuring consistency and reusability.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Set, Callable, Any, Optional, Union
from modules.shared.MessageBroker import MessageBroker


class ProcessStateMachineInterface(ABC):
    """
    Abstract interface for all process state machines.
    
    This interface defines the contract that all application-specific state machines
    must implement. It ensures consistent behavior across different robot applications
    (glue dispensing, painting, pick-and-place, etc.).
    """
    
    @abstractmethod
    def __init__(self, initial_state: Enum, context: Any = None, broker: MessageBroker = None):
        """
        Initialize the state machine.
        
        Args:
            initial_state: The initial state of the process
            context: Optional context object (e.g., robot service, settings)
            broker: Message broker for state change notifications
        """
        pass
    
    @property
    @abstractmethod
    def current_state(self) -> Enum:
        """
        Get the current state of the process.
        
        Returns:
            Enum: The current state
        """
        pass
    
    @property
    @abstractmethod
    def application_type(self) -> str:
        """
        Get the application type identifier.
        
        Returns:
            str: Application type (e.g., "glue", "paint", "pick_place")
        """
        pass
    
    @abstractmethod
    def can_transition(self, to_state: Enum) -> bool:
        """
        Check if a transition to the specified state is allowed.
        
        Args:
            to_state: The target state
            
        Returns:
            bool: True if transition is allowed, False otherwise
        """
        pass
    
    @abstractmethod
    def transition(self, to_state: Enum, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Attempt to transition to a new state.
        
        Args:
            to_state: The target state
            context: Optional context data for the transition
            
        Returns:
            bool: True if transition was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_valid_transitions(self) -> Set[Enum]:
        """
        Get all valid transitions from the current state.
        
        Returns:
            Set[Enum]: Set of valid target states
        """
        pass
    
    @abstractmethod
    def register_state_handler(self, state: Enum, handler_type: str, handler: Callable):
        """
        Register a handler for state entry/exit events.
        
        Args:
            state: The state to register the handler for
            handler_type: Type of handler ("on_enter", "on_exit")
            handler: The handler function
        """
        pass
    
    @abstractmethod
    def get_transition_history(self) -> list:
        """
        Get the history of state transitions.
        
        Returns:
            list: List of transition records with timestamps
        """
        pass
    
    @abstractmethod
    def reset(self, initial_state: Optional[Enum] = None):
        """
        Reset the state machine to its initial state or specified state.
        
        Args:
            initial_state: Optional state to reset to (uses original if not provided)
        """
        pass
    
    # === MESSAGE BROKER INTEGRATION ===
    
    @abstractmethod
    def publish_state_change(self, old_state: Enum, new_state: Enum, context: Optional[Dict[str, Any]] = None):
        """
        Publish state change notification via MessageBroker.
        
        Args:
            old_state: The previous state
            new_state: The new state
            context: Optional context data
        """
        pass
    
    @abstractmethod
    def subscribe_to_control_messages(self):
        """
        Subscribe to control messages that can trigger state changes.
        This includes messages like pause, stop, resume, etc.
        """
        pass
    
    # === OPTIONAL ADVANCED FEATURES ===
    
    def get_state_metadata(self, state: Enum) -> Dict[str, Any]:
        """
        Get metadata about a specific state (optional to implement).
        
        Args:
            state: The state to get metadata for
            
        Returns:
            Dict[str, Any]: Metadata about the state (description, category, etc.)
        """
        return {}
    
    def validate_transition_context(self, from_state: Enum, to_state: Enum, context: Optional[Dict[str, Any]]) -> bool:
        """
        Validate that the context is appropriate for the transition (optional to implement).
        
        Args:
            from_state: The source state
            to_state: The target state
            context: The transition context
            
        Returns:
            bool: True if context is valid, False otherwise
        """
        return True
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about state machine usage (optional to implement).
        
        Returns:
            Dict[str, Any]: Statistics like time in each state, transition counts, etc.
        """
        return {}


class ProcessStateManagerInterface(ABC):
    """
    Interface for managing multiple process state machines.
    
    This is useful for applications that need to coordinate multiple processes
    or manage state machine lifecycles.
    """
    
    @abstractmethod
    def register_state_machine(self, name: str, state_machine: ProcessStateMachineInterface):
        """
        Register a state machine with the manager.
        
        Args:
            name: Unique name for the state machine
            state_machine: The state machine instance
        """
        pass
    
    @abstractmethod
    def get_state_machine(self, name: str) -> Optional[ProcessStateMachineInterface]:
        """
        Get a registered state machine by name.
        
        Args:
            name: The name of the state machine
            
        Returns:
            ProcessStateMachineInterface: The state machine or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_states(self) -> Dict[str, Enum]:
        """
        Get the current state of all registered state machines.
        
        Returns:
            Dict[str, Enum]: Mapping of state machine names to their current states
        """
        pass
    
    @abstractmethod
    def broadcast_event(self, event: str, context: Optional[Dict[str, Any]] = None):
        """
        Broadcast an event to all registered state machines.
        
        Args:
            event: The event name
            context: Optional event context
        """
        pass


# === HELPER TYPES ===

class StateTransition:
    """
    Represents a state transition record.
    """
    
    def __init__(self, from_state: Enum, to_state: Enum, timestamp: float, context: Optional[Dict[str, Any]] = None):
        self.from_state = from_state
        self.to_state = to_state
        self.timestamp = timestamp
        self.context = context or {}
    
    def __repr__(self):
        return f"StateTransition({self.from_state} -> {self.to_state} at {self.timestamp})"


class StateHandler:
    """
    Represents a state handler configuration.
    """
    
    def __init__(self, state: Enum, handler_type: str, handler: Callable, priority: int = 0):
        self.state = state
        self.handler_type = handler_type  # "on_enter", "on_exit"
        self.handler = handler
        self.priority = priority  # Higher priority handlers run first
    
    def __repr__(self):
        return f"StateHandler({self.state}.{self.handler_type}, priority={self.priority})"