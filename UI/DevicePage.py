import ctypes
import sys
import time

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QFrame, QVBoxLayout, QWidget, QSpacerItem, QSizePolicy
from qfluentwidgets import SubtitleLabel, ElevatedCardWidget, FluentIcon, InfoBadge, BodyLabel, ComboBox, \
    SingleDirectionScrollArea, qconfig, ColorConfigItem, InfoBarIcon, FlyoutAnimationType, Flyout, InfoLevel

from qfluentwidgets import (SwitchButton, ToolButton)
import res.resource_rc
from internal.server import server, DeviceStatus
from UI import public
from internal.util import import_meta_modules, device_change


class ThreeColumnLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(f"background-color: rgba(0,0,0,0);")

        self.setWindowTitle("三列布局示例")
        self.setGeometry(100, 100, 800, 600)

        # 创建主布局
        self.main_layout = QVBoxLayout(self)

        # 创建滚动区域
        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 创建一个容器小部件
        self.container = QWidget()
        self.scroll_area.setWidget(self.container)

        # 创建水平布局
        self.h_layout = QHBoxLayout(self.container)
        self.h_layout.setSpacing(35)

        # 创建三个垂直布局作为列
        self.column1 = QVBoxLayout()
        self.column2 = QVBoxLayout()
        self.column3 = QVBoxLayout()

        # 将三个垂直布局添加到水平布局中，并设置伸展因子
        self.h_layout.addLayout(self.column1, 1)
        self.h_layout.addLayout(self.column2, 1)
        self.h_layout.addLayout(self.column3, 1)

        # 将滚动区域添加到主布局中
        self.main_layout.addWidget(self.scroll_area)

        self.setLayout(self.main_layout)

        # 记录当前添加的 widget 数量
        self.widget_count = 0

        # qconfig.themeChanged.connect(self.response_theme)

    def add_widget(self, widget):
        # 计算当前 widget 应该添加到哪一列
        column_index = self.widget_count % 3

        if column_index == 0:
            self.column1.addWidget(widget)
        elif column_index == 1:
            self.column2.addWidget(widget)
        else:
            self.column3.addWidget(widget)

        # 更新 widget 计数
        self.widget_count += 1

    def clear(self):
        # 遍历清空所有组件
        for layout in [self.column1, self.column2, self.column3]:
            for i in range(layout.count()):
                layout.itemAt(i).widget().deleteLater()

        self.widget_count = 0

    def response_theme(self):
        if qconfig.theme == "light":
            self.setStyleSheet(f"background-color: rgba(0,0,0,0);")
        else:
            self.setStyleSheet(f"background-color: rgba(0,0,0,0);")


