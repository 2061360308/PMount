# 接受命令行参数
import argparse
from json import dumps
from os import getcwd
import win32file

pipe_name = r"\\.\pipe\PMountPipe"

parser = argparse.ArgumentParser(description='PMount任务通信工具')
parser.add_argument('-d', '--device', help='任务来源设备名称', required=True)
parser.add_argument('-p', '--path', help='任务地址', required=True)
args = parser.parse_args()

handle = win32file.CreateFile(
    pipe_name,
    win32file.GENERIC_WRITE,
    0,
    None,
    win32file.OPEN_EXISTING,
    0,
    None
)

message = dumps({
    'device': args.device,
    'path': args.path,
    'workdir': getcwd()
})

win32file.WriteFile(handle, message.encode())
handle.close()
