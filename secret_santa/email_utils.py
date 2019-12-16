import logging
import os
from typing import Dict, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .api import decrypt_with_api


def extract_all_pairings_from_emails(email_dir: str, api_base_url: str) -> Dict[str, str]:
    pairings = {}  # type: Dict[str, str]
    for fname in os.listdir(email_dir):
        if fname.endswith(".html"):
            path = os.path.join(email_dir, fname)
            giver, receiver = extract_pairing_from_email(path, api_base_url)
            assert giver != receiver
            assert giver not in pairings
            pairings[giver] = receiver
    return pairings


def extract_link_from_email(email_fname: str) -> str:
    with open(email_fname) as fp:
        contents = fp.read()
        soup = BeautifulSoup(contents, "html.parser")
        for link in soup.find_all("a"):
            if link.attrs["href"].startswith("https://boompig.herokuapp.com"):
                return link.attrs["href"]
    raise Exception("fatal error: link not found in email")


def extract_all_enc_pairings_from_emails(email_dir: str) -> Dict[str, dict]:
    enc_pairings = {}  # type: Dict[str, dict]
    for fname in os.listdir(email_dir):
        if fname.endswith(".html"):
            path = os.path.join(email_dir, fname)
            giver, enc_msg, key = extract_enc_pairing_from_email(path)
            assert giver not in enc_pairings
            enc_pairings[giver] = {
                "encrypted_message": enc_msg,
                "key": key
            }
    return enc_pairings


def extract_enc_pairing_from_email(email_fname: str) -> Tuple[str, str, str]:
    # get the giver name from the email's filename
    fname = os.path.split(email_fname)[1]
    giver = os.path.splitext(fname)[0]
    logging.debug("Extracting encrypted msg from email to %s...", giver)
    link = extract_link_from_email(email_fname)
    o = urlparse(link)
    d = parse_qs(o.query)
    d2 = {}  # type: Dict[str, str]
    # parse_qs returns dictionary mapping string to list
    # we know that each list item will actually have a single item
    for k, v in d.items():
        assert isinstance(v, list) and len(v) == 1
        d2[k] = v[0]
    return giver, d2["name"], d2["key"]


def extract_pairing_from_email(email_fname: str, api_base_url: str) -> Tuple[str, str]:
    giver, enc_name, key = extract_enc_pairing_from_email(email_fname)
    # get the receiver's name
    logging.debug("Decrypting encrypted msg for %s...", giver)
    receiver = decrypt_with_api(key=key, msg=enc_name, api_base_url=api_base_url)
    logging.debug("Got receiver information for %s", giver)
    return giver, receiver
