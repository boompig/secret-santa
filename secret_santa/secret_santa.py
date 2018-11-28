from __future__ import print_function

import json
import logging
import os
import random
import subprocess
import urllib.parse
from pprint import pprint
from typing import List, Dict, Tuple
import tempfile
from markdown2 import Markdown

import requests

from .gmail import send_secret_santa_email

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
# used to encrypt names
SITE_URL = "https://boompig.herokuapp.com/secret-santa/2018"
API_BASE_URL = "https://boompig.herokuapp.com/secret-santa/api"

DATA_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def get_email_text(format_text_fname: str, fields_dict: dict) -> str:
    """Transform the email template with values for each person."""
    markdown_dir = os.path.join(DATA_OUTPUT_DIR, "markdown")
    if not os.path.exists(markdown_dir):
        # also makes DATA_OUTPUT_DIR if not exists
        os.makedirs(markdown_dir)
    markdown_fname = os.path.join(
        markdown_dir,
        fields_dict["giver_name"].replace(" ", "-") + ".md"
    )
    # read template
    with open(format_text_fname) as fp:
        contents = fp.read()
    # fill in template
    filled_in_template = contents.format(**fields_dict)
    with open(markdown_fname, "w") as fp:
        fp.write(filled_in_template)
    html_dir = os.path.join(DATA_OUTPUT_DIR, "html")
    if not os.path.exists(html_dir):
        os.mkdir(html_dir)
    html_fname = os.path.join(
        html_dir,
        fields_dict["giver_name"].replace(" ", "-") + ".html"
    )
    markdowner = Markdown()
    html_out = markdowner.convert(filled_in_template)
    with open(html_fname, "w") as fp:
        fp.write(html_out)
    email_text = ""
    with open(html_fname) as fp:
        email_text = fp.read()
    return email_text


def read_people(fname: str) -> Dict[str, str]:
    with open(fname) as fp:
        obj = json.load(fp)
    return obj


def is_derangement(l1: list, l2: list) -> bool:
    assert isinstance(l1, list)
    assert isinstance(l2, list)
    if len(l1) != len(l2):
        return False
    for e1, e2 in zip(l1, l2):
        if e1 == e2:
            return False
    return True


def fisher_yates(l: list) -> None:
    """in-place shuffle of list l"""
    assert isinstance(l, list)
    random.shuffle(l)


def get_derangement(l: list) -> list:
    """Return a derangement of the list l. Expected runtime is e * O(n).
    l is not modified
    """
    assert isinstance(l, list)
    # necessary because we do not actually want to modify l
    l2 = l[:]
    while not is_derangement(l, l2):
        fisher_yates(l2)
    return l2


def secret_santa_hat(names: List[str]) -> Dict[str, str]:
    assert isinstance(names, list)
    derangement = get_derangement(names)
    d = {}
    for giver, receiver in zip(names, derangement):
        assert giver != receiver
        d[giver] = receiver
    return d


def get_decryption_url(d: dict) -> str:
    import urllib.parse
    return "{}?name={}&key={}".format(
        urllib.parse.quote_plus(d["enc_receiver_name"]),
        urllib.parse.quote_plus(d["enc_key"])
    )


def send_encrypted_pairings(pairings: Dict[str, dict],
                  people_fname: str,
                  email_fname: str,
                  send_emails: bool = True) -> None:
    assert os.path.exists(people_fname)
    people = read_people(people_fname)
    for giver in pairings:
        print("Creating email for %s..." % giver)
        key = pairings[giver]["key"]
        enc_receiver_name = pairings[giver]["encrypted_message"]
        url = get_decryption_url({
            "enc_key": key,
            "enc_receiver_name": enc_receiver_name
        })
        email_format = {
            "giver_name": giver,
            "link": url
        }
        subject = "Secret Santa 2017: Pairings and Instructions"
        email_body = get_email_text(email_fname, email_format)
        # save the email body
        try:
            os.mkdir("data")
        except Exception:
            # ignore
            pass
        with open("data/{person}.html".format(person=giver), "w") as fp:
            fp.write(email_body)
        if send_emails:
            send_secret_santa_email(subject, email_body, people[giver])
            print("Sent to %s" % giver)


def encrypt_name_with_api(name: str, api_base_url: str = API_BASE_URL) -> Tuple[str, str]:
    enc_url = api_base_url + "/encrypt"
    response = requests.post(enc_url, { "name": name })
    r_json = response.json()
    return r_json["key"], r_json["msg"]


def decrypt_with_api(key: str, msg: str, api_base_url: str = API_BASE_URL) -> str:
    dec_url = api_base_url + "/decrypt"
    response = requests.post(dec_url, { "key": key, "ciphertext": msg })
    r_json = response.json()
    return r_json["name"]


def create_pairings(people_fname: str) -> Dict[str, str]:
    people = read_people(people_fname)
    assert isinstance(people, dict)
    names = list(people.keys())
    pairings = secret_santa_hat(names)
    # check...
    for giver in pairings:
        assert giver in people
    return pairings


def encrypt_pairings(pairings: Dict[str, str], api_base_url: str = API_BASE_URL) -> Dict[str, dict]:
    d = {}
    for giver, receiver in pairings.items():
        # create keys
        key, enc_receiver_name = encrypt_name_with_api(receiver, api_base_url)
        logging.debug("Checking decryption API gives the correct value for %s...", receiver)
        r_name = decrypt_with_api(key, enc_receiver_name, api_base_url)
        assert r_name == receiver
        d[giver] = {
            "name": receiver,
            "key": key,
            "encrypted_message": enc_receiver_name
        }
    return d


def create_decryption_url(encrypted_msg: str, key: str) -> str:
    return "{site_url}?name={name}&key={key}".format(
        site_url=SITE_URL,
        name=urllib.parse.quote_plus(encrypted_msg),
        key=urllib.parse.quote_plus(key)
    )


def main(people_fname: str, email_fname: str, live: bool, encrypt: bool):
    pairings = create_pairings(people_fname)
    if not live:
        logging.warning("Not sending emails since this is a dry run.")
        print("Pairings:")
        for i, (g, r) in enumerate(pairings.items()):
            print(f"\t{i + 1}. {g} -> {r}")
    if encrypt:
        enc_pairings = encrypt_pairings(pairings)
        if live:
            send_encrypted_pairings(enc_pairings, people_fname, email_fname, live)
        else:
            # print the decryption URLs
            for g, d in enc_pairings.items():
                url = create_decryption_url(d["encrypted_message"], d["key"])
                print(f"Giver = {g}")
                print(f"Decryption URL = {url}")
    else:
        raise Exception("Unencrypted pairings no longer supported")
