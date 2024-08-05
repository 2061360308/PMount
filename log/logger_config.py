import os

from loguru import logger
import sys

current_path = os.path.dirname(os.path.abspath(__file__))

# 配置日志格式
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 移除默认的控制台输出
logger.remove()

# 配置日志文件
logger.add(
    os.path.join(current_path, "pmount.log"),
    rotation="10 MB",  # 文件大小达到 10 MB 时自动切分
    retention="10 days",  # 保留 10 天的日志文件
    compression="zip",  # 压缩日志文件
    format=log_format,
    level="DEBUG"  # 设置日志级别
)

# 配置控制台输出
logger.add(
    sys.stdout,
    format=log_format,
    level="INFO"  # 设置日志级别
)

# 示例日志记录
# logger.debug("这是一个调试日志")
# logger.info("这是一个信息日志")
# logger.warning("这是一个警告日志")
# logger.error("这是一个错误日志")
# logger.critical("这是一个严重错误日志")


# # 示例函数
# def example_function():
#     logger.info("这是在函数中的日志")


# example_function()
