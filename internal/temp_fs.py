import queue
from hashlib import md5 as hashlib_md5
import os

from config import config
import shelve
from collections import deque
import asyncio

current_path = os.path.abspath(os.path.dirname(__file__))


class TempFs:
    """
    用于缓存文件的目录映射和ALU更新
    """

    def __init__(self):
        self.root = config.temp.file.ROOT  # 缓存根目录
        self.max_size = config.temp.file.MAX_SIZE  # 缓存占用最大大小
        self.timeout = config.temp.file.TIMEOUT  # 缓存超时时间
        self.meta_file = os.path.join(current_path, '../file_cache_meta.db')  # 缓存元数据文件

        if not os.path.exists(self.root):
            os.makedirs(self.root)

        if os.path.exists(self.meta_file):
            # 打开一个 shelve 文件
            self.meta = shelve.open(self.meta_file)
        else:
            open(self.meta_file, 'w+').close()
            self.meta = shelve.open(self.meta_file)
            self.meta['weight'] = deque()  # 缓存文件的访问权重, 用于淘汰策略
            self.meta['size'] = 0  # 当前缓存占用大小

    def __del__(self):
        # 关闭 shelve 文件
        self.meta.close()

    @staticmethod
    def generate_key(driver_name, uid):
        key = f'{driver_name}@@{uid}'
        return hashlib_md5(key.encode()).hexdigest()

    @staticmethod
    async def remove_file_sync(file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

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

        # 生成一个文件路径
        file_path = os.path.join(self.root, key[:2], key[2:4] + suffix)
        # 储存文件元信息
        data = {
            'path': file_path,
            'size': size,
        }
        if md5:
            data['md5'] = md5
        self.meta[key] = data
        weight = self.meta['weight']
        weight.appendleft(key)
        self.meta['weight'] = weight
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
        weight = self.meta['weight']
        key = weight.pop()
        self.meta['weight'] = weight

        file_path = self.meta[key]['path']
        self.remove_file_sync(file_path)
        self.meta['size'] -= self.meta[key]['size']
        del self.meta[key]

    def update_weight(self, key):
        """
        更新缓存文件的权重

        :param key: 缓存文件的 key
        """
        weight = self.meta['weight']
        weight.remove(key)
        weight.appendleft(key)
        self.meta['weight'] = weight

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
        self.update_weight(key)  # 更新权重

        self.meta[key]['size'] = size  # 更新文件元信息
        if md5:
            self.meta[key]['md5'] = md5
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
        weight = self.meta['weight']
        weight.remove(key)
        self.meta['weight'] = weight
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
