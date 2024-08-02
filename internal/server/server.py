# 启动服务
import os.path
import threading
from blinker import signal
from internal.server.device import Device, DeviceStatus
from internal.server.MountManager import mount, unmount

from config import config, update_config, add_device_config, remove_device_config

from internal.system_res import mount_thread, stop_event


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
        for name, device in self.devices.items():
            if device.use:
                mount(device)

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


server = Server()
