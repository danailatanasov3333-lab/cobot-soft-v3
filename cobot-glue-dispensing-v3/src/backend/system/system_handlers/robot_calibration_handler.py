import threading

from modules.robot.calibration.newRobotCalibUsingTopLeftCornersOfArucoMarkers import CalibrationPipeline

def calibrate_robot(application):

        required_ids = [0,1, 2,3,4,5, 6,8]
        print(f"Robot Calibration: Using required IDs: {required_ids}")
        try:
            robot_calib_pipeline = CalibrationPipeline(system=application.visionService,
                                                       robot_service=application.robotService,
                                                       required_ids=required_ids,
                                                       debug=True,
                                                       step_by_step=False,
                                                       live_visualization=False)
        except Exception as e:
            import traceback
            traceback.print_exc()

        application.visionService.drawContours = False
        
        # Add debug print and ensure thread execution
        print("About to start calibration thread...")
        calibration_thread = threading.Thread(target=robot_calib_pipeline.run, daemon=False)  # Change to non-daemon
        print(f"Created thread: {calibration_thread}")
        calibration_thread.start()
        print(f"Thread started: {calibration_thread.is_alive()}")
        
        message = "Calibration started in background thread"
        image = None
        return True, message, image
