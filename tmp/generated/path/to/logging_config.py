import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file):
    # Create a logger object
    logger = logging.getLogger('cli_tool_logger')
    logger.setLevel(logging.DEBUG)

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger
    logger.addHandler(ch)

    # Create file handler which logs even debug messages
    fh = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=3)
    fh.setLevel(logging.DEBUG)

    # Add formatter to fh
    fh.setFormatter(formatter)

    # Add fh to logger
    logger.addHandler(fh)

    return logger