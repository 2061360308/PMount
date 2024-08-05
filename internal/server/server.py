# 启动服务
import json
import os.path
import sys
import threading

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication
from blinker import signal
from internal.server.device import Device, DeviceStatus
from internal.server.MountManager import mount, unmount
from internal.server.pipe import pipeServer
from internal.fileSystem import fileSystem, DownloadStatus, tempFs
from config import config, update_config, add_device_config, remove_device_config
from log import logger


class Server:
    # 设备改变信号，新增，删除，状态更改，设备修改都会触发
    deviceChange = signal('deviceChange')  # 设备改变信号

    def __init__(self):
        self.devices = {}
        for name in config.devices.keys():
            device = Device(name, **config.devices[name])
            device.changeSignal.connect(self.device_change)
            self.devices[name] = device

    def start(self):
        """
        启动所有已启用的设备
        :return:
        """
        logger.info("启动挂载设备")
        for name, device in self.devices.items():
            if device.use:
                mount(device)

        logger.info("启动管道服务")
        pipeServer.start()  # 启动管道服务
        pipeServer.messageSignal.connect(self.new_tool_signal)  # 管道消息信号

    def stop(self):
        """
        停止所有设备
        :return:
        """
        for name, device in self.devices.items():
            if device.use:
                unmount(device)

    def start_device(self, arg):
        """
        启动设备
        :param arg: 设备名称或者设备对象
        :return:
        """
        if isinstance(arg, str):
            device = self.devices.get(arg)
        elif isinstance(arg, Device):
            device = arg
        else:
            raise ValueError("参数类型错误")

        mount(device)  # 挂载设备

    def stop_device(self, arg):
        if isinstance(arg, str):
            device = self.devices.get(arg)
        elif isinstance(arg, Device):
            device = arg
        else:
            raise ValueError("参数类型错误")

        unmount(device)  # 卸载设备

    def add_device(self, name: str, device_type: str, use: bool, path: str, device_config: dict):
        """
        添加设备(如果需要挂载，需要手动调用start_device)
        :return:
        """
        add_device_config(name, device_type, use, path, device_config)
        self.devices[name] = Device(name, device_type, use, path)
        self.deviceChange.send("add_device", device=self.devices[name])  # 发送设备删除信号

    def remove_device(self, arg):
        """
        删除设备
        :return:
        """
        if isinstance(arg, str):
            device = self.devices.get(arg)
        elif isinstance(arg, Device):
            device = arg
        else:
            raise ValueError("参数类型错误")

        self.devices.pop(device.name)
        remove_device_config(device.name)  # 从配置项中删除设备
        self.deviceChange.send("remove_device", device=device)  # 发送设备删除信号

    def device_change(self, event: str, device: Device):
        """
        设备状态改变
        :param event: 信号类型
        :param device:
        :return:
        """
        self.deviceChange.send(event, device=device)  # 发送设备状态改变信号

    def new_tool_signal(self, message):
        """
        PMountTaskTool工具发来新的信号
        :param message: 消息内容
        :return:
        """
        # 解析数据
        logger.info(f"New download task: {json.loads(message)}")
        data = json.loads(message)
        device = self.devices.get(data["device"])
        path = data["path"]

        workdir = data["workdir"].replace("\\", "/")

        if workdir.startswith(device.path.replace("\\", "/")):
            # 打开操作
            fileSystem.view(device, path)
        else:
            # 复制操作
            fileSystem.download_copy(device, path, workdir)


server = Server()
