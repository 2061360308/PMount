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
                    print(f"Listener process received: {message.decode()}")
                    print_memory_usage()
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


def print_memory_usage():
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print("[ Top 10 memory usage ]")
    for stat in top_stats[:10]:
        print(stat)


def main(pipe_name):
    tracemalloc.start()
    reader_thread = threading.Thread(target=read_from_pipe, args=(pipe_name,))
    reader_thread.start()

    # try:
    #     while reader_thread.is_alive():
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     print("Stopping the process...")
    #     stop_event.set()
    #     reader_thread.join()
    #     print("Process stopped.")
    start = time.time()
    while True:
        end = time.time()
        if end - start > 20:
            stop_event.set()
            reader_thread.join()
            print("那个线程还活着吗", reader_thread.isAlive())
            break
        else:
            print(f"Main process is running...{end - start}")
            time.sleep(1)


if __name__ == "__main__":
    pipe_name = r'\\.\pipe\my_fifo'
    main(pipe_name)
