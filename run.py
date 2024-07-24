from fuse import FUSE

from x import CloudFS


class MainArgs:
    def __init__(self, mount):
        self.mount = mount
        self.debug = True
        self.BDUSS = ''


if __name__ == '__main__':
    mainArgs = MainArgs("mnt2")

    FUSE(CloudFS(mainArgs), mainArgs.mount, foreground=True, nonempty=False, async_read=True, raw_fi=True)
