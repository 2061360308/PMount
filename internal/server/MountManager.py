#!/usr/bin/python
# -*- coding: utf-8 -*-
# 挂载器，
# 一个继承自fuse.Operations的CloudFS类用来实现文件系统的操作（封装了FileSystem）
# mount函数用来挂载设备
# unmount函数用来卸载设备

import ctypes
import errno
import os
import threading

from internal.server.device import DeviceStatus

try:
    import _find_fuse_parts
except ImportError:
    pass
from fuse import Operations, _libfuse, FUSE, FuseOSError
from internal.fileSystem import fileSystem
from log import logger

PRELOAD_LEVEL = 4
CACHE_TIMEOUT = 60


class CloudFS(Operations):
    """Baidu netdisk cloud filesystem"""

    def __init__(self, device):
        """

        :param device: 设备对象
        """
        self.device = device

        logger.info(f"- fuse 4 cloud driver ({self.device.name}) -")
        self.avail, self.total_size, self.used = fileSystem.disk_quota(self.device)  # 初始化磁盘空间大小
        fileSystem.preReadDir(self.device)  # 预读根目录(默认深度为2)

    def init(self, path):
        """
        初始化方法
        :param path:
        :return:
        """

        # 保存 fuse 指针，供后续主线程使用
        fuse_ptr = ctypes.c_void_p(_libfuse.fuse_get_context().contents.fuse)
        self.device.fuse_ptr = fuse_ptr
        self.device.status = DeviceStatus.MOUNTED  # 更改设备状态为挂载成功
        self.device.changeSignal.send("status_change", device=self.device)  # 发送状态改变信号

    def getattr(self, path, fh=None):
        '''
        Returns a dictionary with keys identical to the stat C structure of
        stat(2).

        st_atime, st_mtime and st_ctime should be floats.

        NOTE: There is an incompatibility between Linux and Mac OS X
        concerning st_nlink of directories. Mac OS X counts all files inside
        the directory, while Linux counts only the subdirectories.
        '''

        return fileSystem.getattr(self.device, path, fh)

    @logger.catch
    def truncate(self, path, length, fh=None):
        """
        更改文件大小

        :param path:
        :param length:
        :param fh:
        :return:
        """
        pass
        # self.unlink(path)
        # self.create(path, None)
        # self.writing_files[path]["uploading_tmp"].truncate(length)

    @logger.catch
    def readdir(self, path, offset):
        """
        读取目录的内容。列出目录中的文件和子目录。

        :param path:
        :param offset:
        :return:
        """
        for item in fileSystem.getdirs(self.device, path, offset):
            yield item

    def updateCache(self, path, newValue):
        '''
        add     updateCache(path,value)
        delete  updateCache(path,None)
        udpate  updateCache(path,value)

        '''
        pass

    def updateCacheKeyOnly(self, old, new):
        '''
        delete     updateCacheKeyOnly(old,None)
        add/update updateCacheKeyOnly(old,new)
        '''
        try:
            old_parent_dir = os.path.dirname(old)
            old_name = os.path.basename(old)
            if not new:
                oldCache = fileSystem.dir_buffer.get(old_parent_dir)
                # remove
                if oldCache:
                    if old_name in oldCache:
                        oldCache.remove(old_name)
                        fileSystem.dir_buffer[old_parent_dir] = oldCache
                    if old in fileSystem.buffer:
                        fileSystem.buffer.pop(old)
                else:
                    pass
            else:
                # print("updateCache", old, new)
                oldCache = fileSystem.dir_buffer[old_parent_dir]
                new_parent_dir = os.path.dirname(new)
                if old_name in oldCache:
                    # dir old remove
                    oldCache.remove(old_name)
                    fileSystem.dir_buffer[old_parent_dir] = oldCache
                    # dir new add
                    newfilename = new[new.rfind("/") + 1:]
                    newCache = fileSystem.dir_buffer.get(new_parent_dir, [])
                    newCache.append(newfilename)
                    fileSystem.dir_buffer[new_parent_dir] = newCache

                if old in fileSystem.buffer:
                    old_info = fileSystem.buffer.pop(old)
                    fileSystem.buffer[new] = old_info
        except Exception as e:
            logger.info(e)

    def unlink(self, path):
        '''
        删除文件
        '''
        # print("unlink .....................")
        logger.info(f"unlink {path}")
        pass

    def rmdir(self, path):
        '''
        will only delete directory
        '''
        logger.info(f"rmdir {path}")
        pass

    def access(self, path, amode):
        """
        检查文件访问权限
        函数对应于系统调用 access()，它允许程序检查调用进程是否可以访问指定的文件，
        以及可以进行哪些操作（例如读、写、执行）。
        :param path: 文件的路径
        :param amode: 访问模式，可能的值包括 os.F_OK (存在性检查), os.R_OK (可读性检查), os.W_OK (可写性检查), 和 os.X_OK (可执行性检查)
        :return: 0 表示成功，-errno 表示失败
        """
        # 假设所有文件都是可访问的
        return 0

    @logger.catch
    def rename(self, old, new):
        '''
        will effect dir and file
        '''
        return fileSystem.rename(self.device, old, new)

    @logger.catch
    def mkdir(self, path, mode):
        # TODO: 完善接口的上传等相关功能
        logger.info(f"mkdir {path}")
        fileSystem.mkdir(self.device, path, mode)

    @logger.catch
    def open(self, path, flags):
        return fileSystem.open(self.device, path, flags)

    @logger.catch
    def read(self, path, size, offset, fh):
        return fileSystem.read(self.device, path, size, offset, fh)

    @logger.catch
    def release(self, path, fh):
        return fileSystem.release(self.device, path, fh)

    @logger.catch
    def create(self, path, mode, fh=None):
        # Todo
        logger.info(f"create {path}")
        pass

    def write(self, path, data, offset, fp):
        # Todo： 写文件
        return fileSystem.write(self.device, path, data, offset, fp)

    def statfs(self, path):
        # TODO read from cloud disk
        return {'f_bavail': int((self.avail) / 4096), 'f_bfree': int((self.avail) / 4096),  # 相同的值  block
                'f_favail': 4290675908, 'f_ffree': 4290675908,  # 相同的值  node
                'f_bsize': 104857,  # perferd value
                'f_blocks': int(self.total_size / 8), 'f_files': 4294967279, 'f_flag': 0, 'f_frsize': 4096,
                'f_namemax': 255}


