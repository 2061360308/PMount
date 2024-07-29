# import os
import threading
import requests
from internal.server import server
from UI.tray_icon import TrayIcon

if __name__ == '__main__':
    server.start()
    tray_icon = TrayIcon('logo.ico', 'PMount')
    tray_icon.run()
