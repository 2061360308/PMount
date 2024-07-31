import sys

from PySide6.QtCore import Qt, QPoint, QSize, QUrl, QRect, QPropertyAnimation
from PySide6.QtGui import QIcon, QFont, QColor, QPainter
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect, QFrame

from qfluentwidgets import (IconWidget, BodyLabel, CaptionLabel, PushButton,
                            TransparentToolButton, FluentIcon,
                            ImageLabel, isDarkTheme, SimpleCardWidget,
                            HeaderCardWidget, InfoBarIcon, HyperlinkLabel, HorizontalFlipView,
                            PrimaryPushButton, TitleLabel, PillPushButton, setFont, SingleDirectionScrollArea,
                            VerticalSeparator, GroupHeaderCardWidget,
                            ComboBox, SearchLineEdit)

from qfluentwidgets.components.widgets.acrylic_label import AcrylicBrush

# Todo 先用这个填充一下界面，后期有空整理完善

def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


class StatisticsWidget(QWidget):
    """ Statistics widget """

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent=parent)
        self.titleLabel = CaptionLabel(title, self)
        self.valueLabel = BodyLabel(value, self)
        self.vBoxLayout = QVBoxLayout(self)

        self.vBoxLayout.setContentsMargins(16, 0, 16, 0)
        self.vBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignBottom)

        setFont(self.valueLabel, 18, QFont.DemiBold)
        self.titleLabel.setTextColor(QColor(96, 96, 96), QColor(206, 206, 206))


class AppInfoCard(SimpleCardWidget):
    """ App information card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.iconLabel = ImageLabel(":/logo/logo/logo_256.png", self)
        self.iconLabel.setBorderRadius(8, 8, 8, 8)
        self.iconLabel.scaledToWidth(120)

        self.nameLabel = TitleLabel('PMount', self)
        self.installButton = PrimaryPushButton('官网', self)
        self.companyLabel = HyperlinkLabel(
            QUrl('https://github.com/2061360308'), '@Author 盧瞳', self)
        self.installButton.setFixedWidth(160)

        self.scoreWidget = StatisticsWidget('安装包', '50M', self)
        self.separator = VerticalSeparator(self)
        self.commentWidget = StatisticsWidget('内存占用', '100M', self)

        self.descriptionLabel = BodyLabel(
            'Python开发的云盘挂载工具，轻量、易用、拓展性强。', self)
        self.descriptionLabel.setWordWrap(True)

        self.tagButton = PillPushButton('Python', self)
        self.tagButton.setCheckable(False)
        setFont(self.tagButton, 12)
        self.tagButton.setFixedSize(80, 32)

        self.shareButton = TransparentToolButton(FluentIcon.SHARE, self)
        self.shareButton.setFixedSize(32, 32)
        self.shareButton.setIconSize(QSize(14, 14))

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()
        self.topLayout = QHBoxLayout()
        self.statisticsLayout = QHBoxLayout()
        self.buttonLayout = QHBoxLayout()

        self.initLayout()
        self.setBorderRadius(8)

    def initLayout(self):
        self.hBoxLayout.setSpacing(30)
        self.hBoxLayout.setContentsMargins(34, 24, 24, 24)
        self.hBoxLayout.addWidget(self.iconLabel)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        # name label and install button
        self.vBoxLayout.addLayout(self.topLayout)
        self.topLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.addWidget(self.nameLabel)
        self.topLayout.addWidget(self.installButton, 0, Qt.AlignRight)

        # company label
        self.vBoxLayout.addSpacing(3)
        self.vBoxLayout.addWidget(self.companyLabel)

        # statistics widgets
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addLayout(self.statisticsLayout)
        self.statisticsLayout.setContentsMargins(0, 0, 0, 0)
        self.statisticsLayout.setSpacing(10)
        self.statisticsLayout.addWidget(self.scoreWidget)
        self.statisticsLayout.addWidget(self.separator)
        self.statisticsLayout.addWidget(self.commentWidget)
        self.statisticsLayout.setAlignment(Qt.AlignLeft)

        # description label
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.descriptionLabel)

        # button
        self.vBoxLayout.addSpacing(12)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addLayout(self.buttonLayout)
        self.buttonLayout.addWidget(self.tagButton, 0, Qt.AlignLeft)
        self.buttonLayout.addWidget(self.shareButton, 0, Qt.AlignRight)


class GalleryCard(HeaderCardWidget):
    """ Gallery card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('屏幕截图')
        self.setBorderRadius(8)

        self.flipView = HorizontalFlipView(self)
        self.expandButton = TransparentToolButton(
            FluentIcon.CHEVRON_RIGHT_MED, self)

        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))

        self.flipView.addImages([
            'resource/shoko1.jpg', 'resource/shoko2.jpg',
            'resource/shoko3.jpg', 'resource/shoko4.jpg',
        ])
        self.flipView.setBorderRadius(8)
        self.flipView.setSpacing(10)

        self.headerLayout.addWidget(self.expandButton, 0, Qt.AlignRight)
        self.viewLayout.addWidget(self.flipView)


