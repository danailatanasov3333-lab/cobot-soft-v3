import logging
import os

from applications.glue_dispensing_application.controllers.glue_robot_controller import GlueRobotController
from applications.glue_dispensing_application.controllers.glue_workpiece_controller import GlueWorkpieceController
from applications.glue_dispensing_application.repositories.workpiece.GlueWorkPieceRepositorySingleton import \
    GlueWorkPieceRepositorySingleton
from applications.glue_dispensing_application.services.workpiece.glue_workpiece_service import GlueWorkpieceService
from communication_layer.api_gateway.dispatch.main_router import RequestHandler
from core.application.interfaces.application_settings_interface import ApplicationSettingsRegistry
from core.application.ApplicationContext import set_current_application, get_core_settings_path
from core.controllers.vision.camera_system_controller import CameraSystemController
from core.services.robot_service.impl.RobotStateManager import RobotStateManager
from core.services.robot_service.impl.base_robot_service import RobotService
from core.services.robot_service.impl.robot_monitor.fairino_monitor import FairinoRobotMonitor
from frontend.core.utils.localization import setup_localization

# Import SystemStateManager and related components
from core.system_state_management import SystemStateManager, SYSTEM_STATE_PRIORITY, ServiceState, SystemState, ServiceRegistry
from communication_layer.api.v1.topics import RobotTopics, VisionTopics


from modules.shared.MessageBroker import MessageBroker
from communication_layer.api_gateway.DomesticRequestSender import DomesticRequestSender
from core.application_factory import create_application_factory
from core.base_robot_application import ApplicationType

# IMPORT CONTROLLERS
from core.controllers.settings.SettingsController import SettingsController

# IMPORT SERVICES
from core.services.settings.SettingsService import SettingsService
from core.services.vision.VisionService import VisionServiceSingleton
from modules.utils import PathResolver

setup_localization()

