import ctypes
import logging
import os
import threading
import time
import traceback

import requests

import requests
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from easydict import EasyDict
from requests import Request
from collections import defaultdict
from api import baiduNetdiskApi

session = requests.Session()
queue = Queue()
# 手动创建线程池
pool = ThreadPoolExecutor(max_workers=40)  # 可以指定最大工作线程数
task_count = defaultdict(int)  # 用来保存每个文件的下载任务数, 文件写出后减一， 为0时删除文件句柄


# 需要不停的从队列中取出数据，然后写出到文件中
def write_file():
    print("写出线程启动")
    file_handler = {}  # 用来保存文件句柄
    while True:
        item = queue.get()
        # 拿出队列项目中的fs_id（文件id）, block_infos（对应文件分块信息）,
        # part_index（当前块index）, resp.content（当前块内容）
        if item.file_obj.fs_id not in file_handler:
            # 文件存储位置应当是"/tmp/{fs_id}.tmp"
            # 按理说会先触发open_preload，所以这里先不加判断 Todo
            if not os.path.exists(f"./temp/{item.file_obj.fs_id}.tmp"):
                open(f"./temp/{item.file_obj.fs_id}.tmp", "wb").close()
            file_handler[item.file_obj.fs_id] = open(f"./temp/{item.file_obj.fs_id}.tmp", "r+b")
        file_handler[item.file_obj.fs_id].seek(item.file_obj.block_infos[item.part_index]["start"])
        file_handler[item.file_obj.fs_id].write(item.content)
        file_handler[item.file_obj.fs_id].flush()
        print("写出完成：", item.part_index, item.file_obj.fs_id)
        item.file_obj.block_infos[item.part_index]["status"] = "Complete"
        # print("我以为的", item.file_obj.block_infos)
        # 判断fs_id是否还有未写出的数据，如果没有则关闭文件
        task_count[item.file_obj.fs_id] -= 1
        if task_count[item.file_obj.fs_id] == 0:
            file_handler[item.file_obj.fs_id].close()
            del file_handler[item.file_obj.fs_id]

        queue.task_done()  # 标记任务完成


# 启动写出线程
write_thread = threading.Thread(target=write_file).start()


