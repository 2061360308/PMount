from fuse import FUSE

from internal.fileSystem.cloud_fs import CloudFS

fs = CloudFS("百度网盘")
FUSE(fs, "E:/hello", foreground=False, nothreads=True, nonempty=False, async_read=False, raw_fi=False)