def mount(device):
    # 挂载设备
    def fun():
        fs = CloudFS(device)
        device.use = True
        device.update_info(use=True)  # 更新设备信息, 使其之后启用
        device.status = DeviceStatus.WAIT_MOUNT
        device.changeSignal.send("status_change", device=device)  # 发送状态改变信号
        try:
            FUSE(fs, device.path, nothreads=True, foreground=True)
            # FUSE(fs, device.path, foreground=False, nothreads=True, nonempty=False, async_read=False, raw_fi=False)
        except Exception as e:
            device.status = DeviceStatus.MOUNT_FAILED
            device.changeSignal.send("status_change", device=device)  # 发送状态改变信号
            print(e)
            print(f"挂载失败，请检查是否有其他程序占用了该盘符{device.path}, {device.name}")

    threading.Thread(target=fun).start()


def unmount(device):
    # 卸载设备
    if device.fuse_ptr:
        try:
            print(device.fuse_ptr)
            _libfuse.fuse_exit(device.fuse_ptr)  # 通知 fuse 退出
            device.status = DeviceStatus.UNMOUNTED  # 更改设备状态
            device.use = False
            device.fuse_ptr = None
            device.clear_drive()  # 清理设备已经实例化的驱动实例
            device.update_info(use=False)  # 更新设备信息, 使其不再启用
            device.changeSignal.send("status_change", device=device)  # 发送状态改变信号
            print(f"卸载设备 {device.name}")
        except Exception as e:
            print(e)
            print(f"卸载设备 {device.name} 失败")
