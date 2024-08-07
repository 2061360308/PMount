import asyncio
import queue
import threading
import time
from collections import deque
from hashlib import md5 as hashlib_md5
import os

from config import config
from internal.system_res import temp_fs_cache

current_path = os.path.abspath(os.path.dirname(__file__))


class TempFs:
    """
    用于缓存文件的目录映射和ALU更新
    """

    def __init__(self):
        self.root = config.temp.file.ROOT  # 缓存根目录
        self.max_size = config.temp.file.MAX_CACHE_SIZE * 1024 * 1024 * 1024  # 缓存占用最大大小
        self.timeout = config.temp.file.CACHE_TIMEOUT  # 缓存超时时间

        if not os.path.exists(self.root):
            os.makedirs(self.root)

        self.meta = temp_fs_cache  # 缓存文件元信息
        self.weight = self.build_weight()  # 重建权重队列，用于淘汰策略

    @staticmethod
    def generate_key(driver_name, uid):
        key = f'{driver_name}@@{uid}'
        return hashlib_md5(key.encode()).hexdigest()

    @staticmethod
    def remove_file_sync(file_path):
        def func():
            if os.path.exists(file_path):
                os.remove(file_path)
        threading.Thread(target=func).start()

    def build_weight(self):
        """
        重建权重队列
        :return:
        """
        weight = deque()
        # 按时间戳升序排序并只保留键
        # for key in self.meta:
        #     print("输出：：", key)
        #     print(key, self.meta[key]['time'], type(self.meta[key]['time']))
        # print('meta::', self.meta)
        sorted_keys = sorted(
            (key for key in self.meta if key != 'size'),
            key=lambda k: self.meta[k]['time']
        )
        # 创建队列，最新的时间戳在最左侧
        for key in sorted_keys:
            weight.appendleft(key)

        return weight

    def allocate(self, driver_name: str, uid, size: int, suffix: str = "", md5=None) -> str:
        """
        为文件分配一个缓存路径，如果缓存空间不足会根据缓存文件的访问权重淘汰一部分文件

        返回在缓存目录为其分配的文件路径

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        :param size: 文件大小，单位为字节
        :param suffix: 文件后缀,可选，如果传入会在返回的文件路径中添加后缀，方便后续直接查看缓存文件
        :param md5: 可以附加存储的md5，对于TempFs来说，这个参数没有意义，但是可以通过 get_md5 方法获取到
        :return: 分配的文件路径
        """
        # 验证剩余空间是否足够
        if self.meta['size'] + size > self.max_size:
            # 淘汰一部分文件
            while self.meta['size'] + size > self.max_size:
                self.pop()

        # 利用driver_name和uid生成一个唯一的key
        key = self.generate_key(driver_name, uid)

        if key in self.meta:
            raise KeyError(f'key {driver_name} and {uid} already exists')

        # 验证传入的后缀
        if suffix != "":
            if not suffix.startswith('.'):
                suffix = '.' + suffix

        # 添加到权重队列开头
        if key not in self.weight:
            self.weight.appendleft(key)

        # 生成一个文件路径
        file_path = os.path.join(self.root, key[:2], key[2:] + suffix)
        # 储存文件元信息
        data = {
            'path': file_path,
            'size': size,
            'time': time.time(),
        }
        if md5:
            data['md5'] = md5
        self.meta[key] = data
        self.meta['size'] += size

        # 创建文件夹
        file_dir = os.path.split(file_path)[0]
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        return file_path

    def pop(self):
        """
        弹出一个缓存文件

        :param key: 缓存文件的 key
        :return: 缓存文件的路径
        """
        key = self.weight.pop()

        file_path = self.meta[key]['path']
        self.remove_file_sync(file_path)
        self.meta['size'] -= self.meta[key]['size']
        del self.meta[key]

    def update_weight(self, key):
        """
        更新缓存文件的权重

        :param key: 缓存文件的 key
        """
        # 更新权重队列
        self.weight.remove(key)
        self.weight.appendleft(key)

        # 更新时间戳
        data = self.meta[key]
        data['time'] = time.time()
        self.meta[key] = data

    def update(self, driver_name: str, uid, size: int, md5=None):
        """
        更新缓存文件的大小

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        :param size: 文件大小，单位为字节
        :param md5: 可以附加存储的md5，对于TempFs来说，这个参数没有意义，但是可以通过 get_md5 方法获取到
        """
        if size > self.max_size:
            raise ValueError('size is too large')

        key = self.generate_key(driver_name, uid)
        if key not in self.meta:
            raise KeyError(f'key {driver_name} and {uid} not exists')
        self.update_weight(key)  # 更新权重

        data = self.meta[key]
        data['size'] = size  # 更新文件元信息
        if md5:
            data['md5'] = md5
        data['time'] = time.time()
        self.meta[key] = data
        old_size = self.meta[key]['size']
        # 计算差值
        diff = size - old_size
        self.meta['size'] += diff  # 更新缓存占用大小
        if self.meta['size'] > self.max_size:
            # 淘汰一部分文件
            while self.meta['size'] > self.max_size:
                self.pop()

    def remove(self, driver_name: str, uid):
        """
        移除缓存文件

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        """
        key = self.generate_key(driver_name, uid)

        if key not in self.meta:
            raise KeyError(f'key {driver_name} and {uid} not exists')

        self.remove_file_sync(self.meta[key]['path'])
        self.meta['size'] -= self.meta[key]['size']
        self.weight.remove(key)
        del self.meta[key]

    def get_md5(self, driver_name: str, uid):
        """
        获取保存缓存文件的时候传入的md5

        只有分配空间的时候传入了md5，这个方法才会返回正确的值，否则返回None

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        :return: 缓存文件的uuid
        """
        key = self.generate_key(driver_name, uid)
        if key not in self.meta:
            raise KeyError(f'key {driver_name} and {uid} not exists')
        return self.meta[key].get('md5', None)

    def has(self, driver_name: str, uid):
        """
        判断是否存在缓存文件

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        :return: 是否存在
        """
        key = self.generate_key(driver_name, uid)
        return key in self.meta

    def use(self, driver_name: str, uid):
        """
        使用缓存文件

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        """
        key = self.generate_key(driver_name, uid)

        if key not in self.meta:
            raise KeyError(f'key {driver_name} and {uid} not exists')

        self.update_weight(key)

    def get(self, driver_name: str, uid) -> str:
        """
        获取缓存文件的路径

        :param driver_name: 存储方案的名称
        :param uid: 对应的文件的唯一标识符，只要在当前存储方案中唯一即可，可以是文件的路径，或者是文件的 hash 值
        :return: 缓存文件的路径
        """
        key = self.generate_key(driver_name, uid)

        if key not in self.meta:
            raise KeyError(f'key {driver_name} and {uid} not exists')

        self.update_weight(key)
        return self.meta[key]['path']


tempFs = TempFs()
