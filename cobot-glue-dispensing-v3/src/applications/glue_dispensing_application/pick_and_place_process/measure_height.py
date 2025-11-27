import time
from dataclasses import dataclass

import cv2

from applications.glue_dispensing_application.pick_and_place_process.execute_pick_and_place_sequence import move_to
from core.services.robot_service.impl.base_robot_service import RobotService
from core.services.vision.VisionService import _VisionService
from modules.VisionSystem.heightMeasuring.LaserTracker import LaserTrackService
from modules.shared.tools.Laser import Laser


@dataclass
class HeightMeasureContext:
    robot_service: RobotService
    vision_service: _VisionService
    laser_tracking_service: LaserTrackService
    laser: Laser

def measure_height_at_position(context: HeightMeasureContext,position: tuple):

    ret = move_to(context.robot_service, position)

    if ret != 0:
        context.laser.turnOff()
        return False, "Failed to move to height measuring position"

    # 2.Turn laser on and measure height
    time.sleep(1)  # wait for brightness to stabilize
    skip_images_count = 5
    while skip_images_count > 0:
        # skip initial images to allow auto-exposure to stabilize
        _ = context.vision_service.getLatestFrame()
        skip_images_count -= 1
        if skip_images_count <= 0:
            break
    latest_image = context.vision_service.getLatestFrame()
    # convert to RGB
    latest_image = cv2.cvtColor(latest_image, cv2.COLOR_BGR2RGB)

    if latest_image is None:
        context.laser.turnOff()
        return False, "Failed to capture image for height measurement"
    cv2.imwrite("debug_laser_image.png", latest_image)
    return context.laser_tracking_service.measure_height(latest_image)