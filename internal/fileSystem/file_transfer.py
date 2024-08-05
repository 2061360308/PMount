import os
import traceback
from enum import Enum

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from time import time, sleep
from .temp_fs import tempFs
from blinker import signal
from internal.server.device import Device

from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QGuiApplication, QIcon, QFont, Qt
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QSizePolicy,
                               QSpacerItem, QVBoxLayout, QWidget)
from qfluentwidgets import ProgressBar, StrongBodyLabel, CaptionLabel, FluentIcon
import res.resource_rc

CHUNK_SIZE = 1024 * 128  # 每次下载的数据块大小

SEGMENT_COUNT = 4  # 分片下载时分片的数量

MAX_RETRIES = 3  # 最大重试次数

MAX_WORKS = 4  # 同时下载的任务数


class DownloadStatus(Enum):
    PENDING = 0  # 等待下载
    PREPARING = 1  # 准备下载  (通过初始化请求获取文件大小、分配缓存空间等)
    DOWNLOADING = 1  # 下载中
    COMPLETED = 2  # 下载完成
    FAILED = 3  # 下载失败
    RETRYING = 4  # 重试中


class Segment:
    def __init__(self):
        self.index = None
        self.start = 0
        self.end = 0
        self.downloaded = 0
        self.speed = 0

    def init(self, index, start, end):
        self.index = index
        self.start = start
        self.end = end


class DownloadTask:
    def __init__(self, device, device_fp):
        """

        :param device: 设备对象
        :param device_fp: 文件在设备中路径
        """
        if not isinstance(device, Device):
            raise ValueError("device参数必须是Device对象")
        self.device = device
        self.device_fp = device_fp
        self._url = None  # 文件下载链接
        self.size = None  # 文件大小
        self.temp_fp = None  # 缓存系统中申请到的文件路
        self.speed = 0  # 下载速度(单位: 字节/秒)
        self.status = DownloadStatus.PENDING  # 下载状态
        self.retries = 0  # 重试次数

        self.supports_range = False  # 是否支持分片下载
        self.segments = [Segment() for _ in range(SEGMENT_COUNT)]  # 初始化分片进度
        self.downloaded = 0  # 下载的字节数，只有在不支持分片下载时才会用到

    @property
    def url(self):
        if self._url is None:
            self._url = self.device.driver.download_url(self.device_fp)
        return self._url

    @property
    def headers(self):
        return self.device.driver.headers

    @property
    def destination(self):
        if self.temp_fp is None:
            suffix = os.path.splitext(self.device_fp)[-1]
            if tempFs.has(self.device.name, self.device_fp):
                tempFs.remove(self.device.name, self.device_fp)
            self.temp_fp = tempFs.allocate(self.device.name, self.device_fp, self.size, suffix)
        return self.temp_fp

    @property
    def segment_size(self):
        if self.size:
            return self.size // SEGMENT_COUNT
        else:
            raise ValueError("文件大小未知")

    @property
    def process(self):
        """
        百分比下载进度
        :return:
        """
        if self.size is None:
            return 0

        if self.supports_range:  # 如果支持分片下载，计算分片总进度
            return sum(segment.downloaded for segment in self.segments) / self.size * 100
        else:
            return self.downloaded / self.size * 100

    @property
    def format_speed(self):
        """
        格式化下载速度
        :return:
        """
        if self.supports_range:
            speed = sum(segment.speed for segment in self.segments)
        else:
            speed = self.speed

        if speed < 1024:
            return f"{speed:.2f} B/s"
        elif speed < 1024 ** 2:
            return f"{speed / 1024:.2f} KB/s"
        else:
            return f"{speed / 1024 ** 2:.2f} MB/s"

    @property
    def format_size(self):
        """
        格式化文件大小
        :return:
        """
        if self.size is None:
            return "未知"

        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 ** 2:
            return f"{self.size / 1024:.2f} KB"
        elif self.size < 1024 ** 3:
            return f"{self.size / 1024 ** 2:.2f} MB"
        elif self.size < 1024 ** 4:
            return f"{self.size / 1024 ** 3:.2f} GB"
        else:
            return f"{self.size / 1024 ** 4:.2f} TB"

    @property
    def residue_time(self):
        """
        剩余时间
        :return:
        """
        if self.supports_range:
            speed = sum(segment.speed for segment in self.segments)
            downloaded = sum(segment.downloaded for segment in self.segments)
        else:
            speed = self.speed
            downloaded = self.downloaded

        if speed == 0:
            return "未知"

        residue_time = (self.size - downloaded) / speed
        if residue_time < 60:
            return f"{residue_time:.1f} 秒"
        elif residue_time < 3600:
            return f"{residue_time / 60:.1f} 分"
        elif residue_time < 86400:
            return f"{residue_time / 3600:.2f} 时"
        else:
            return f"{residue_time / 86400:.2f} 天"

    @property
    def residue_size(self):
        """
        剩余时间
        :return:
        """
        if self.size is None:
            return "未知"

        if self.supports_range:
            residue_size = self.size - sum(segment.downloaded for segment in self.segments)
        else:
            residue_size = self.size - self.downloaded

        if residue_size < 1024:
            return f"{residue_size} B"
        elif residue_size < 1024 ** 2:
            return f"{residue_size / 1024:.2f} KB"
        elif residue_size < 1024 ** 3:
            return f"{residue_size / 1024 ** 2:.2f} MB"
        elif residue_size < 1024 ** 4:
            return f"{residue_size / 1024 ** 3:.2f} GB"
        else:
            return f"{residue_size / 1024 ** 4:.2f} TB"


