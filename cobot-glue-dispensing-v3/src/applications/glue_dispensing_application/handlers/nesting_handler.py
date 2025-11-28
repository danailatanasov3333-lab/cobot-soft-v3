from applications.glue_dispensing_application.pick_and_place_process.nesting_entry import start_nesting as nesting_start
from applications.glue_dispensing_application.pick_and_place_process.workflows import NestingResult


def start_nesting(application, workpieces) -> NestingResult:
    """
    Start nesting operation using the new layered architecture.
    
    Args:
        application: Application instance with movement methods and services
        workpieces: List of workpiece templates to match against
        
    Returns:
        NestingResult with operation status and message
    """
    return nesting_start(
        application=application,
        vision_service=application.visionService,
        robot_service=application.robotService,
        preselected_workpiece=workpieces
    )
