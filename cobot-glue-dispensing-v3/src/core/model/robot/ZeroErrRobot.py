from core.model.robot.IRobot import IRobot
from core.model.robot.enums.axis import Direction
from frontend.core.services.domain.RobotService import RobotAxis


class ZeroErrRobot(IRobot):
    """
      A wrapper for the real robot controller, abstracting motion and I/O operations.
      """
    def __init__(self, ip):
        """
               Initializes the robot wrapper and connects to the robot via RPC.

               Args:
                   ip (str): IP address of the robot controller.
               """
        """ADD IMPLEMENTATION HERE"""
        pass


    def move_cartesian(self,position, tool=0, user=0, vel=30, acc=30,blendR=0):
        """
              Moves the robot in Cartesian space.

              Args:
                  position (list): Target Cartesian position.
                  tool (int): Tool frame ID.
                  user (int): User frame ID.
                  vel (float): Velocity.
                  acc (float): Acceleration.

              Returns:
                  list: Result from robot move command.
              """

        """ADD IMPLEMENTATION HERE"""
        pass

    def move_liner(self,position, tool=0, user=0, vel=30, acc=30, blendR=0):
        """
              Executes a linear movement with blending.

              Args:
                  position (list): Target position.
                  tool (int): Tool frame ID.
                  user (int): User frame ID.
                  vel (float): Velocity.
                  acc (float): Acceleration.
                  blendR (float): Blend radius.

              Returns:
                  list: Result from robot linear move command.
                  """

        """ADD IMPLEMENTATION HERE"""
        pass

    def get_current_position(self):
        """
              Retrieves the current TCP (tool center point) position.

              Returns:
                  list: Current robot TCP pose.
              """
        """ADD IMPLEMENTATION HERE"""
        pass

    def get_current_velocity(self):
        """
               Retrieves the current linear speed of the TCP.

               Returns:
                   float: TCP composite speed.
               """

        """ADD IMPLEMENTATION HERE"""
        pass

    def get_current_acceleration(self):
        """
               Retrieves the current linear acceleration of the TCP.

               Returns:
                   float: TCP composite acceleration.
               """

        """ADD IMPLEMENTATION HERE"""
        pass

    def enable(self):
        """
               Enables the robot, allowing motion.
               """

        """ADD IMPLEMENTATION HERE"""
        pass

    def disable(self):
        """
             Disables the robot, preventing motion.
             """
        """ADD IMPLEMENTATION HERE"""
        pass




    def start_jog(self,axis:RobotAxis,direction:Direction,step,vel,acc):
        """
              Starts jogging the robot in a specified axis and direction.

              Args:
                  axis (Axis): Axis to jog.
                  direction (Direction): Jog direction (PLUS or MINUS).
                  step (float): Distance to move.
                  vel (float): Velocity of jog.
                  acc (float): Acceleration of jog.

              Returns:
                  object: Result of the StartJOG command.
              """
        """ADD IMPLEMENTATION HERE"""
        pass


    def stop_motion(self):
        """
               Stops all current robot motion.

               Returns:
                   object: Result of StopMotion command.
               """
        """ADD IMPLEMENTATION HERE"""
        pass
