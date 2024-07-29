import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QApplication
from qfluentwidgets import RoundMenu, Action, FluentIcon

from UI.MainWindow import MainWindow
import res.resource_rc
from internal.system_res import close_system_res

app = QApplication(sys.argv)


def on_tray_icon_activated(reason):
    if reason == QSystemTrayIcon.Trigger:
        mainWindow = MainWindow()
        mainWindow.show()


def app_exit():
    global app

    # 弹出弹框提醒用户等待资源释放完毕
    # w = Dialog("正在退出...", "请稍等，我们需要一些时间来保存您的数据和释放资源，操作完成后将自动退出")
    # w.cancelButton.hide()
    # w.buttonLayout.insertStretch(1)
    # w.exec()
    close_system_res()
    app.exit()
    os._exit(0)


def startApp():
    tray_icon = QSystemTrayIcon()
    tray_icon.setIcon(QIcon(':/logo/logo/logo_64.ico'))  # 设置图标
    tray_icon.setToolTip("PMount")  # 设置提示文本
    # 创建上下文菜单
    menu = RoundMenu()

    # 逐个添加动作，Action 继承自 QAction，接受 FluentIconBase 类型的图标
    # 批量添加动作
    menu.addActions([
        Action(FluentIcon.GITHUB, 'Github'),
        Action(FluentIcon.DOCUMENT, '文档')
    ])
    # 添加分割线
    menu.addSeparator()

    menu.addAction(Action(FluentIcon.CLOSE, '退出', triggered=lambda: app_exit()))
    # 将菜单设置为系统托盘图标的上下文菜单
    tray_icon.setContextMenu(menu)
    # 显示系统托盘图标
    tray_icon.show()
    # 双击托盘图标恢复窗口
    tray_icon.activated.connect(on_tray_icon_activated)

    sys.exit(app.exec())
