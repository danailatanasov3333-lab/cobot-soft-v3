import json
import os
import logging

class SettingsRepositoryError(Exception):
    """Custom exception for SettingsJsonRepository errors."""
    pass

class SettingsJsonRepository:

    def __init__(self, file_path: str,settings_object):
        self.file_path = file_path
        self.settings_object = settings_object
        self.logger = logging.getLogger(self.__class__.__name__)

    def save(self):
        """
        Persist the repository's associated settings object to its configured file path.

        Uses:
            self.file_path (str): target JSON file path
            self.settings_object: object that implements .to_dict()
        """
        try:
            # Create the directory for the JSON file if it doesn't exist
            if self.file_path:
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            else:
                raise SettingsRepositoryError("File path is not set.")

            settings_data = self.settings_object.to_dict()

            with open(self.file_path, 'w') as f:
                json.dump(settings_data, f, indent=4)
            self.logger.info(f"Settings saved to {self.file_path}.")

        except Exception as e:
            self.logger.error(f"Error saving settings to {self.file_path}: {e}")
            import traceback
            traceback.print_exc()

    def load(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)

            self.logger.debug(f"Settings loaded from {self.file_path} Settings: {settings_data}.")

            # Support both: instance.from_dict(mutates) and class.from_dict(returns new instance)
            result = None
            if hasattr(self.settings_object, 'from_dict'):
                result = self.settings_object.from_dict(settings_data)

            # If from_dict returned a new instance of the expected type, replace our reference
            if result is not None and not result is self.settings_object:
                # update internal reference to the new instance
                self.settings_object = result
                return result

            # otherwise assume in-place mutation has happened
            return self.settings_object

        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error loading settings from {self.file_path}: {e}")
            self.logger.info(f"Using default values for {type(self.settings_object).__name__}.")
            return self.settings_object

