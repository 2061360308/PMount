from enum import Enum

from qfluentwidgets import FluentIconBase, Theme
import res.resource_rc


class CustomIcon(FluentIconBase, Enum):
    """ Custom icons """

    ADD = "Add"
    CUT = "Cut"
    COPY = "Copy"
    LIGHT_NIGHT = "日夜"
    DEVICE = "设备"

    def path(self, theme=Theme.AUTO):
        # getIconColor() 根据主题返回字符串 "white" 或者 "black"
        return f':/icon/icon/{self.value}.svg'
