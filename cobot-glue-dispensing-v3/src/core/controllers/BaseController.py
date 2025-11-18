import traceback
from abc import abstractmethod

from core.controllers.IController import IController


class BaseController(IController):

    def __init__(self):
        self._handlers = {}


    def register_handler(self, endpoint, handler):
        print(f"Registering handler for endpoint: {endpoint}")
        self._handlers[endpoint] = handler

    @abstractmethod
    def _initialize_handlers(self):
        """
        Subclasses MUST implement this method to register their endpoint handlers.
        """
        pass

    def handle(self, request, parts=None, data=None):
        # First try static handlers
        handler = self._handlers.get(request)

        # If no static handler, fallback to dynamic registry
        if handler is None and hasattr(self, "_dynamic_handler_resolver"):
            handler = self._dynamic_handler_resolver(request)

        if handler is None:
            raise ValueError(f"No handler registered for: {request}")

        try:
            if handler.__code__.co_argcount == 1:
                return handler()
            else:
                return handler(data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"Error handling '{request}': {e}"}