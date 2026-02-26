"""Loguru 日志封装，按日期分文件。"""

import os
import sys
from datetime import datetime

from loguru import logger as _logger

from product_search.core.config import PROJECT_ROOT

_print_level = "INFO"
_stderr_handler_id = None


def set_stderr_level(level: str) -> None:
    """动态调整 stderr 日志级别（CLI 模式用）。"""
    global _stderr_handler_id
    if _stderr_handler_id is not None:
        _logger.remove(_stderr_handler_id)
    _stderr_handler_id = _logger.add(
        sys.stderr, level=level, colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )


def define_log_level(print_level: str = "INFO", logfile_level: str = "DEBUG", name: str = None):
    """配置日志级别和输出目标。"""
    global _print_level, _stderr_handler_id
    _print_level = print_level

    formatted_date = datetime.now().strftime("%Y%m%d")
    log_name = f"{name}_{formatted_date}" if name else formatted_date

    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    _logger.remove()
    _stderr_handler_id = _logger.add(
        sys.stderr, level=print_level, colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    _logger.add(logs_dir / f"{log_name}.log", level=logfile_level, rotation="00:00", retention="7 days")
    return _logger


# 从环境变量读取日志级别
_log_level = os.environ.get("LOG_LEVEL", "INFO")
logger = define_log_level(print_level=_log_level)
