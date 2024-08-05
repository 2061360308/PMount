class UploadTask:
    def __init__(self, cloud_fp, local_fp, size):
        """

        :param cloud_fp: 云端路径
        :param local_fp: 本地路径
        :param size: 文件大小
        """
        self.cloud_fp = cloud_fp
        self.local_fp = local_fp
        self.size = size
        self.uploadid = None

        self.chunk_size = 4 * 1024 * 1024  # 分片大小
        self.speed = 0  # 上传速度
        self.completed = 0  # 完成的块数
        self.total = 0  # 总块数
        self.block_list = []  # 分片md5列表
        self.md5 = None  # 上传完成后返回的云端文件的md5

    @property
    def process(self):
        return ((self.completed / self.total) * 100) if self.total != 0 else 100