import win32pipe, win32file, pywintypes
import tracemalloc
import time
import threading

from blinker import signal

# 创建一个事件对象，用于控制线程的停止
stop_event = threading.Event()


class PipeServer:
    def __init__(self, pipe_name):
        self.messageSignal = signal("pipeMessageSignal")
        self.pipe_name = fr"\\.\pipe\{pipe_name}"
        self.stop_words = "close_pipe"

    def read_from_pipe(self):
        try:
            pipe = win32pipe.CreateNamedPipe(
                self.pipe_name,
                win32pipe.PIPE_ACCESS_INBOUND,  # 只读
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1, 65536, 65536, 0, None
            )
            win32pipe.ConnectNamedPipe(pipe, None)
            while True:
                try:
                    result, message = win32file.ReadFile(pipe, 65536)
                    if result == 0:
                        message = message.decode()
                        if message == self.stop_words:
                            break
                        else:
                            self.messageSignal.send(message)  # 发送有新消息的信号
                    else:
                        print("pipe遇到result不是0的情况了")
                        pass
                except pywintypes.error as e:
                    if e.winerror == 109:  # ERROR_BROKEN_PIPE
                        # Pipe has been closed by the writer.
                        win32pipe.DisconnectNamedPipe(pipe)
                        win32pipe.ConnectNamedPipe(pipe, None)
                    else:
                        print(f"Failed to read from named pipe: {e}")
                        break
        except pywintypes.error as e:
            print(f"Failed to read from named pipe: {e}")

    def stop(self):
        handle = win32file.CreateFile(
            self.pipe_name,
            win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        win32file.WriteFile(handle, self.stop_words.encode())
        handle.close()

    def start(self):
        threading.Thread(target=self.read_from_pipe).start()


pipeServer = PipeServer("PMountPipe")
