from PySide6.QtWidgets import QFrame


class TaskPageWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName("TaskPage")


class DownloadPageWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName("DownloadTaskPage")


class UploadPageWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName("UploadTaskPage")
