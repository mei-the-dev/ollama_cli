import logging

def setup_logging(debug=False):
    '''Configure logging based on the debug flag.

    Args:
        debug (bool): If True, set logging level to DEBUG. Otherwise, set to INFO.
    '''
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')