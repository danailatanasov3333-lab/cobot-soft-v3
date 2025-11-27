from applications.glue_dispensing_application.pick_and_place_process.logging_utils import log_workpiece_dimensions, \
    log_calculated_drop_position, log_moving_to_next_row, log_placement_calculations
from modules.shared.core.ContourStandartized import Contour
from modules.shared.tools.enums.Gripper import Gripper
from modules.utils.custom_logging import log_info_message, LoggingLevel, log_info_message


def calculate_workpiece_dimensions(cntObject):
    # Calculate workpiece dimensions
    minRect = cntObject.getMinAreaRect()
    bboxCenter = (minRect[0][0], minRect[0][1])
    width = minRect[1][0]
    height = minRect[1][1]
    if width < height:
        width, height = height, width

    return width, height, bboxCenter, minRect


def calculate_target_drop_position(plane, width, height):
    # Calculate target placement position
    targetPointX = plane.xOffset + plane.xMin + (width / 2)
    targetPointY = plane.yMax - plane.yOffset - (height / 2)
    return targetPointX, targetPointY


def calculate_drop_off_position(match, centroid, orientation, plane, pickup_height, gripper, logger_context,
                                rz_orientation, rotation_offset_between_pickup_and_drop_place):
    """
    Calculate the drop-off position for a workpiece on the placement plane.

    Args:
        match: The matched workpiece object
        centroid: Original centroid coordinates
        orientation: Object orientation in degrees
        plane: Plane object for placement calculations
        pickup_height: Height at which the workpiece was picked up

    Returns:
        tuple: (drop_off_position, width, height, plane_updated)
    """

    # === LOGGING ===
    log_info_message(logger_context, f"Starting drop-off calculation for orientation: {orientation:.2f}°")
    log_info_message(logger_context, f"Input: centroid={centroid}, pickup_height={pickup_height}mm")

    # === FUNCTIONALITY ===
    # Get and rotate contour
    cnt = match.get_main_contour()
    cntObject = Contour(cnt)
    cntObject.rotate(-orientation, centroid)  # Align with X-axis

    # Calculate workpiece dimensions
    width, height, bboxCenter, minRect = calculate_workpiece_dimensions(cntObject)
    log_workpiece_dimensions(logger_context, width, height, bboxCenter, minRect, orientation)

    # === FUNCTIONALITY ===
    # Update the tallest contour for row spacing
    previous_tallest = plane.tallestContour
    if height > plane.tallestContour:
        plane.tallestContour = height

    targetPointX, targetPointY = calculate_target_drop_position(plane, width, height)
    log_calculated_drop_position(logger_context, targetPointX, targetPointY, width,height,plane)

    log_placement_calculations(logger_context,previous_tallest,height,plane,targetPointX,targetPointY)

    # Handle row overflow - move to next row if needed
    if targetPointX + (width / 2) > plane.xMax:
        # === FUNCTIONALITY ===
        plane.rowCount += 1
        plane.xOffset = 0
        plane.yOffset += plane.tallestContour + 50
        targetPointX = plane.xMin + (width / 2)
        targetPointY = plane.yMax - plane.yOffset
        plane.tallestContour = height  # Reset for new row

        # === LOGGING ===
        log_moving_to_next_row(logger_context,targetPointX,targetPointY,width,plane)

        # === FUNCTIONALITY ===
        # Check vertical bounds
        if targetPointY - (height / 2) < plane.yMin:
            # === LOGGING ===
            log_info_message(logger_context, "❌ PLANE FULL: Cannot fit more workpieces vertically")

            # === FUNCTIONALITY ===
            plane.isFull = True
            return None, width, height, plane

    # === FUNCTIONALITY ===
    # Position the contour at target location
    translation_x = targetPointX - bboxCenter[0]
    translation_y = targetPointY - bboxCenter[1]
    cntObject.translate(translation_x, translation_y)
    newCentroid = cntObject.getCentroid()

    # Calculate final drop-off position
    if gripper == Gripper.DOUBLE:
        drop_off_rz = -90
    else:

        drop_off_rz = 0
    drop_off_position1 = [newCentroid[0], newCentroid[1], pickup_height + 50, 180, 0, drop_off_rz]
    drop_off_position2 = [newCentroid[0], newCentroid[1], pickup_height + 20, 180, 0, drop_off_rz]

    # Update offset for next contour
    plane.xOffset += width + plane.spacing

    # === LOGGING ===
    log_info_message(logger_context, f"Translating contour by: ({translation_x:.2f}, {translation_y:.2f}) mm")
    log_info_message(logger_context, f"FINAL DROP-OFF:")
    log_info_message(logger_context, f"  ├─ Translated centroid: ({newCentroid[0]:.2f}, {newCentroid[1]:.2f}) mm")
    log_info_message(logger_context, f"  ├─ Drop height: {pickup_height + 10} mm")
    log_info_message(logger_context,
                     f"  └─ Rotation: {drop_off_rz}° ({rz_orientation}° - {rotation_offset_between_pickup_and_drop_place}°)")
    log_info_message(logger_context, f"Updated X offset for next piece: {plane.xOffset:.1f} mm")

    return drop_off_position1, drop_off_position2, width, height, plane, cntObject.get()
