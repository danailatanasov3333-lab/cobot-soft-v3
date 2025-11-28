from typing import List, Tuple, Optional
from modules.utils.custom_logging import log_info_message
from modules.shared.core.ContourStandartized import Contour
from modules.utils import utils
from ..models import WorkpiecePlacement, GrippersConfig
from ..services import PickupService, PlacementService, GripperService
from ..logging_utils import log_match_details
from .measurement_workflow import MeasurementWorkflow
from ..execute_pick_and_place_sequence import execute_pick_and_place_sequence


class PlacementWorkflow:
    """Workflow for complete workpiece placement operations."""
    
    def __init__(self, pickup_service: PickupService, placement_service: PlacementService,
                 gripper_service: GripperService, measurement_workflow: MeasurementWorkflow,
                 grippers_config: GrippersConfig, logger_context):
        self.pickup_service = pickup_service
        self.placement_service = placement_service
        self.gripper_service = gripper_service
        self.measurement_workflow = measurement_workflow
        self.grippers_config = grippers_config
        self.logger_context = logger_context
    
    def determine_pickup_point(self, match, cnt_obj: Contour) -> Tuple[float, float]:
        """
        Determine the pickup point for a workpiece.
        
        Args:
            match: Matched workpiece object
            cnt_obj: Contour object
            
        Returns:
            Centroid coordinates for pickup
        """
        if match.pickupPoint is not None:
            centroid = match.pickupPoint
            log_info_message(self.logger_context, f"Using predefined pickup point: {centroid}")
        else:
            centroid = cnt_obj.getCentroid()
            log_info_message(self.logger_context, f"No predefined pickup point, using contour centroid: {centroid}")

        return centroid
    
    def transform_centroids(self, vision_service, centroid: Tuple[float, float]) -> Tuple:
        """
        Apply homography transformation to centroids.
        
        Args:
            vision_service: Vision service for transformation matrix
            centroid: Original centroid coordinates
            
        Returns:
            Tuple of (centroid_for_height_measure, flat_centroid)
        """
        log_info_message(self.logger_context, f"[transform_centroids] {centroid}")
        
        transformed_centroid = utils.applyTransformation(
            vision_service.cameraToRobotMatrix, [centroid]
        )
        centroid_for_height_measure = utils.applyTransformation(
            vision_service.cameraToRobotMatrix, [centroid], apply_transducer_offset=False
        )
        
        flat_centroid = transformed_centroid
        while isinstance(flat_centroid, (list, tuple)) and len(flat_centroid) == 1:
            flat_centroid = flat_centroid[0]

        return centroid_for_height_measure, flat_centroid
    
    def process_single_workpiece(self, match, match_index: int, orientation: float,
                               vision_service, robot_service, 
                               rz_orientation: float, match_height: float = 3.0) -> Optional[WorkpiecePlacement]:
        """
        Process a single workpiece for placement.
        
        Args:
            match: Matched workpiece object
            match_index: Index of the match
            orientation: Workpiece orientation
            vision_service: Vision service
            robot_service: Robot service
            rz_orientation: RZ orientation
            match_height: Height of the workpiece
            
        Returns:
            WorkpiecePlacement object or None if failed
        """
        try:
            # Get workpiece contour and setup
            contour = match.get_main_contour()
            cnt_obj = Contour(contour)
            gripper = match.gripperID
            
            # Determine pickup point
            centroid = self.determine_pickup_point(match, cnt_obj)
            
            # Apply homography transformation
            centroid_for_height_measure, flat_centroid = self.transform_centroids(vision_service, centroid)
            
            # Log match details
            log_match_details(
                self.logger_context, match_height, gripper, centroid, flat_centroid, 
                [orientation], match_index
            )
            
            # Calculate pickup positions
            pickup_positions, height_measure_position, pickup_height = self.pickup_service.calculate_pickup_positions(
                flat_centroid, match_height, robot_service, orientation, gripper, rz_orientation
            )
            
            # Calculate placement positions
            placement_result = self.placement_service.calculate_placement_positions(
                match, centroid, orientation, pickup_height, gripper
            )
            
            if not placement_result.success:
                log_info_message(self.logger_context, f"Placement calculation failed: {placement_result.message}")
                return None
            
            # Update placement with pickup positions
            placement_result.placement.pickup_positions = pickup_positions
            
            return placement_result.placement
            
        except Exception as e:
            log_info_message(self.logger_context, f"Error processing workpiece {match_index}: {str(e)}")
            return None
    
    def execute_workpiece_placement(self, placement: WorkpiecePlacement, 
                                  robot_service, laser, gripper,
                                  centroid_for_height_measure) -> bool:
        """
        Execute the complete placement of a workpiece.
        
        Args:
            placement: WorkpiecePlacement with all position data
            robot_service: Robot service
            laser: Laser tool
            gripper: Gripper type
            centroid_for_height_measure: Centroid data for height measurement
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Change gripper if needed
            target_gripper_id = int(gripper.value)
            
            # Measure height at position
            height_position = self.measurement_workflow.prepare_height_measurement_position(
                centroid_for_height_measure, 90  # RZ_ORIENTATION
            )
            
            success, measured_height = self.measurement_workflow.measure_workpiece_height(height_position)
            if not success:
                log_info_message(self.logger_context, "Failed to measure height")
                return False
            
            # Convert positions to list format for execution
            pickup_positions_list = placement.pickup_positions.to_list()
            drop_off_position1, drop_off_position2 = placement.drop_off_positions.to_tuple()
            
            # Apply gripper offsets to drop-off positions
            self.gripper_service.apply_gripper_offsets_to_positions(
                gripper, drop_off_position1, drop_off_position2
            )
            
            # Execute pick and place sequence
            ret = execute_pick_and_place_sequence(
                robot_service,
                pickup_positions_list,
                drop_off_position1,
                drop_off_position2,
                measured_height,
                gripper,
                self.logger_context,
                self.grippers_config
            )
            
            if ret != 0:
                robot_service.tool_manager.pump.turnOff(robot_service.robot)
                log_info_message(self.logger_context, "Pick and place sequence failed")
                return False
            
            log_info_message(self.logger_context, "Workpiece placement completed successfully")
            return True
            
        except Exception as e:
            log_info_message(self.logger_context, f"Error executing placement: {str(e)}")
            return False