import json
import os


from backend.system.settings.CameraSettings import CameraSettings
from backend.system.settings.SettingsJsonRepository import SettingsJsonRepository
from backend.system.settings.robotConfig.robotConfigModel import RobotConfig, get_default_config

from core.application.interfaces.application_settings_interface import ApplicationSettingsRegistry

from modules.shared.v1 import Constants
from backend.system.settings.enums.CameraSettingKey import CameraSettingKey
import logging



class SettingsService:
    """
      Service responsible for managing core system settings (camera and robot).
      
      Application-specific settings are now managed by their respective applications
      through the ApplicationSettingsInterface and are accessible via the settings registry.

      This class handles:
      - Loading and saving core settings (camera and robot) to JSON files
      - Providing settings objects for external access
      - Updating core settings based on external input
      - Routing application-specific settings to registered handlers

      Attributes:
          settings_dir (str): The root directory where settings JSON files are stored.
          settings_file_paths (dict): File paths for core settings files.
          settings_objects (dict): Dictionary storing core settings objects.
      """


    def __init__(self, settings_file_paths, settings_registry: ApplicationSettingsRegistry):
        """
               Initialize the SettingsService by creating and loading core settings (camera and robot).
               Application-specific settings are managed by their respective applications.
               """
        self.settings_file_paths = settings_file_paths
        self.settings_registry = settings_registry
        # robot_config_file_path is still used by existing robot config logic
        self.robot_config_file_path = settings_file_paths.get("robot_config") if settings_file_paths else None
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize settings directory from the first file path
        if settings_file_paths:
            first_path = next(iter(settings_file_paths.values()))
            if first_path:
                self.settings_dir = os.path.dirname(first_path)
            else:
                self.settings_dir = "settings"
        else:
            self.settings_dir = "settings"

        # Initialize a dictionary to store core settings objects
        self.settings_objects = {}

        # Initialize and load core settings only
        self.camera_settings = CameraSettings()

        # Store core settings in the settings dictionary
        self.settings_objects["camera"] = self.camera_settings

        # Create a placeholder RobotConfig instance (use defaults) and register it so a repo will be created
        # We'll load the actual values via the repository afterwards which may return a new RobotConfig instance.
        try:
            self.robot_config = get_default_config()
        except Exception:
            # fallback: create a minimal RobotConfig-like empty object if get_default_config fails
            self.robot_config = RobotConfig.from_dict({})

        self.settings_objects["robot_config"] = self.robot_config

        # Create repository instances for each settings object (may receive None file paths)
        self.settings_repos = {}
        for key, settings_obj in self.settings_objects.items():
            file_path = self.settings_file_paths.get(key) if self.settings_file_paths else None
            # Pass the settings object instance to the repository
            self.settings_repos[key] = SettingsJsonRepository(file_path=file_path, settings_object=settings_obj)

        # Now load robot_config via its repository (the repository handles both in-place mutation and factory returns)
        robot_repo = self.settings_repos.get("robot_config")
        if robot_repo:
            try:
                loaded_robot = robot_repo.load()
                if loaded_robot is not None and loaded_robot is not self.robot_config:
                    self.robot_config = loaded_robot
                    robot_repo.settings_object = self.robot_config
            except Exception:
                self.logger.exception("Failed to load robot_config via repository; using default robot_config")

        # Load core settings from JSON files, or use default values if files do not exist
        self.load_all_settings()

    def get_settings_by_resource(self, key):
        """
        Retrieve settings data based on the key provided.

        Args:
            key (str): The key corresponding to the settings type ("camera", "robot", or application type).

        Returns:
            dict: The settings data as a dictionary.
        """
        # Handle core settings
        if key == Constants.REQUEST_RESOURCE_CAMERA:
            # For camera settings, return the nested JSON structure
            data = self.camera_settings.to_dict()
            self.logger.debug("from Settings Service: %s", data)
            return data

        # Handle application-specific settings through registry
        # Convert resource names to lowercase for registry lookup
        resource_map = {
            "Glue": "glue",
            "Paint": "paint",
        }

        settings_type = resource_map.get(key, key.lower())

        if self.settings_registry.is_type_registered(settings_type):
            try:
                handler = self.settings_registry.get_handler(settings_type)
                return handler.handle_get_settings()
            except KeyError:
                self.logger.warning(f"Settings handler not found for type: {settings_type}")
                return {}
        else:
            self.logger.warning(f"Unknown settings key: {key}")
            return {}

    def save_all_settings(self):
        """Save all settings to their respective files."""
        for key, repo in self.settings_repos.items():
            # delegate to repository - repository will handle missing file path errors
            try:
                repo.save()
            except Exception:
                # repository logs its own errors; continue with other repos
                continue

    def load_all_settings(self):
        """Load all settings from their respective JSON files. Use default values if file doesn't exist."""
        for key, repo in self.settings_repos.items():
            filename = self.settings_file_paths.get(key) if self.settings_file_paths else None
            self.logger.info(f"Loading {key} settings from path: {filename}")
            if filename and os.path.exists(filename):
                self.logger.info(f"File exists, loading settings from: {filename}")
                try:
                    repo.load()
                except Exception:
                    self.logger.exception(f"Failed to load settings for {key} from {filename}")
            else:
                self.logger.info(f"{filename} not found. Using default values for {key} settings.")
                # Automatically save default settings to the missing file
                try:
                    repo.save()
                except Exception:
                    self.logger.exception(f"Failed to save default settings for {key} to {filename}")

    def updateSettings(self, settings: dict):
        """
               Update the relevant settings object based on the header type.

               Args:
                   settings (dict): A dictionary containing settings data and a "header" field indicating the type.

               Raises:
                   ValueError: If the "header" key is missing or invalid.
               """
        print(f"SettingsService.updateSettings called with: {settings}")
        print(f"Settings keys: {list(settings.keys()) if isinstance(settings, dict) else 'Not a dict'}")

        if 'header' not in settings:
            raise ValueError("Settings dictionary must contain a 'header' key")

        header = settings['header']

        if header == Constants.REQUEST_RESOURCE_CAMERA:
            self.updateCameraSettings(settings)
            return

        # Handle application-specific settings through registry
        # Convert resource names to lowercase for registry lookup
        resource_map = {
            "Glue": "glue"
        }

        settings_type = resource_map.get(header, header.lower())

        if self.settings_registry.is_type_registered(settings_type):
            try:
                handler = self.settings_registry.get_handler(settings_type)
                success, message = handler.handle_set_settings(settings)
                if not success:
                    raise ValueError(f"Failed to update {header} settings: {message}")
            except KeyError:
                raise ValueError(f"Settings handler not found for type: {settings_type}")
        else:
            raise ValueError(f"Invalid or unsupported settings header: {header}")

    def get_camera_settings(self) -> CameraSettings:
        return self.camera_settings


    def get_robot_config(self) -> RobotConfig:
        return self.robot_config

    def reload_robot_config(self):
        """Reload the robot configuration from its JSON file."""
        robot_repo = self.settings_repos.get("robot_config")
        if robot_repo:
            try:
                loaded_robot = robot_repo.load()
                if loaded_robot is not None and loaded_robot is not self.robot_config:
                    self.robot_config = loaded_robot
                    robot_repo.settings_object = self.robot_config
                self.logger.info("Robot configuration reloaded successfully.")
            except Exception:
                self.logger.exception("Failed to reload robot configuration from file.")
        else:
            self.logger.warning("Robot configuration repository not found; cannot reload.")

    def updateCameraSettings(self, settings: dict):
        self.logger.info(f"Updating Camera Settings: {settings}")
        """
              Update camera-specific settings and persist them to file.

              Args:
                  settings (dict): Dictionary containing camera settings data.
              """
        self._update_camera_settings_from_data(settings)
        repo = self.settings_repos.get("camera")
        repo.save()


    def _update_camera_settings_from_data(self, settings: dict):
        """
        Update camera settings from either flat or nested dictionary format.
        This handles updates from both UI changes and nested JSON structures.
        """
        # Handle flat keys directly in the root
        if CameraSettingKey.INDEX.value in settings:
            self.camera_settings.set_camera_index(settings.get(CameraSettingKey.INDEX.value))
        if CameraSettingKey.WIDTH.value in settings:
            self.camera_settings.set_width(settings.get(CameraSettingKey.WIDTH.value))
        if CameraSettingKey.HEIGHT.value in settings:
            self.camera_settings.set_height(settings.get(CameraSettingKey.HEIGHT.value))
        if CameraSettingKey.SKIP_FRAMES.value in settings:
            self.camera_settings.set_skip_frames(settings.get(CameraSettingKey.SKIP_FRAMES.value))
        if CameraSettingKey.CAPTURE_POS_OFFSET.value in settings:
            self.camera_settings.set_capture_pos_offset(settings.get(CameraSettingKey.CAPTURE_POS_OFFSET.value))
        if CameraSettingKey.THRESHOLD.value in settings:
            self.camera_settings.set_threshold(settings.get(CameraSettingKey.THRESHOLD.value))
        if CameraSettingKey.THRESHOLD_PICKUP_AREA.value in settings:
            self.camera_settings.set_threshold_pickup_area(settings.get(CameraSettingKey.THRESHOLD_PICKUP_AREA.value))
        if CameraSettingKey.EPSILON.value in settings:
            self.camera_settings.set_epsilon(settings.get(CameraSettingKey.EPSILON.value))
        if CameraSettingKey.MIN_CONTOUR_AREA.value in settings:
            self.camera_settings.set_min_contour_area(settings.get(CameraSettingKey.MIN_CONTOUR_AREA.value))
        if CameraSettingKey.MAX_CONTOUR_AREA.value in settings:
            self.camera_settings.set_max_contour_area(settings.get(CameraSettingKey.MAX_CONTOUR_AREA.value))
        if CameraSettingKey.CONTOUR_DETECTION.value in settings:
            self.camera_settings.set_contour_detection(settings.get(CameraSettingKey.CONTOUR_DETECTION.value))
        if CameraSettingKey.DRAW_CONTOURS.value in settings:
            self.camera_settings.set_draw_contours(settings.get(CameraSettingKey.DRAW_CONTOURS.value))

        # Handle nested Preprocessing section
        if "Preprocessing" in settings:
            preprocessing = settings["Preprocessing"]
            if CameraSettingKey.GAUSSIAN_BLUR.value in preprocessing:
                self.camera_settings.set_gaussian_blur(preprocessing.get(CameraSettingKey.GAUSSIAN_BLUR.value))
            if CameraSettingKey.BLUR_KERNEL_SIZE.value in preprocessing:
                self.camera_settings.set_blur_kernel_size(preprocessing.get(CameraSettingKey.BLUR_KERNEL_SIZE.value))
            if CameraSettingKey.THRESHOLD_TYPE.value in preprocessing:
                self.camera_settings.set_threshold_type(preprocessing.get(CameraSettingKey.THRESHOLD_TYPE.value))
            if CameraSettingKey.DILATE_ENABLED.value in preprocessing:
                self.camera_settings.set_dilate_enabled(preprocessing.get(CameraSettingKey.DILATE_ENABLED.value))
            if CameraSettingKey.DILATE_KERNEL_SIZE.value in preprocessing:
                self.camera_settings.set_dilate_kernel_size(
                    preprocessing.get(CameraSettingKey.DILATE_KERNEL_SIZE.value))
            if CameraSettingKey.DILATE_ITERATIONS.value in preprocessing:
                self.camera_settings.set_dilate_iterations(preprocessing.get(CameraSettingKey.DILATE_ITERATIONS.value))
            if CameraSettingKey.ERODE_ENABLED.value in preprocessing:
                self.camera_settings.set_erode_enabled(preprocessing.get(CameraSettingKey.ERODE_ENABLED.value))
            if CameraSettingKey.ERODE_KERNEL_SIZE.value in preprocessing:
                self.camera_settings.set_erode_kernel_size(preprocessing.get(CameraSettingKey.ERODE_KERNEL_SIZE.value))
            if CameraSettingKey.ERODE_ITERATIONS.value in preprocessing:
                self.camera_settings.set_erode_iterations(preprocessing.get(CameraSettingKey.ERODE_ITERATIONS.value))

        # Handle nested Calibration section
        if "Calibration" in settings:
            calibration = settings["Calibration"]
            if CameraSettingKey.CHESSBOARD_WIDTH.value in calibration:
                self.camera_settings.set_chessboard_width(calibration.get(CameraSettingKey.CHESSBOARD_WIDTH.value))
            if CameraSettingKey.CHESSBOARD_HEIGHT.value in calibration:
                self.camera_settings.set_chessboard_height(calibration.get(CameraSettingKey.CHESSBOARD_HEIGHT.value))
            if CameraSettingKey.SQUARE_SIZE_MM.value in calibration:
                self.camera_settings.set_square_size_mm(calibration.get(CameraSettingKey.SQUARE_SIZE_MM.value))
            if "Skip frames" in calibration:  # Special mapping for nested calibration skip frames
                self.camera_settings.set_calibration_skip_frames(calibration.get("Skip frames"))
            if CameraSettingKey.CAPTURE_POS_OFFSET.value in calibration:
                self.camera_settings.set_capture_pos_offset(calibration.get(CameraSettingKey.CAPTURE_POS_OFFSET.value))

        # Handle nested Brightness Control section
        if "Brightness Control" in settings:
            brightness = settings["Brightness Control"]
            if CameraSettingKey.BRIGHTNESS_AUTO.value in brightness:
                self.camera_settings.set_brightness_auto(brightness.get(CameraSettingKey.BRIGHTNESS_AUTO.value))
            if CameraSettingKey.BRIGHTNESS_KP.value in brightness:
                self.camera_settings.set_brightness_kp(brightness.get(CameraSettingKey.BRIGHTNESS_KP.value))
            if CameraSettingKey.BRIGHTNESS_KI.value in brightness:
                self.camera_settings.set_brightness_ki(brightness.get(CameraSettingKey.BRIGHTNESS_KI.value))
            if CameraSettingKey.BRIGHTNESS_KD.value in brightness:
                self.camera_settings.set_brightness_kd(brightness.get(CameraSettingKey.BRIGHTNESS_KD.value))
            if CameraSettingKey.TARGET_BRIGHTNESS.value in brightness:
                self.camera_settings.set_target_brightness(brightness.get(CameraSettingKey.TARGET_BRIGHTNESS.value))

        # Handle nested Aruco section
        if "Aruco" in settings:
            aruco = settings["Aruco"]
            if "Enable detection" in aruco:  # Special mapping for nested ArUco enabled
                self.camera_settings.set_aruco_enabled(aruco.get("Enable detection"))
            if CameraSettingKey.ARUCO_DICTIONARY.value in aruco:
                self.camera_settings.set_aruco_dictionary(aruco.get(CameraSettingKey.ARUCO_DICTIONARY.value))
            if CameraSettingKey.ARUCO_FLIP_IMAGE.value in aruco:
                self.camera_settings.set_aruco_flip_image(aruco.get(CameraSettingKey.ARUCO_FLIP_IMAGE.value))

        # Handle flat keys that might be from UI updates (fallback for direct enum-based updates)
        preprocessing_keys = [
            CameraSettingKey.GAUSSIAN_BLUR, CameraSettingKey.BLUR_KERNEL_SIZE, CameraSettingKey.THRESHOLD_TYPE,
            CameraSettingKey.DILATE_ENABLED, CameraSettingKey.DILATE_KERNEL_SIZE, CameraSettingKey.DILATE_ITERATIONS,
            CameraSettingKey.ERODE_ENABLED, CameraSettingKey.ERODE_KERNEL_SIZE, CameraSettingKey.ERODE_ITERATIONS
        ]

        calibration_keys = [
            CameraSettingKey.CHESSBOARD_WIDTH, CameraSettingKey.CHESSBOARD_HEIGHT,
            CameraSettingKey.SQUARE_SIZE_MM, CameraSettingKey.CALIBRATION_SKIP_FRAMES
        ]

        brightness_keys = [
            CameraSettingKey.BRIGHTNESS_AUTO, CameraSettingKey.BRIGHTNESS_KP, CameraSettingKey.BRIGHTNESS_KI,
            CameraSettingKey.BRIGHTNESS_KD, CameraSettingKey.TARGET_BRIGHTNESS
        ]

        aruco_keys = [
            CameraSettingKey.ARUCO_ENABLED, CameraSettingKey.ARUCO_DICTIONARY, CameraSettingKey.ARUCO_FLIP_IMAGE
        ]

