import errno
import math
import os
import shutil
import sys
import time
import winreg

import pythoncom
import win32com.client
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication
from fuse import FuseOSError

from log import logger
from .file_transfer import fileTransferManager, DownloadDialog
from .temp_fs import tempFs
from internal.system_res import dir_info_pool, dir_info_buffer, dir_info_dir_buffer, \
    dir_info_traversed_folder, stop_event

CACHE_TIMEOUT = 60

PRELOAD_LEVEL = 2  # 预加载层级

current_path = os.path.dirname(os.path.abspath(__file__))

PMountTaskToolPath = os.path.join(current_path, "../../PMountTaskTool.exe")


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
    shortcut.WindowStyle = 7  # 7 表示隐藏窗口
    shortcut.save()


def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s} {size_name[i]}"


def show_download_dialog(task):
    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        app = QCoreApplication.instance()
    downloadDialog = DownloadDialog()
    downloadDialog.showDialog(task)
    app.exec()


class FileSystem:

    def __init__(self):
        self.pool = dir_info_pool  # 线程池，用于异步遍历目录

        self.buffer = dir_info_buffer  # 缓存文件属性
        self.dir_buffer = dir_info_dir_buffer  # 缓存目录结构
        self.traversed_folder = dir_info_traversed_folder  # 缓存已经遍历的目录

        self.file_icon = {}  # 文件图标缓存
        self.view_task = []  # 查看任务
        self.download_copy_task = {}  # 下载复制任务
        fileTransferManager.taskComplete.connect(self.cloud_download_complete)

        self.file_handle = {}  # 文件句柄
        self.handle_counter = 0
        self.uid = self.__get_current_uid()
        self.gid = self.__get_current_gid()

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

    def __get_current_uid(self):
        """获取当前用户的 UID"""
        if os.name == 'nt':
            # Windows 系统，使用当前用户名的哈希值作为 UID
            return hash(os.getlogin())
        else:
            # Unix 系统，使用实际的 UID
            return os.getuid()

    def __get_current_gid(self):
        """获取当前用户的 GID"""
        if os.name == 'nt':
            # Windows 系统，使用固定的 GID 值
            return 0
        else:
            # Unix 系统，使用实际的 GID
            return os.getgid()

    def __add_file_attr(self, path: str, info):
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
            'st_mode': 0o040777 if info['isdir'] else 0o100777,
            'st_nlink': 2 if info['isdir'] else 1,
            'st_uid': self.uid,
            'st_gid': self.gid,
            'st_size': int(info['size']) if 'size' in info else 0,
            'st_atime': 0,
            'st_mtime': info['local_mtime'] if 'local_mtime' in info else info['mtime'],
            'st_ctime': info['local_ctime'] if 'local_ctime' in info else info['ctime']
        }

        self.buffer[path] = fileAttr

    def __readDir(self, device, path: str, depth: int):
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
                        # 缓存文件里有这个文件，直接添加文件本身
                        hasFile = False
                        if tempFs.has(name, item.path):  # 缓存是否有这个文件
                            if tempFs.get_md5(name, item.path) == item.info.md5:  # 文件未变化
                                hasFile = True
                            else:
                                tempFs.remove(name, item.path)  # 文件变化，删除缓存

                        if hasFile:
                            items.append(item['name'])
                        else:
                            # 缓存文件中有这个文件的快捷方式
                            if tempFs.has(name, item.path + '.lnk'):
                                temp_path = tempFs.get(name, item.path + '.lnk')
                            else:
                                temp_path = tempFs.allocate(name, item.path + '.lnk', 0, suffix=".lnk",
                                                            md5=item.info.md5)
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
                                    target_path='cmd.exe',
                                    shortcut_path=temp_path,
                                    description=f"类型:{description}\n大小:{format_size(item.info.size)}\n提示:双击可自动下载并打开",
                                    working_dir=os.path.join(device.path, os.path.dirname(item['path'])[1:]),
                                    arguments=f' /c {PMountTaskToolPath} -d "{device.name}" -p "{item.path}"',
                                    icon_location=icon_path,
                                    icon_index=icon_index
                                )

                                tempFs.update(name, item.path + '.lnk', size=os.path.getsize(temp_path))

                            # 更新文件的大小属性
                            item.info.size = os.path.getsize(temp_path)
                            # 添加文件的快捷方式
                            items.append(f"{item['name']}.lnk")

                    self.__add_file_attr(f"{name}@@{item['path']}", item.info)  # 将文件属性加入缓存

                    # 如果还有剩余允许深度，且遇到目录则继续遍历
                    if depth > 0:
                        if item.info.isdir:
                            self.__readDirAsync(device, item['path'], depth)

                self.dir_buffer[f"{name}@@{path}"] = items

            except Exception as s:
                logger.error(f"读取目录失败: {s}")

    def __readDirAsync(self, device, path: str, depth: int):
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

        self.pool.submit(self.__readDir, device, path, depth)

    def preReadDir(self, device):
        """
        预读目录

        :return:
        """
        self.__readDirAsync(device, "/", PRELOAD_LEVEL)

    def open(self, device, path, flags):
        """
        打开文件句柄
        :param device:
        :param path:
        :param flags:
        :return:
        """
        name = device.name

        if tempFs.has(name, path):
            file_path = tempFs.get(name, path)
        else:
            raise FuseOSError(errno.ENOENT)

        # 根据 flags 确定模式
        if flags & os.O_RDWR:
            mode = 'r+b'
        elif flags & os.O_WRONLY:
            mode = 'wb'
        else:
            mode = 'rb'

        mode = 'r+b'

        # 打开文件并存储文件对象
        file_obj = open(file_path, mode)

        # 生成唯一的整数句柄
        self.handle_counter += 1
        handle = self.handle_counter

        # 存储句柄和文件对象的映射关系
        self.file_handle[handle] = file_obj
        return handle

    def read(self, device, path, size, offset, fh):
        handel = self.file_handle[fh]
        handel.seek(offset)
        return handel.read(size)

    def release(self, device, path, fh):
        handel = self.file_handle[fh]
        handel.close()
        del self.file_handle[fh]
        return fh

    def write(self, device, path, data, offset, fp):
        os.lseek(fp, offset, os.SEEK_SET)
        return os.write(fp, data)

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
                    'st_mode': 0o040777,
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
            self.__readDir(device, parentDir, 1)

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

        self.__readDirAsync(name, path, PRELOAD_LEVEL)  # 异步读取目录

        # print(f"getdirs: {name}@@{path}")

        if f'{name}@@{path}' in self.dir_buffer:  # 在缓存中的话就读取对应缓存内容
            for r in self.dir_buffer[f'{name}@@{path}']:
                yield r.strip('/')
        else:  # 不在缓存中的话就返回基本的.和..
            files = ['.', '..']
            for r in files:
                yield r

    def view(self, device, path):
        """
        打开文件(宏观层面的打开，不是系统的打开文件读取)
        :return:
        """
        for task in self.view_task:
            if task.device == device and task.device_fp == path:
                return  # 如果已经在下载队列中就不再处理

        if not tempFs.has(device.name, path):
            task = fileTransferManager.add(device, path)
            self.view_task.append(task)
            show_download_dialog(task)  # 显示下载对话框

        file_path = f'{device.path}{path}'
        if os.path.isfile(file_path):
            os.startfile(file_path)
        else:
            print('erro, 下载完发现没有文件')

    def download_copy(self, device, path, workdir):
        """
        下载文件(用户复制快捷方式到其他位置后双击打开触发此下载操作)
        :return:
        """
        for task in self.download_copy_task.keys():
            if task.device == device and task.device_fp == path:
                return  # 如果已经在下载队列中就不再处理

        if not tempFs.has(device.name, path):
            task = fileTransferManager.add(device, path)
            self.download_copy_task[task] = workdir
            show_download_dialog(task)  # 显示下载对话框

        # 复制文件
        file_path_src = tempFs.get(device.name, path)
        file_name = os.path.split(path)[1]
        file_path_dst = os.path.join(workdir, file_name)
        shutil.copy2(file_path_src, file_path_dst)

    def cloud_download_complete(self, task):
        """
        云端下载任务完成

        :param task:
        :return:
        """
        # 更新目录缓存
        self.update_download_file_cache(task.device, task.device_fp)

        # 重新调用文件操作
        if task in self.view_task:
            self.view_task.remove(task)
            self.view(device=task.device, path=task.device_fp)
        elif task in self.download_copy_task:
            workdir = self.download_copy_task[task]
            del self.download_copy_task
            self.download_copy(device=task.device, path=task.device_fp, workdir=workdir)

    def update_file_size(self, device, path):
        """
        更新文件大小

        :param device: 设备对象
        :param path: 文件路径
        :param size: 文件大小
        :return:
        """
        # 更新文件的大小属性
        if tempFs.has(device.name, path):
            file_path = tempFs.get(device.name, path)
            size = os.path.getsize(file_path)
            if f"{device.name}@@{path}" in self.buffer:
                attr = self.buffer[f"{device.name}@@{path}"]
                attr['st_size'] = size
                self.buffer[f"{device.name}@@{path}"] = attr

    def update_folder_cache(self, device, path, name, type='add', old=''):
        if f'{device.name}@@{path}' in self.dir_buffer:
            children_list = self.dir_buffer[f'{device.name}@@{path}']

            if type == 'add':
                children_list.append(name)
            elif type == 'remove':
                children_list.remove(name)
            else:
                if old in children_list:
                    children_list.remove(old)
                    children_list.append(name)

            self.dir_buffer[f'{device.name}@@{path}'] = children_list

    def update_download_file_cache(self, device, path):
        """
        文件下载之后 更新对应的缓存

        :param device: 所属的设备对象
        :param path: 文件路径
        :param value: 文件信息
        :return:
        """
        parentDir = os.path.dirname(path)  # 文件夹路径
        fileName = os.path.basename(path)  # 文件名
        old = fileName + '.lnk'
        # 更新目录缓存
        self.update_folder_cache(device, parentDir, fileName, type='update', old=old)
        # if f'{device.name}@@{parentDir}' in self.dir_buffer:
        #     children_list = self.dir_buffer[f'{device.name}@@{parentDir}']
        #     if f'{fileName}.lnk' in children_list:
        #         children_list.remove(f'{fileName}.lnk')
        #         children_list.append(fileName)
        #         self.dir_buffer[f'{device.name}@@{parentDir}'] = children_list

        # 更新文件的大小属性
        self.update_file_size(device, path)
        # if tempFs.has(device.name, path):
        #     file_path = tempFs.get(device.name, path)
        #     size = os.path.getsize(file_path)
        #     if f"{device.name}@@{path}" in self.buffer:
        #         attr = self.buffer[f"{device.name}@@{path}"]
        #         attr['st_size'] = size
        #         self.buffer[f"{device.name}@@{path}"] = attr

    def mkdir(self, device, path, mode):
        """
        创建目录

        :param device: 设备对象
        :param path: 要创建的目录路径
        :return:
        """
        parentDir = os.path.dirname(path)  # 文件夹路径
        name = os.path.basename(path)  # 文件夹名
        children_list = self.dir_buffer.get(f'{device.name}@@{parentDir}', [])
        if name in children_list:
            return

        response = device.driver.mkdir(path)
        if 'errno' in response and response['errno'] == -8:
            # 文件已存在
            raise FuseOSError(errno.EEXIST)

        # 更新目录缓存
        self.update_folder_cache(device, parentDir, name)

        attr = {
            'st_ino': 0,
            'st_dev': 0,
            'st_mode': 0o040777,
            'st_nlink': 2,
            'st_uid': 0,
            'st_gid': 0,
            'st_size': 0,
            'st_atime': 0,
            'st_mtime': time.time(),
            'st_ctime': time.time()
        }
        # 更新属性缓存
        self.buffer[f'{device.name}@@{path}'] = attr

    def rename(self, device, old, new):
        """
        重命名文件

        :param device: 设备对象
        :param old: 旧路径
        :param new: 新路径
        :return:
        """
        device.driver.rename(old, new)

        parentDir = os.path.dirname(old)
        old_name = os.path.basename(old)
        new_name = os.path.basename(new)

        # 更新目录缓存
        self.update_folder_cache(device, parentDir, new_name, type='update', old=old_name)
        # 更新属性缓存
        if f'{device.name}@@{old}' in self.buffer:
            self.buffer[f'{device.name}@@{new}'] = self.buffer.pop(f'{device.name}@@{old}')


fileSystem = FileSystem()
