import os.path

import pytest
from easydict import EasyDict
from driver import MyDriver
from config import DriverConfig
from internal.BaseDriver import QuotaInfo, Info, Item, BaseDriver

# 下面测试用例的一些具体文件路径和文件名可能需要根据你的实际情况进行修改
name = "测试设备名"  # 设备名
package_name = "test_driver"  # 驱动包名
file1 = "/test/file1.txt"  # 用来测试的一个文件的路径，符合实际情况下随便找一个就好

# 1. 假设你已经手动编写好了config内的配置信息，
# 那么你可以直接使用DriverConfig，name是假设用户用你的驱动创建的设备名，package_name是你的驱动包名（推荐）
# 2. 否则你可以手动创建一个，具体方法参考config内的driver_config.py中的实现方式（不推荐这种方式）
config = DriverConfig(name, package_name)

# 创建 你的驱动 实例
driver = MyDriver(config)


def test_driver():
    assert isinstance(driver, BaseDriver)


def test_quota():
    result = driver.quota()
    assert isinstance(result, EasyDict)
    assert "total" in result
    assert "used" in result
    assert isinstance(result.total, int)
    assert isinstance(result.used, int)


def test_list():
    result = driver.list('/')
    assert isinstance(result, list)
    assert len(result) > 0
    item: Item = result[0]
    assert isinstance(item, EasyDict)
    assert "name" in item
    assert "path" in item
    assert "info" in item
    assert isinstance(item.info, EasyDict)
    assert "isdir" in item.info
    assert "size" in item.info
    assert "mtime" in item.info
    assert "ctime" in item.info


def test_copy():
    global file1

    src_path = file1
    dest_path = "/test_copy_file.txt"
    result = driver.copy(src_path, dest_path)
    assert result is True


def test_rname():
    path = "/test_copy_file.txt"
    new_name = "test_copy_file2.txt"
    result = driver.rname(path, new_name)
    assert result is True


def test_move():
    global file1

    path = os.path.split(file1)[0]
    src_path = "/test_copy_file2.txt"
    dest_path = os.path.join(path, "test_copy_file2.txt")
    result = driver.move(src_path, dest_path)
    assert result is True


def test_delete():
    global file1

    path = os.path.split(file1)[0]
    path = os.path.join(path, "test_copy_file2.txt")
    result = driver.delete(path)
    assert result is True