if os.environ.get("WAYLAND_DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

logging.basicConfig(
    level=logging.CRITICAL,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
)

# sensorPublisher = SensorPublisher()

API_VERSION = 1
newGui = True
testRobot = False
if newGui:
    from frontend.core.runPlUi import PlGui
else:
    pass

if __name__ == "__main__":

    # Choose which application to run - CHANGE THIS LINE TO SWITCH APPS
    # ApplicationFactory will automatically create the correct robot based on metadata:
    # - GLUE_DISPENSING uses Fairino robot
    # - PAINT_APPLICATION uses ZeroError robot
    # - TEST_APPLICATION uses test robot

    #SELECTED_APP_TYPE = ApplicationType.GLUE_DISPENSING  # Uses Fairino robot
    SELECTED_APP_TYPE = ApplicationType.PAINT_APPLICATION  # Uses ZeroError robot
    # SELECTED_APP_TYPE = ApplicationType.TEST_APPLICATION  # Uses test robot

    # Set application context using the enum directly
    set_current_application(SELECTED_APP_TYPE)

    # Global registry instance
    settings_registry = ApplicationSettingsRegistry()

    # Use application-specific core settings paths (now that context is set)
    settings_file_paths = {
        "camera": get_core_settings_path("camera_settings.json", create_if_missing=True) or PathResolver.get_settings_file_path("camera_settings.json"),
        "robot_config": get_core_settings_path("robot_config.json", create_if_missing=True) or PathResolver.get_settings_file_path("robot_config.json"),
    }

    settings_service = SettingsService(settings_file_paths=settings_file_paths,settings_registry=settings_registry)

    # ROBOT INITIALIZATION NOW HANDLED BY APPLICATION FACTORY
    # Robot and robot service will be created dynamically based on application metadata
    robot_config = settings_service.get_robot_config()

    # INIT CAMERA SERVICE
    cameraService = VisionServiceSingleton().get_instance()

    # INIT GLUE WORKPIECE REPOSITORY AND SERVICE
    repository = GlueWorkPieceRepositorySingleton().get_instance()
    workpieceService = GlueWorkpieceService(repository=repository)

    # CREATE A DEFAULT ROBOT SERVICE FOR SYSTEM INITIALIZATION
    # Import factories
    from core.model.robot.robot_factory import RobotFactory
    from core.services.robot_service.impl.robot_monitor.robot_monitor_factory import RobotMonitorFactory
    from core.base_robot_application import ApplicationType
    from core.model.robot.robot_types import RobotType

    # Robot type is determined by the selected application or testRobot flag
    if testRobot:
        robot_type = RobotType.TEST
    elif SELECTED_APP_TYPE == ApplicationType.GLUE_DISPENSING:
        robot_type = RobotType.FAIRINO
    elif SELECTED_APP_TYPE == ApplicationType.PAINT_APPLICATION:
        robot_type = RobotType.ZERO_ERROR
    elif SELECTED_APP_TYPE == ApplicationType.TEST_APPLICATION:
        robot_type = RobotType.TEST
    else:
        robot_type = RobotType.FAIRINO  # Default fallback

    # Create robot using factory (handles ROS2 initialization automatically)
    default_robot = RobotFactory.create_robot(robot_type, robot_config.robot_ip)

    # Create robot monitor using factory
    robot_monitor = RobotMonitorFactory.create_monitor(robot_type, robot_config.robot_ip, cycle_time=0.03)
    robot_state_manager = RobotStateManager(robot_monitor=robot_monitor)
    robotService = RobotService(default_robot, settings_service, robot_state_manager)

    # INIT SYSTEM STATE MANAGER
    # Create and configure the system-wide state manager
    service_registry = ServiceRegistry()
    service_registry.register_service(robotService.service_id,RobotTopics.SERVICE_STATE,ServiceState.UNKNOWN)
    service_registry.register_service(cameraService.service_id,VisionTopics.SERVICE_STATE,ServiceState.UNKNOWN)
    system_state_manager = SystemStateManager(SYSTEM_STATE_PRIORITY, MessageBroker(),service_registry)

    # Subscribe to system state updates (optional - for logging/debugging)
    def on_system_state_change(state: SystemState):
        print(f"[Main] System state changed to: {state.value}")

    system_state_manager.subscribers.append(on_system_state_change)
    system_state_manager.start_state_publisher_thread()

    # INIT CONTROLLERS
    settingsController = SettingsController(settings_service,settings_registry)
    cameraSystemController = CameraSystemController(cameraService)
    workpieceController = GlueWorkpieceController(workpieceService)
    robotController = GlueRobotController(robotService)

    # INIT APPLICATION FACTORY
    application_factory = create_application_factory(
        vision_service=cameraService,
        settings_service=settings_service,
        workpiece_service=workpieceService,
        robot_service=robotService,
        settings_registry=settings_registry,
        service_registry= service_registry,
        auto_register=True
    )

    # GET CURRENT APPLICATION (uses the same app type selected above)
    current_application = application_factory.switch_application(SELECTED_APP_TYPE)

    # INIT REQUEST HANDLER
    if API_VERSION == 1:
        requestHandler = RequestHandler(current_application, settingsController, cameraSystemController,
                                        workpieceController, robotController, application_factory)

    else:
        raise ValueError("Unsupported API_VERSION. Please set to 1")

    logging.info("Request Handler initialized")
    """GUI RELATED INITIALIZATIONS"""

    # INIT DOMESTIC REQUEST SENDER
    domesticRequestSender = DomesticRequestSender(requestHandler)
    logging.info("Domestic Request Sender initialized")
    # INIT MAIN WINDOW

    if API_VERSION == 1:
        from frontend.core.ui_controller.UIController import UIController
        controller = UIController(domesticRequestSender)
    else:
        raise ValueError("Unsupported API_VERSION. Please set to 1")


    from frontend.core.runPlUi import PlGui
    gui = PlGui(controller=controller)

    try:
        gui.start()
    finally:
        # Clean up ROS2 when GUI exits (handled by RobotFactory)
        from core.model.robot.robot_factory import RobotFactory
        RobotFactory.shutdown_ros2()
