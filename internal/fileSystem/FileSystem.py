import errno
import math
import os
import time
import winreg

import pythoncom
import win32com.client
from fuse import FuseOSError

from internal.log import get_logger
from internal.fileSystem.temp_fs import tempFs
from internal.system_res import dir_info_pool, dir_info_buffer, dir_info_dir_buffer, \
    dir_info_traversed_folder, stop_event

logger = get_logger(__name__)

CACHE_TIMEOUT = 60


def expand_icon_path(icon_path):
    # 展开环境变量
    expanded_path = os.path.expandvars(icon_path)
    # 检查是否包含逗号和索引
    if ',' in expanded_path:
        path, index = expanded_path.split(',', 1)
        return path.strip(), int(index.strip())
    return expanded_path.strip(), 0


def get_default_icon(file_extension):
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, file_extension) as key:
            # 尝试获取直接关联的 DefaultIcon
            try:
                default_icon, _ = winreg.QueryValueEx(key, "DefaultIcon")
                if default_icon and default_icon != "%1" and (not default_icon.startswith("@{")):
                    return expand_icon_path(default_icon)
            except (FileNotFoundError, OSError):
                pass

            # 尝试获取 ProgID
            try:
                prog_id, _ = winreg.QueryValueEx(key, "")
                if prog_id:
                    try:
                        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\DefaultIcon") as icon_key:
                            default_icon, _ = winreg.QueryValueEx(icon_key, "")
                            if default_icon and default_icon != "%1" and (not default_icon.startswith("@{")):
                                return expand_icon_path(default_icon)
                    except (FileNotFoundError, OSError):
                        pass
            except (FileNotFoundError, OSError):
                pass

            # 尝试获取 OpenWithProgids
            try:
                with winreg.OpenKey(key, "OpenWithProgids") as openwith_key:
                    i = 0
                    while True:
                        try:
                            prog_id = winreg.EnumValue(openwith_key, i)[0]
                            try:
                                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                                                    f"{prog_id}\\DefaultIcon") as icon_key:
                                    default_icon, _ = winreg.QueryValueEx(icon_key, "")
                                    if default_icon and default_icon != "%1" and (
                                            not default_icon.startswith("@{")):
                                        return expand_icon_path(default_icon)
                            except (FileNotFoundError, OSError):
                                pass
                        except OSError:
                            break
                        i += 1
            except (FileNotFoundError, OSError):
                pass

    except (FileNotFoundError, OSError):
        return None

    # 如果以上步骤都没有找到 DefaultIcon，则返回 None
    return None


def get_file_type_description(extension):
    """
        获取文件类型描述

        :param extension:
        :return:
        """
    try:
        # 打开注册表项
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension)
        # 读取默认值
        file_type, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)

        # 打开文件类型描述的注册表项
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, file_type)
        # 读取默认值
        description, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)

        return description
    except FileNotFoundError:
        return "未知文件类型"


def create_shortcut(target_path, shortcut_path, description, working_dir, arguments, icon_location, icon_index):
    """
        创建快捷方式

        :param target_path:  目标路径
        :param shortcut_path:  快捷方式保存路径
        :param description:  快捷方式描述
        :param working_dir:  工作目录
        :param arguments:  传递的参数
        :param icon_location:  图标路径
        :param icon_index:  图标索引
        :return:
        """
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = target_path
    shortcut.WorkingDirectory = working_dir
    shortcut.Arguments = arguments
    shortcut.Description = description  # 设置鼠标悬浮提示信息
    shortcut.IconLocation = f"{icon_location},{icon_index}"
    shortcut.save()


def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s} {size_name[i]}"


