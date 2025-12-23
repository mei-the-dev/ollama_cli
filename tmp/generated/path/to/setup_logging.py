# setup_logging.py
import logging

def setup_logging(debug=False):
    '''Configure logging based on the debug flag.

    Args:
        debug (bool): If True, set logging level to DEBUG. Otherwise, set to INFO.
    '''
    # Create a logger object
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger
    if not logger.hasHandlers():
        logger.addHandler(ch)

    return logger