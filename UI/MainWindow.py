import sys

from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import NavigationItemPosition, FluentWindow
from qfluentwidgets import FluentIcon as FIF
import res.resource_rc
from UI.DevicePage import DevicePageWidget
from UI.TaskPage import TaskPageWidget, DownloadPageWidget, UploadPageWidget
from UI.DashboardPage import DashboardPageWidget
from UI.AboutPage import AboutPageWidget
from UI.DocPage import DocPageWidget
from UI.SettingPage import SettingPageWidget


class MainWindow(FluentWindow):
    """ 主界面 """

    def __init__(self):
        super().__init__()

        # 创建子界面，实际使用时将 Widget 换成自己的子界面
        self.deviceInterface = DevicePageWidget(self)  # 设备界面
        self.taskInterface = TaskPageWidget(self)
        self.downloadTaskInterface = DownloadPageWidget(self)
        self.uploadTaskInterface = UploadPageWidget(self)
        self.dashboardInterface = DashboardPageWidget(self)
        self.aboutInterface = AboutPageWidget(self)
        self.docInterface = DocPageWidget(self)
        self.settingInterface = SettingPageWidget(self)

        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.deviceInterface, FIF.HOME, '设备')
        self.addSubInterface(self.taskInterface, FIF.BOOK_SHELF, '任务', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.downloadTaskInterface, FIF.DOWN, '下载任务', parent=self.taskInterface)
        self.addSubInterface(self.uploadTaskInterface, FIF.UP, '上传任务', parent=self.taskInterface)

        self.addSubInterface(self.dashboardInterface, FIF.SPEED_OFF, '仪表盘')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.aboutInterface, FIF.GITHUB, '关于')
        self.addSubInterface(self.docInterface, FIF.DOCUMENT, '文档')

        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1100, 600)
        self.setWindowIcon(QIcon(':/logo/logo/logo_64.ico'))
        self.setWindowTitle('PMount')

    def closeEvent(self, event):
        event.accept()
        # 清理GUI所占资源 Todo 目前无效，需要修改
        QTimer.singleShot(5, QApplication.instance().quit)
