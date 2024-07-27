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

    @property
    def config(self):
        return self._config

    def _load_config(self):
        # if not os.path.exists(self.configPath):
        #     with open(self.configPath, 'w') as f:
        #         json.dump({
        #             "client_id": "",
        #             "client_secret": "",
        #             "refresh_token": "",
        #             "access_token": "",
        #             "access_token_time": 0
        #         }, f, indent=4)
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


configManager = ConfigManager()
