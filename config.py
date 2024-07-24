import json
import os
import time

from easydict import EasyDict


class ConfigManager:
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    configPath = os.path.join(current_file_dir, './config/config.json')

    def __init__(self):
        self._config = self._load_config()

    @property
    def config(self):
        return EasyDict(self._config)

    def _load_config(self):
        if not os.path.exists(self.configPath):
            with open(self.configPath, 'w') as f:
                json.dump({
                    "client_id": "",
                    "client_secret": "",
                    "refresh_token": "",
                    "access_token": "",
                    "access_token_time": 0
                }, f, indent=4)

        with open(self.configPath, 'r') as f:
            return json.load(f)

    def _save_config(self):
        with open(self.configPath, 'w') as f:
            json.dump(self.config, f, indent=4)

    def update_config(self, key, value):
        self._config[key] = value
        self._save_config()


configManager = ConfigManager()


if __name__ == '__main__':
    print(configManager.config)
    configManager.update_config('client_id', 'iYCeC9g08h5vuP9UqvPHKKSVrKFXGa1v')
    configManager.update_config('client_secret', ' jXiFMOPVPCWlO2M5CwWQzffpNPaGTRBG')
    configManager.update_config('refresh_token', '122.2821ea596466cb6dbe818088afe84f21.YBJV0PKyEWOFsOC0zypaqSlwb0brkDTn0oPX73S._gmClQ')
    configManager.update_config('access_token', '121.2692197c2651cd75c5cbfea038413a02.Y7m39lVCjJtnmNyhDo8Mc2mjh5StLTkrZkmWQQe.cYJqQg')
    configManager.update_config('access_token_time', time.time())
