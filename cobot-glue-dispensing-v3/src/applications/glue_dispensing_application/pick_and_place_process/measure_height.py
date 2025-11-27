import time

import cv2

from applications.glue_dispensing_application.pick_and_place_process.execute_pick_and_place_sequence import move_to


def measure_height_at_position(robot_service, vision_service, laser_tracking_service, position, laser):
    ret = move_to(robot_service, position)

    if ret != 0:
        laser.turnOff()
        return False, "Failed to move to height measuring position"

    # 2.Turn laser on and measure height
    time.sleep(1)  # wait for brightness to stabilize
    skip_images_count = 5
    while skip_images_count > 0:
        # skip initial images to allow auto-exposure to stabilize
        _ = vision_service.getLatestFrame()
        skip_images_count -= 1
        if skip_images_count <= 0:
            break
    latest_image = vision_service.getLatestFrame()
    # convert to RGB
    latest_image = cv2.cvtColor(latest_image, cv2.COLOR_BGR2RGB)

    if latest_image is None:
        laser.turnOff()
        return False, "Failed to capture image for height measurement"
    cv2.imwrite("debug_laser_image.png", latest_image)
    return laser_tracking_service.measure_height(latest_image)