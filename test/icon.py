# import pystray  # 导入 PyStray 库
# from PIL import Image  # 导入 PIL 库中的 Image 模块
#
#
# def on_quit_clicked(icon):  # 自定义回调函数
#     icon.stop()  # 对象停止方法
#
#
# # 创建图标对象
# image = Image.open(r"E:\AlistPanBaidu\res\logo\logo_32.ico")  # 打开 ICO 图像文件并创建一个 Image 对象
# menu = (pystray.MenuItem(text='退出', action=on_quit_clicked),)  # 创建菜单项元组
# icon = pystray.Icon("name", image, "托盘名称", menu)  # 创建 PyStray Icon 对象，并传入关键参数
#
# # 显示图标
# icon.run()  # 启动托盘图标目录
import win32con
import win32gui
import time
import abc
from threading import Thread


class Pystray(object):
    '''windows添加系统托盘'''

    def __init__(self, ico_path: str, ico_class_name: str, window_name: str = 'mywindowclass'):
        '''
        @params  ico_path           --> 系统托盘图标路径;
        @params  ico_class_name     --> 图标名;
        @params  window_name        --> 窗口类(非必要);
        '''
        self._ico_path: str = ico_path
        self._ico_class_name = ico_class_name
        self.__window_name = window_name
        self._menu = {}  # {1024: ('菜单名', fun1), 1025: ('菜单名1', fun2)}

    @property
    def menu(self):
        return self._menu

    @menu.setter
    def menu(self, value: dict):
        if isinstance(value, dict):
            self._menu.update(value)
        else:
            raise TypeError('参数必须为字典;{1024: (菜单名, fun1), 1025: (菜单名1, fun2)}')

    @abc.abstractmethod
    def left_doubleclick(self):
        '''鼠标左键双击事件'''
        print("鼠标左键被双击了")

    @abc.abstractmethod
    def left_click(self):
        '''鼠标左键单击事件'''
        print("鼠标左键被单击了")

    @abc.abstractmethod
    def right_doubleclick(self):
        '''鼠标右键双击事件'''
        print("鼠标右键被双击了！")

    def _create_window(self):
        '''创建window对象'''
        wc = win32gui.WNDCLASS()
        self.hinst = wc.hInstance = win32gui.GetModuleHandle(None)
        wc.lpszClassName = self.__window_name
        wc.lpfnWndProc = self.wndProc
        self.classAtom = win32gui.RegisterClass(wc)

    def create_tray_icon(self):
        '''创建图标'''
        self._create_window()
        self.hwnd = win32gui.CreateWindow(self.classAtom, self.__window_name,
                                          win32con.WS_OVERLAPPED | win32con.WS_SYSMENU, 0, 0,
                                          win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, 0, 0, self.hinst, None)

        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        hicon = win32gui.LoadImage(self.hinst, self._ico_path, win32con.IMAGE_ICON, 0, 0, icon_flags)

        # 设置系统托盘图标的属性
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, hicon, self._ico_class_name)
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

    @abc.abstractmethod
    def wndProc(self, hwnd, msg, wparam, lparam):
        ''' 定义系统托盘图标的消息处理函数'''
        if msg == win32con.WM_USER + 20:  # 监听系统托盘图标的消息
            if lparam == win32con.WM_LBUTTONDBLCLK:  # 监听鼠标左键双击事件
                self.left_doubleclick()

            elif lparam == win32con.WM_RBUTTONDOWN:  # 监听右键单击事件
                # 显示右键菜单
                menu = win32gui.CreatePopupMenu()
                # for k, v in self._menu.items():
                #     ids, name = k, v[0]
                #     win32gui.AppendMenu(menu, win32con.MF_STRING, ids, name)
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1023, "菜单项1")
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1024, "菜单项2")
                win32gui.AppendMenu(menu, win32con.MF_STRING, 1025, "退出")
                pos = win32gui.GetCursorPos()
                win32gui.SetForegroundWindow(hwnd)
                win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, hwnd, None)
                win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)

            elif lparam == win32con.WM_LBUTTONDOWN:  # 监听鼠标左键单击事件
                self.left_click()

            elif lparam == win32con.WM_RBUTTONDBLCLK:  # 监听右键双击事件
                self.right_doubleclick()

        elif msg == win32con.WM_COMMAND:
            id = win32gui.LOWORD(wparam)
            if id == 1023:
                print("执行菜单项1的操作")
            elif id == 1024:
                print("执行菜单项2的操作")
            elif id == 1025:
                win32gui.DestroyWindow(hwnd)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def run(self):
        '''消息循环（正常启动）'''
        self.create_tray_icon()
        while True:
            time.sleep(0.1)
            win32gui.PumpWaitingMessages()

    def run_detached(self):
        '''非阻塞(须有父进程)'''
        t = Thread(target=a.run)
        t.daemon = True
        t.start()


if __name__ == "__main__":
    a = Pystray(r"E:\AlistPanBaidu\res\logo\logo_32.ico", 'edg')
    a.run()
    # a.run_detached()
