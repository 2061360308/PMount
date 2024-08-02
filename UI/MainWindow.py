import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QGuiApplication, QColor
from PySide6.QtWidgets import QApplication
from qfluentwidgets import NavigationItemPosition, MSFluentWindow, toggleTheme, setTheme, Theme
from qfluentwidgets import FluentIcon as FIF
import res.resource_rc
from UI.DevicePage import DevicePageWidget
from UI.Icon import CustomIcon
from UI.TaskPage import TaskPageWidget
from UI.DashboardPage import DashboardPageWidget
from UI.AboutPage import AboutPageWidget
from UI.SettingPage import SettingPageWidget
from UI.NewDevicePage import NewDevicePageWidget, EditConfigWidget
from UI import public


class MainWindow(MSFluentWindow):
    """ 主界面 """

    def __init__(self):
        super().__init__()

        # 创建子界面，实际使用时将 Widget 换成自己的子界面
        self.deviceInterface = DevicePageWidget(self)  # 设备界面
        self.taskInterface = TaskPageWidget(self)
        self.dashboardInterface = DashboardPageWidget(self)
        self.aboutInterface = AboutPageWidget(self)
        self.settingInterface = SettingPageWidget(self)

        self.initNavigation()
        self.initWindow()

        self.newDevicePage = NewDevicePageWidget(self)
        self.stackedWidget.addWidget(self.newDevicePage)
        self.editConfigPage = EditConfigWidget(self)
        self.stackedWidget.addWidget(self.editConfigPage)

        self.childrenPages = {
            'device': self.deviceInterface,
            'task': self.taskInterface,
            'dashboard': self.dashboardInterface,
            'about': self.aboutInterface,
            'setting': self.settingInterface,
            'new_device': self.newDevicePage,
            'edit_config': self.editConfigPage,
        }

        public.childrenPages = self.childrenPages
        public.switchTo = self.switchTo

    def initNavigation(self):
        self.addSubInterface(self.deviceInterface, FIF.HOME, '设备')
        self.addSubInterface(self.taskInterface, FIF.BOOK_SHELF, '任务')
        self.addSubInterface(self.dashboardInterface, FIF.SPEED_OFF, '仪表盘')
        self.addSubInterface(self.aboutInterface, FIF.GITHUB, '关于/文档')

        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', position=NavigationItemPosition.BOTTOM)

        # 添加自定义导航组件
        self.navigationInterface.addItem(
            routeKey='light_night',
            icon=CustomIcon.LIGHT_NIGHT.colored(QColor(0, 0, 0), QColor(255, 255, 255)),
            text='日/夜',
            onClick=toggleTheme,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

    def initWindow(self):
        self.resize(900, 400)
        self.setWindowIcon(QIcon(':/logo/logo/logo_64.ico'))
        self.setWindowTitle('PMount')

        desktop = QGuiApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        setTheme(Theme.LIGHT)

    def closeEvent(self, event):
        event.accept()
        # 清理GUI所占资源 Todo 目前无效，需要修改


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
