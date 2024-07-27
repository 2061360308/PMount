import logging
import sys


def get_logger(name):
    formatter = logging.Formatter(fmt='%(module)s:%(lineno)d - %(levelname)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


def funcLog(func):
    def wrapper(*args, **kw):
        ret = func(*args, **kw)
        return ret

    return wrapper
