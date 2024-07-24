#!/usr/bin/python
# -*- coding: utf-8 -*-
import queue

import requests
import math
import time
import os
import threading
import mmap

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from core.log import get_my_logger

logger = get_my_logger(__name__)


# def process_queue_task():
#     while True:
#         try:
#             tries = 1
#             f, args, tries = q.get()
#             f(*args)
#         except Exception as e:
#             logger.info(e)
#             tries = tries + 1
#
#             if tries < 10:
#                 logger.warn("retry times:" + str(tries))
#                 downloadTaskQueue.put((f, args, tries))

def process_queue_task():
    while True:
        try:
            # 使用正确的队列变量名
            f, args, tries = downloadTaskQueue.get()
            f(*args)
        except Exception as e:
            logger.info(e)
            tries += 1

            # 确保f和args在异常处理逻辑中被定义
            if 'f' in locals() and 'args' in locals() and tries < 10:
                logger.warn("retry times:" + str(tries))
                downloadTaskQueue.put((f, args, tries))


class CustomHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop('max_retries', 3)
        self.pool_connections = kwargs.pop('pool_connections', 100)
        self.pool_maxsize = kwargs.pop('pool_maxsize', 100)

        super(CustomHTTPAdapter, self).__init__(*args, **kwargs)

        # 设置重试策略
        self.max_retries = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )

        # 设置连接池大小
        self._pool_connections = self.pool_connections
        self._pool_maxsize = self.pool_maxsize


downloadTaskQueue = queue.Queue()
threads = []
num_worker_threads = 250
session = requests.Session()
custom_adapter = CustomHTTPAdapter(
    max_retries=3,
    pool_connections=num_worker_threads * 2,
    pool_maxsize=num_worker_threads * 3
)
# a = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=num_worker_threads * 2,
#                                   pool_maxsize=num_worker_threads * 3)
session.mount('http://', custom_adapter)
session.mount('https://', custom_adapter)

for i in range(num_worker_threads):
    t = threading.Thread(target=process_queue_task, daemon=True)
    t.start()
    threads.append(t)


