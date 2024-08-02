import os

from easydict import EasyDict as edict
import yaml

config_file = 'config.yaml'


def save(config):
    print("得到的：", config)

    def easydict_to_dict(easy_dict):
        def convert(obj):
            if isinstance(obj, edict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            else:
                return obj

        return convert(easy_dict)

    config = easydict_to_dict(config)

    config_back = open("config.yml_back", "w", encoding='utf-8')
    try:
        yaml.dump(config, config_back, default_flow_style=False, allow_unicode=True)
        config_back.close()
        os.replace(config_back.name, config_file)
    except Exception as e:
        # os.remove(config_back.name)
        raise e


class AutoSaveEasyDict(dict):
    def __init__(self, d=None, **kwargs):
        if d is None:
            d = {}
        else:
            d = dict(d)
        if kwargs:
            d.update(**kwargs)
        for k, v in d.items():
            setattr(self, k, v)
        # Class attributes
        for k in self.__class__.__dict__.keys():
            if not (k.startswith('__') and k.endswith('__')) and k not in ('update', 'pop'):
                setattr(self, k, getattr(self, k))

    def __setattr__(self, name, value):
        if isinstance(value, (list, tuple)):
            value = type(value)(self.__class__(x)
                                if isinstance(x, dict) else x for x in value)
        elif isinstance(value, dict) and not isinstance(value, AutoSaveEasyDict):
            value = AutoSaveEasyDict(value)
        super(AutoSaveEasyDict, self).__setattr__(name, value)
        super(AutoSaveEasyDict, self).__setitem__(name, value)
        save(dict(self))

    __setitem__ = __setattr__

    def update(self, e=None, **f):
        d = e or dict()
        d.update(f)
        for k in d:
            setattr(self, k, d[k])

    def pop(self, k, *args):
        if hasattr(self, k):
            delattr(self, k)
        return super(AutoSaveEasyDict, self).pop(k, *args)


# 加载配置文件
with open('config.yaml', 'r') as file:
    config_data = yaml.safe_load(file)

# # 使用 AutoSaveEasyDict
settings = AutoSaveEasyDict(config_data)

settings.some.nested.key2 = 'new_value'

print(settings.some.nested.key2)
#
# # 通过点号访问嵌套配置项
# print(settings.some.nested.key)  # 输出: value
#
# # 修改嵌套配置项
# settings.some.nested.key = 'new_value'
#
# # 通过字典方式访问配置项
# print(settings['some']['nested']['key'])  # 输出: new_value
#
# # 通过字典方式修改配置项
# settings['some']['nested']['key'] = 'new_value2'
#
# print(settings.some.nested.key)  # 输出: new_value2
#
# print(dict(settings))
