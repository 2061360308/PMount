# import os
import threading
import requests
from internal.server import Server

if __name__ == '__main__':
    server = Server()
    server.start(True)
