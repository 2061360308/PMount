# import win32com.client
#
#
# def create_shortcut(target_path, shortcut_path, description, working_dir, arguments, icon_location, icon_index):
#     shell = win32com.client.Dispatch("WScript.Shell")
#     shortcut = shell.CreateShortcut(shortcut_path)
#     shortcut.TargetPath = target_path
#     shortcut.WorkingDirectory = working_dir
#     shortcut.Arguments = arguments
#     shortcut.Description = description  # 设置鼠标悬浮提示信息
#     shortcut.IconLocation = f"{icon_location},{icon_index}"
#     shortcut.save()
#
#
# # 示例：创建一个快捷方式，目标是一个cmd命令
# target_path = r"C:\Windows\System32\cmd.exe"
# shortcut_path = r"MyShortcut.lnk"
# description = "这是我的快捷方式"  # 设置鼠标悬浮提示信息
# working_dir = r"C:\\"
# arguments = "/c echo Hello, World!"
# icon_location = r"D:\software\Microsoft VS Code\resources\app\resources\win32\config.ico"
# icon_index = 0  # 设置IconIndex
#
# # 创建快捷方式
# create_shortcut(target_path, shortcut_path, description, working_dir, arguments, icon_location, icon_index)

import os
import winreg


def get_default_icon(file_extension):
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, file_extension) as key:
            # 尝试获取直接关联的 DefaultIcon
            try:
                default_icon, _ = winreg.QueryValueEx(key, "DefaultIcon")
                if default_icon and default_icon != "%1" and (not default_icon.startswith("@{")):
                    return expand_icon_path(default_icon)
            except (FileNotFoundError, OSError):
                pass

            # 尝试获取 ProgID
            try:
                prog_id, _ = winreg.QueryValueEx(key, "")
                if prog_id:
                    try:
                        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\DefaultIcon") as icon_key:
                            default_icon, _ = winreg.QueryValueEx(icon_key, "")
                            if default_icon and default_icon != "%1" and (not default_icon.startswith("@{")):
                                return expand_icon_path(default_icon)
                    except (FileNotFoundError, OSError):
                        pass
            except (FileNotFoundError, OSError):
                pass

            # 尝试获取 OpenWithProgids
            try:
                with winreg.OpenKey(key, "OpenWithProgids") as openwith_key:
                    i = 0
                    while True:
                        try:
                            prog_id = winreg.EnumValue(openwith_key, i)[0]
                            try:
                                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\DefaultIcon") as icon_key:
                                    default_icon, _ = winreg.QueryValueEx(icon_key, "")
                                    if default_icon and default_icon != "%1" and (not default_icon.startswith("@{")):
                                        return expand_icon_path(default_icon)
                            except (FileNotFoundError, OSError):
                                pass
                        except OSError:
                            break
                        i += 1
            except (FileNotFoundError, OSError):
                pass

    except (FileNotFoundError, OSError):
        return None

    # 如果以上步骤都没有找到 DefaultIcon，则返回 None
    return None


def expand_icon_path(icon_path):
    # 展开环境变量
    expanded_path = os.path.expandvars(icon_path)
    # 检查是否包含逗号和索引
    if ',' in expanded_path:
        path, index = expanded_path.split(',', 1)
        return path.strip(), int(index.strip())
    return expanded_path.strip(), 0


# 示例：检查更多常用文件类型的默认图标
file_extensions = [
    ".ini", ".pdf", ".png", ".ico", ".txt", ".docx", ".xlsx", ".pptx",
    ".html", ".css", ".js", ".json", ".xml", ".jpg", ".jpeg", ".gif",
    ".bmp", ".mp3", ".wav", ".mp4", ".avi", ".mkv", ".zip", ".rar",
    ".7z", ".exe", ".dll", ".bat", ".cmd", ".py", ".java", ".c", ".cpp"
]
# file_extensions = ["xml"]

for file_extension in file_extensions:
    default_icon = get_default_icon(file_extension)
    if default_icon:
        path, index = default_icon
        if path == "%1":
            print(f"{file_extension} {path} 的默认图标是文件本身的图标")
        else:
            print(f"{file_extension} 的默认图标是: {path}, 索引: {index}")
    else:
        print(f"未找到 {file_extension} 的默认图标")
