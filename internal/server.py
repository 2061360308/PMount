# 启动服务
import ctypes
import os.path
import threading

from fuse import FUSE, _libfuse

from internal import context
from internal.cloud_fs import CloudFS

from internal.driver import drivers_obj

from config import config, use_device

from internal.system_res import mount_thread, stop_event


def mount_node(name, mount):
    fs = CloudFS(name, mount)
    try:
        if stop_event.is_set():
            print("停止挂载")
            return
        FUSE(fs, mount, foreground=False, nothreads=True, nonempty=False, async_read=False, raw_fi=False)

    except Exception as e:
        print(e)
        print(f"挂载失败，请检查是否有其他程序占用了该盘符{mount}, {name}")


class Server:
    def __init__(self):
        self.mountNodes = {}  # 当前登记的可挂载的节点
        if config.disk:
            for item in config.disk:
                self.mountNodes[item.name] = {
                    'use': item.use,
                    'mount': item.mount,
                    'type': item.type,
                    'state': "等待挂载" if item.use else "未启用"
                }

            # self.mount_thread = {}

    def start(self, join=False):
        for name, item in self.mountNodes.items():
            if item['use'] and (name not in context.fuse_ptrs):
                # 检查这个目录是否被占用
                path = os.path.split(item['mount'])
                if os.path.exists(item['mount']):
                    self.mountNodes[name]['state'] = "挂载失败"
                    print(f"目录 {path} 已被占用")
                    continue
                # 创建前置目录
                if not os.path.exists(path[0]):
                    os.makedirs(path[0])
                fs_thread = threading.Thread(target=mount_node, args=(name, item['mount']))
                self.mountNodes[name]['state'] = "已挂载"
                # mount_thread[name] = fs_thread
                fs_thread.start()

        if join:
            for name, thread in mount_thread.items():
                thread.join()

    def updateMountNodes(self):
        current_nodes = []

        for item in config.disk:
            current_nodes.append(item.name)
            if item.name not in self.mountNodes:
                self.mountNodes[item.name] = {
                    'use': item.use,
                    'mount': item.mount,
                    'type': item.type,
                    'state': "等待挂载" if item.use else "未启用"
                }
            else:
                self.mountNodes[item.name]['use'] = item.use
                self.mountNodes[item.name]['mount'] = item.mount

        # 删除不存在的节点
        del_nodes = []

        for name in current_nodes:
            if name not in self.mountNodes:
                del self.mountNodes[name]

    def use(self, name):
        """
        启用一个设备
        :param name:
        :return:
        """
        use_device(name, True)
        self.mountNodes[name]['use'] = True
        self.mountNodes[name]['state'] = "等待挂载"
        self.start()

    def stop(self, name):
        if name in context.fuse_ptrs:
            use_device(name, False)
            self.mountNodes[name]['use'] = False
            self.mountNodes[name]['state'] = "未启用"
            _libfuse.fuse_exit(context.fuse_ptrs[name])
            del context.fuse_ptrs[name]


server = Server()
