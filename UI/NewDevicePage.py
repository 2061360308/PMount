import importlib
import os
import pkgutil
from config import config, add_device, update_config, use_device
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QFrame, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QSpacerItem, QSizePolicy, \
    QFormLayout, QFileDialog
from qfluentwidgets import SubtitleLabel, setFont, PrimaryToolButton, FluentIcon, BreadcrumbBar, LineEdit, ComboBox, \
    HyperlinkLabel, BodyLabel, HyperlinkButton, SingleDirectionScrollArea, SpinBox, DoubleSpinBox, SwitchButton, \
    IconWidget, TransparentPushButton, Flyout, InfoBarIcon, FlyoutAnimationType
from UI import public
from internal.server import server
from internal.util import import_meta_modules, device_change


# Todo 心态崩溃，开始瞎写的布局，我看着代码都感觉糟心，后续再优化吧


class ConfigWidget(SingleDirectionScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent, orient=Qt.Vertical)
        self.setObjectName("configWidget")

        self.values = {}

        self.innerWidget = QWidget(self)
        self.innerWidgetLayout = QFormLayout()
        self.innerWidgetLayout.setContentsMargins(0, 0, 8, 0)
        self.innerWidget.setLayout(self.innerWidgetLayout)

        self.setWidgetResizable(True)
        self.setWidget(self.innerWidget)

    def clear(self):
        self.values = {}
        while self.innerWidgetLayout.count():
            item = self.innerWidgetLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def get(self, key):
        if key in self.values:
            value = self.values[key]
            if value['type'] == str:
                return value['edit'].text()
            elif value['type'] == int:
                return value['edit'].value()
            elif value['type'] == float:
                return value['edit'].value()
            else:
                return value['edit'].isChecked()
        else:
            return None

    def addConfig(self, config):
        for key, value in config.items():
            label = BodyLabel(self)

            if value.get('required', False):
                label.setText(f"{value['name']} *(必填)")
                label.setTextColor("red")
            else:
                label.setText(value['name'])

            edit_layout = QHBoxLayout()
            # 根据value['type']的类型，选择不同的编辑器
            edit_type = value.get('type', str)
            if edit_type == str:
                edit = LineEdit(self)
                edit_layout.addWidget(edit)
                if value.get('default', None) is not None:
                    edit.setText(str(value['default']))
            elif edit_type == int:
                edit = SpinBox(self)
                edit_layout.addWidget(edit)
                if value.get('default', None) is not None:
                    edit.setValue(int(value['default']))
            elif edit_type == float:
                edit = DoubleSpinBox(self)
                edit.setRange(0, 1e10)  # 设置一个较大的范围
                edit.setDecimals(6)  # 设置小数位数为 6 位
                edit_layout.addWidget(edit)
                if value.get('default', None) is not None:
                    edit.setValue(float(value['default']))
            else:
                edit = SwitchButton(self)
                edit_layout.addWidget(edit)
                if value.get('default', False):
                    edit.setChecked(True)

            self.values[key] = {"edit": edit, "type": edit_type}

            # 添加链接, 如果有的话
            if value.get('link', None) is not None:
                link = HyperlinkButton(self)
                link.setText("相关链接")
                link.setUrl(QUrl(value['link']))
                edit_layout.addWidget(link)

            # 添加描述, 如果有的话
            if value.get('desc', None) is not None:
                desc = IconWidget(self)
                desc.setToolTip(value['desc'])
                desc.setIcon(FluentIcon.INFO)
                desc.setFixedSize(20, 20)
                edit_layout.addWidget(desc)

            self.innerWidgetLayout.addRow(label, edit_layout)


class ComplationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("complationWidget")

        self.layout = QVBoxLayout(self)
        self.titleLabel = SubtitleLabel(self)
        self.titleLabel.setText("设备添加完成")
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.titleLabel)

        button_layout = QHBoxLayout()
        self.mountButton = TransparentPushButton(FluentIcon.CLOUD, "立即挂载设备", self)
        button_layout.addWidget(self.mountButton)
        self.finishButton = TransparentPushButton(FluentIcon.ACCEPT, "完成", self)
        button_layout.addWidget(self.finishButton)

        self.layout.addLayout(button_layout)

        self.mountButton.clicked.connect(self.mount)
        self.finishButton.clicked.connect(self.finish)

    def mount(self):
        use_device(self.device_name, True)  # 更新配置文件
        device_change()  # 通知设备变更
        server.use(self.device_name)  # 启用设备
        public.childrenPages['device'].update_device()  # UI更新设备列表
        public.switchTo(public.childrenPages['device'])  # 切换到设备列表页面

    def finish(self):
        device_change()  # 通知设备变更
        public.childrenPages['device'].update_device()  # UI更新设备列表
        public.switchTo(public.childrenPages['device'])  # 切换到设备列表页面

    def setPage(self, data):
        self.device_name = data


