import sys

from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy, \
    QScrollArea
from qfluentwidgets import ToolButton, SwitchButton, FluentIcon, BodyLabel, InfoBadge, SubtitleLabel, \
    ElevatedCardWidget, SingleDirectionScrollArea


class ThreeColumnLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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


class DeviceCard(ElevatedCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet("background-color: #F5F5F5; border-radius: 10px;")

        self.layout = QVBoxLayout(self)

        self.deviceNameLabel = SubtitleLabel(self)  # 设备名称
        self.deviceNameLabel.setGeometry(QRect(100, 10, 131, 31))
        self.deviceNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.deviceNameLabel.setStyleSheet("font: 16pt 'Segoe UI';background-color: #00000000")
        self.deviceNameLabel.setText("百度网盘")

        self.layout.addWidget(self.deviceNameLabel)

        infoLayout = QHBoxLayout()
        self.typeLabel = BodyLabel(self)
        self.typeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.typeLabel.setStyleSheet("font: 12pt 'Segoe UI';background-color: #00000000")
        self.typeLabel.setText("类型：百度网盘")
        infoLayout.addWidget(self.typeLabel)
        infoLayout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.stateBadge = InfoBadge.success("状态：Work", parent=self)
        infoLayout.addWidget(self.stateBadge)

        self.layout.addLayout(infoLayout)

        self.mountLabel = BodyLabel(self)
        self.mountLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # self.mountLabel.setStyleSheet("font: 12pt 'Segoe UI';background-color: #00000000")
        self.mountLabel.setText("挂载点：/mnt/baidu")
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

        self.horizontalLayout.addWidget(self.switchButton)

        self.layout.addWidget(self.horizontalLayoutWidget)
        self.setLayout(self.layout)


def main():
    app = QApplication(sys.argv)

    window = ThreeColumnLayout()

    # 添加一些示例标签
    for i in range(18):
        label = DeviceCard()
        window.add_widget(label)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
