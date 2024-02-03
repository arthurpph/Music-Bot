import logging


def load_logger():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(handler)


def get_logger():
    return logging.getLogger('discord')