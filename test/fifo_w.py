import win32pipe, win32file, pywintypes


def write_to_pipe(pipe_name, message):
    try:
        handle = win32file.CreateFile(
            pipe_name,
            win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        win32file.WriteFile(handle, message.encode())
        handle.close()
    except pywintypes.error as e:
        print(f"Failed to write to named pipe: {e}")


if __name__ == "__main__":
    pipe_name = r'\\.\pipe\my_fifo'
    message = "我是卢澳发来的消息很长很长很长很长很长的一条消息"
    write_to_pipe(pipe_name, message)
