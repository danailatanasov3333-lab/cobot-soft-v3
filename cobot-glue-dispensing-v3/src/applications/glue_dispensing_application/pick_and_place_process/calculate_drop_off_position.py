from modules.shared.core.ContourStandartized import Contour
from modules.shared.tools.enums.Gripper import Gripper
from modules.utils.custom_logging import log_if_enabled, LoggingLevel


def calculate_drop_off_position(match, centroid, orientation, plane, pickup_height, gripper,logging_enabled,logger,rz_orientation,rotation_offset_between_pickup_and_drop_place):
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
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"Starting drop-off calculation for orientation: {orientation:.2f}°")
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Input: centroid={centroid}, pickup_height={pickup_height}mm")

    # === FUNCTIONALITY ===
    # Get and rotate contour
    cnt = match.get_main_contour()
    cntObject = Contour(cnt)
    cntObject.rotate(-orientation, centroid)  # Align with X-axis

    # Calculate workpiece dimensions
    minRect = cntObject.getMinAreaRect()
    bboxCenter = (minRect[0][0], minRect[0][1])
    width = minRect[1][0]
    height = minRect[1][1]
    if width < height:
        width, height = height, width

    # === LOGGING ===
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Rotating contour by {-orientation:.2f}° to align with X-axis")
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   "Swapped width/height to ensure width >= height" if width != minRect[1][0] else "")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"WORKPIECE DIMENSIONS:")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"  ├─ Width:  {width:.2f} mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"  ├─ Height: {height:.2f} mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"  └─ Bbox center: ({bboxCenter[0]:.2f}, {bboxCenter[1]:.2f})")

    # === FUNCTIONALITY ===
    # Update the tallest contour for row spacing
    previous_tallest = plane.tallestContour
    if height > plane.tallestContour:
        plane.tallestContour = height

    # Calculate target placement position
    targetPointX = plane.xOffset + plane.xMin + (width / 2)
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Calculated target X position: {targetPointX:.1f} = {plane.xOffset} + {plane.xMin}+{width / 2} mm")
    targetPointY = plane.yMax - plane.yOffset - (height / 2)
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Calculated target Y position: {targetPointY:.1f} = {plane.yOffset} + {plane.yMax}+{height / 2} mm")

    # === LOGGING ===
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Updated tallest contour: {previous_tallest:.1f} → {height:.1f} mm" if height > previous_tallest else "")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"PLACEMENT CALCULATION:")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Current offset: ({plane.xOffset:.1f}, {plane.yOffset:.1f}) mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Target point:  ({targetPointX:.1f}, {targetPointY:.1f}) mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"  └─ Plane bounds:  ({plane.xMin}-{plane.xMax}, {plane.yMin}-{plane.yMax}) mm")

    # === FUNCTIONALITY ===
    # Handle row overflow - move to next row if needed
    if targetPointX + (width / 2) > plane.xMax:
        # === LOGGING ===
        log_if_enabled(logging_enabled, logger, LoggingLevel.WARNING, f"⚠️  Width exceeded, moving to next row")
        log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                       f"Exceeded by: {(targetPointX + width / 2) - plane.xMax:.1f} mm")

        # === FUNCTIONALITY ===
        plane.rowCount += 1
        plane.xOffset = 0
        plane.yOffset += plane.tallestContour + 50
        targetPointX = plane.xMin + (width / 2)
        targetPointY = plane.yMax - plane.yOffset
        plane.tallestContour = height  # Reset for new row

        # === LOGGING ===
        log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"NEW ROW {plane.rowCount}:")
        log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                       f"  ├─ Reset to: ({targetPointX:.1f}, {targetPointY:.1f}) mm")
        log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                       f"  └─ Row spacing: {plane.tallestContour + 50:.1f} mm")

        # === FUNCTIONALITY ===
        # Check vertical bounds
        if targetPointY - (height / 2) < plane.yMin:
            # === LOGGING ===
            log_if_enabled(logging_enabled, logger, LoggingLevel.ERROR,
                           "❌ PLANE FULL: Cannot fit more workpieces vertically")
            log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                           f"Needed: {targetPointY - height / 2:.1f}, Available: {plane.yMin}")

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
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Translating contour by: ({translation_x:.2f}, {translation_y:.2f}) mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"FINAL DROP-OFF:")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"  ├─ Translated centroid: ({newCentroid[0]:.2f}, {newCentroid[1]:.2f}) mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO, f"  ├─ Drop height: {pickup_height + 10} mm")
    log_if_enabled(logging_enabled, logger, LoggingLevel.INFO,
                   f"  └─ Rotation: {drop_off_rz}° ({rz_orientation}° - {rotation_offset_between_pickup_and_drop_place}°)")
    log_if_enabled(logging_enabled, logger, LoggingLevel.DEBUG,
                   f"Updated X offset for next piece: {plane.xOffset:.1f} mm")

    return drop_off_position1, drop_off_position2, width, height, plane, cntObject.get()
