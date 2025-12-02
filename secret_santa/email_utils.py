"""
Send pairings via email
"""

import logging
import os
from typing import Dict, Tuple, List, Optional, Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .encryption_api import decrypt_with_api, create_decryption_url, API_BASE_URL
from .gmail import Mailer
from .secret_santa import sanity_check_pairings
from markdown2 import Markdown


def sanity_check_emails(data_dir: str, emails: Dict[str, str]):
    """
    Throws assertion error on failure
    """
    email_dir = os.path.join(data_dir, "emails")
    pairings = extract_all_pairings_from_emails(email_dir, API_BASE_URL)
    logging.debug("All pairings extracted from emails")
    assert isinstance(pairings, dict)
    names = list(emails.keys())
    assert isinstance(names, list)
    logging.debug("Successfully read names from config folder")
    sanity_check_pairings(pairings, names)


def create_emails(
    pairings: dict[str, Any], email_template_fname: str, output_dir: str
) -> None:
    """
    Create HTML email text for everyone and write it to `output_dir`
    :param pairings: Either encrypted or unencrypted pairings.
        If encrypted, values should be dictionaries with `key` and `encrypted_message` keys
    """
    for giver in pairings:
        logging.debug("Creating email body for %s...", giver)
        if isinstance(pairings[giver], dict):
            key = pairings[giver]["key"]
            enc_receiver_name = pairings[giver]["encrypted_message"]
            url = create_decryption_url(key=key, encrypted_msg=enc_receiver_name)
            email_format = {"giver_name": giver, "link": url}
        else:
            assert isinstance(pairings[giver], str)
            receiver_name = pairings[giver]
            email_format = {"giver_name": giver, "receiver_name": receiver_name}
        email_body = get_email_text(email_template_fname, email_format, output_dir)
        email_fname = get_email_fname(giver, output_dir)
        with open(email_fname, "w") as fp:
            fp.write(email_body)
    logging.debug("Created emails for everyone")


def get_email_text(format_text_fname: str, fields_dict: dict, output_dir: str) -> str:
    """Transform the email template with values for each person.
    Save the final markdown and HTML transformation in `output_dir`
    Also return the email text"""
    markdown_dir = os.path.join(output_dir, "markdown")
    if not os.path.exists(markdown_dir):
        # also creates `output_dir` if it doesn't exist
        os.makedirs(markdown_dir)
    markdown_fname = os.path.join(
        markdown_dir, fields_dict["giver_name"].replace(" ", "-") + ".md"
    )
    # read template
    with open(format_text_fname) as fp:
        contents = fp.read()
    # fill in template
    filled_in_template = contents.format(**fields_dict)
    with open(markdown_fname, "w") as fp:
        fp.write(filled_in_template)
    html_dir = os.path.join(output_dir, "html")
    if not os.path.exists(html_dir):
        os.mkdir(html_dir)
    html_fname = os.path.join(
        html_dir, fields_dict["giver_name"].replace(" ", "-") + ".html"
    )
    markdowner = Markdown()
    html_out = markdowner.convert(filled_in_template)
    with open(html_fname, "w") as fp:
        fp.write(html_out)
    email_text = ""
    with open(html_fname) as fp:
        email_text = fp.read()
    return email_text


def send_all_emails(
    givers: List[str],
    emails: Dict[str, str],
    email_subject: str,
    output_dir: str,
    mailer: Optional[Mailer] = None,
    email_body_map: Optional[dict[str, str]] = None,
) -> None:
    """
    Send an email to each person. Assume email text already exists in `output_dir`
    """
    assert isinstance(givers, list)
    if mailer is None:
        mailer = Mailer()
    for giver in givers:
        logging.info("Sending email to %s...", giver)
        if email_body_map is None:
            email_fname = get_email_fname(giver, output_dir=output_dir)
            with open(email_fname) as fp:
                email_body = fp.read()
        else:
            email_body = email_body_map[giver]
        assert isinstance(email_body, str)
        mailer.send_email(email_subject, email_body, emails[giver])
        logging.info("Sent to %s", giver)
    mailer.cleanup()
    logging.debug("Connection closed. All emails sent.")


def get_email_fname(giver_name: str, output_dir: str) -> str:
    email_output_dir = os.path.join(output_dir, "emails")
    try:
        os.makedirs(email_output_dir)
    except Exception:
        # ignore
        pass
    email_fname = os.path.join(email_output_dir, f"{giver_name}.html")
    return email_fname


def extract_all_pairings_from_emails(
    email_dir: str, api_base_url: str
) -> Dict[str, str]:
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
            href = link.attrs["href"]
            assert isinstance(href, str)
            if href.startswith("https://kats.coffee"):
                return href
    raise Exception("fatal error: link not found in email")


def extract_all_enc_pairings_from_emails(email_dir: str) -> Dict[str, dict]:
    enc_pairings = {}  # type: Dict[str, dict]
    for fname in os.listdir(email_dir):
        if fname.endswith(".html"):
            path = os.path.join(email_dir, fname)
            giver, enc_msg, key = extract_enc_pairing_from_email(path)
            assert giver not in enc_pairings
            enc_pairings[giver] = {"encrypted_message": enc_msg, "key": key}
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