class File:
    # base_size = 65536 * 4 * 4  # 256KB
    base_size = 1024 * 1024  # 1MB

    def __init__(self, total_size, fs_id, dlink):
        self.total_size = total_size  # 总大小
        self.fs_id = fs_id  # 文件id
        self.dlink = dlink  # 下载链接
        self.last_access_time = time.time()  # 最后访问时间
        self.part_size = self.base_size  # 预设分块大小
        self.block_infos = []
        """
        一个文件块的状态（status）包括：
            1. None: 未下载，初始化完成
            2. Wait: 等待下载，推入下载队列，线程池仍未处理
            3. Downloading: 下载中，线程池处理中
            4. Downloaded: 下载完成，等待写出
            5. Complete: 写出完成，文件块准备就绪
        """
        self.block_infos.append({"status": None, "start": 0, "size": min(self.base_size, self.total_size)})
        self.access_size = 0  # 已访问大小, 访问超过1MB的文件时，会触发下载完整的文件
        self.file_handler = None  # 文件句柄
        self.file_handler_time = 0  # 文件句柄最后访问时间

    def request(self, parts_index):
        """
        构造请求

        :param parts_index:
        :return:
        """

        def download_part(prepped, file_obj, part_index):
            file_obj.block_infos[part_index]["status"] = "Downloading"  # 标记为下载中
            resp = session.send(prepped)
            file_obj.block_infos[part_index]["status"] = "Downloaded"  # 标记为下载完成
            print("块下载完成：", part_index, file_obj.fs_id, resp.content[0:7])
            # fs_id（文件id）, block_infos（对应文件分块信息）,
            # part_index（当前块index）, resp.content（当前块内容）
            queue.put(EasyDict({"file_obj": file_obj, "part_index": part_index, "content": resp.content}))

        for part_index in parts_index:
            part_info = EasyDict(self.block_infos[part_index])
            headers = {
                "Range": f"bytes={part_info.start}-{part_info.start + part_info.size - 1}",
                "User-Agent": "pan.baidu.com"
            }
            req = Request('GET', self.dlink, headers=headers)
            prepped = req.prepare()
            self.block_infos[part_index]["status"] = "Wait"
            pool.submit(download_part, prepped, self, part_index)
            task_count[self.fs_id] += 1

        # 更新当前文件的最后访问时间， 防止被删除
        self.last_access_time = time.time()

    def open_preload(self):
        """
        预加载
        :return:
        """
        if not os.path.exists("./temp"):
            os.mkdir("./temp")
        # 预分配文件空间
        saved_path = f"./temp/{self.fs_id}.tmp"
        print("total_size:::", self.total_size)
        if not os.path.exists(saved_path):
            open(saved_path, "wb").close()
        if self.file_handler is None:  # 如果文件句柄不存在，则创建
            self.file_handler = open(saved_path, "r+b")
            self.file_handler_time = time.time()
        # self.file_handler.seek(self.total_size - 1)
        # self.file_handler.write(b'\0')
        # self.file_handler.flush()
        # 获取文件句柄
        # handle = self.file_handler.fileno()
        # # 设置文件指针
        # result = ctypes.windll.kernel32.SetFilePointer(handle, self.total_size - 1, None, 0)
        # if result == 0xFFFFFFFF:
        #     raise ctypes.WinError()
        # # 设置文件末尾，从而扩展文件大小
        # if not ctypes.windll.kernel32.SetEndOfFile(handle):
        #     print("写出失败！", self.file_handler, handle)
        #     raise ctypes.WinError()
        # print("写出完毕！")
        # 预加载min(base_size, total_size)大小的数据
        self.request([0])  # 预加载第一个块

        # def func():
        #     # 预分配文件空间
        #     saved_path = f"temp/{self.fs_id}.tmp"
        #     if self.file_handler is None:  # 如果文件句柄不存在，则创建
        #         self.file_handler = open(saved_path, "wb")
        #     self.file_handler.seek(self.total_size - 1)
        #     self.file_handler.write(b'\0')
        #     # 预加载min(base_size, total_size)大小的数据
        #     self.request([0])  # 预加载第一个块
        #
        # # 调用线程执行函数
        # threading.Thread(target=func).start()

    def download(self):
        """
        下载整个文件
        :return:
        """

        def fun():
            # 遍历还没有推入线程池的块
            indexs = []
            for index, block_info in enumerate(self.block_infos):
                if block_info["status"] is None:
                    indexs.append(index)
            self.request(indexs)

        print("开始下载整个文件")

        threading.Thread(target=fun).start()

    def find_need_parts_indexes(self, start, size):
        """
        使用二分查找，查找从start开始，长度为size的内容落在哪些block_info的范围内，并返回这些block_info的索引列表。
        假设self.block_infos已经按照start键排序。
        """
        left, right = 0, len(self.block_infos) - 1
        need_parts_index = []

        # 找到第一个可能重叠的块
        while left <= right:
            mid = (left + right) // 2
            block_info = self.block_infos[mid]
            block_end = block_info["start"] + block_info["size"]

            if block_end >= start:
                right = mid - 1
            else:
                left = mid + 1

        # left现在指向第一个可能重叠的块或其后的块
        # 从left开始向后遍历，直到块的开始位置大于start + size
        end = start + size
        i = left
        while i < len(self.block_infos) and self.block_infos[i]["start"] <= end:
            need_parts_index.append(i)
            i += 1

        print("查找完了，返回", need_parts_index)
        return need_parts_index

    def readPartSync(self, start, size):
        """
        同步读取部分数据

        :param start:
        :param size:
        :return:
        """

        def check_status(need_parts_index):
            # print("开始检测状态", self.block_infos)
            flag = True  # 出事标记假设所有块都已经下载完成
            for i in need_parts_index:
                if self.block_infos[i]["status"] != "Complete":
                    flag = False
                    # 处理这个块的状态
                    if self.block_infos[i]["status"] is None:  # 还没准备下载的，推入线程池等待下载
                        self.request([i])
            return flag

        self.access_size += size  # 更新已访问大小

        # 判断当前文件是否完成了分块, 拿出最后一块的信息和文件总大小比较
        if self.block_infos[-1]["start"] + self.block_infos[-1]["size"] < self.total_size:
            # 先根据要求的size来调整part_size
            self.set_part_size(size)
            self.calculate_blocks()
        # 计算所需要的数据保存在哪些块中
        need_parts_index = self.find_need_parts_indexes(start, size)

        # 查看这些块的状态，如果有未下载的块，则等待下载完成
        while not check_status(need_parts_index):
            logging.debug(f"【readPartSync】waiting for {self.fs_id} to download")
            time.sleep(0.1)

        # 如果访问超过1MB的文件，触发下载整个文件（异步操作）
        if self.access_size > 1024 * 1024:
            self.download()

        # 更新当前文件的最后访问时间， 防止被删除
        self.last_access_time = time.time()

        # 读取数据
        if self.file_handler is None:
            self.file_handler = open(f"./temp/{self.fs_id}.tmp", "rb")
            self.file_handler_time = time.time()

        self.file_handler.seek(start)
        data = b""
        try:
            data = self.file_handler.read(size)
        except Exception as e:
            print("读取数据失败:", str(e), self.file_handler, start, size)
            print("异常类型:", type(e).__name__)
            traceback.print_exc()
        print("成功读取数据", data[0:7])
        return data

    def set_part_size(self, part_size):
        """
        根据传入的值得到一个不小于base_size的值

        :param part_size:
        :return:
        """
        if part_size >= self.base_size:
            self.part_size = part_size
            return

        i = 2
        while part_size * i < self.base_size:
            i += 1

        self.part_size = part_size * i

    def calculate_blocks(self):
        """
        根据文件大小和部分大小计算出需要下载的文件块信息
        :return:
        """
        start = self.base_size
        while start < self.total_size:
            size = min(self.part_size, self.total_size - start)
            self.block_infos.append({"status": None, "start": start, "size": size})
            start += size

    def close_file_handler(self):
        # 如果文件句柄超过30秒没有访问，则关闭文件句柄
        # 这是为了防止线程正在使用文件句柄时，文件句柄被关闭
        if time.time() - self.file_handler_time > 30:
            if self.file_handler:
                self.file_handler.close()
                self.file_handler = None


class FileManager:
    def __init__(self):
        self.files = {}
        self._opening = []  # 正在打开的文件

    def open(self, path):
        def fun():
            fs_id = baiduNetdiskApi.path_to_fsid(path)
            file_info = baiduNetdiskApi.files(fs_id, dlink=1).list[0]
            print("file_info:::-----", file_info)
            dlink = baiduNetdiskApi.get_final_download_link(file_info.dlink)
            file = File(file_info.size, fs_id, dlink)
            file.open_preload()
            self.files[path] = file
            self._opening.remove(path)

        if path not in self.files and path not in self._opening:
            print(self.files, self._opening, "不在其中", path)
            self._opening.append(path)  # 添加到正在打开的文件列表
            threading.Thread(target=fun).start()

    def getFile(self, path):
        if path not in self.files:  # 文件还没打开
            # 如果文件不在任务队列，就立刻准备打开
            if path not in self._opening:
                self.open(path)

            # 等待文件打开完毕
            while path not in self.files:
                logging.debug(f"【getFile】waiting for {path} to open")
                time.sleep(0.1)

        return self.files[path]


fileManager = FileManager()
