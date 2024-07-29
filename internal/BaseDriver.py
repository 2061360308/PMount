from abc import ABC, abstractmethod
from typing import TypedDict, Protocol

from config import DriverConfig
from easydict import EasyDict


# 定义容量信息的 TypedDict
class QuotaInfo(TypedDict):
    total: int  # 总容量(字节)
    used: int  # 已使用容量(字节)


# 定义返回文件、文件夹信息的 TypedDict
class Info(TypedDict):
    isdir: bool  # 是否为文件夹
    size: int  # 文件大小(字节)
    mtime: int  # 修改时间(时间戳)，不确定的可以使用time.time()获取当前时间戳来代替
    ctime: int  # 创建时间(时间戳)，不确定的可以使用time.time()获取当前时间戳来代替


class Item(TypedDict):
    name: str  # 文件、文件夹名
    path: str  # 文件、文件夹路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
    info: Info  # 详细信息（属性）


class BaseDriver(ABC):
    def __init__(self, config: DriverConfig):
        pass

    @abstractmethod
    def quota(self) -> EasyDict[QuotaInfo]:
        """
        返回容量信息

        返回内容为 EasyDict 对象，
        包含 total 和 used 两个字段，分别表示总容量和已使用容量
        二者要求为 int ，且均为字节单位
        :return:  EasyDict({"total": total, "used": used})
        """
        pass

    @abstractmethod
    def list(self, path:str) -> list[EasyDict[Item]]:
        """
        获取文件列表

        :param path: 需要获取文件列表的目录路径，相对于网盘根目录，以 / 开头，例如: /path/to/dir
        :return: list[EasyDict(Item)]
            即：[
                {
                 "name": name,"path": path,
                 "info": {"isdir": isdir, "size": size, "mtime": mtime, "ctime": ctime }
                }
               ]
        """
        pass

    @abstractmethod
    def copy(self, src_path: str, dest_path: str) -> bool:
        """
        复制文件

        :param src_path: 源文件路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
        :param dest_path: 目标文件路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
        :return: bool
        """
        pass

    @abstractmethod
    def move(self, src_path: str, dest_path: str) -> bool:
        """
        移动文件

        :param src_path: 源文件路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
        :param dest_path: 目标文件路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
        :return: bool
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        删除文件或文件夹

        :param path: 文件或文件夹路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
        :return: bool
        """
        pass
    
    @abstractmethod
    def rname(self, path: str, new_name: str) -> bool:
        """
        重命名文件或文件夹

        :param path: 文件或文件夹路径，相对于网盘根目录，以 / 开头，例如: /path/to/file.txt
        :param new_name: 新的文件或文件夹名
        :return: bool
        """
        pass
