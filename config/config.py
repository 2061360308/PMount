import json
import os
import time
from pprint import pprint

import yaml
from easydict import EasyDict


class ConfigManager:
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    configPath = os.path.join(current_file_dir, './config.yml')  # 配置文件路径

    def __init__(self):
        self._config = self._load_config()

        if 'disk' not in self._config or not isinstance(self._config['disk'], list):
            self._config['disk'] = []

    @property
    def config(self):
        return self._config

    def _load_config(self):
        if not os.path.exists(self.configPath):
            with open(self.configPath, 'w+', encoding='utf-8') as f:
                f.write(yaml.dump({
                    'disk': [],
                    'temp': {
                        'dir': {
                            'CACHE_TIMEOUT': 60,
                            'PRELOAD_LEVEL': 2,
                        },
                        'file': {
                            'CACHE_TIMEOUT': 604800,
                            'MAX_CACHE_SIZE': 10737418240,
                            'ROOT': './temp'
                        }
                    }
                }))
        with open(self.configPath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_config(self):
        config_back = open("./config.yml_back", "w", encoding='utf-8')
        try:
            yaml.safe_dump(self.config, config_back, default_flow_style=False, allow_unicode=True)
            config_back.close()
            os.replace(config_back.name, self.configPath)
        except Exception as e:
            os.remove(config_back.name)
            raise e

    def _update_nested_config(self, config, keys, value):
        if len(keys) == 1:
            if isinstance(config, dict) and keys[0] in config:
                config[keys[0]] = value
            elif isinstance(config, list) and isinstance(keys[0], int) and keys[0] < len(config):
                config[keys[0]] = value
            else:
                raise KeyError(f"Key '{keys[0]}' not found in config")
        else:
            if isinstance(config, dict) and keys[0] in config:
                self._update_nested_config(config[keys[0]], keys[1:], value)
            elif isinstance(config, list) and isinstance(keys[0], int) and keys[0] < len(config):
                self._update_nested_config(config[keys[0]], keys[1:], value)
            else:
                raise KeyError(f"Key '{keys[0]}' not found in config")

    def update_config(self, value, *keys):
        """
        更新配置的值

        注意：只允许更新已有的配置项，意外的配置项将返回KeyError错误
        example:
            如果是字典，可以直接按顺序传入键名：
                update_value('new_value', 'key1', 'key2', 'key3' ... 'keyN')
            如果包含列表，也可以使用列表序号：
                update_value('new_value', 'key1', 0, 1 ... n)
        :param value: 值
        :param keys: 键名，如果是嵌套的配置项，请依次传入键名
        :return:
        """
        keys = list(keys)
        self._update_nested_config(self._config, keys, value)
        self._save_config()

    def add_device(self, device, config):
        """
        添加一个设备

        :param device:
        :param config:
        :return:
        """
        self._config['disk'].append(device)
        self._config[device['name']] = config
        self._save_config()

    def use_device(self, name, use=True):
        """
        使用一个设备

        :param use: bool, True: 使用，False: 不使用
        :param name:  设备名
        :return:
        """
        for item in self._config['disk']:
            if item['name'] == name:
                item['use'] = use
                break
        self._save_config()

    def remove_device(self, name):
        """
        删除一个设备

        :param name: 设备名
        :return:
        """
        for item in self._config['disk']:
            if item['name'] == name:
                self._config['disk'].remove(item)
                break

        if self._config[name]:
            del self._config[name]
        self._save_config()


configManager = ConfigManager()
