import importlib
from enum import Enum

from config import DriverConfig, update_config
from blinker import signal


class DeviceStatus(Enum):
    WAIT_MOUNT = 0  # 等待挂载，即设备已启用，但是还没有挂载
    MOUNTED = 1  # 已挂载
    UNMOUNTED = 2  # 为挂载，即设备未启用
    MOUNT_FAILED = 3  # 挂载失败


class Device:
    def __init__(self, name, device_type, use, path):
        """

        :param name: 设备名称
        :param device_type:  设备类型（对应驱动的包名）
        :param used:  是否启用
        :param path:  设备路径(mount/挂载点)
        :param config:  设备配置
        """
        self.name = name
        self.device_type = device_type
        self.use = use
        self.status = DeviceStatus.WAIT_MOUNT if use else DeviceStatus.UNMOUNTED
        self.path = path
        self.config = DriverConfig(name, self.device_type)
        self.fuse_ptr = None  # fuse 文件系统指针,挂载后会有值, 用于卸载
        self._driver = None  # 设备对应的驱动实例
        self.changeSignal = signal(f'{self.name}ChangeSignal')  # 设备状态改变信号

    @property
    def driver(self):
        if not self._driver:
            module = importlib.import_module(f"drivers.{self.device_type}")
            api_class = getattr(module, 'Driver', None)
            if api_class:
                self._driver = api_class(self.config)

        assert self._driver is not None, f"无法实例化驱动 {self.device_type}"
        return self._driver

    def clear_drive(self):
        if self._driver:
            self._driver = None

    def update_info(self, **kwargs):
        if "path" in kwargs.keys():
            update_config(kwargs['path'], "devices", self.name, 'path')
            self.path = kwargs['path']
        if "use" in kwargs.keys():
            update_config(kwargs['use'], "devices", self.name, 'use')
            self.use=kwargs['use']
        if "config" in kwargs.keys():
            update_config(kwargs['config'], self.name)
            self.config = DriverConfig(self.name, self.device_type)
            self.clear_drive()  # 直接清除驱动实例，下次调用时会重新实例化

        self.changeSignal.send("info_change", device=self)  # 发送状态改变信号
