import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QHBoxLayout, \
    QFrame


class SideNavWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("侧边导航栏示例")
        # self.setGeometry(100, 100, 300, 400)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)

        # 创建 QTreeWidget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)  # 隐藏表头

        # 添加顶级项目
        item1 = QTreeWidgetItem(["项目 1"])
        item1.setIcon(0, QIcon(r"E:\AlistPanBaidu\logo.ico"))  # 设置图标
        self.tree.addTopLevelItem(item1)

        # 添加子项目
        sub_item1 = QTreeWidgetItem(["子项目 1-1"])
        sub_item1.setIcon(0, QIcon("path/to/icon2.png"))  # 设置图标
        item1.addChild(sub_item1)

        sub_item2 = QTreeWidgetItem(["子项目 1-2"])
        sub_item2.setIcon(0, QIcon("path/to/icon3.png"))  # 设置图标
        item1.addChild(sub_item2)

        # 添加另一个顶级项目
        item2 = QTreeWidgetItem(["项目 2"])
        item2.setIcon(0, QIcon("path/to/icon4.png"))  # 设置图标
        self.tree.addTopLevelItem(item2)

        # 添加子项目
        sub_item3 = QTreeWidgetItem(["子项目 2-1"])
        sub_item3.setIcon(0, QIcon("path/to/icon5.png"))  # 设置图标
        item2.addChild(sub_item3)

        sub_item4 = QTreeWidgetItem(["子项目 2-2"])
        sub_item4.setIcon(0, QIcon("path/to/icon6.png"))  # 设置图标
        item2.addChild(sub_item4)

        layout.addWidget(self.tree, 1)

        # 添加一个内容区域
        # self.content = QLabel("这里是内容区域")
        # self.content.setAlignment(Qt.AlignCenter)
        # layout.addWidget(self.content)

        self.setLayout(layout)

        # 设置样式表
        self.setStyleSheet("""
                    QTreeWidget {
                        border: none;
                    }
                    QTreeWidget::item {
                        height: 40px;
                        padding: 5px;
                    }
                    QTreeWidget::item:selected {
                        outline: none;  /* 去掉虚线框 */
                    }
                    QTreeWidget::item:hover {
                    }
                    QLabel {
                        border: none;
                        padding: 10px;
                        outline: none;
                    }
                """)

        # 进一步去掉虚线框
        self.tree.setStyleSheet("""
                    QTreeWidget::item:selected:focus {
                        outline: none;
                        border: none;
                    }
                    QTreeWidget::item:selected:!focus {
                        outline: none;
                        border: none;
                    }
                """)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = SideNavWidget()
    window.show()

    sys.exit(app.exec())
