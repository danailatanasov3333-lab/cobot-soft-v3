from typing import Tuple
from modules.utils.custom_logging import log_info_message
from ..models import Position
from ..measure_height import measure_height_at_position, HeightMeasureContext


class MeasurementWorkflow:
    """Workflow for height measurement operations."""
    
    def __init__(self, height_measure_context: HeightMeasureContext, logger_context):
        self.height_measure_context = height_measure_context
        self.logger_context = logger_context
    
    def measure_workpiece_height(self, height_measure_position: Position, 
                                measurement_height: float = 350.0,
                                height_adjustment: float = 2.0) -> Tuple[bool, float]:
        """
        Measure the height of a workpiece at the specified position.
        
        Args:
            height_measure_position: Position for height measurement
            measurement_height: Safe height for measurement
            height_adjustment: Additional height to add to measurement
            
        Returns:
            Tuple of (success, measured_height)
        """
        # Set measurement height
        position_list = height_measure_position.to_list()
        position_list[2] = measurement_height
        
        log_info_message(
            self.logger_context, 
            f"Measuring height at position: {position_list[:3]}"
        )
        
        # Perform height measurement
        result, measured_height, value_in_pixels = measure_height_at_position(
            self.height_measure_context, position_list
        )
        
        if not result:
            log_info_message(self.logger_context, "Height measurement failed")
            return False, 0.0
        
        # Apply height adjustment
        adjusted_height = measured_height + height_adjustment
        
        log_info_message(
            self.logger_context,
            f"Measured workpiece height: {measured_height:.2f}mm, "
            f"adjusted to: {adjusted_height:.2f}mm (pixels: {value_in_pixels})"
        )
        
        return True, adjusted_height
    
    def prepare_height_measurement_position(self, centroid_for_height_measure, 
                                          rz_orientation: float) -> Position:
        """
        Prepare and adjust height measurement position from centroid data.
        
        Args:
            centroid_for_height_measure: Raw centroid data from vision
            rz_orientation: RZ orientation for measurement
            
        Returns:
            Position object for height measurement
        """
        # Extract raw centroid coordinates
        cx = centroid_for_height_measure[0][0][0][0]
        cy = centroid_for_height_measure[0][0][0][1]

        # Rotate centroid by 90 degrees counterclockwise around origin
        rotated_cx = -cy
        rotated_cy = cx
        
        # Create position for height measurement
        position = Position(
            x=rotated_cx,
            y=rotated_cy,
            z=350.0,  # Will be set during measurement
            rx=180,
            ry=0,
            rz=rz_orientation
        )
        
        log_info_message(
            self.logger_context,
            f"Prepared height measurement position: ({rotated_cx:.2f}, {rotated_cy:.2f})"
        )
        
        return position