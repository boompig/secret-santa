from __future__ import print_function

import json
import logging
import os
import random
import subprocess
from argparse import ArgumentParser
from pprint import pprint

import coloredlogs
import requests
from bs4 import BeautifulSoup

from gmail import send_secret_santa_email


def get_email_text(format_text_fname, fields_dict):
    # read md and modify template
    with open(format_text_fname) as fp:
        contents = fp.read()
    s = contents.format(**fields_dict)
    # write out result
    new_fname = "/tmp/f.md"
    with open(new_fname, "w") as fp:
        fp.write(s)
    # convert to HTML
    html_fname = "test.html"
    args = ["grip", new_fname, "--user-content", "--export", html_fname]
    exit_status = subprocess.call(args)
    assert exit_status == 0
    with open(html_fname) as fp:
        contents = fp.read()
        soup = BeautifulSoup(contents, "html.parser")
        body = soup.findAll("div", {"id": "grip-content"})[0]
    email_text = body.prettify()
    os.remove(new_fname)
    os.remove(html_fname)
    return email_text


def read_people(fname):
    with open(fname) as fp:
        obj = json.load(fp)
    return obj


def is_derangement(l1, l2):
    assert isinstance(l1, list)
    assert isinstance(l2, list)
    if len(l1) != len(l2):
        return False
    for e1, e2 in zip(l1, l2):
        if e1 == e2:
            return False
    return True


def fisher_yates(l):
    """in-place shuffle of list l"""
    assert isinstance(l, list)
    return random.shuffle(l)


def get_derangement(l):
    """Return a derangement of the list l. Expected runtime is e * O(n).
    l is not modified
    """
    assert isinstance(l, list)
    # necessary because we do not actually want to modify l
    l2 = l[:]
    while not is_derangement(l, l2):
        fisher_yates(l2)
    return l2


def secret_santa_hat(names):
    derangement = get_derangement(names)
    d = {}
    for giver, receiver in zip(names, derangement):
        assert giver != receiver
        d[giver] = receiver
    return d


def get_decryption_url(d):
    import urllib.parse
    return "https://boompig.herokuapp.com/secret-santa/2017?name={}&key={}".format(
        urllib.parse.quote_plus(d["enc_receiver_name"]),
        urllib.parse.quote_plus(d["enc_key"])
    )


def send_pairings(pairings, people_fname, email_fname):
    people = read_people(people_fname)
    for giver in pairings:
        print("Creating email for %s..." % giver)
        receiver = pairings[giver]["name"]
        key = pairings[giver]["key"]
        enc_receiver_name = pairings[giver]["encrypted_message"]
        url = get_decryption_url({
            "enc_key": key,
            "enc_receiver_name": enc_receiver_name
        })
        email_format = {
            "giver_name": receiver,
            "link": url
        }
        subject = "Secret Santa 2016: Pairings and Instructions"
        email_body = get_email_text(email_fname, email_format)
        send_secret_santa_email(subject, email_body, people[giver])
        print("Sent to %s" % giver)


def encrypt_name_with_api(api_base_url, name):
    enc_url = api_base_url + "/encrypt"
    response = requests.post(enc_url, { "name": name })
    r_json = response.json()
    return r_json["key"], r_json["msg"]


def decrypt_with_api(api_base_url, key, msg):
    dec_url = api_base_url + "/decrypt"
    response = requests.post(dec_url, { "key": key, "ciphertext": msg })
    r_json = response.json()
    return r_json["name"]


def create_pairings(people_fname):
    people = read_people(people_fname)
    assert isinstance(people, dict)
    names = list(people.keys())
    pairings = secret_santa_hat(names)
    # check...
    for giver in pairings:
        assert giver in people
    return pairings


def encrypt_pairings(pairings):
    api_base_url = "http://localhost:9897/secret-santa/2016"
    d = {}
    for giver, receiver in pairings.items():
        # create keys
        key, enc_receiver_name = encrypt_name_with_api(api_base_url, receiver)
        r_name = decrypt_with_api(api_base_url, key, enc_receiver_name)
        logging.info("Checking decryption API gives the correct value...")
        assert r_name == receiver
        d[giver] = {
            "name": receiver,
            "key": key,
            "encrypted_message": enc_receiver_name
        }
    return d


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    coloredlogs.install()
    parser = ArgumentParser()
    parser.add_argument("--live", action="store_true", default=False,
        help="Actually send the emails. By default dry run")
    parser.add_argument("--encrypt", action="store_true", default=False,
        help="Use the boompig encryption/decryption service to encrypt/decrypt the pairings")
    args = parser.parse_args()
    people_fname = "names.json"
    email_fname = "instructions_email.md"
    pairings = create_pairings(people_fname)
    if not args.live:
        logging.warning("Not sending emails since this is a dry run.")
        print("Pairings:")
        for g, r in pairings.items():
            print("{} -> {}".format(g, r))
    if args.encrypt:
        pairings = encrypt_pairings(pairings)
        if not args.live:
            for g, d in pairings.items():
                # create the URL here:
                import urllib.parse
                url = "http://localhost:9897/secret-santa/2017?name={}&key={}".format(
                    urllib.parse.quote_plus(d["encrypted_message"]),
                    urllib.parse.quote_plus(d["key"])
                )
                print(g)
                print(url)
    if args.live:
        send_pairings(pairings, people_fname, email_fname)
