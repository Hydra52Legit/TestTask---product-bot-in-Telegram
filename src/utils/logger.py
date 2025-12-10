import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def setup_logger():
    """Настройка логирования"""
    # Создание папки logs если не существует
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Хендлер для файла
    file_handler = RotatingFileHandler(
        'logs/bot.log',
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Хендлер для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Логи для SQLAlchemy
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    return logger