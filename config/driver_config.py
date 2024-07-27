from easydict import EasyDict

from config import configManager


class DriverConfig:
    def __init__(self, name, package_name):
        super().__setattr__('name', name)
        super().__setattr__('package_name', package_name)

    def __getattr__(self, name):
        return EasyDict(configManager.config)[self.name][name]

    def __setattr__(self, name, value):
        if name in ['name', 'package_name']:
            super().__setattr__(name, value)
        configManager.update_config(value, self.name, name)
