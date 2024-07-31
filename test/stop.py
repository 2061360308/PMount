import os
import platform
import ctypes
import fcntl


def terminate_fuse(fuse_device):
    system = platform.system()
    if system == "Windows":
        # 在 Windows 上使用 WinFsp 的 fuse_exit
        try:
            winfsp = ctypes.windll.LoadLibrary("winfsp-x64.dll")
            fuse_exit = winfsp.fuse_exit
            fuse_exit.argtypes = [ctypes.c_void_p]
            fuse_exit.restype = None

            # 获取 FUSE 会话对象
            fuse_session = get_fuse_session(fuse_device)
            if fuse_session:
                fuse_exit(fuse_session)
                print("File system terminated on Windows")
            else:
                print("Failed to get FUSE session on Windows")
        except Exception as e:
            print(f"Failed to terminate file system on Windows: {e}")
    elif system == "Linux":
        # 在 Linux 上使用自定义 ioctl
        try:
            FUSE_IOCTL_TERMINATE = 0xABCDEF  # 自定义的 ioctl 操作码
            with open(fuse_device, 'r') as fd:
                fcntl.ioctl(fd, FUSE_IOCTL_TERMINATE)
            print("File system terminated on Linux")
        except Exception as e:
            print(f"Failed to terminate file system on Linux: {e}")
    else:
        print(f"Unsupported platform: {system}")


def get_fuse_session(fuse_device):
    # 这里需要实现获取 FUSE 会话对象的逻辑
    # 具体实现取决于你的 FUSE 文件系统的实现细节
    return None


if __name__ == "__main__":
    fuse_device = "/dev/fuse"  # 替换为你的 FUSE 设备路径
    terminate_fuse(fuse_device)
