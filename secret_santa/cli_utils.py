import logging

import coloredlogs


def setup_logging(verbose: bool):
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)
    coloredlogs.install(level=log_level)
    for module in ["urllib3", "botocore"]:
        logging.getLogger(module).setLevel(logging.WARNING)
