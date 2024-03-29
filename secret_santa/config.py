import json
import logging
import os


def read_config(fname: str) -> dict:
    try:
        with open(fname) as fp:
            return json.load(fp)
    except Exception as err:
        logging.critical("Failed to read config file %s", fname)
        logging.critical(err)
        raise SystemExit


CONFIG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config"))
CONFIG_FNAME = os.path.join(CONFIG_DIR, "config.json")
CONFIG = read_config(CONFIG_FNAME)
