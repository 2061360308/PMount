import importlib
import pkgutil
from uuid import uuid1

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QFrame, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QSpacerItem, QSizePolicy
from qfluentwidgets import SubtitleLabel, setFont, PrimaryToolButton, FluentIcon, BreadcrumbBar, LineEdit, ComboBox, \
    HyperlinkLabel, BodyLabel


class AddDevicePageWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("addDevicePage")


class AddDeviceConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("addDeviceConfig")
        self.meta = None
        self.initUI()

    def initUI(self):
        pass

    def setPage(self, data=None):
        self.meta = data


class DriverSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("driverSelection")
        self.initUI()

        # 获取所有驱动的meta信息
        self.meta_list = self.import_meta_modules("drivers")

        # 生成驱动名字和meta的映射,驱动名字添加到下拉框中
        self.meta_dict = {}
        for item in self.meta_list:
            self.meta_dict[item.meta['name']] = item.meta
            self.driverComboBox.addItem(item.meta['name'])

        self.nextButton.clicked.connect(self.next)

    def next(self):
        driver_name = self.driverComboBox.currentText()
        self.parent.setInterface('addDeviceConfig', self.meta_dict[driver_name])

    def initUI(self):
        # 创建布局
        self.layout = QVBoxLayout(self)

        select_layout = QHBoxLayout()
        self.driverComboBox = ComboBox()
        select_layout.addWidget(self.driverComboBox)
        select_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Minimum))

        self.nextButton = PrimaryToolButton(FluentIcon.SEND, self)
        select_layout.addWidget(self.nextButton)

        self.layout.addLayout(select_layout, 0)

        tip_layout = QHBoxLayout()
        self.tipLabel = BodyLabel(self)
        self.tipLabel.setText("有关添加设备的说明请查看：")
        self.docLinkLabel = HyperlinkLabel(QUrl('https://github.com/'), 'GitHub')
        tip_layout.addWidget(self.tipLabel, 0)
        tip_layout.addWidget(self.docLinkLabel, 0)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        tip_layout.addSpacerItem(spacer)

        self.layout.addLayout(tip_layout, 0)

        spacer2 = QSpacerItem(40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addSpacerItem(spacer2)

    @staticmethod
    def import_meta_modules(package_name):
        package = importlib.import_module(package_name)
        package_path = package.__path__

        meta_list = []

        for _, module_name, is_pkg in pkgutil.iter_modules(package_path):
            if is_pkg:
                full_package_name = f"{package_name}.{module_name}"
                try:
                    meta_module = importlib.import_module(f"{full_package_name}.meta")
                    meta_list.append(meta_module)
                    print(f"Successfully imported {full_package_name}.meta")
                except ModuleNotFoundError:
                    print(f"No meta.py found in {full_package_name}")

        return meta_list

    def setPage(self, data):
        pass


class Demo(QWidget):

    def __init__(self):
        super().__init__()
        self.setStyleSheet('Demo{background:rgb(255,255,255)}')

        self.functionWidgets = {
            'driverSelection': DriverSelectionWidget(self),
            'addDeviceConfig': AddDeviceConfigWidget(self),
        }

        self.breadcrumbBar = BreadcrumbBar(self)
        self.stackedWidget = QStackedWidget(self)

        self.vBoxLayout = QVBoxLayout(self)

        self.breadcrumbBar.currentItemChanged.connect(self.switchInterface)

        # 调整面包屑导航的尺寸
        setFont(self.breadcrumbBar, 18)
        self.breadcrumbBar.setSpacing(20)

        # 初始化布局
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.addWidget(self.breadcrumbBar)
        self.vBoxLayout.addWidget(self.stackedWidget)

        self.resize(500, 500)

        for name in self.functionWidgets:
            self.stackedWidget.addWidget(self.functionWidgets[name])
        self.setInterface('driverSelection', None)

    def setInterface(self, name, data):
        self.functionWidgets[name].setPage(data)

        self.stackedWidget.setCurrentWidget(self.functionWidgets[name])

        if name == 'driverSelection':
            self.breadcrumbBar.addItem('driverSelection', "选择驱动")
        elif name == 'addDeviceConfig':
            self.breadcrumbBar.addItem('addDeviceConfig', "补充设备信息")

    def switchInterface(self, objectName):
        if objectName == 'driverSelection':
            self.setInterface('driverSelection', None)


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    demo = Demo()
    demo.show()
    sys.exit(app.exec())