class DescriptionCard(HeaderCardWidget):
    """ Description card """

    def __init__(self, parent=None):
        super().__init__(parent)
        desc = """
        PMount 是一个基于 Python 开发的云盘挂载工具，支持多种云盘，轻量、易用、拓展性强。 使用PMount，通过简单的几个步骤你就可以将云盘挂载到本地，通过Windows的资源管理器轻松地访问那些云上资源。

PMount的灵感来自于AList,仿照AList的设计，PMount也支持通过添加新的drivers文件来支持新的云盘。 相比于那些使用WebDAV协议的云盘挂载工具，PMount提供的挂载系统不单单是网络云盘的目录映射，而是云盘目录加本地虚拟缓存目录的相互结合。 PMount内置了一个文件缓存系统，你可以自定义缓存目录和空间上限，在展示云盘文件时，PMount会自动优先展示缓存目录的对应文件，否则会显示指向网盘资源的超链接。

依赖于上述的模式，PMount打开那些常用的文件和浏览本地文件没有区别，它能将你从 1.下载文件->2.查看/修改文件->3.上传文件 的繁琐流程中解放出来。 让大容量的云盘资源更好的结合进入你的日常工作流程中。
        """
        self.descriptionLabel = BodyLabel(desc, self)
        self.descriptionLabel.setWordWrap(True)
        self.viewLayout.addWidget(self.descriptionLabel)
        self.setTitle('描述')
        self.setBorderRadius(8)