class DownloadDialog(QWidget):
    def __init__(self):
        super(DownloadDialog, self).__init__()
        self.setupUi()

        self.setWindowTitle("下载任务")
        self.setFixedSize(400, 190)

        # 居中显示
        desktop = QGuiApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        self.setWindowIcon(QIcon(":/logo/logo/logo_32.ico"))
        # 设置窗口标志，禁用关闭按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)

    def showDialog(self, task):
        self.task = task
        self.updataDialog()
        # 创建 QTimer 对象
        self.timer = QTimer()
        self.timer.timeout.connect(self.updataDialog)
        self.timer.start(1000)
        self.show()

    def updataDialog(self):
        parentDir, fileName = os.path.split(self.task.device_fp)
        self.titleLabel.setText(f"    正在下载 {fileName}({self.task.format_size})")
        self.deviceLabel.setText(f"所属设备：{self.task.device.name}")
        self.pathLabel.setText(f"完整路径：{self.task.device_fp}")
        self.residueLabel.setText(f"剩余：       {self.task.residue_size}({self.task.residue_time})")
        self.speedLabel.setText(f"下载速度：{self.task.format_speed}")
        self.progressBar.setValue(int(self.task.process))
        if self.task.status == DownloadStatus.COMPLETED:
            self.timer.stop()
            self.close()

    def test(self):
        self.titleLabel.setText(f"    正在下载 测试文件(50Mb)")
        self.deviceLabel.setText(f"所属设备：百度网盘")
        self.pathLabel.setText(f"完整路径：E:/baidu/测试文件")
        self.residueLabel.setText(f"剩余：       26Mb(13秒)")
        self.speedLabel.setText(f"下载速度：5Mb/s")
        self.progressBar.setValue(50)
        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        # 移除窗口置顶标志
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def setupUi(self):
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.titleLabel = StrongBodyLabel(self)

        self.titleLabel.setObjectName(u"titleLabel")
        self.titleLabel.setStyleSheet("border-image: url(':/image/image/cyan_bg.png');")
        self.titleLabel.setScaledContents(True)

        self.verticalLayout.addWidget(self.titleLabel)

        self.widget = QWidget(self)
        self.widget.setObjectName(u"widget")
        self.widget.setStyleSheet(u"background-color: rgb(255, 255, 255);")
        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.deviceLabel = CaptionLabel(self.widget)
        self.deviceLabel.setObjectName(u"deviceLabel")

        self.verticalLayout_2.addWidget(self.deviceLabel)

        self.pathLabel = CaptionLabel(self.widget)
        self.pathLabel.setObjectName(u"pathLabel")

        self.verticalLayout_2.addWidget(self.pathLabel)

        self.residueLabel = CaptionLabel(self.widget)
        self.residueLabel.setObjectName(u"residueLabel")

        self.verticalLayout_2.addWidget(self.residueLabel)

        self.speedLabel = CaptionLabel(self.widget)
        self.speedLabel.setObjectName(u"speedLabel")

        self.verticalLayout_2.addWidget(self.speedLabel)

        self.progressBar = ProgressBar(self.widget)
        # 设置最小值和最大值
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setFixedHeight(14)
        self.progressBar.setValue(0)

        self.verticalLayout_2.addWidget(self.progressBar)

        self.verticalLayout.addWidget(self.widget)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.hideButton = QPushButton(self)
        self.hideButton.setIcon(FluentIcon.DOWN.icon())
        self.hideButton.setText("隐藏后台")
        self.hideButton.setIconSize(QSize(12, 12))
        self.hideButton.setFont(QFont("Microsoft YaHei", 9))
        self.hideButton.setFlat(True)
        self.hideButton.setObjectName(u"hideButton")

        self.horizontalLayout.addWidget(self.hideButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pauseButton = QPushButton(self)
        self.pauseButton.setText("暂停")
        self.pauseButton.setFixedSize(80, 30)
        self.pauseButton.setStyleSheet("font-size:13px;")
        self.pauseButton.setObjectName(u"pauseButton")

        self.horizontalLayout.addWidget(self.pauseButton)

        self.cancelButton = QPushButton(self)
        self.cancelButton.setText("取消")
        self.cancelButton.setFixedSize(80, 30)
        self.cancelButton.setStyleSheet("font-size:13px;")
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout.addWidget(self.cancelButton)

        self.verticalLayout.addLayout(self.horizontalLayout)


class FileTransferManager:
    taskComplete = signal("FileTransferTaskComplete")

    def __init__(self):
        """

        :param max_workers: 同时下载的任务数
        :param max_retries: 最大重试次数
        :param segment_count: 分片下载时分片的数量
        """
        self.tasks = []  # 任务列表
        self.failed_tasks = []  # 失败的任务列表
        self.lock = Lock()  # 用于保护任务列表的锁
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKS)  # 线程池

    def add(self, device, device_fp):
        """
        添加下载任务
        :param device: 设备对象
        :param device_fp: 设备文件路径
        :return:
        """
        task = DownloadTask(device, device_fp)
        self.tasks.append(task)
        self.executor.submit(self._download_task, task)
        return task

    def get_tasks(self):
        return self.tasks

    def get_failed_tasks(self):
        return self.failed_tasks

    def _download_task(self, task: DownloadTask):
        url = task.url
        headers = task.headers

        while task.retries <= MAX_RETRIES:
            try:
                response = requests.head(url, headers=headers, allow_redirects=True)
                if not (200 <= response.status_code < 400):
                    raise Exception(f"Unexpected status code: {response.status_code}")

                file_size = int(response.headers.get('content-length', 0))  # 获取文件大小
                task.size = file_size

                supports_range = response.headers.get('accept-ranges', '') == 'bytes'  # 是否支持分片下载
                task.supports_range = supports_range

                if task.supports_range:
                    self._download_in_segments(task)  # 分片下载
                else:
                    self._download_single(task)  # 直接下载

                task.status = DownloadStatus.COMPLETED
                self.taskComplete.send(task)  # 任务完成发送信号
                break
            except Exception as e:
                print(e)
                # 打印详细的错误位置
                traceback.print_exc()

                task.retries += 1
                task.status = DownloadStatus.FAILED
                if task.retries > MAX_RETRIES:
                    with self.lock:
                        self.failed_tasks.append(task)
                    self.taskComplete.send(task)  # 任务失败发送信号
                    # 失败后清除缓存文件
                    tempFs.has(task.device.name, task.device_fp) and tempFs.remove(task.device.name, task.device_fp)
                    task.temp_fp = None
                else:
                    task.status = DownloadStatus.RETRYING

    def _download_single(self, task: DownloadTask):
        """
        直接下载整个文件
        :param task:
        :return:
        """
        url = task.url
        destination = task.destination
        headers = task.headers

        start_time = time()
        response = requests.get(url, headers=headers, stream=True)
        total_length = response.headers.get('content-length')

        # 标记任务已开始
        task.status = DownloadStatus.DOWNLOADING

        with open(destination, 'wb') as f:
            if total_length is None:
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=CHUNK_SIZE):
                    dl += len(data)
                    f.write(data)
                    task.downloaded = dl  # 更新下载的字节
                    task.speed = dl / (time() - start_time)

    def _download_in_segments(self, task: DownloadTask):
        """
        分片下载文件 (分配任务)
        :param task:  任务对象
        :return:
        """
        destination = task.destination
        futures = []

        # 创建一个空文件，并设置文件大小，以便后续写入
        with open(destination, 'wb') as f:
            f.truncate(task.size)

        task.status = DownloadStatus.DOWNLOADING

        # 为每个分片创建一个线程
        for i in range(SEGMENT_COUNT):
            start = i * task.segment_size
            end = start + task.segment_size - 1 if i < SEGMENT_COUNT - 1 else task.size - 1
            task.segments[i].init(i, start, end)
            futures.append(self.executor.submit(self._download_segment, i, task))

        for future in as_completed(futures):
            future.result()

    def _download_segment(self, index, task: DownloadTask):
        """
        下载分片
        :param task: 任务对象
        :return:
        """
        segment = task.segments[index]

        start_time = time()
        segment_headers = task.headers.copy()
        segment_headers['Range'] = f'bytes={segment.start}-{segment.end}'
        response = requests.get(task.url, headers=segment_headers, stream=True)

        segment_size = segment.end - segment.start + 1
        downloaded = 0

        with open(task.destination, 'r+b') as f:
            f.seek(segment.start)
            for data in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(data)
                downloaded += len(data)
                segment.downloaded = downloaded
                # task['segment_progress'][segment_index] = downloaded / segment_size * 100
                # task['progress'] = sum(task['segment_progress']) / self.segment_count
                segment.speed = downloaded / (time() - start_time)

        segment.speed = 0  # 下载完成后速度置为0


fileTransferManager = FileTransferManager()