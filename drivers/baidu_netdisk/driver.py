from easydict import EasyDict

from .api import BaiduNetdisk


class Driver:
    def __init__(self, config):
        self.config = config
        self.api = BaiduNetdisk(config)

    def quota(self):
        """
        获取容量信息

        返回内容为 EasyDict 对象，
        包含 total 和 used 两个字段，分别表示总容量和已使用容量
        二者要求为 int ，且均为字节单位
        :return:  EasyDict({"total": total, "used": used})
        """
        return self.api.quota()

    def list(self, **kwargs):
        """
        获取文件列表

        :param kwargs:
        :return:
        """
        data = self.api.list(**kwargs)
        if 'list' not in data:
            return []
        file_lists = data.list

        return_lists = []

        for item in file_lists:
            return_lists.append(EasyDict({
                'name': item.server_filename,
                'path': item.path,
                'info': {
                    'isdir': item.isdir,
                    'size': item.size,
                    'mtime': item.server_mtime,
                    'ctime': item.server_mtime
                }
            }))
        return return_lists

    def copy(self, filePath, destPath):
        """
        复制文件

        :param filePath:
        :param destPath:
        :return:
        """
        return self.api.copy(filePath, destPath)

    def move(self, filePath, destPath):
        """
        移动文件

        :param filePath:
        :param destPath:
        :return:
        """
        return self.api.move(filePath, destPath)

    def rename(self, filePath, newName):
        """
        重命名文件

        :param filePath:
        :param newName:
        :return:
        """
        return self.api.rename(filePath, newName)

    def delete(self, filePath):
        """
        删除文件

        :param filePath:
        :return:
        """
        return self.api.delete(filePath)

    def download_url(self, path):
        """
        获取下载链接

        :param path:
        :return:
        """
        fsid = self.api.path_to_fsid(path)
        url = self.api.get_res_url(fsid)
        return url

    @property
    def headers(self):
        return {"User-Agent": "pan.baidu.com"}