import importlib
import pkgutil


def import_meta_modules(package_name):
    package = importlib.import_module(package_name)
    package_path = package.__path__

    meta_list = []

    for _, module_name, is_pkg in pkgutil.iter_modules(package_path):
        if is_pkg:
            full_package_name = f"{package_name}.{module_name}"
            try:
                meta_module = importlib.import_module(f"{full_package_name}.meta")
                meta_list.append(meta_module)
            except ModuleNotFoundError:
                print(f"No meta.py found in {full_package_name}")

    return meta_list


def device_change():
    """
    设备列表改变（新增 或 删除）

    需要提前更新好config，然后调用此函数，
    用于更新server以及drivers_obj

    :param config:
    :param device:
    :param driver:
    :return:
    """
    from internal.server import server
    from internal.fileSystem.driver import update_driver

    server.updateMountNodes()
    update_driver()
    print("设备列表改变")
