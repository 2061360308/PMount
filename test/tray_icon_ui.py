import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("主窗口")
        self.resize(800, 600)

        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(QIcon(r"E:\AlistPanBaidu\logo.ico"))  # 设置图标
        self.tray_icon.setToolTip("这是一个系统托盘图标")  # 设置提示文本

        # 创建上下文菜单
        menu = QMenu()

        # 添加一个动作
        action_quit = QAction("退出")
        action_quit.triggered.connect(self.quit_application)
        menu.addAction(action_quit)

        # 将菜单设置为系统托盘图标的上下文菜单
        self.tray_icon.setContextMenu(menu)

        # 显示系统托盘图标
        self.tray_icon.show()

        # 双击托盘图标恢复窗口
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def closeEvent(self, event):
        # 重写关闭事件，将窗口最小化到托盘
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "应用程序最小化",
            "应用程序已最小化到系统托盘。要退出，请使用托盘菜单。",
            QSystemTrayIcon.Information,
            2000
        )

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    def quit_application(self):
        self.tray_icon.hide()
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()