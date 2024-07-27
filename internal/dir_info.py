import os
import time
from concurrent.futures import ThreadPoolExecutor as Pool
from pprint import pprint

import win32com.client
from diskcache import Cache

from internal.log import get_logger, funcLog
from .driver import drivers_obj

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
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = working_dir
        shortcut.Arguments = arguments
        shortcut.Description = description  # 设置鼠标悬浮提示信息
        shortcut.IconLocation = f"{icon_location},{icon_index}"
        shortcut.save()

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
            # logger.debug(f'net dir {depth} - {path} ')
            try:
                # print(driver)
                item_list = driver.list(dir=path)

                files = ['.', '..']
                # if 'error_code' in item_list and foo["error_code"] != 0:
                #     logger.info(f'{error_map[str(foo["error_code"])]} args: {path}')
                # if "list" not in foo:
                #     return

                depth -= 1
                for file in item_list:
                    if file['name'].startswith("."):
                        continue
                    files.append(file['name'])
                    self.add_file_attr(f"{name}@@{file['path']}", file.info)
                    # self._baidu_file_attr_convert(file['path'], file)
                    if depth > 0:
                        if file.info.isdir:
                            self.readDirAsync(name, file['path'], depth)

                self.dir_buffer[f"{name}@@{path}"] = files


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
