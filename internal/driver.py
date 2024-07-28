import importlib

from easydict import EasyDict

from config import config, DriverConfig

need_modules = {}


def get_need_module(disk):
    for node in disk:
        need_modules[node.name] = node.type


get_need_module(config.disk)

# 导入并实例化需要的 Api 对象
drivers_obj = {}

for name in need_modules:
    package_name = need_modules[name]

    try:
        module = importlib.import_module(f"drivers.{package_name}")
        api_class = getattr(module, 'Driver', None)
        if api_class:
            config = DriverConfig(name, package_name)
            drivers_obj[name] = api_class(config)
    except ImportError as e:
        print(f"无法导入模块 {package_name}: {e}")
    except AttributeError as e:
        print(f"模块 {package_name} 中没有找到 Api 类: {e}")

print("实例化的 Api 对象:", drivers_obj)