class AddDeviceConfigWidget(QWidget):
    """添加设备配置的页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("addDeviceConfig")
        self.meta = None
        self.initUI()

        self.submitButton.clicked.connect(self.submit)
        self.selectPathButton.clicked.connect(self.selectPath)

    def verify(self):
        """
        验证用户输入的配置是否合法
        :return:
        """
        # 检测名称以及路径是否填写
        name = self.nameLineEdit.text()
        if not name:
            return False, "设备名称不能为空"

        if config.disk:
            for item in config.disk:
                if item['name'] == name:
                    return False, f"设备名称“{name}”已存在"

        mount_path = self.pathLineEdit.text()
        mount_dir = self.pathFolderLineEdit.text()
        if not mount_path or not mount_dir:
            return False, "挂载路径不能为空"

        if not os.path.isdir(mount_path):
            return False, "挂载路径不存在"

        if not os.access(mount_path, os.W_OK):
            return False, "挂载路径无写权限"

        if os.path.isdir(os.path.join(mount_path, mount_dir)):
            return False, f"挂载路径下已存在同名文件夹{mount_dir}"

        device_config = {}

        # 检测配置的必填项是否都填写
        for key in self.meta['config']:
            value = self.configWidget.get(key)
            if self.meta['config'][key].get('required', False):
                if not value:
                    return False, f"{self.meta['config'][key]['name']} 为必填项"

            device_config[self.meta['config'][key]['name']] = value

        return True, {"name": name, "mount": os.path.join(mount_path, mount_dir), "type": self.meta['package_name'], "config": device_config}

    def selectPath(self):
        parent_dir = QFileDialog.getExistingDirectory(self, "选择要挂在到路径", "C:/")
        if not parent_dir:
            return
        self.pathLineEdit.setText(parent_dir)

    def submit(self):
        status, msg = self.verify()
        if not status:
            Flyout.create(
                icon=InfoBarIcon.WARNING,
                title='提示',
                content=msg,
                target=self,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return

        else:
            config_data = msg

        device = {
            "name": config_data['name'],
            "mount": config_data['mount'],
            "type": config_data['type'],
            "use": False,
        }

        # 更新配置文件
        add_device(device, config_data['config'])

        self.parent.setInterface('complation', device['name'])

    def initUI(self):
        self.layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        self.titleLabel = SubtitleLabel(self)
        top_layout.addWidget(self.titleLabel)
        self.driver_link = HyperlinkButton(self)
        top_layout.addWidget(self.driver_link)
        top_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.layout.addLayout(top_layout)

        name_layout = QHBoxLayout()
        self.nameLabel = BodyLabel(self)
        self.nameLabel.setText("设备名称（唯一）")
        name_layout.addWidget(self.nameLabel)
        self.nameLineEdit = LineEdit(self)
        name_layout.addWidget(self.nameLineEdit)
        self.layout.addLayout(name_layout)

        path_select_layout = QHBoxLayout()
        self.pathLabel = BodyLabel(self)
        self.pathLabel.setText("选择挂载路径")
        path_select_layout.addWidget(self.pathLabel)
        self.pathLineEdit = LineEdit(self)
        path_select_layout.addWidget(self.pathLineEdit)
        self.selectPathButton = PrimaryToolButton(FluentIcon.FOLDER, self)
        path_select_layout.addWidget(self.selectPathButton)
        self.pathFolderLabel = BodyLabel("挂载文件夹名", self)
        path_select_layout.addWidget(self.pathFolderLabel)
        self.pathFolderLineEdit = LineEdit(self)
        path_select_layout.addWidget(self.pathFolderLineEdit)
        self.layout.addLayout(path_select_layout)

        self.configWidget = ConfigWidget(self)

        self.layout.addWidget(self.configWidget)

        submit_layout = QHBoxLayout()
        submit_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.submitButton = PrimaryToolButton(FluentIcon.SEND, self)
        submit_layout.addWidget(self.submitButton)
        self.layout.addLayout(submit_layout)

    def setPage(self, data=None):
        self.meta = data
        self.titleLabel.setText(f"驱动：{self.meta['name']}")
        self.driver_link.setText(f"查看{self.meta['name']}的配置说明")
        self.driver_link.setUrl(QUrl(self.meta['doc_link']))

        self.configWidget.clear()
        self.configWidget.addConfig(self.meta['config'])


class DriverSelectionWidget(QWidget):
    """选择驱动的页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("driverSelection")
        self.initUI()

        # 获取所有驱动的meta信息
        self.meta_list = import_meta_modules("drivers")

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

    def setPage(self, data):
        pass


class NewDevicePageWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("addDevicePage")

        self.functionWidgets = {
            'driverSelection': DriverSelectionWidget(self),
            'addDeviceConfig': AddDeviceConfigWidget(self),
            'complation': ComplationWidget(self),
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
        elif name == 'complation':
            self.breadcrumbBar.addItem('complation', "完成")

    def switchInterface(self, objectName):
        if objectName == 'driverSelection':
            self.setInterface('driverSelection', None)


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    demo = NewDevicePageWidget()
    demo.show()
    sys.exit(app.exec())
