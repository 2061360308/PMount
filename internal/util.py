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
