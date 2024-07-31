from typing import Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QVBoxLayout, QSizePolicy, QSpacerItem, QWidget, QHBoxLayout, QLabel, QPushButton, \
    QFileDialog
from qfluentwidgets import QConfig, OptionsConfigItem, OptionsValidator, qconfig, ComboBoxSettingCard, FluentIcon, \
    OptionsSettingCard, ExpandGroupSettingCard, PushButton, BodyLabel, ComboBox, SwitchButton, IndicatorPosition, \
    Slider, CaptionLabel, SettingCard, FluentIconBase, PushSettingCard, CardWidget, IconWidget, StrongBodyLabel, \
    ToolButton, SingleDirectionScrollArea

from config import update_config, config


class SettingCardTitle(CardWidget):
    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title: str, content=None, parent=None):
        super().__init__(parent)

        self.layout = QHBoxLayout(self)

        self.icon = IconWidget(icon, self)
        self.icon.setFixedSize(24, 24)
        self.layout.addWidget(self.icon)

        self.title_layout = QVBoxLayout(self)

        self.title_label = StrongBodyLabel(title, self)
        self.title_layout.addWidget(self.title_label)

        self.contentLabel = CaptionLabel(content, self)
        self.contentLabel.setTextColor("#999999")
        self.title_layout.addWidget(self.contentLabel)

        self.layout.addLayout(self.title_layout)
        self.layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.setLayout(self.layout)


class RangeSettingCard(SettingCard):
    """ Setting card with a slider """

    valueChanged = Signal(int)

    def __init__(self, configs, icon: Union[str, QIcon, FluentIconBase], title, content=None, parent=None):
        """
        Parameters
        ----------
        configItem: (configValue, configNames, range)

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configs = configs
        self.slider = Slider(Qt.Horizontal, self)
        self.valueLabel = QLabel(self)
        self.slider.setMinimumWidth(268)

        self.slider.setSingleStep(1)
        self.slider.setRange(*configs[2])
        self.slider.setValue(configs[0])
        self.valueLabel.setNum(configs[0])

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(6)
        self.hBoxLayout.addWidget(self.slider, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.valueLabel.setObjectName('valueLabel')

        self.slider.valueChanged.connect(self.__onValueChanged)

    def __onValueChanged(self, value: int):
        """ slider value changed slot """
        update_config(value, *self.configs[1])
        self.valueLabel.setNum(value)
        self.valueChanged.emit(value)


class FileSettingCard(SettingCard):
    """ Setting card with a slider """

    valueChanged = Signal(int)

    def __init__(self, configs, icon: Union[str, QIcon, FluentIconBase], title, content=None, parent=None):
        """
        Parameters
        ----------
        configItem: RangeConfigItem
            configuration item operated by the card

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configs = configs
        self.pushButton = QPushButton("更改文件夹", self)
        self.valueLabel = CaptionLabel(self)
        self.valueLabel.setTextColor("#999999")

        self.valueLabel.setText(configs[0])

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(6)
        self.hBoxLayout.addWidget(self.pushButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.valueLabel.setObjectName('valueLabel')
        self.pushButton.clicked.connect(self.__onButtonClicked)

    def __onButtonClicked(self):
        """ slider value changed slot """

        # 弹出文件夹选择对话框

        folder_selected = QFileDialog.getExistingDirectory(self, "选择文件夹")

        if not folder_selected:
            return

        update_config(folder_selected, *self.configs[1])
        self.valueLabel.setText(folder_selected)
        self.valueChanged.emit(update_config)


class SettingCard(ExpandGroupSettingCard):
    pass


class TempDirSettingCard(ExpandGroupSettingCard):

    def __init__(self, parent=None):
        super().__init__(FluentIcon.SPEED_OFF, "目录结构缓存选项", "预先处理网盘目录的层级以及缓存数据的刷新频率",
                         parent)

        # 第一组
        self.cacheTimeOutComboBox = ComboBox()
        self.cacheTimeOutComboBox.addItems(["30", "60", "90", "120", "150", "180"])
        self.cacheTimeOutLabel = BodyLabel("过期时间（单位秒）")

        # 第二组
        self.cachePreloadLevelComboBox = ComboBox()
        self.cachePreloadLevelComboBox.addItems(["1", "2", "3", "4"])
        self.cachePreloadLevelLabel = BodyLabel("预先缓存层级")

        # 调整内部布局
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        # 添加各组到设置卡中
        self.add(self.cacheTimeOutLabel, self.cacheTimeOutComboBox)
        self.add(self.cachePreloadLevelLabel, self.cachePreloadLevelComboBox)

    def add(self, label, widget):
        w = QWidget()
        w.setFixedHeight(60)

        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)

        # 添加组件到设置卡
        self.addGroupWidget(w)


class TempFileSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent=None):
        super().__init__(FluentIcon.SPEED_OFF, "虚拟文件系统设置",
                         "内置虚拟文件系统映射的数据文件路径选择最大可用容量以及文件过期时间", parent)

        # 第一组
        self.cacheTimeOutComboBox = ComboBox()
        self.cacheTimeOutComboBox.addItems(["7", "14", "30", "45", "60"])
        self.cacheTimeOutLabel = BodyLabel("过期时间（单位天）")

        # 第二组
        self.maxCacheSizeComboBox = ComboBox()
        self.maxCacheSizeComboBox.addItems(["1", "5", "10", "12", "15", "20", "30"])
        self.maxCacheSizeLabel = BodyLabel("最大缓存容量（单位GB）")

        # 第三组
        self.fileCachePath = QWidget()
        w_layout = QHBoxLayout(self.fileCachePath)
        w_layout.setContentsMargins(0, 0, 0, 0)
        self.fileCachePathTitleLabel = BodyLabel("文件缓存路径")
        w_layout.addWidget(self.fileCachePathTitleLabel)
        self.fileCachePathValueLabel = CaptionLabel("C:/Users/username/AppData/Local/Temp")
        self.fileCachePathValueLabel.setTextColor("#999999")
        w_layout.addWidget(self.fileCachePathValueLabel)
        self.fileCachePath.setLayout(w_layout)

        self.fileCachePathButton = PushButton("更改文件夹")

        # 调整内部布局
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        # 添加各组到设置卡中
        self.add(self.cacheTimeOutLabel, self.cacheTimeOutComboBox)
        self.add(self.maxCacheSizeLabel, self.maxCacheSizeComboBox)
        self.add(self.fileCachePath, self.fileCachePathButton)

    def add(self, label, widget):
        w = QWidget()
        w.setFixedHeight(60)

        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)

        # 添加组件到设置卡
        self.addGroupWidget(w)


class SettingPageWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName("SettingPage")

        self.layout = QVBoxLayout(self)

        self.scrollArea = SingleDirectionScrollArea(orient=Qt.Vertical)
        self.scrollArea.setStyleSheet("background-color: transparent;")
        self.scrollArea.setWidgetResizable(True)

        self.layout.addWidget(self.scrollArea)

        self.innerWidget = QWidget(self)

        self.innerLayout = QVBoxLayout(self.innerWidget)

        baseTitle = SettingCardTitle(FluentIcon.APPLICATION, "基础设置", "PMount界面语言、主题设置", self)
        self.innerLayout.addWidget(baseTitle)

        class Config(QConfig):
            language = OptionsConfigItem(
                "MainWindow", "language", "跟随系统设置", OptionsValidator(["跟随系统设置", "简体中文", "English"]),
                restart=True)

        cfg = Config()
        qconfig.load("config.json", cfg)

        card = ComboBoxSettingCard(
            configItem=cfg.language,
            icon=FluentIcon.ZOOM,
            title="语言",
            content="选择界面所使用的语言",
            texts=["跟随系统设置", "简体中文", "English"],
        )

        self.innerLayout.addWidget(card)

        cfg.language.valueChanged.connect(print)

        dirCacheTitle = SettingCardTitle(FluentIcon.FOLDER, "目录缓存设置", "网盘目录结构缓存模式配置", self)
        self.innerLayout.addWidget(dirCacheTitle)

        self.cacheDirTimeOutSettingCard = RangeSettingCard(
            (config.temp.dir.CACHE_TIMEOUT, ("temp", "dir", "CACHE_TIMEOUT"), (30, 180)),
            '', "缓存过期时间", "设置缓存数据的过期时间，单位为秒(推荐60s)"
        )

        self.innerLayout.addWidget(self.cacheDirTimeOutSettingCard)

        self.cacheDirPreloadSettingCard = RangeSettingCard(
            (config.temp.dir.PRELOAD_LEVEL, ("temp", "dir", "PRELOAD_LEVEL"), (1, 4)),
            '', "预加载层级", "设置预加载的目录层级，最大为4"
        )

        self.innerLayout.addWidget(self.cacheDirPreloadSettingCard)

        fileCacheTitle = SettingCardTitle(FluentIcon.DOWNLOAD, "下载文件设置", "内置虚拟磁盘管理", self)
        self.innerLayout.addWidget(fileCacheTitle)

        self.cacheFileTimeOutSettingCard = RangeSettingCard(
            (config.temp.file.CACHE_TIMEOUT, ("temp", "file", "CACHE_TIMEOUT"), (7, 60)),
            '', "文件过期时间", "设置下载文件的过期时间，单位为天(推荐30天)"
        )

        self.innerLayout.addWidget(self.cacheFileTimeOutSettingCard)

        self.cacheFileSizeSettingCard = RangeSettingCard(
            (config.temp.file.MAX_CACHE_SIZE, ("temp", "file", "MAX_CACHE_SIZE"), (5, 30)),
            '', "最大缓存容量", "设置文件缓存的最大容量，单位为GB(推荐10GB)"
        )

        self.innerLayout.addWidget(self.cacheFileSizeSettingCard)

        self.fileCachePathSettingCard = FileSettingCard(
            (config.temp.file.ROOT, ("temp", "file", "ROOT")),
            '', "文件缓存路径", "设置文件缓存的路径"
        )

        self.innerLayout.addWidget(self.fileCachePathSettingCard)

        self.innerLayout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.innerWidget.setLayout(self.innerLayout)

        self.scrollArea.setWidget(self.innerWidget)
