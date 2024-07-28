#!/usr/bin/python
# -*- coding: utf-8 -*-

import errno
import os
import json
import time

try:
    import _find_fuse_parts
except ImportError:
    pass
from fuse import FuseOSError, Operations
from termcolor import colored
from internal.log import get_logger, funcLog
from internal.dir_info import dirInfoManager
from internal.driver import drivers_obj
from internal.temp_fs import tempFs

encrpted_length = 512

logger = get_logger(__name__)

PRELOAD_LEVEL = 4
CACHE_TIMEOUT = 60


class CloudFS(Operations):
    """Baidu netdisk cloud filesystem"""

    def __init__(self, name, *args, **kw):
        self.name = name
        logger.info(colored("- fuse 4 cloud driver -", 'red'))
        self.avail, self.total_size, self.used = self.init_disk_quota()  # 初始化磁盘空间大小
        dirInfoManager.readDirAsync(self.name, "/", PRELOAD_LEVEL)  # 预读根目录(默认深度为2)

    def init_disk_quota(self):
        """
        初始化磁盘空间大小
        :return:
        """
        # 初始化磁盘空间大小
        disk_quota = drivers_obj[self.name].quota()
        # only request once
        try:
            total_size = disk_quota.total
            used = disk_quota.used
        except Exception as e:
            total_size = 100000000000
            used = 0
            logger.exception(e)
            logger.debug(f'con`t load quota api, fall back to default')

        avail = total_size - used  # 可用空间
        return avail, total_size, used

    def _getRootAttr(self):
        path = "/"
        if f'{self.name}@@{path}' in dirInfoManager.buffer:
            return dirInfoManager.buffer[f'{self.name}@@{path}']

        file_info = {
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
        return file_info

    @funcLog
    def getattr(self, path, fh=None):
        '''
        Returns a dictionary with keys identical to the stat C structure of
        stat(2).

        st_atime, st_mtime and st_ctime should be floats.

        NOTE: There is an incompatibility between Linux and Mac OS X
        concerning st_nlink of directories. Mac OS X counts all files inside
        the directory, while Linux counts only the subdirectories.
        '''
        # if path in self.writing_files:
        #     return self.writing_files[path]

        attr = None

        if path.split("/")[-1].startswith("."):
            raise FuseOSError(errno.ENOENT)

        # special handle root Attr
        if path == "/":
            attr = self._getRootAttr()

        # 父目录没有缓存的话先缓存父目录
        parentDir = os.path.dirname(path)
        if f'{self.name}@@{parentDir}' not in dirInfoManager.dir_buffer:
            dirInfoManager.readDirAsync(self.name, parentDir, 1)

        if f'{self.name}@@{path}' in dirInfoManager.buffer:
            attr = dirInfoManager.buffer[f'{self.name}@@{path}']

        if attr is None:
            if (f'{self.name}@@{path}'.endswith('.lnk')) and (f'{self.name}@@{path}'[:-4] in dirInfoManager.buffer):
                # 如果是快捷方式文件，需要尝试读取原文件信息
                original_path = f'{self.name}@@{path}'[:-4]
                attr = dirInfoManager.buffer[original_path]
            else:
                raise FuseOSError(errno.ENOENT)

        return attr

    @funcLog
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

    @funcLog
    def readdir(self, path, offset):
        """
        读取目录的内容。列出目录中的文件和子目录。

        :param path:
        :param offset:
        :return:
        """
        dirInfoManager.readDirAsync(self.name, path, PRELOAD_LEVEL)  # 异步读取目录

        # with open('log.txt', 'w+', encoding='utf-8') as f:
        #     for k in dirInfoManager.dir_buffer.iterkeys():
        #         f.write(f'{k}: {dirInfoManager.dir_buffer[k]}\n')

        if f'{self.name}@@{path}' in dirInfoManager.dir_buffer:  # 在缓存中的话就读取对应缓存内容
            for r in dirInfoManager.dir_buffer[f'{self.name}@@{path}']:
                yield r.strip('/')
        else:  # 不在缓存中的话就返回基本的.和..
            files = ['.', '..']
            for r in files:
                yield r

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
                oldCache = dirInfoManager.dir_buffer.get(old_parent_dir)
                # remove
                if oldCache:
                    if old_name in oldCache:
                        oldCache.remove(old_name)
                        dirInfoManager.dir_buffer[old_parent_dir] = oldCache
                    if old in dirInfoManager.buffer:
                        dirInfoManager.buffer.pop(old)
                else:
                    pass
            else:
                # print("updateCache", old, new)
                oldCache = dirInfoManager.dir_buffer[old_parent_dir]
                new_parent_dir = os.path.dirname(new)
                if old_name in oldCache:
                    # dir old remove
                    oldCache.remove(old_name)
                    dirInfoManager.dir_buffer[old_parent_dir] = oldCache
                    # dir new add
                    newfilename = new[new.rfind("/") + 1:]
                    newCache = dirInfoManager.dir_buffer.get(new_parent_dir, [])
                    newCache.append(newfilename)
                    dirInfoManager.dir_buffer[new_parent_dir] = newCache

                if old in dirInfoManager.buffer:
                    old_info = dirInfoManager.buffer.pop(old)
                    dirInfoManager.buffer[new] = old_info
        except Exception as e:
            logger.info(e)

    def unlink(self, path):
        '''
        删除文件
        '''
        # print("unlink .....................")
        driver_path, driver = dirInfoManager.get_driver(path)
        if driver:
            driver.delete(driver_path)  # 删除文件
        self.updateCacheKeyOnly(path, None)

    def rmdir(self, path):
        '''
        will only delete directory
        '''
        driver_path, driver = dirInfoManager.get_driver(path)
        if driver:
            driver.delete(driver_path)  # 删除文件夹
        self.updateCacheKeyOnly(path, None)

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

    def rename(self, old, new):
        '''
        will effect dir and file
        '''
        logger.info(f'rename {old}, {new}')
        driver_path, driver = dirInfoManager.get_driver(old)

        if driver:
            driver.rename(driver_path, new)  # Todo

        self.updateCacheKeyOnly(old, new)

    @funcLog
    def mkdir(self, path, mode):
        # TODO: 完善接口的上传等相关功能
        logger.info(f'making dir {path}')

        driver_path, driver = dirInfoManager.get_driver(path)
        if driver:
            driver.delete(path)  # 删除文件夹

        r = json.loads(driver.mkdir(driver_path))  # Todo

        if 'error_code' in r:
            logger.info(f'{r}')
            # logger.info(f'{error_map[str(r["error_code"])]} args: {path}, response:{r}')
            return

        directory = path[:path.rfind("/")]
        filename = path[path.rfind("/") + 1:]

        cache = None
        if directory in dirInfoManager.dir_buffer:
            cache = dirInfoManager.dir_buffer[directory]
            cache.append(filename)
        dirInfoManager.dir_buffer[directory] = cache

        dirInfoManager.add_file_attr(path, r)

    def open(self, path, flags):
        return 0

    def read(self, path, size, offset, fh):
        if tempFs.has(self.name, path):
            file_path = tempFs.get(self.name, path)
        elif tempFs.has(self.name, path + ".lnk"):
            file_path = tempFs.get(self.name, path + ".lnk")
        else:
            raise FuseOSError(errno.ENOENT)
        with open(file_path, 'rb') as f:
            f.seek(offset)
            return f.read(size)

    def release(self, path, fh):
        return 0

    @funcLog
    def create(self, path, mode, fh=None):
        pass
        # Todo
        # logger.debug(f'create {path}')
        # with self.createLock:
        #     if path not in self.writing_files:
        #         attr = fileAttr.copy()
        #         t = time.time()
        #
        #         attr['uploading_tmp'] = tempfile.NamedTemporaryFile('wb')
        #         attr['st_mode'] = attr['st_mode'] | stat.S_IFREG | stat.S_ISUID | stat.S_ISGID
        #
        #         self.writing_files[path] = attr
        #     else:
        #         logger.debug(f'{path} is writing on, wait another turn..')
        # return 0

    def write(self, path, data, offset, fp):
        print("write .....................")
        # Todo： 写文件

    def statfs(self, path):
        # TODO read from cloud disk
        return {'f_bavail': int((self.avail) / 4096), 'f_bfree': int((self.avail) / 4096),  # 相同的值  block
                'f_favail': 4290675908, 'f_ffree': 4290675908,  # 相同的值  node
                'f_bsize': 104857,  # perferd value
                'f_blocks': int(self.total_size / 8), 'f_files': 4294967279, 'f_flag': 0, 'f_frsize': 4096,
                'f_namemax': 255}
