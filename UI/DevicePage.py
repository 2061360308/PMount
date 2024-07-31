import ctypes
import sys

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QFrame, QVBoxLayout, QWidget, QSpacerItem, QSizePolicy
from qfluentwidgets import SubtitleLabel, ElevatedCardWidget, FluentIcon, InfoBadge, BodyLabel, ComboBox, \
    SingleDirectionScrollArea, qconfig, ColorConfigItem, InfoBarIcon, FlyoutAnimationType, Flyout

from qfluentwidgets import (SwitchButton, ToolButton)
import res.resource_rc
from internal.server import server
from UI import public
from internal.util import import_meta_modules


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
    def __init__(self, device_name, driver_pkg_name, mount_path, state, use, parent=None):
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

        self.device_name = device_name
        self.driver_pkg_name = driver_pkg_name
        self.mount_path = mount_path
        self.state = state
        self.use = use

        self.setMaximumSize(300, 200)

        self.setStyleSheet("border-radius: 10px;")

        self.layout = QVBoxLayout(self)

        self.deviceNameLabel = SubtitleLabel(self)  # 设备名称
        self.deviceNameLabel.setGeometry(QRect(100, 10, 131, 31))
        self.deviceNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.deviceNameLabel.setStyleSheet("font: 16pt 'Segoe UI';background-color: #00000000")
        self.deviceNameLabel.setText(self.device_name)

        self.layout.addWidget(self.deviceNameLabel)

        infoLayout = QHBoxLayout()
        self.typeLabel = BodyLabel(self)
        self.typeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.typeLabel.setStyleSheet("font: 12pt 'Segoe UI';background-color: #00000000")
        self.typeLabel.setText(f"类型：{self.driver_pkg_name}")
        infoLayout.addWidget(self.typeLabel)
        infoLayout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.stateBadge = QHBoxLayout(self)
        self.updateStateBadge(state)
        infoLayout.addLayout(self.stateBadge)

        self.layout.addLayout(infoLayout)

        self.mountLabel = BodyLabel(self)
        self.mountLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # self.mountLabel.setStyleSheet("font: 12pt 'Segoe UI';background-color: #00000000")
        self.mountLabel.setText(f"挂载点：{self.mount_path}")
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
        self.switchButton.setChecked(True if self.use else False)

        self.horizontalLayout.addWidget(self.switchButton)

        self.layout.addWidget(self.horizontalLayoutWidget)
        self.setLayout(self.layout)

        self.switchButton.checkedChanged.connect(self.switch_use)
        self.delButton.clicked.connect(self.delete_device)
        self.editButton.clicked.connect(self.edit_device)

    def updateStateBadge(self, state=None):
        if not state:
            state = server.mountNodes[self.device_name]['state']

        # 清空之前的状态标签
        for i in range(self.stateBadge.count()):
            self.stateBadge.itemAt(i).widget().deleteLater()

        if state == "已挂载":
            stateBadge = InfoBadge.success(f"状态：{state}", self)
        elif state == "等待挂载":
            stateBadge = InfoBadge.warning(f"状态：{state}", self)
            # 等待挂载是一个动态状态，3 秒后更新状态
            QTimer.singleShot(3000, self.updateStateBadge)
        elif state == "挂载失败":
            stateBadge = InfoBadge.error(f"状态：{state}", self)
        else:
            stateBadge = InfoBadge.info(f"状态：{state}", self)

        self.stateBadge.addWidget(stateBadge)

    def switch_use(self, checked):
        if not checked:
            server.stop(self.device_name)
            self.use = False
        else:
            server.use(self.device_name)
            self.use = True

        self.updateStateBadge()

    def delete_device(self):
        if self.use:
            Flyout.create(
                icon=InfoBarIcon.WARNING,
                title='无法删除',
                content="设备正在使用中，无法删除，请停用设备后重试",
                target=self.delButton,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )

    def edit_device(self):
        public.switchTo(public.childrenPages['edit_device'])


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
        print(self.meta_list)
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

    def showDevice(self):
        for name in server.mountNodes:
            item = server.mountNodes[name]
            deviceCard = DeviceCard(name, item['type'], item['mount'], item['state'], item['use'])
            self.threeColumnLayout.add_widget(deviceCard)

    def showNewDevicePage(self):
        public.switchTo(public.childrenPages['new_device'])

    def update_device(self):
        self.threeColumnLayout.clear()
        self.showDevice()
