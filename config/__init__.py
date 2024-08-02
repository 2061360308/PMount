# 全局配置
from easydict import EasyDict

from .config import configManager
from .driver_config import DriverConfig
# 更方便的获取配置

update_config = configManager.update_config
add_device_config = configManager.add_device_config
remove_device_config = configManager.remove_device_config


class ConfigWrapper:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def __getattr__(self, name):
        return EasyDict(configManager.config)[name]

    def __getitem__(self, name):
        return EasyDict(configManager.config)[name]


config = ConfigWrapper(configManager)