class FileSystem:

    def __init__(self):
        self.pool = dir_info_pool  # 线程池，用于异步遍历目录

        self.buffer = dir_info_buffer  # 缓存文件属性
        self.dir_buffer = dir_info_dir_buffer  # 缓存目录结构
        self.traversed_folder = dir_info_traversed_folder  # 缓存已经遍历的目录

        self.file_icon = {}  # 文件图标缓存

    def disk_quota(self, device):
        """
        获取存储方案的配额

        :param device:
        :return: 配额
        """
        disk_quota = device.driver.quota()

        try:
            total_size = disk_quota.total
            used = disk_quota.used
        except Exception as e:
            total_size = 100000000000
            used = 0
            print(f"获取存储方案配额失败: {e}")

        avail = total_size - used  # 可用空间

        return avail, total_size, used

    def add_file_attr(self, path: str, info):
        """
        创建属性

        :param path: 路径
        :param info: 信息列表

        需要的info信息有
            info={
                "isdir": bool,
                "size": int,
                "mtime": float,
                "atime": float,
                "ctime": float,
            }
        :return:
        """
        fileAttr = {
            'st_ino': 0,
            'st_dev': 0,
            'st_mode': 16877 if info['isdir'] else 36279,
            'st_nlink': 2 if info['isdir'] else 1,
            'st_uid': 0,
            'st_gid': 0,
            'st_size': int(info['size']) if 'size' in info else 0,
            'st_atime': 0,
            'st_mtime': info['local_mtime'] if 'local_mtime' in info else info['mtime'],
            'st_ctime': info['local_ctime'] if 'local_ctime' in info else info['ctime']
        }

        self.buffer[path] = fileAttr

    def readDir(self, device, path: str, depth: int):
        """
        读取目录

        会将遍历指定目录，并将结果录入缓存
        注意为了分别不同的存储对象缓存内容的key为 f'{name}@@{path}'

        :param device: 设备对象
        :param path: 要读取的路径，相对于网盘根目录，以 / 开头
        :param depth: 读取深度
        :return:
        """
        if stop_event.is_set():
            return

        driver = device.driver
        name = device.name

        if f'{name}@@{path}' not in self.traversed_folder:
            self.traversed_folder.set(f'{name}@@{path}', b'1', expire=CACHE_TIMEOUT)
            try:
                item_list = driver.list(dir=path)

                items = ['.', '..']  # 基本子项，当前目录和上级目录

                depth -= 1
                for item in item_list:  # 遍历返回的文件、文件夹列表
                    if item['name'].startswith("."):  # 隐藏文件不显示
                        continue

                    if item.info.isdir:
                        items.append(item['name'])  # 文件夹直接添加
                    else:
                        # # 缓存文件里有这个文件，直接添加文件本身
                        if tempFs.has(name, item.path):
                            items.append(item['name'])
                        else:
                            # pass
                            # 缓存文件中有这个文件的快捷方式
                            if tempFs.has(name, item.path + '.lnk'):
                                temp_path = tempFs.get(name, item.path + '.lnk')
                            else:
                                temp_path = tempFs.allocate(name, item.path + '.lnk', 0, suffix=".lnk")
                                # 获取文件后缀
                            suffix = os.path.splitext(item['path'])[1]
                            # 获取文件类型描述
                            description = get_file_type_description(suffix)
                            # 获取文件图标
                            if suffix in self.file_icon:
                                icon_path, icon_index = self.file_icon[suffix]
                            else:
                                default_icon = get_default_icon(suffix)
                                if default_icon:
                                    icon_path, icon_index = default_icon
                                else:
                                    icon_path, icon_index = "", 0
                                self.file_icon[suffix] = (icon_path, icon_index)
                            create_shortcut(
                                target_path="",
                                shortcut_path=temp_path,
                                description=f"类型:{description}\n大小:{format_size(item.info.size)}\n提示:双击可自动下载并打开",
                                working_dir=os.path.dirname(item['path']),
                                arguments="",
                                icon_location=icon_path,
                                icon_index=icon_index
                            )

                            tempFs.update(name, item.path + '.lnk', size=os.path.getsize(temp_path))
                            # 添加文件的快捷方式
                            items.append(f"{item['name']}.lnk")
                            # 更新文件的大小属性
                            item.info.size = os.path.getsize(temp_path)

                    self.add_file_attr(f"{name}@@{item['path']}", item.info)  # 将文件属性加入缓存

                    # 如果还有剩余允许深度，且遇到目录则继续遍历
                    if depth > 0:
                        if item.info.isdir:
                            self.readDirAsync(device, item['path'], depth)

                self.dir_buffer[f"{name}@@{path}"] = items

            except Exception as s:
                logger.exception(s)

    def readDirAsync(self, device, path: str, depth: int):
        """
        异步读取目录

        会将遍历指定目录，并将结果录入缓存
        注意为了分别不同的存储对象缓存内容的key为 f'{name}@@{path}'

        :param device: 设备对象
        :param path: 要读取的路径，相对于网盘根目录，以 / 开头
        :param depth: 读取深度
        :return:
        """

        if stop_event.is_set():
            return

        self.pool.submit(self.readDir, device, path, depth)

    def read(self, device, path, size, offset, fh):
        name = device.name
        if tempFs.has(name, path):
            file_path = tempFs.get(name, path)
        elif tempFs.has(name, path + ".lnk"):
            file_path = tempFs.get(name, path + ".lnk")
        else:
            raise FuseOSError(errno.ENOENT)

        with open(file_path, 'rb') as f:
            f.seek(offset)
            return f.read(size)

    def getattr(self, device, path, fh=None):
        name = device.name

        attr = None

        if path.split("/")[-1].startswith("."):
            raise FuseOSError(errno.ENOENT)

        # special handle root Attr
        if path == "/":
            if f'{name}@@{path}' in self.buffer:
                attr = self.buffer[f'{name}@@{path}']
            else:
                attr = {
                    'st_ino': 0,
                    'st_dev': 0,
                    'st_mode': 16877,
                    'st_nlink': 2,
                    'st_uid': 0,
                    'st_gid': 0,
                    'st_size': 0,
                    'st_atime': 0,
                    'st_mtime': time.time(),
                    'st_ctime': time.time()
                }

        # 父目录没有缓存的话先缓存父目录
        # 这里是同步堵塞读取，以便下方总能查找到信息
        parentDir = os.path.dirname(path)
        if f'{name}@@{parentDir}' not in self.dir_buffer:
            self.readDir(device, parentDir, 1)

        # 查看缓存中是否有这个文件的缓存
        if f'{name}@@{path}' in self.buffer:
            attr = self.buffer[f'{name}@@{path}']

        if attr is None:
            # 如果是快捷方式文件，需要尝试去掉.lnk查找对应的信息
            if (f'{name}@@{path}'.endswith('.lnk')) and (
                    f'{name}@@{path}'[:-4] in self.buffer):
                original_path = f'{name}@@{path}'[:-4]
                attr = self.buffer[original_path]
            else:
                raise FuseOSError(errno.ENOENT)

        return attr

    def getdirs(self, device, path, offset):
        name = device.name
        PRELOAD_LEVEL = 2  # 预加载层级

        self.readDirAsync(name, path, PRELOAD_LEVEL)  # 异步读取目录

        if f'{name}@@{path}' in self.dir_buffer:  # 在缓存中的话就读取对应缓存内容
            for r in self.dir_buffer[f'{name}@@{path}']:
                yield r.strip('/')
        else:  # 不在缓存中的话就返回基本的.和..
            files = ['.', '..']
            for r in files:
                yield r


fileSystem = FileSystem()