#!/usr/bin/python
# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor as Pool
import queue
import requests
import threading
import logging
from core.log import get_my_logger, funcLog

logger = get_my_logger(__name__)
logger.setLevel(logging.DEBUG)


def process_queue_task():
    while True:
        try:
            tries = 1
            f, args, tries = q.get()
            f(*args)
        except Exception as e:
            logger.info(e)
            tries = tries + 1

            if tries < 10:
                logger.warn("retry times:" + str(tries))
                q.put((f, args, tries))


q = queue.Queue()
threads = []
num_worker_threads = 250

session = requests.Session()
a = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=num_worker_threads * 2,
                                  pool_maxsize=num_worker_threads * 3)
session.mount('http://', a)
session.mount('https://', a)

for i in range(num_worker_threads):
    t = threading.Thread(target=process_queue_task, daemon=True)
    t.start()
    threads.append(t)
