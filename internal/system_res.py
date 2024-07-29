# 集中定义一些退出程序前需要关闭的资源
import os
import threading
from concurrent.futures import ThreadPoolExecutor as Pool
from diskcache import Cache
from collections import deque

current_path = os.path.abspath(os.path.dirname(__file__))

# 全局标志位，用于通知任务终止
stop_event = threading.Event()

dir_info_pool = Pool(10)
dir_info_buffer = Cache(os.path.join(current_path, '../cache/buffer-batchmeta'))
dir_info_dir_buffer = Cache(os.path.join(current_path, '../cache/dir_buffer-buffer-batchmeta'))
dir_info_traversed_folder = Cache(os.path.join(current_path, '../cache/traversed-folder'))

temp_fs_cache_path = os.path.join(current_path, '../cache/temp-fs')
if os.path.exists(temp_fs_cache_path):
    temp_fs_cache = Cache(temp_fs_cache_path)
else:
    temp_fs_cache = Cache(temp_fs_cache_path)
    temp_fs_cache['size'] = 0  # 当前缓存占用大小


mount_thread = {}


def close_system_res():
    stop_event.set()
    dir_info_buffer.close()
    dir_info_dir_buffer.close()
    dir_info_traversed_folder.close()
    temp_fs_cache.close()
    print('system resources closed')
    dir_info_pool.shutdown(wait=True)
    print('dir_info_pool closed')
    # Todo 关闭挂载线程
