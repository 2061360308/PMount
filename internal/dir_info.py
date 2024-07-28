import math
import os
import time
import winreg
from concurrent.futures import ThreadPoolExecutor as Pool
from pprint import pprint

import pythoncom
import win32com.client
from diskcache import Cache

from internal.log import get_logger, funcLog
from internal.driver import drivers_obj
from internal.temp_fs import tempFs

logger = get_logger(__name__)

CACHE_TIMEOUT = 60


class DirInfoManager:
    """ 映射资源路径 """
    current_path = os.path.abspath(os.path.dirname(__file__))

    def __init__(self):
        self.pool = Pool(10)  # 线程池，用于异步遍历目录

        self.buffer = Cache(os.path.join(self.current_path, '../cache/buffer-batchmeta'))
        self.dir_buffer = Cache(os.path.join(self.current_path, '../cache/dir_buffer-buffer-batchmeta'))
        self.traversed_folder = Cache(os.path.join(self.current_path, '../cache/traversed-folder'))

        self.file_icon = {}  # 文件图标缓存

    @staticmethod
    def expand_icon_path(icon_path):
        # 展开环境变量
        expanded_path = os.path.expandvars(icon_path)
        # 检查是否包含逗号和索引
        if ',' in expanded_path:
            path, index = expanded_path.split(',', 1)
            return path.strip(), int(index.strip())
        return expanded_path.strip(), 0

    @staticmethod
    def get_default_icon(file_extension):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, file_extension) as key:
                # 尝试获取直接关联的 DefaultIcon
                try:
                    default_icon, _ = winreg.QueryValueEx(key, "DefaultIcon")
                    if default_icon and default_icon != "%1" and (not default_icon.startswith("@{")):
                        return DirInfoManager.expand_icon_path(default_icon)
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
                                    return DirInfoManager.expand_icon_path(default_icon)
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
                                            return DirInfoManager.expand_icon_path(default_icon)
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def format_size(size_bytes):
        if size_bytes == 0:
            return "0B"

        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)

        return f"{s} {size_name[i]}"

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

    def readDir(self, name, path: str, depth: int):
        """
        读取目录

        会将遍历指定目录，并将结果录入缓存
        注意为了分别不同的存储对象缓存内容的key为 f'{name}@@{path}'

        :param name: 对应驱动的名称
        :param path: 要读取的路径，相对于网盘根目录，以 / 开头
        :param depth: 读取深度
        :return:
        """
        driver = drivers_obj[name]
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
                            if tempFs.has(name, item.path+'.lnk'):
                                temp_path = tempFs.get(name, item.path + '.lnk')
                            else:
                                temp_path = tempFs.allocate(name, item.path+'.lnk', 0, suffix=".lnk")
                                # 获取文件后缀
                            suffix = os.path.splitext(item['path'])[1]
                            # 获取文件类型描述
                            description = self.get_file_type_description(suffix)
                            # 获取文件图标
                            if suffix in self.file_icon:
                                icon_path, icon_index = self.file_icon[suffix]
                            else:
                                default_icon = self.get_default_icon(suffix)
                                if default_icon:
                                    icon_path, icon_index = default_icon
                                else:
                                    icon_path, icon_index = "", 0
                                self.file_icon[suffix] = (icon_path, icon_index)
                            self.create_shortcut(
                                target_path="",
                                shortcut_path=temp_path,
                                description=f"类型:{description}\n大小:{self.format_size(item.info.size)}\n提示:双击可自动下载并打开",
                                working_dir=os.path.dirname(item['path']),
                                arguments="",
                                icon_location=icon_path,
                                icon_index=icon_index
                            )

                            tempFs.update(name, item.path+'.lnk', size=os.path.getsize(temp_path))
                            # 添加文件的快捷方式
                            items.append(f"{item['name']}.lnk")
                            # 更新文件的大小属性
                            item.info.size = os.path.getsize(temp_path)

                    self.add_file_attr(f"{name}@@{item['path']}", item.info)  # 将文件属性加入缓存

                    # 如果还有剩余允许深度，且遇到目录则继续遍历
                    if depth > 0:
                        if item.info.isdir:
                            self.readDirAsync(name, item['path'], depth)

                self.dir_buffer[f"{name}@@{path}"] = items

            except Exception as s:
                logger.exception(s)

    def readDirAsync(self, name, path: str, depth: int):
        """
        异步读取目录

        会将遍历指定目录，并将结果录入缓存
        注意为了分别不同的存储对象缓存内容的key为 f'{name}@@{path}'

        :param name: 对应驱动的名称
        :param path: 要读取的路径，相对于网盘根目录，以 / 开头
        :param depth: 读取深度
        :return:
        """

        self.pool.submit(self.readDir, name, path, depth)


dirInfoManager = DirInfoManager()
