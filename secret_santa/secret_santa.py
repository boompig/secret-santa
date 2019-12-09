from __future__ import print_function

import json
import logging
import os
import random
import sys
import urllib.parse
from typing import Dict, List, Optional, Tuple

import requests
from markdown2 import Markdown

from .gmail import Mailer


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

# used to encrypt names
SITE_URL = f"https://boompig.herokuapp.com/secret-santa/{CONFIG['year']}"
DEFAULT_API_BASE_URL = "https://boompig.herokuapp.com/secret-santa/api"
API_BASE_URL = CONFIG.get("API_BASE_URL", DEFAULT_API_BASE_URL)

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
    try:
        with open(fname) as fp:
            return json.load(fp)["names"]
    except FileNotFoundError:
        logging.critical("Failed to read people from file %s", fname)
        sys.exit(1)


def read_constraints(fname: str) -> Dict[str, list]:
    try:
        with open(fname) as fp:
            o = json.load(fp)
            return o.get("constraints", {})
    except FileNotFoundError:
        logging.critical("Failed to read people from file %s", fname)
        sys.exit(1)


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
    https://en.wikipedia.org/wiki/Derangement
    """
    assert isinstance(l, list)
    # necessary because we do not actually want to modify l
    l2 = l[:]
    while not is_derangement(l, l2):
        fisher_yates(l2)
    return l2


def secret_santa_hat_simple(names: List[str]) -> Dict[str, str]:
    """This is the nice and simple way of generating correct pairings"""
    assert isinstance(names, list)
    derangement = get_derangement(names)
    d = {}
    for giver, receiver in zip(names, derangement):
        assert giver != receiver
        d[giver] = receiver
    return d


def secret_santa_search(assignments: dict,
                        available_givers: List[str],
                        available_receivers: List[str]) -> bool:
    """
    This is an implementation of secret santa as a search program.
    This implementation support pre-existing assignments, just make sure to set other variables correctly
    To support fully random assignments, both arrays should be shuffled prior to running this method
    warning: in-place modification of assignments"""
    assert isinstance(assignments, dict)
    assert isinstance(available_givers, list)
    assert isinstance(available_receivers, list)

    if (len(available_givers) == 1 and
        len(available_receivers) == 1 and
        available_givers[0] == available_receivers[0]):
        # failed to create a full assignment
        return False

    if available_givers == []:
        assert available_receivers == []
        return True

    g = available_givers.pop()
    for r in available_receivers:
        r2 = available_receivers.copy()
        r2.remove(r)
        assignments[g] = r
        if secret_santa_search(assignments, available_givers, r2):
            return True
        else:
            assignments.pop(g)

    # restore g to its former position
    available_givers.insert(0, g)
    return False


def secret_santa_hat(names: List[str],
                     always_constraints: Optional[List[list]] = None) -> Dict[str, str]:
    """
    Constraints are expressed with giver first then receiver
    """
    assert isinstance(names, list)
    if always_constraints is None:
        return secret_santa_hat_simple(names)
    else:
        assignments = {}
        givers = set(names)
        receivers = set(names)
        # fix the always constraints
        for item in always_constraints:
            assert len(item) == 2, "always constraint must be expressed as a list of lists with each element having 2 items"
            giver, receiver = item
            assignments[giver] = receiver
            givers.remove(giver)
            receivers.remove(receiver)

        g2 = list(givers)
        random.shuffle(g2)
        r2 = list(receivers)
        random.shuffle(r2)
        assert secret_santa_search(assignments, g2, r2)
        return assignments


def get_email_fname(giver_name: str) -> str:
    email_output_dir = os.path.join(DATA_OUTPUT_DIR, "emails")
    try:
        os.makedirs(email_output_dir)
    except Exception:
        # ignore
        pass
    email_fname = os.path.join(email_output_dir, f"{giver_name}.html")
    return email_fname


def send_all_emails(givers: List[str],
                    email_subject: str,
                    people_fname: str) -> None:
    people = read_people(people_fname)
    # create email text for each person
    mailer = Mailer()
    for giver in givers:
        logging.info("Sending email to %s...", giver)
        email_fname = get_email_fname(giver)
        with open(email_fname) as fp:
            email_body = fp.read()
        assert isinstance(email_body, str)
        mailer.send_email(email_subject, email_body, people[giver])
        logging.info("Sent to %s", giver)
    mailer.cleanup()
    logging.debug("Connection closed. All emails sent.")


def create_emails(pairings: Dict[str, dict],
                  email_template_fname: str) -> None:
    for giver in pairings:
        logging.debug("Creating email body for %s...", giver)
        key = pairings[giver]["key"]
        enc_receiver_name = pairings[giver]["encrypted_message"]
        url = create_decryption_url(
            key=key,
            encrypted_msg=enc_receiver_name
        )
        email_format = {
            "giver_name": giver,
            "link": url
        }
        email_body = get_email_text(email_template_fname, email_format)
        email_fname = get_email_fname(giver)
        with open(email_fname, "w") as fp:
            fp.write(email_body)
    logging.debug("Created emails for everyone")


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
    constraints = read_constraints(people_fname)
    assert isinstance(constraints, dict)
    names = list(people.keys())
    pairings = secret_santa_hat(
        names,
        always_constraints=constraints.get("always", None)
    )
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
    """:param encrypted_msg:        Receiver's encrypted name
    """
    return "{site_url}?name={name}&key={key}".format(
        site_url=SITE_URL,
        name=urllib.parse.quote_plus(encrypted_msg),
        key=urllib.parse.quote_plus(key)
    )


def resend(people_fname: str, email_fname: str, config_fname: str,
           resend_to: List[str]) -> None:
    assert isinstance(resend_to, list)
    config = read_config(config_fname)
    send_all_emails(
        givers=resend_to,
        email_subject=config["email_subject"],
        people_fname=people_fname
    )


def main(people_fname: str, email_fname: str, config_fname: str,
         live: bool, encrypt: bool) -> None:
    pairings = create_pairings(people_fname)
    if not live:
        logging.warning("Not sending emails since this is a dry run.")
        print("Pairings:")
        for i, (g, r) in enumerate(pairings.items()):
            print(f"\t{i + 1}. {g} -> {r}")
    config = read_config(config_fname)
    if encrypt:
        enc_pairings = encrypt_pairings(pairings)
        create_emails(
            pairings=enc_pairings,
            email_template_fname=email_fname,
        )
        if live:
            givers = list(enc_pairings.keys())
            send_all_emails(
                givers=givers,
                people_fname=people_fname,
                email_subject=config["email_subject"],
            )
        else:
            # print the decryption URLs
            for g, d in enc_pairings.items():
                url = create_decryption_url(encrypted_msg=d["encrypted_message"], key=d["key"])
                print(f"Giver = {g}")
                print(f"Decryption URL = {url}")
    else:
        logging.critical("Unencrypted pairings no longer supported")
        sys.exit(1)
