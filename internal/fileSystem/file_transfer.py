import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from time import time, sleep

CHUNK_SIZE = 1024 * 128  # 每次下载的数据块大小


class FileTransferManager:
    def __init__(self, max_workers=4, max_retries=3, segment_count=4):
        """

        :param max_workers: 同时下载的任务数
        :param max_retries: 最大重试次数
        :param segment_count: 分片下载时分片的数量
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.segment_count = segment_count
        self.tasks = []  # 任务列表
        self.failed_tasks = []  # 失败的任务列表
        self.lock = Lock()  # 用于保护任务列表的锁
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # 线程池

    def add_task(self, url, destination, headers=None):
        """
        添加下载任务
        :param url: 链接
        :param destination: 下载后文件的保存路径
        :param headers: 自定义的请求头
        :return:
        """
        task = {
            'url': url,
            'destination': destination,
            'headers': headers or {},
            'progress': 0,
            'speed': 0,
            'status': 'pending',
            'retries': 0,
            'segment_progress': [0] * self.segment_count  # 初始化分片进度
        }
        self.tasks.append(task)
        self.executor.submit(self._download_task, task)

    def get_tasks(self):
        return self.tasks

    def get_failed_tasks(self):
        return self.failed_tasks

    def _download_task(self, task):
        url = task['url']
        destination = task['destination']
        headers = task['headers']
        retries = 0

        while retries <= self.max_retries:
            try:
                response = requests.head(url, headers=headers, allow_redirects=True)
                if not (200 <= response.status_code < 400):
                    raise Exception(f"Unexpected status code: {response.status_code}")

                file_size = int(response.headers.get('content-length', 0))  # 获取文件大小
                supports_range = response.headers.get('accept-ranges', '') == 'bytes'  # 是否支持分片下载

                if supports_range:
                    self._download_in_segments(url, destination, file_size, task, headers)
                else:
                    self._download_single(url, destination, task, headers)

                task['status'] = 'completed'
                break
            except Exception as e:
                retries += 1
                task['retries'] = retries
                task['status'] = 'failed'
                if retries > self.max_retries:
                    with self.lock:
                        self.failed_tasks.append(task)
                else:
                    task['status'] = 'retrying'

    def _download_single(self, url, destination, task, headers):
        """
        直接下载整个文件
        :param url:
        :param destination:
        :param task:
        :param headers:
        :return:
        """
        start_time = time()
        response = requests.get(url, headers=headers, stream=True)
        total_length = response.headers.get('content-length')

        with open(destination, 'wb') as f:
            if total_length is None:
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=CHUNK_SIZE):
                    dl += len(data)
                    f.write(data)
                    task['progress'] = dl / total_length * 100
                    task['speed'] = dl / (time() - start_time)

    def _download_in_segments(self, url, destination, file_size, task, headers):
        """
        分片下载文件 (分配任务)
        :param url: 下载链接
        :param destination: 下载后文件的保存路径
        :param file_size:  文件大小
        :param task:  任务对象
        :param headers:  请求头
        :return:
        """
        segment_size = file_size // self.segment_count  # 计算每个分片的大小
        futures = []

        # 创建一个空文件，并设置文件大小，以便后续写入
        with open(destination, 'wb') as f:
            f.truncate(file_size)

        # 为每个分片创建一个线程
        for i in range(self.segment_count):
            start = i * segment_size
            end = start + segment_size - 1 if i < self.segment_count - 1 else file_size - 1
            futures.append(self.executor.submit(self._download_segment, url, destination, start, end, task, i, headers))

        for future in as_completed(futures):
            future.result()

    def _download_segment(self, url, destination, start, end, task, segment_index, headers):
        """
        下载分片
        :param url: 链接
        :param destination: 保存路径
        :param start: 开始位置
        :param end: 结束位置
        :param task: 任务对象
        :param segment_index: 分片索引
        :param headers: 请求头
        :return:
        """
        start_time = time()
        segment_headers = headers.copy()
        segment_headers['Range'] = f'bytes={start}-{end}'
        response = requests.get(url, headers=segment_headers, stream=True)

        segment_size = end - start + 1
        downloaded = 0

        with open(destination, 'r+b') as f:
            f.seek(start)
            for data in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(data)
                downloaded += len(data)
                task['segment_progress'][segment_index] = downloaded / segment_size * 100
                task['progress'] = sum(task['segment_progress']) / self.segment_count
                task['speed'] = downloaded / (time() - start_time)


# 示例使用
if __name__ == "__main__":
    manager = FileTransferManager(max_workers=4, max_retries=3, segment_count=4)
    headers = {
        'User-Agent': 'pan.baidu.com'
    }
    manager.add_task(
        #"http://bjbgp01.baidupcs.com/file/7402347a4o23ac30488672569174b9e6?bkt=en-d3a65691252603d39e631c6cd0b8992f69490790e268df1bbbe465997289adaa7d016d5a97aa7da6&fid=1102622167898-250528-693942807233165&time=1722446826&sign=FDTAXUbGERQlBHSKfWaqi-DCb740ccc5511e5e8fedcff06b081203-Q8%2F%2BBc23BSwNGML84E0g96b0%2BLE%3D&to=14&size=815070175&sta_dx=815070175&sta_cs=1&sta_ft=zip&sta_ct=4&sta_mt=4&fm2=MH%2CBaoding%2CAnywhere%2C%2C%E5%8C%97%E4%BA%AC%2Cany&ctime=1720456218&mtime=1720456218&resv0=-1&resv1=0&resv2=rlim&resv3=5&resv4=815070175&vuk=1102622167898&iv=2&vl=3&htype=&randtype=&tkbind_id=0&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-2e80b7e0052a0907d329229d8f7ddc96d95b14108b5a95b141f70fac12b6d341b46faada5245a2f0&expires=8h&rt=pr&r=636365071&vbdid=3977136403&fin=changnian.zip&rtype=1&dp-logid=3609893449190764887&dp-callid=0.1&tsl=0&csl=0&fsl=-1&csign=SLbmN3pVn8baCBwyvbG11fpdkyo%3D&so=1&ut=1&uter=0&serv=0&uc=1559654663&ti=e38f2d2f207d23152b63dbc2328fc128599ca904cacf7c21305a5e1275657320&hflag=30&from_type=1&adg=a_1e90462db47c19d159d8e554ba0225c9&reqlabel=25571201_f_3200ce5c487f6a001f08e0db8662371f_-1_17f75b2f34b2c77783959349da0a3890&by=themis",
        "http://152.136.139.116:5244/d/%E7%99%BE%E5%BA%A6%E7%BD%91%E7%9B%98/changnian.zip?sign=Aa6MnZ2jq9AebCeWEAYX8BrrFUwSvjZ1yAyTSRBkGSc=:0",
        "file.zip", headers=headers)

    time0 = time()

    while True:
        tasks = manager.get_tasks()
        for task in tasks:
            print(f"URL: {task['url']}")
            print(f"Destination: {task['destination']}")
            print(f"Progress: {task['progress']:.2f}%")
            print(f"Speed: {task['speed']:.2f} bytes/sec")
            print(f"Status: {task['status']}")
            print(f"Retries: {task['retries']}")
            print("-" * 20)

        # 检查是否所有任务都完成
        if all(task['status'] == 'completed' for task in tasks):
            print("所有任务已完成")
            break

        # 每隔一段时间检查一次进度
        sleep(8)

    print("总用时：", time() - time0)