class DeviceCard(ElevatedCardWidget):
    def __init__(self, device, parent=None):
        """
        设备卡片

        :param device_name: 设备名
        :param driver_pkg_name: 驱动包名
        :param mount_path: 挂载路径
        :param state: 状态
        :param use: 是否启用
        :param parent:
        """
        super().__init__(parent)

        self.device = device
        self.driver_pkg_name = device.device_type

        self.setMaximumSize(300, 200)

        self.setStyleSheet("border-radius: 10px;")

        self.layout = QVBoxLayout(self)

        self.deviceNameLabel = SubtitleLabel(self)  # 设备名称
        self.deviceNameLabel.setGeometry(QRect(100, 10, 131, 31))
        self.deviceNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.deviceNameLabel.setStyleSheet("font: 16pt 'Segoe UI';background-color: #00000000")
        self.deviceNameLabel.setText(self.device.name)

        self.layout.addWidget(self.deviceNameLabel)

        infoLayout = QHBoxLayout()
        self.typeLabel = BodyLabel(self)
        self.typeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.typeLabel.setStyleSheet("font: 12pt 'Segoe UI';background-color: #00000000")
        self.typeLabel.setText(f"类型：{self.driver_pkg_name}")
        infoLayout.addWidget(self.typeLabel)
        infoLayout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.stateBadge = InfoBadge(self)
        self.updateStateBadge(self.device.status)
        infoLayout.addWidget(self.stateBadge)

        self.layout.addLayout(infoLayout)

        self.mountLabel = BodyLabel(self)
        self.mountLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # self.mountLabel.setStyleSheet("font: 12pt 'Segoe UI';background-color: #00000000")
        self.mountLabel.setText(f"挂载点：{self.device.path}")
        self.layout.addWidget(self.mountLabel)

        self.horizontalLayoutWidget = QWidget(self)
        self.horizontalLayoutWidget.setObjectName(u"horizontalLayoutWidget")
        self.horizontalLayoutWidget.setGeometry(QRect(0, 100, 341, 41))
        self.horizontalLayout = QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.editButton = ToolButton(self.horizontalLayoutWidget)
        self.editButton.setIcon(FluentIcon.EDIT)
        self.horizontalLayout.addWidget(self.editButton)

        self.delButton = ToolButton(self.horizontalLayoutWidget)
        self.delButton.setIcon(FluentIcon.DELETE)

        self.horizontalLayout.addWidget(self.delButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.switchButton = SwitchButton(self.horizontalLayoutWidget)
        self.switchButton.setChecked(True if self.device.use else False)

        self.horizontalLayout.addWidget(self.switchButton)

        self.layout.addWidget(self.horizontalLayoutWidget)
        self.setLayout(self.layout)

        self.switchButton.checkedChanged.connect(self.switch_use)
        self.delButton.clicked.connect(self.delete_device)
        self.editButton.clicked.connect(self.edit_device)

        self.device.changeSignal.connect(self.device_change)

    def updateStateBadge(self, state=None):
        if state is None:
            state = self.device.status

        if state == DeviceStatus.MOUNTED:
            self.stateBadge.setLevel(InfoLevel.SUCCESS)
            self.stateBadge.setText("状态：已挂载")
        elif state == DeviceStatus.WAIT_MOUNT:
            self.stateBadge.setLevel(InfoLevel.WARNING)
            self.stateBadge.setText("状态：等待挂载")
        elif state == DeviceStatus.MOUNT_FAILED:
            self.stateBadge.setLevel(InfoLevel.ERROR)
            self.stateBadge.setText("状态：挂载失败")
        elif state == DeviceStatus.UNMOUNTED:
            self.stateBadge.setLevel(InfoLevel.INFOAMTION)
            self.stateBadge.setText("状态：未启用")
        else:
            raise ValueError("未知状态")

    def switch_use(self, checked):
        """
        启用/停用设备
        :param checked:
        :return:
        """
        if checked:
            server.start_device(self.device)
        else:
            server.stop_device(self.device)

        self.updateStateBadge()

    def delete_device(self):
        if self.device.use:
            Flyout.create(
                icon=InfoBarIcon.WARNING,
                title='无法删除',
                content="设备正在使用中，无法删除，请停用设备后重试",
                target=self.delButton,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return

        server.remove_device(self.device)

    def edit_device(self):
        if self.device.use:
            Flyout.create(
                icon=InfoBarIcon.WARNING,
                title='无法修改',
                content="设备正在使用中，无法修改，请停用设备后重试",
                target=self.delButton,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return
        public.childrenPages['edit_config'].load_config(self.device)
        public.switchTo(public.childrenPages['edit_config'])

    def device_change(self, event, device):
        print(event)
        if event == "status_change":
            self.updateStateBadge(device.status)
        elif event == "info_change":
            self.mountLabel.setText(f"挂载点：{device.path}")
            self.switchButton.setChecked(True if device.use else False)


class DevicePageWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName("DevicePage")

        self.layout = QVBoxLayout(self)

        topLayout = QHBoxLayout(self)
        self.titleLabel = BodyLabel(self)
        self.titleLabel.setText("全部设备")
        topLayout.addWidget(self.titleLabel)
        self.addButton = ToolButton(self)
        self.addButton.setIcon(FluentIcon.ADD)
        topLayout.addWidget(self.addButton)

        topLayout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.filterComboBox = ComboBox()

        items = ['全部']
        self.meta_list = import_meta_modules('drivers')
        for item in self.meta_list:
            # 添加选项
            items.append(item.meta['name'])

        self.filterComboBox.addItems(items)
        # 当前选项的索引改变信号
        self.filterComboBox.currentIndexChanged.connect(lambda index: print(self.filterComboBox.currentText()))
        topLayout.addWidget(self.filterComboBox)

        self.viewSwitchButton = ToolButton(self)
        self.viewSwitchButton.setIcon(FluentIcon.TILES)
        topLayout.addWidget(self.viewSwitchButton)

        self.layout.addLayout(topLayout)

        self.threeColumnLayout = ThreeColumnLayout()
        self.layout.addWidget(self.threeColumnLayout)

        self.addButton.clicked.connect(self.showNewDevicePage)

        self.showDevice()

        server.deviceChange.connect(self.device_change)

    def showDevice(self):
        for device in server.devices.values():
            deviceCard = DeviceCard(device, self)
            self.threeColumnLayout.add_widget(deviceCard)

    def showNewDevicePage(self):
        """
        切换到添加新设备页面
        :return:
        """
        public.switchTo(public.childrenPages['new_device'])

    def device_change(self, event, device):
        """
        如果有增删设备的情况，更新设备列表
        :param event:
        :param device:
        :return:
        """
        if event == "remove_device" or event == "add_device":
            self.update_device()

    def update_device(self):
        self.threeColumnLayout.clear()
        self.showDevice()
