import json
import logging
import os
import sys


def read_config(fname: str) -> dict:
    try:
        with open(fname) as fp:
            return json.load(fp)
    except Exception:
        logging.critical("Failed to read config file %s", fname)
        sys.exit(1)


CONFIG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config"))
CONFIG_FNAME = os.path.join(CONFIG_DIR, "config.json")
CONFIG = read_config(CONFIG_FNAME)
