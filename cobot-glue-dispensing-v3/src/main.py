
import logging
import os

from applications.glue_dispensing_application.workpiece.GlueWorkPieceRepositorySingleton import \
    GlueWorkPieceRepositorySingleton
from communication_layer.api_gateway.dispatch.main_router import RequestHandler
from core.application.interfaces.application_settings_interface import ApplicationSettingsRegistry
from frontend.core.utils.localization import setup_localization
from core.services.robot_service.RobotStateManager import RobotStateManager

setup_localization()


from modules.shared.MessageBroker import MessageBroker
from core.services.workpiece.WorkpieceService import WorkpieceService
from modules.shared.v1.DomesticRequestSender import DomesticRequestSender
from core.application_factory import create_application_factory
from core.base_robot_application import ApplicationType
from backend.system.SensorPublisher import SensorPublisher

from applications.glue_dispensing_application.controllers.RobotController import RobotController
from applications.glue_dispensing_application.services.robot_service.GlueRobotService import RobotService
# IMPORT CONTROLLERS
from backend.system.settings.SettingsController import SettingsController

# IMPORT SERVICES
from backend.system.settings.SettingsService import SettingsService


from applications.glue_dispensing_application.controllers.CameraSystemController import CameraSystemController
from core.services.vision.VisionService import VisionServiceSingleton
from applications.glue_dispensing_application.workpiece.WorkpieceController import WorkpieceController
from backend.system.utils import PathResolver


if os.environ.get("WAYLAND_DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

logging.basicConfig(
    level=logging.CRITICAL,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
)

sensorPublisher = SensorPublisher()



API_VERSION = 1
newGui = True
testRobot = False
if newGui:
    from frontend.core.runPlUi import PlGui
else:
    pass

if __name__ == "__main__":
    messageBroker = MessageBroker()
    # INIT SERVICES

    # Global registry instance
    settings_registry = ApplicationSettingsRegistry()
    camera_settings_path = PathResolver.get_settings_file_path("camera_settings.json")

    settings_file_paths = {
        "camera":camera_settings_path,
        "robot_config": PathResolver.get_settings_file_path("robot_config.json"),
    }

    settings_service = SettingsService(settings_file_paths=settings_file_paths,settings_registry=settings_registry)
    robot_config = settings_service.get_robot_config()
    if testRobot:
        from core.model.robot import TestRobotWrapper
        robot = TestRobotWrapper()
    else:
        from core.model.robot import fairino_robot
        robot = fairino_robot.FairinoRobot(robot_config.robot_ip)

    cameraService = VisionServiceSingleton().get_instance()

    repository = GlueWorkPieceRepositorySingleton().get_instance()
    workpieceService = WorkpieceService(repository=repository)

    robot_state_manager_cycle_time = 0.03  # 30ms cycle time
    robot_state_manager = RobotStateManager(robot_ip=robot_config.robot_ip,
                                            cycle_time=robot_state_manager_cycle_time)
    robotService = RobotService(robot, settings_service,robot_state_manager)

    # INIT CONTROLLERS
    settingsController = SettingsController(settings_service,settings_registry)
    cameraSystemController = CameraSystemController(cameraService)

    workpieceController = WorkpieceController(workpieceService)
    robotController = RobotController(robotService)

    # INIT APPLICATION FACTORY
    
    application_factory = create_application_factory(
        vision_service=cameraService,
        settings_service=settings_service,
        workpiece_service=workpieceService,
        robot_service=robotService,
        settings_registry=settings_registry,
        auto_register=True
    )
    
    # GET CURRENT APPLICATION (defaulting to glue dispensing)
    # current_application = application_factory.switch_application(ApplicationType.PAINT_APPLICATION)
    current_application = application_factory.switch_application(ApplicationType.GLUE_DISPENSING)

    # INIT REQUEST HANDLER
    if API_VERSION == 1:

        requestHandler = RequestHandler(current_application, settingsController, cameraSystemController,
                                        workpieceController, robotController, application_factory)


    else:
        raise ValueError("Unsupported API_VERSION. Please set to 1 or 2.")

    logging.info("Request Handler initialized")
    """GUI RELATED INITIALIZATIONS"""

    # INIT DOMESTIC REQUEST SENDER
    domesticRequestSender = DomesticRequestSender(requestHandler)
    logging.info("Domestic Request Sender initialized")
    # INIT MAIN WINDOW

    if API_VERSION == 1:
        from frontend.core.controller.Controller import Controller
        controller = Controller(domesticRequestSender)
    else:
        raise ValueError("Unsupported API_VERSION. Please set to 1")


    from frontend.core.runPlUi import PlGui
    gui = PlGui(controller=controller)
    gui.start()

