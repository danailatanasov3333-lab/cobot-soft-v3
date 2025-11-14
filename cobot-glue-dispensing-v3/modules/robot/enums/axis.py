from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class RobotAxis(Enum):
    """
    Enum representing robot movement axes.
    """
    X = 1
    Y = 2
    Z = 3
    RX = 4
    RY = 5
    RZ = 6

    def __str__(self):
        return self.name

    @staticmethod
    def get_by_string(name:str):
        """
        Retrieve an Axis enum value by its string representation.

        Args:
            name (str): The string representation of the axis.

        Returns:
            RobotAxis: The corresponding Axis enum value.

        Raises:
            ValueError: If the string does not match any Axis enum.
        """
        try:
            return RobotAxis[name.upper()]
        except KeyError:
            raise ValueError(f"Invalid axis name: {name}")

class Direction(Enum):
    """
       Enum representing movement directions along an axis.
       """
    MINUS = -1
    PLUS = 1

    def __str__(self):
        return self.name

    @staticmethod
    def get_by_string(name:str):
        try:
            return Direction[name.upper()]
        except KeyError:
            raise ValueError(f"Invalid Direction name: {name}")

class ImageAxis(Enum):
    X = auto()
    Y = auto()

@dataclass
class AxisMapping:
    image_axis: ImageAxis
    direction: Direction

    def apply(self, dx_img: float, dy_img: float) -> float:
        """Return the robot movement along THIS robot axis."""
        img_value = dx_img if self.image_axis == ImageAxis.X else dy_img
        return img_value * self.direction.value

@dataclass
class AxisMapping:
    image_axis: ImageAxis
    direction: Direction

    def apply(self, dx_img: float, dy_img: float) -> float:
        """Return the robot movement along THIS robot axis."""
        img_value = dx_img if self.image_axis == ImageAxis.X else dy_img
        return img_value * self.direction.value


@dataclass
class ImageToRobotMapping:
    robot_x: AxisMapping
    robot_y: AxisMapping

    def map(self, camera_x: float, camera_y: float) -> Tuple[float, float]:
        """
        Map image offsets to robot coordinate offsets based on this mapping.

        Args:
            camera_x (float): Offset along image X axis relative to center (mm).
            camera_y (float): Offset along image Y axis relative to center (mm).

        Returns:
            Tuple[float, float]: (robot_x_offset, robot_y_offset) in mm
        """
        # Map robot X
        if self.robot_x.image_axis == ImageAxis.X:
            mapped_x = camera_x
        else:  # ImageAxis.Y
            mapped_x = camera_y

        if self.robot_x.direction == Direction.MINUS:
            mapped_x = -mapped_x

        # Map robot Y
        if self.robot_y.image_axis == ImageAxis.Y:
            mapped_y = camera_y
        else:  # ImageAxis.X
            mapped_y = camera_x

        if self.robot_y.direction == Direction.MINUS:
            mapped_y = -mapped_y

        return mapped_x, mapped_y
