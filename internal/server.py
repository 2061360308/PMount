# 启动服务
import os.path
import threading

from fuse import FUSE

from internal.cloud_fs import CloudFS

from internal.driver import drivers_obj

from config import config

from internal.system_res import mount_thread, stop_event


def mount_node(name, mount):
    fs = CloudFS(name, mount)
    try:
        if stop_event.is_set():
            print("停止挂载")
            return
        FUSE(fs, mount, foreground=True, nonempty=False, async_read=True, raw_fi=True)
    except Exception as e:
        print(e)
        print(f"挂载失败，请检查是否有其他程序占用了该盘符{mount}, {name}")


class Server:
    def __init__(self):
        self.mountNodes = {}  # 当前已挂载的节点

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
            if item['use']:
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
                mount_thread[name] = fs_thread
                fs_thread.start()

        if join:
            for name, thread in mount_thread.items():
                thread.join()


server = Server()
