"""
Optionally, you may encrypt the pairings.
This provides an interface to do so
"""


import json
import logging
import os
import urllib.parse
from datetime import datetime
from typing import Dict, Tuple

import requests

from .config import CONFIG
from .secret_santa import sanity_check_pairings

CURRENT_YEAR = CONFIG.get("year", datetime.now().year)
SITE_URL = f"https://boompig.herokuapp.com/secret-santa/{CURRENT_YEAR}"
DEFAULT_API_BASE_URL = "https://boompig.herokuapp.com/secret-santa/api"
API_BASE_URL = CONFIG.get("API_BASE_URL", DEFAULT_API_BASE_URL)


def encrypt_name_with_api(name: str, api_base_url: str) -> Tuple[str, str]:
    enc_url = api_base_url + "/encrypt"
    response = requests.post(enc_url, {"name": name})
    r_json = response.json()
    return r_json["key"], r_json["msg"]


def decrypt_with_api(key: str, msg: str, api_base_url: str) -> str:
    dec_url = api_base_url + "/decrypt"
    response = requests.post(dec_url, {"key": key, "ciphertext": msg})
    r_json = response.json()
    return r_json["name"]


def create_decryption_url(encrypted_msg: str, key: str) -> str:
    """:param encrypted_msg:        Receiver's encrypted name
    """
    return "{site_url}?name={name}&key={key}".format(
        site_url=SITE_URL,
        name=urllib.parse.quote_plus(encrypted_msg),
        key=urllib.parse.quote_plus(key),
    )


def encrypt_pairings(
    pairings: Dict[str, str], api_base_url: str = API_BASE_URL
) -> Dict[str, dict]:
    d = {}
    for giver, receiver in pairings.items():
        # create keys
        key, enc_receiver_name = encrypt_name_with_api(receiver, api_base_url)
        logging.debug(
            "Checking decryption API gives the correct value for %s...", receiver
        )
        r_name = decrypt_with_api(key, enc_receiver_name, api_base_url)
        assert r_name == receiver
        d[giver] = {
            "name": receiver,
            "key": key,
            "encrypted_message": enc_receiver_name,
        }
    return d


def sanity_check_encrypted_pairings(data_dir: str, emails: Dict[str, str]):
    """
    Throws assertion error on failure
    """
    fname = os.path.join(data_dir, "encrypted_pairings.json")
    enc_pairings = {}  # type: Dict[str, dict]
    with open(fname) as fp:
        enc_pairings = json.load(fp)
    logging.debug("Read encrypted pairings from disk")
    pairings = {}  # type: Dict[str, str]
    for giver, enc_receiver in enc_pairings.items():
        r = decrypt_with_api(
            key=enc_receiver["key"],
            msg=enc_receiver["encrypted_message"],
            api_base_url=API_BASE_URL,
        )
        pairings[giver] = r
    names = list(emails.keys())
    assert isinstance(names, list)
    logging.debug("Successfully read names from config folder")
    sanity_check_pairings(pairings, names)
