from typing import List, Optional
from modules.VisionSystem.heightMeasuring.LaserTracker import LaserTrackService
from modules.shared.localization.enums.Message import Message
from modules.utils.custom_logging import setup_logger, LoggerContext, log_info_message
from core.services.robot_service.impl.base_robot_service import RobotService

from .models import GrippersConfig
from .services import PickupService, PlacementService, PlaneManagementService, GripperService
from .workflows import VisionWorkflow, RobotWorkflow, MeasurementWorkflow, PlacementWorkflow, NestingResult
from .measure_height import HeightMeasureContext
from .debug import save_nesting_debug_plot
from .Plane import Plane


class NestingController:
    """Clean controller for the nesting operation using layered architecture."""
    
    # Constants
    RZ_ORIENTATION = 90  # degrees
    DESCENT_HEIGHT_OFFSET = 150  # mm above workpiece for descent
    
    def __init__(self, application, vision_service, robot_service: RobotService):
        self.application = application
        self.vision_service = vision_service
        self.robot_service = robot_service
        
        # Setup logging
        enable_logging = True
        self.logger = setup_logger("nesting") if enable_logging else None
        self.logger_context = LoggerContext(enabled=enable_logging, logger=self.logger)
        
        # Initialize components
        self._setup_components()
        
        # Tracking variables
        self.count = 0
        self.workpiece_found = False
        self.placed_contours = []
    
    def _setup_components(self):
        """Initialize all services and workflows."""
        # Configuration
        self.grippers_config = GrippersConfig(
            gripper_x_offset=100.429,
            gripper_y_offset=1.991,
            double_gripper_z_offset=14,
            single_gripper_z_offset=19
        )
        
        # Initialize plane
        self.plane = Plane()
        
        # Get tools
        self.laser = self.robot_service.tool_manager.get_tool("laser")
        laser_tracking_service = LaserTrackService()
        
        # Setup services
        self.pickup_service = PickupService(self.grippers_config, self.DESCENT_HEIGHT_OFFSET)
        plane_service = PlaneManagementService(self.plane)
        self.placement_service = PlacementService(plane_service)
        self.gripper_service = GripperService(self.grippers_config)
        
        # Setup workflows
        self.vision_workflow = VisionWorkflow(self.vision_service, self.logger_context)
        self.robot_workflow = RobotWorkflow(self.robot_service, self.logger_context)
        
        height_measure_context = HeightMeasureContext(
            robot_service=self.robot_service,
            vision_service=self.vision_service,
            laser_tracking_service=laser_tracking_service,
            laser=self.laser
        )
        self.measurement_workflow = MeasurementWorkflow(height_measure_context, self.logger_context)
        
        self.placement_workflow = PlacementWorkflow(
            self.pickup_service, self.placement_service, self.gripper_service,
            self.measurement_workflow, self.grippers_config, self.logger_context
        )
    
    def start_nesting(self, preselected_workpiece: List) -> NestingResult:
        """
        Main nesting operation entry point.
        
        Args:
            preselected_workpiece: List of workpieces to nest
            
        Returns:
            NestingResult with operation status
        """
        log_info_message(self.logger_context, "Starting Nesting Operation")
        
        try:
            return self._execute_nesting_loop(preselected_workpiece)
        except Exception as e:
            log_info_message(self.logger_context, f"Nesting operation failed with exception: {str(e)}")
            self.laser.turnOff()
            return NestingResult(success=False, message=f"Nesting failed: {str(e)}")
    
    def _execute_nesting_loop(self, workpieces: List) -> NestingResult:
        """Execute the main nesting loop."""
        log_info_message(self.logger_context, "BEFORE WHILE LOOP IN START_NESTING")
        
        while True:
            # Move to capture position
            if not self.robot_workflow.move_to_capture_position(self.application, self.laser):
                return NestingResult(success=False, message="Failed to move to start position")
            
            # Setup vision and get contours
            self.vision_workflow.setup_vision_capture()
            success, contours = self.vision_workflow.get_contours_with_retries()
            
            if not success:
                return self.robot_workflow.finish_nesting(
                    self.laser, self.workpiece_found,
                    "Nesting complete, no more workpieces to pick",
                    "No contours found after retries"
                )
            
            # Process contours
            processed_contours = self.vision_workflow.process_detected_contours(contours)
            filtered_contours = self.vision_workflow.filter_contours_by_pickup_area(processed_contours)
            
            if filtered_contours is None:
                filtered_contours = processed_contours
            
            # Match workpieces
            matches_data, no_matches = self.vision_workflow.match_contours_to_workpieces(
                workpieces, filtered_contours
            )
            
            if matches_data is None:
                log_info_message(self.logger_context, "Error during contour matching.")
                self.laser.turnOff()
                return NestingResult(success=False, message="Error during contour matching")
            
            # Process matches
            orientations = matches_data["orientations"]
            matches = matches_data["workpieces"]
            
            if not matches or len(matches) == 0:
                return self.robot_workflow.finish_nesting(
                    self.laser, self.workpiece_found,
                    "Nesting complete, no more workpieces to pick",
                    "No workpieces matched detected contours",
                    move_before_finish=True, application=self.application
                )
            
            self.workpiece_found = True
            log_info_message(self.logger_context, f"Found {len(matches)} matching workpieces, processing each match...")
            
            # Process each matched workpiece
            result = self._process_matched_workpieces(matches, orientations)
            if result is not None:
                return result
            
            # Continue loop for more workpieces
    
    def _process_matched_workpieces(self, matches: List, orientations: List) -> Optional[NestingResult]:
        """
        Process each matched workpiece.
        
        Returns:
            NestingResult if operation should end, None to continue with next iteration
        """
        for match_i, match in enumerate(matches):
            # Move to capture position for each workpiece
            if not self.robot_workflow.move_to_capture_position(self.application, self.laser):
                return NestingResult(success=False, message="Failed to move to start position")
            
            # Process workpiece placement
            placement = self.placement_workflow.process_single_workpiece(
                match, match_i, orientations[match_i], self.vision_service,
                self.robot_service, self.RZ_ORIENTATION
            )
            
            # Check if placement calculation failed
            if placement is None:
                log_info_message(self.logger_context, f"Failed to calculate placement for workpiece {match_i + 1}")
                continue
                
            # Check if plane is full (this would be indicated by placement service)
            if hasattr(self.plane, 'isFull') and self.plane.isFull:
                log_info_message(self.logger_context, "⚠️  PLANE FULL: Cannot place more workpieces")
                break
            
            # Change gripper if needed
            target_gripper_id = int(match.gripperID.value)
            gripper_result = self.robot_workflow.change_gripper_if_needed(target_gripper_id, self.laser)
            if not gripper_result.success:
                log_info_message(self.logger_context, f"Failed to change gripper to {target_gripper_id}: {gripper_result.message}")
                return gripper_result
            
            # Get centroid for height measurement
            # Create contour object for pickup point determination
            from modules.shared.core.ContourStandartized import Contour
            contour = match.get_main_contour()
            cnt_obj = Contour(contour)
            
            centroid = self.placement_workflow.determine_pickup_point(match, cnt_obj)
            centroid_for_height_measure, _ = self.placement_workflow.transform_centroids(
                self.vision_service, centroid
            )
            
            # Execute placement
            success = self.placement_workflow.execute_workpiece_placement(
                placement, self.robot_service, self.laser, match.gripperID, centroid_for_height_measure
            )
            
            if not success:
                return NestingResult(success=False, message="Failed during pick and place sequence")
            
            # Update tracking
            self.count += 1
            self.placed_contours.append({
                'contour': placement.contour,
                'drop_position': placement.drop_off_positions.position1.to_list(),
                'dimensions': (placement.dimensions.width, placement.dimensions.height),
                'match_index': match_i + 1
            })
            
            # Save debug plot
            save_nesting_debug_plot(self.plane, self.placed_contours, match_i + 1)
            
            log_info_message(self.logger_context, f"Successfully placed workpiece {match_i + 1}")
        
        return None  # Continue with next iteration