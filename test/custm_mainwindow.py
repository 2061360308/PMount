import sys
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSizePolicy


class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #2E2E2E; color: white;")

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.title = QLabel("自定义标题栏")
        self.title.setStyleSheet("background-color: white; color: #2E2E2E;")
        self.title.setAlignment(Qt.AlignCenter)

        self.minimize_button = QPushButton("-")
        # self.minimize_button.setFlat(True)
        self.minimize_button.setStyleSheet("background-color: #2E2E2E; color: white;")
        self.minimize_button.setFixedSize(40, 40)
        self.minimize_button.clicked.connect(parent.showMinimized)

        self.close_button = QPushButton("x")
        # self.close_button.setFlat(True)
        self.close_button.setStyleSheet("background-color: #2E2E2E; color: white;")
        self.close_button.setFixedSize(40, 40)
        self.close_button.clicked.connect(parent.close)

        self.layout.addWidget(self.title)
        self.layout.addWidget(self.minimize_button)
        self.layout.addWidget(self.close_button)

        self.setLayout(self.layout)

        self.start = QPoint(0, 0)
        self.pressing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = event.globalPosition().toPoint()
            self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.parent().move(self.parent().pos() + event.globalPosition().toPoint() - self.start)
            self.start = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.pressing = False


class ResizeHandle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setStyleSheet("background-color: #2E2E2E;")

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.spacer = QLabel()
        self.spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.resize_label = QLabel("⇲")
        self.resize_label.setFixedSize(20, 20)
        self.resize_label.setAlignment(Qt.AlignCenter)
        self.resize_label.setStyleSheet("color: white;")

        self.layout.addWidget(self.spacer)
        self.layout.addWidget(self.resize_label)

        self.setLayout(self.layout)

        self.start = QPoint(0, 0)
        self.resizing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.globalPosition().toPoint().x() >= self.width() - 20:
            self.start = event.globalPosition().toPoint()
            self.resizing = True

    def mouseMoveEvent(self, event):
        if self.resizing:
            delta = event.globalPosition().toPoint() - self.start
            new_size = self.parent().size() + QSize(delta.x(), delta.y())
            self.parent().resize(new_size)
            self.start = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.resizing = False

    def enterEvent(self, event):
        self.setCursor(Qt.SizeFDiagCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)


class CustomWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.layout.addWidget(self.title_bar)

        self.content = QLabel("这里是窗体内容")
        self.content.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.content)

        self.resize_handle = ResizeHandle(self)
        self.layout.addWidget(self.resize_handle)


def main():
    app = QApplication(sys.argv)

    custom_widget = CustomWidget()
    custom_widget.resize(800, 600)
    custom_widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()