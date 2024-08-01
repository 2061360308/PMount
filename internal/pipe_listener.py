import win32pipe, win32file, pywintypes
import tracemalloc
import time
import threading

# 创建一个事件对象，用于控制线程的停止
stop_event = threading.Event()


def read_from_pipe(pipe_name):
    try:
        pipe = win32pipe.CreateNamedPipe(
            pipe_name,
            win32pipe.PIPE_ACCESS_INBOUND,  # 只读
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, None
        )
        print("Listener process is waiting for data...")
        win32pipe.ConnectNamedPipe(pipe, None)
        while not stop_event.is_set():
            try:
                result, message = win32file.ReadFile(pipe, 65536)
                if result == 0:
                    message = message.decode()
                    if message == "exit":
                        print("Exiting the process...")
                        break
                    else:
                        pass
                    print(f"Listener process received: {message.decode()}")
                else:
                    break
            except pywintypes.error as e:
                if e.winerror == 109:  # ERROR_BROKEN_PIPE
                    print("Pipe has been closed by the writer.")
                    win32pipe.DisconnectNamedPipe(pipe)
                    win32pipe.ConnectNamedPipe(pipe, None)
                else:
                    print(f"Failed to read from named pipe: {e}")
                    break
    except pywintypes.error as e:
        print(f"Failed to read from named pipe: {e}")


def main(pipe_name):
    tracemalloc.start()
    reader_thread = threading.Thread(target=read_from_pipe, args=(pipe_name,))
    reader_thread.start()

if __name__ == "__main__":
    pipe_name = r'\\.\pipe\my_fifo'
    main(pipe_name)
