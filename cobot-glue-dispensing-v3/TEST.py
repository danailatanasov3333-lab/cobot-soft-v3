
if workpiece_found:
    # THERE WERE WORKPIECES BEFORE, BUT NOW NONE LEFT -> FINISH NESTING SUCCESSFULLY
    log_info_message(logger_context,"No more workpieces detected, dropping off gripper and completing nesting.")
    robotService.dropOffGripper(robotService.current_tool)
    laser.turnOff()
    return NestingResult(success=True, message="Nesting complete, no more workpieces to pick")
else:
    # THIS IS FIRST ITERATION AND NO WORKPIECES FOUND
    laser.turnOff()
    return NestingResult(success=False, message="No contours found after retries")

if workpiece_found:
    log_info_message(logger_context, "No more workpieces matched, completing nesting operation.")
    robotService.dropOffGripper(robotService.current_tool)

    ret = application.move_to_nesting_capture_position()
    if ret != 0:
        laser.turnOff()
        return NestingResult(success=False, message="Failed to move to start position")
    return NestingResult(success=True, message="Nesting complete, no more workpieces to pick")
else:
    log_info_message(logger_context, "No workpieces matched in this cycle.")
    return NestingResult(success=False, message="No workpieces matched detected contours")


def finish_nesting(robotService, laser, workpiece_found: bool, message_success: str, message_failure: str, move_before_finish=False, application=None):
    """
    Finish nesting operation, handling gripper drop, laser, and success/failure messages.
    """
    if workpiece_found:
        log_info_message(logger_context, "No more workpieces detected, completing nesting.")
        robotService.dropOffGripper(robotService.current_tool)
        if move_before_finish and application is not None:
            ret = application.move_to_nesting_capture_position()
            if ret != 0:
                laser.turnOff()
                return NestingResult(success=False, message="Failed to move to start position")
        laser.turnOff()
        return NestingResult(success=True, message=message_success)
    else:
        laser.turnOff()
        return NestingResult(success=False, message=message_failure)
