"""统一日志配置。"""
import logging
import sys

from app.core.config import settings

_configured = False


def setup_logging() -> None:
    """配置全局日志格式与级别。"""
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    # 避免重复添加 handler
    if not any(
        isinstance(h, logging.StreamHandler) for h in root.handlers
    ):
        root.addHandler(handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取按模块命名的 logger。"""
    setup_logging()
    return logging.getLogger(name)
