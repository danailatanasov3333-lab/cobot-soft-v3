from collections import namedtuple
from modules.shared.shared.settings.conreateSettings.enums.RobotSettingKey import RobotSettingKey
from src.robot_application.glue_dispensing_application.glue_dispensing.glue_dispensing_operation import glue_dispensing_logger_context
from modules.robot.robotService.enums.RobotServiceState import RobotServiceState
from src.backend.system.utils.custom_logging import log_debug_message, log_error_message
from modules.robot.robotService.RobotService import CancellationToken

HandlerResult = namedtuple(
    "HandlerResult",
    [
        "handled",
        "resume",
        "next_state",
        "next_path_index",
        "next_point_index",
        "next_path",
        "next_settings",
    ]
)

def handle_send_path_to_robot(context):
    """
    Sends path points to robot with immediate pause support using cancellation tokens.
    Returns a HandlerResult describing success/failure and next FSM state.
    """
    path = context.current_path
    settings = context.current_settings
    start_point_index = context.current_point_index
    path_index = context.current_path_index

    log_debug_message(
        glue_dispensing_logger_context,
        message=f"Sending {len(path)} points to robot with pause support (path index {path_index})"
    )

    # Create a cancellation token that monitors state machine
    cancellation_token = CancellationToken()
    
    for i, point in enumerate(path, start_point_index):
        # Check for pause/stop before each movement
        if context.state_machine.state == RobotServiceState.PAUSED:
            context.save_progress(path_index, i)
            log_debug_message(glue_dispensing_logger_context, message=f"Paused before point {i}")
            return HandlerResult(True, True, RobotServiceState.PAUSED, path_index, i, path, settings)

        if context.state_machine.state == RobotServiceState.STOPPED:
            log_debug_message(glue_dispensing_logger_context, message=f"Stopped before point {i}")
            return HandlerResult(True, False, RobotServiceState.STOPPED, path_index, i, path, settings)

        try:
            # Send move command (non-blocking)
            ret = context.robot_service.robot.moveL(
                position=point,
                tool=context.robot_service.robot_config.robot_tool,
                user=context.robot_service.robot_config.robot_user,
                vel=settings.get(RobotSettingKey.VELOCITY.value, 10),
                acc=settings.get(RobotSettingKey.ACCELERATION.value, 30),
                blendR=1,
            )

            if ret != 0:
                log_error_message(glue_dispensing_logger_context, message=f"MoveL failed with code {ret} at point {i}")
                return HandlerResult(False, False, RobotServiceState.ERROR, path_index, i, path, settings)

            # Now wait for robot to reach this point with cancellation support
            # Reset cancellation token for this movement
            cancellation_token.reset()
            
            # Monitor state machine and cancel if needed
            def monitor_state_machine():
                import threading
                import time
                def check_state():
                    while not cancellation_token.is_cancelled():
                        if context.state_machine.state in [RobotServiceState.PAUSED, RobotServiceState.STOPPED]:
                            reason = f"State changed to {context.state_machine.state.value}"
                            cancellation_token.cancel(reason)
                            break
                        time.sleep(0.01)  # Check every 10ms
                
                monitor_thread = threading.Thread(target=check_state, daemon=True)
                monitor_thread.start()
            
            # Start monitoring
            monitor_state_machine()
            
            # Wait for robot to reach this point with cancellation support
            reached = context.robot_service._waitForRobotToReachPosition(
                endPoint=point,
                threshold=2.0,  # 2mm threshold
                delay=0.01,
                timeout=60,  # 60 second timeout
                cancellation_token=cancellation_token
            )
            
            # Check if movement was cancelled
            if cancellation_token.is_cancelled():
                reason = cancellation_token.get_cancellation_reason()
                log_debug_message(glue_dispensing_logger_context, 
                    message=f"Movement to point {i} cancelled: {reason}")
                
                if "PAUSED" in reason:
                    context.save_progress(path_index, i)
                    return HandlerResult(True, True, RobotServiceState.PAUSED, path_index, i, path, settings)
                else:
                    return HandlerResult(True, False, RobotServiceState.STOPPED, path_index, i, path, settings)
            
            if not reached:
                log_error_message(glue_dispensing_logger_context, 
                    message=f"Robot failed to reach point {i} within timeout")
                return HandlerResult(False, False, RobotServiceState.ERROR, path_index, i, path, settings)

            log_debug_message(glue_dispensing_logger_context, message=f"Reached point {i} successfully")

        except Exception as e:
            import traceback
            traceback.print_exc()
            log_error_message(glue_dispensing_logger_context, message=f"Exception at point {i}: {e}")
            return HandlerResult(False, False, RobotServiceState.ERROR, path_index, i, path, settings)

    # All points completed successfully
    log_debug_message(glue_dispensing_logger_context, message="All points sent and reached. Path completed.")
    return HandlerResult(True, False, RobotServiceState.WAIT_FOR_PATH_COMPLETION, path_index, 0, path, settings)

