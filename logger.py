import logging
import colorlog


def load_logger():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)s%(reset)s:%(levelname)s:%(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', reset=True, log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'
    }))

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(handler)
    logger.addHandler(console_handler)


def get_logger():
    return logging.getLogger('discord')