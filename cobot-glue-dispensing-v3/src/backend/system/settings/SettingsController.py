import traceback

from core.application.interfaces.application_settings_interface import ApplicationSettingsRegistry
from core.controllers.BaseController import BaseController
from communication_layer.api.v1 import Constants
from communication_layer.api.v1.Response import Response
import communication_layer.api.v1.endpoints.settings_endpoints as settings_endpoints

from backend.system.settings.SettingsService import SettingsService
from core.services.vision.VisionService import VisionServiceSingleton


class SettingsController(BaseController):
    """
    Controller for managing system settings via API requests.

    Supports:
        - Core settings (robot and camera)
        - Application-specific settings through registry
        - Generic settings routing
        - Dynamic endpoint handling
    """

    def __init__(self, settingsService: SettingsService, settings_registry: ApplicationSettingsRegistry):
        self.settingsService = settingsService
        self.settings_registry = settings_registry
        super().__init__()
        self._initialize_handlers()

        # Dynamic resolver
        self._dynamic_handler_resolver = self._resolve_dynamic_handler
    # ============================================================
    # REGISTER HANDLERS
    # ============================================================
    def _initialize_handlers(self):
        # ------------------------------
        # CORE SETTINGS - GET
        # ------------------------------
        self.register_handler(
            settings_endpoints.SETTINGS_ROBOT_GET,
            lambda data=None: self._handleGet("robot")
        )
        self.register_handler(
            settings_endpoints.SETTINGS_CAMERA_GET,
            lambda data=None: self._handleGet("camera")
        )
        self.register_handler(
            settings_endpoints.SETTINGS_GET,
            lambda data=None: self._handleGet("general")
        )

        # ------------------------------
        # CORE SETTINGS - SET / UPDATE
        # ------------------------------
        self.register_handler(
            settings_endpoints.SETTINGS_ROBOT_SET,
            lambda data=None: self._handleSet("robot", data)
        )
        self.register_handler(
            settings_endpoints.SETTINGS_CAMERA_SET,
            lambda data=None: self._handleSet("camera", data)
        )
        self.register_handler(
            settings_endpoints.SETTINGS_UPDATE,
            lambda data=None: self._handleSet("general", data)
        )

        # ------------------------------
        # APPLICATION-SPECIFIC SETTINGS (dynamic)
        # ------------------------------
        for endpoint in self.settings_registry.get_all_endpoints():
            # Late-binding safe: create closure for each endpoint
            self.register_handler(
                endpoint,
                (lambda ep: (lambda data=None: self._handle_application_settings(ep, data)))(endpoint)
            )

    # Called at request time for dynamic endpoints
    def _resolve_dynamic_handler(self, request):
        endpoint_mapping = self.settings_registry.get_all_endpoints()
        if request not in endpoint_mapping:
            return None
        ep = request
        return lambda data=None: self._handle_application_settings(ep, data)
    # =========================
    # INTERNAL HELPERS
    # =========================

    def _handle_application_settings(self, request, data=None):
        """
        Handle application-specific settings requests using the registry.
        
        Args:
            request: The request endpoint
            data: Optional data for SET requests
            
        Returns:
            dict: Response dictionary
        """
        try:
            # Get mapping of endpoints to settings types
            endpoint_mapping = self.settings_registry.get_all_endpoints()
            
            if request not in endpoint_mapping:
                return Response(
                    Constants.RESPONSE_STATUS_ERROR,
                    message=f"Unknown settings endpoint: {request}"
                ).to_dict()
            
            settings_type = endpoint_mapping[request]
            
            try:
                handler = self.settings_registry.get_handler(settings_type)
            except KeyError:
                return Response(
                    Constants.RESPONSE_STATUS_ERROR,
                    message=f"Settings handler not found for type: {settings_type}"
                ).to_dict()
            
            # Determine if this is a GET or SET operation based on data presence
            if data is None:
                # GET operation
                result_data = handler.handle_get_settings()
                return Response(
                    Constants.RESPONSE_STATUS_SUCCESS,
                    message="Success",
                    data=result_data
                ).to_dict()
            else:
                # SET operation
                success, message = handler.handle_set_settings(data)
                if success:
                    return Response(
                        Constants.RESPONSE_STATUS_SUCCESS,
                        message=message
                    ).to_dict()
                else:
                    return Response(
                        Constants.RESPONSE_STATUS_ERROR,
                        message=message
                    ).to_dict()
                    
        except Exception as e:
            traceback.print_exc()
            return Response(
                Constants.RESPONSE_STATUS_ERROR,
                message=f"Error handling application settings: {e}"
            ).to_dict()

    def _handleGet(self, resource):
        """
        Get settings for a given domain.
        """
        try:
            # Map lowercase resource names to proper constants
            resource_map = {
                "robot": Constants.REQUEST_RESOURCE_ROBOT,
                "camera": Constants.REQUEST_RESOURCE_CAMERA
            }
            
            # Use mapped resource if available, otherwise use as-is (for application settings)
            actual_resource = resource_map.get(resource, resource)
            
            data = self.settingsService.get_settings_by_resource(actual_resource)
            if data is not None:
                return Response(Constants.RESPONSE_STATUS_SUCCESS, message="Success", data=data).to_dict()
            return Response(Constants.RESPONSE_STATUS_ERROR, message=f"Error getting {resource} settings").to_dict()
        except Exception as e:
            traceback.print_exc()
            return Response(Constants.RESPONSE_STATUS_ERROR, message=f"Error retrieving {resource} settings: {e}").to_dict()

    def _handleSet(self, resource, data):
        """
        Set/update settings for a given domain.
        """
        if data is None:
            # This is a GET request, nothing to update
            return Response(
                Constants.RESPONSE_STATUS_ERROR,
                message=f"No data provided for setting {resource} settings"
            ).to_dict()

        try:
            print(f"SettingsController._handleSet: resource={resource}, data={data}")
            self.settingsService.updateSettings(data)

            # Update camera settings separately
            if resource == "camera":
                result, message = VisionServiceSingleton().get_instance().updateCameraSettings(data)
                if not result:
                    return Response(Constants.RESPONSE_STATUS_ERROR,
                                    message=f"Error saving camera settings: {message}").to_dict()

            return Response(
                Constants.RESPONSE_STATUS_SUCCESS,
                message=f"{resource.capitalize()} settings saved successfully"
            ).to_dict()

        except Exception as e:
            traceback.print_exc()
            return Response(
                Constants.RESPONSE_STATUS_ERROR,
                message=f"Error saving {resource} settings: {e}"
            ).to_dict()
