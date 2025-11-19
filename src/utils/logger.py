"""
日志工具模块
基于 loguru 的日志封装
提供统一的日志记录接口
"""

from loguru import logger
import sys
from pathlib import Path
from src.config import settings


def setup_logger():
    """
    配置日志系统
    - 控制台输出: 根据LOG_LEVEL设置
    - 文件输出: logs目录下按日期分割
    """
    
    # 移除默认的logger
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # 创建logs目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 添加文件输出 - 所有日志
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # 每天零点轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        encoding="utf-8"
    )
    
    # 添加文件输出 - 错误日志
    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="90 days",  # 错误日志保留更长时间
        compression="zip",
        encoding="utf-8"
    )
    
    logger.info("日志系统初始化完成")
    return logger


# 全局logger实例
setup_logger()


if __name__ == "__main__":
    # 测试日志功能
    logger.debug("这是DEBUG日志")
    logger.info("这是INFO日志")
    logger.warning("这是WARNING日志")
    logger.error("这是ERROR日志")
    logger.success("这是SUCCESS日志")