class SystemRequirementCard(HeaderCardWidget):
    """ System requirements card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('系统要求')
        self.setBorderRadius(8)

        self.infoLabel = BodyLabel('PMount暂时只支持Windows设备，且需要安装WinFsp。', self)
        self.successIcon = IconWidget(InfoBarIcon.SUCCESS, self)
        self.detailButton = HyperlinkLabel('详细信息', self)

        self.vBoxLayout = QVBoxLayout()
        self.hBoxLayout = QHBoxLayout()

        self.successIcon.setFixedSize(16, 16)
        self.hBoxLayout.setSpacing(10)
        self.vBoxLayout.setSpacing(16)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)

        self.hBoxLayout.addWidget(self.successIcon)
        self.hBoxLayout.addWidget(self.infoLabel)
        self.vBoxLayout.addLayout(self.hBoxLayout)
        self.vBoxLayout.addWidget(self.detailButton)

        self.viewLayout.addLayout(self.vBoxLayout)


class SettinsCard(GroupHeaderCardWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("基本设置")
        self.setBorderRadius(8)

        self.chooseButton = PushButton("选择")
        self.comboBox = ComboBox()
        self.lineEdit = SearchLineEdit()

        self.chooseButton.setFixedWidth(120)
        self.lineEdit.setFixedWidth(320)
        self.comboBox.setFixedWidth(320)
        self.comboBox.addItems(["始终显示（首次打包时建议启用）", "始终隐藏"])
        self.lineEdit.setPlaceholderText("输入入口脚本的路径")

        self.addGroup("resource/Rocket.svg", "构建目录", "选择 Nuitka 的输出目录", self.chooseButton)
        self.addGroup("resource/Joystick.svg", "运行终端", "设置是否显示命令行终端", self.comboBox)
        self.addGroup("resource/Python.svg", "入口脚本", "选择软件的入口脚本", self.lineEdit)


class LightBox(QWidget):
    """ Light box """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        if isDarkTheme():
            tintColor = QColor(32, 32, 32, 200)
        else:
            tintColor = QColor(255, 255, 255, 160)

        self.acrylicBrush = AcrylicBrush(self, 30, tintColor, QColor(0, 0, 0, 0))

        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.opacityAni = QPropertyAnimation(self.opacityEffect, b"opacity", self)
        self.opacityEffect.setOpacity(1)
        self.setGraphicsEffect(self.opacityEffect)

        self.vBoxLayout = QVBoxLayout(self)
        self.closeButton = TransparentToolButton(FluentIcon.CLOSE, self)
        self.flipView = HorizontalFlipView(self)
        self.nameLabel = BodyLabel('屏幕截图 1', self)
        self.pageNumButton = PillPushButton('1 / 4', self)

        self.pageNumButton.setCheckable(False)
        self.pageNumButton.setFixedSize(80, 32)
        setFont(self.nameLabel, 16, QFont.DemiBold)

        self.closeButton.setFixedSize(32, 32)
        self.closeButton.setIconSize(QSize(14, 14))
        self.closeButton.clicked.connect(self.fadeOut)

        self.vBoxLayout.setContentsMargins(26, 28, 26, 28)
        self.vBoxLayout.addWidget(self.closeButton, 0, Qt.AlignRight | Qt.AlignTop)
        self.vBoxLayout.addWidget(self.flipView, 1)
        self.vBoxLayout.addWidget(self.nameLabel, 0, Qt.AlignHCenter)
        self.vBoxLayout.addSpacing(10)
        self.vBoxLayout.addWidget(self.pageNumButton, 0, Qt.AlignHCenter)

        self.flipView.addImages([
            'resource/shoko1.jpg', 'resource/shoko2.jpg',
            'resource/shoko3.jpg', 'resource/shoko4.jpg',
        ])
        self.flipView.currentIndexChanged.connect(self.setCurrentIndex)

    def setCurrentIndex(self, index: int):
        self.nameLabel.setText(f'屏幕截图 {index + 1}')
        self.pageNumButton.setText(f'{index + 1} / {self.flipView.count()}')
        self.flipView.setCurrentIndex(index)

    def paintEvent(self, e):
        if self.acrylicBrush.isAvailable():
            return self.acrylicBrush.paint()

        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        if isDarkTheme():
            painter.setBrush(QColor(32, 32, 32))
        else:
            painter.setBrush(QColor(255, 255, 255))

        painter.drawRect(self.rect())

    def resizeEvent(self, e):
        w = self.width() - 52
        self.flipView.setItemSize(QSize(w, w * 9 // 16))

    def fadeIn(self):
        rect = QRect(self.mapToGlobal(QPoint()), self.size())
        self.acrylicBrush.grabImage(rect)

        self.opacityAni.setStartValue(0)
        self.opacityAni.setEndValue(1)
        self.opacityAni.setDuration(150)
        self.opacityAni.start()
        self.show()

    def fadeOut(self):
        self.opacityAni.setStartValue(1)
        self.opacityAni.setEndValue(0)
        self.opacityAni.setDuration(150)
        self.opacityAni.finished.connect(self._onAniFinished)
        self.opacityAni.start()

    def _onAniFinished(self):
        self.opacityAni.finished.disconnect()
        self.hide()


class AboutPageWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName("AboutPage")

        self.scrollArea = SingleDirectionScrollArea(orient=Qt.Vertical)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)

        self.view = QWidget(self)

        self.vBoxLayout = QVBoxLayout(self.view)
        self.appCard = AppInfoCard(self)
        # self.galleryCard = GalleryCard(self)
        self.descriptionCard = DescriptionCard(self)
        # self.settingCard = SettinsCard(self)
        self.systemCard = SystemRequirementCard(self)

        self.lightBox = LightBox(self)
        self.lightBox.hide()
        # self.galleryCard.flipView.itemClicked.connect(self.showLightBox)

        self.scrollArea.setWidget(self.view)
        self.scrollArea.setWidgetResizable(True)
        self.setObjectName("appInterface")

        self.vBoxLayout.setSpacing(10)
        self.vBoxLayout.setContentsMargins(0, 0, 10, 30)
        self.vBoxLayout.addWidget(self.appCard, 0, Qt.AlignTop)
        # self.vBoxLayout.addWidget(self.galleryCard, 0, Qt.AlignTop)
        # self.vBoxLayout.addWidget(self.settingCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.descriptionCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.systemCard, 0, Qt.AlignTop)

        self.scrollArea.enableTransparentBackground()

    def showLightBox(self):
        # index = self.galleryCard.flipView.currentIndex()
        # self.lightBox.setCurrentIndex(index)
        self.lightBox.fadeIn()