class Task(object):
    @staticmethod
    def createMmap(filename, size, access=mmap.ACCESS_WRITE):
        """
        创建一个内存映射文件，这对于高效读写大文件非常有用。
        :param filename:
        :param size:
        :param access:
        :return:
        """
        fd = os.open(filename, os.O_RDWR)
        return mmap.mmap(fd, size, access=access)

    @staticmethod
    def createHelperThread(startIdx, endIdx, task):
        """
        用于创建辅助线程，这些线程负责下载文件的不同部分。
        如果文件支持预览（isPreviewAble 为 True），则会优先下载文件的一部分以便快速预览。
        :param startIdx:
        :param endIdx:
        :param task:
        :return:
        """
        isPreviewAble = task.isPreviewAble
        preDownloadPart = 30 if isPreviewAble else 30
        for i in range(startIdx, endIdx + preDownloadPart):
            if i >= len(task.block_infos):
                break

            block_info = task.block_infos[i]

            if block_info["status"] is None:
                block_info["status"] = "ing"
                downloadTaskQueue.put((Task.handle, [block_info, task], 1))

    @staticmethod
    def handle(cache, task):
        start = cache["start"]
        size = cache["size"]
        url = task.get_url()
        user_headers = task.user_headers
        m = task.get_mmap()

        headers = {'Range': f"bytes={start}-{start + size - 1}", **user_headers}

        r = session.get(url, allow_redirects=True, headers=headers, stream=True)

        istart = start

        block_size = 102400
        wrote = 0
        for data in r.iter_content(block_size):
            if data:
                dataLen = len(data)
                try:
                    m[istart:istart + dataLen] = data
                    cache["cur"] = cache["cur"] + dataLen
                    wrote += dataLen
                    with cache["m"]:
                        if wrote >= 65536:
                            wrote = 0
                            cache["m"].notifyAll()

                except Exception as e:
                    logger.info(e)

                finally:
                    if task.is_terminating():
                        return
                istart = istart + dataLen
        cache['status'] = "done"
        with cache["m"]:
            cache["m"].notifyAll()

    def __init__(self, url, path, size):
        saved_path = "./tmp" + path
        if not os.path.exists(os.path.dirname(saved_path)):
            try:
                os.makedirs(os.path.dirname(saved_path))
            except OSError as exc:
                logger.error(f"Failed to create directory {os.path.dirname(saved_path)}: {exc}")
        # almost all the files need to read fast , other wise the app will frozen or exit
        # previewableExts={ "mkv","mpv","mp3","mp4","flv","ts","mov","avi","aac","flac","asf","rma","rmvb", \
        # "rm","ogg","mpeg","vob","m4a","wma","wmv","3gp","zip","rar","tar","7z","pdf","doc","docx","xls","xlsx","dmg" }

        # if you only copy from cloud,then put the file extension in this set,it will down load blazing fast
        nonPreviewAbleExts = {"chunk"}
        self.isPreviewAble = True
        if saved_path.split(".")[-1].lower() in nonPreviewAbleExts:
            self.isPreviewAble = False
            logger.debug(f"{saved_path} is chunable")
        self.path = path
        self.url = url
        self.saved_path = saved_path
        self.user_headers = {'User-Agent': "pan.baidu.com"}  # 官方限制下载请求UA为 pan.baidu.com
        self.part_size = 65536 * 4
        self.block_infos = []
        self.current_file_size = 0
        self.file_size = 0
        self.terminating = False
        self.mmap = None
        self.part_count = None
        self.file_size = size

    def get_url(self):
        return self.url

    def is_terminating(self):
        return self.terminating

    def get_mmap(self):
        return self.mmap

    def get_cache(self, offset, size):
        """
        尝试从内存映射文件中获取指定偏移量和大小的数据。
        如果数据尚未下载完成，它会等待数据变得可用或启动辅助线程加速下载过程。
        :param offset:
        :param size:
        :return:
        """
        try:
            r = self.get_block_range(offset, size)
            c = self.block_infos[r[0]]
            start = time.time()

            maxWaitRound = 10
            curRound = 0
            while True:
                if r[0] == r[1]:
                    if c["cur"] + c["start"] >= (size + offset):
                        return self.mmap[offset:offset + size]
                    else:
                        with c["m"]:
                            c["m"].wait(1)
                else:
                    alldone = True
                    for i in range(r[0], r[1] + 1):
                        if self.block_infos[i]["status"] != "done":
                            alldone = False
                            with self.block_infos[i]["m"]:
                                self.block_infos[i]["m"].wait(1)
                    if alldone:
                        return self.mmap[offset:offset + size]

                downloadTaskQueue.put((Task.createHelperThread, [r[0], r[1], self], 1))
                end = time.time()
                # no response for 10 secs, just drop it 
                # TODO this  shoud be configurable
                if end - start > 10:
                    return None
                curRound += 1
        #                 print("wait ",curRound)

        except Exception as e:
            # logger.debug(f'index:{r[0]},block len:{len(self.block_infos)},path: {self.saved_path}')
            # logger.exception(e) 
            pass

        return None

    def get_block_range(self, offset, size):
        """
        计算给定偏移量和大小对应的文件块范围
        :param offset:
        :param size:
        :return:
        """
        start_idx = offset // self.part_size
        end_idx = (size + offset) // self.part_size
        return [start_idx, end_idx]

    def start(self):
        self.part_count = math.ceil(self.file_size / self.part_size)  # 计算文件需要的部分数

        # 预分配文件空间
        with open(self.saved_path, "wb") as fp:
            fp.seek(self.file_size)
            fp.write(b'\0')

        self.mmap = Task.createMmap(self.saved_path, self.file_size)
        # self.create_range()
        self.calculate_blocks()
        # pre start task to get data 
        if self.isPreviewAble:
            downloadTaskQueue.put(
                (Task.createHelperThread, [0, 8 if 8 < self.part_count else self.part_count - 1, self], 1))
        else:
            downloadTaskQueue.put(
                (Task.createHelperThread, [0, 400 if 400 < self.part_count else self.part_count - 1, self], 1))

    # def create_range(self):
    #     """
    #     根据文件大小和部分大小计算出需要下载的文件块信息
    #     :return:
    #     """
    #     start = 0
    #     size = self.part_size
    #
    #     while start < self.file_size:
    #         if start + size > self.file_size:
    #             size = self.file_size - start
    #         self.block_infos.append(
    #             {"status": None, "start": start, "size": size, "cur": 0, "m": threading.Condition()})
    #         if size == self.file_size - start:
    #             break
    #         start += self.part_size

    def calculate_blocks(self):
        """
        根据文件大小和部分大小计算出需要下载的文件块信息
        :return:
        """
        start = 0
        while start < self.file_size:
            size = min(self.part_size, self.file_size - start)
            self.block_infos.append(
                {"status": None, "start": start, "size": size, "cur": 0, "m": threading.Condition()})
            start += size

    def terminate(self):
        """
        允许外部终止下载过程
        :return:
        """
        self.terminating = True
