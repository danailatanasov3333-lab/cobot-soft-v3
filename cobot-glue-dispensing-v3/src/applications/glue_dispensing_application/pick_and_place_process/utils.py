import math


def rotate_offsets(x_offset, y_offset, orientation_radians):
    """
    Rotate x,y offsets by given orientation angle

    Args:
        x_offset: Original X offset
        y_offset: Original Y offset
        orientation_radians: Rotation angle in radians

    Returns:
        tuple: (rotated_x_offset, rotated_y_offset)
    """
    cos_theta = math.cos(orientation_radians)
    sin_theta = math.sin(orientation_radians)

    # 2D rotation matrix transformation
    rotated_x = x_offset * cos_theta - y_offset * sin_theta
    rotated_y = x_offset * sin_theta + y_offset * cos_theta

    return rotated_x, rotated_y