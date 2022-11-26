import copy
import json
import logging
import os.path
from argparse import ArgumentParser
from datetime import datetime
from typing import Dict, List, Optional

import coloredlogs

from .config import CONFIG_DIR, read_config
from .email_utils import create_emails, sanity_check_emails, send_all_emails
from .encryption_api import (
    create_decryption_url,
    encrypt_pairings,
    sanity_check_encrypted_pairings,
)
from .secret_santa import create_pairings_from_file, read_people_safe
from .sms_utils import send_all_sms_messages, create_text_messages


DATA_OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)


def setup_logging(verbose: bool):
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)
    coloredlogs.install(level=log_level)
    for module in ["urllib3", "botocore"]:
        logging.getLogger(module).setLevel(logging.WARNING)


def save_encrypted_pairings(enc_pairings: Dict[str, dict], output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    logging.debug("Saving encrypted pairings (without receiver name)...")
    p2 = copy.deepcopy(enc_pairings)
    for d in p2.values():
        d.pop("name", None)
    fname = os.path.join(output_dir, "encrypted_pairings.json")
    with open(fname, "w") as fp:
        json.dump(p2, fp, sort_keys=True, indent=4)
    logging.debug("Saved encrypted pairings in file %s", fname)


def save_unencrypted_pairings(pairings: Dict[str, str], output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    fname = os.path.join(output_dir, "unencrypted_pairings.json")
    with open(fname, "w") as fp:
        json.dump(pairings, fp, sort_keys=True, indent=4)
    logging.debug("Saved unencrypted pairings to disk")


def main(
    people_fname: str,
    email_fname: str,
    sms_fname: str,
    config_fname: str,
    aws_config_fname: str,
    output_dir: str,
    live: bool,
    encrypt: bool,
    random_seed: Optional[int],
    encrypted_pairings_fname: Optional[str],
) -> None:
    if encrypted_pairings_fname:
        assert (
            encrypt
        ), "--encrypt option must be specified if supplying encrypted pairings file"
    if encrypted_pairings_fname is None:
        logging.debug(
            "No encrypted pairings file specified, creating pairings from file %s",
            people_fname,
        )
        pairings = create_pairings_from_file(people_fname, random_seed=random_seed)
        if not live:
            logging.warning("Not sending emails since this is a dry run.")
            print("Pairings:")
            for i, (g, r) in enumerate(pairings.items()):
                print(f"\t{i + 1}. {g} -> {r}")
    config = read_config(config_fname)
    people = read_people_safe(people_fname)
    if encrypt:
        if encrypted_pairings_fname:
            logging.debug("Read encrypted pairings from file")
            with open(encrypted_pairings_fname) as fp:
                enc_pairings = json.load(fp)
        else:
            enc_pairings = encrypt_pairings(pairings)
        save_encrypted_pairings(enc_pairings, output_dir=output_dir)
        create_emails(
            pairings=enc_pairings,
            email_template_fname=email_fname,
            output_dir=output_dir,
        )
        if live:
            givers = list(enc_pairings.keys())
            # get the emails
            emails = {}  # type: Dict[str, str]
            for name, item in people.items():
                assert "email" in item
                emails[name] = item["email"]
            send_all_emails(
                givers=givers,
                emails=emails,
                email_subject=config["email_subject"],
                output_dir=output_dir,
            )
        else:
            # print the decryption URLs
            print("Decryption URLs:")
            i = 1
            for g, d in enc_pairings.items():
                url = create_decryption_url(
                    encrypted_msg=d["encrypted_message"], key=d["key"]
                )
                print(f"\t{i}. Giver = {g}")
                print(f"\tDecryption URL = {url}")
                i += 1
            logging.debug("Email subject would have been '%s'", config["email_subject"])
            logging.warning("Not sending emails since this is a dry run.")
    else:
        assert os.path.exists(sms_fname), f"Path to SMS filename {sms_fname} does not exist"
        save_unencrypted_pairings(pairings, output_dir)
        create_text_messages(
            pairings=pairings, template_file=sms_fname, output_dir=output_dir
        )
        send_all_sms_messages(
            people=people,
            output_dir=output_dir,
            is_live=live,
            aws_config_fname=aws_config_fname,
        )


def resend(
    people_fname: str,
    aws_config_fname: str,
    config_fname: str,
    output_dir: str,
    resend_to: List[str],
    encrypt: bool,
) -> None:
    """
    Resend previously sent SMS messages or emails.
    If encrypt is specified, send the emails.
    Otherwise send the text messages.
    :param resend_to: Specifies the people to whom we are resending emails
    """
    assert isinstance(resend_to, list)
    config = read_config(config_fname)
    people = read_people_safe(people_fname)
    if encrypt:
        emails = {}  # type: Dict[str, str]
        for name, item in people.items():
            assert ("email" in item)
            emails[name] = item["email"]
        send_all_emails(
            givers=resend_to,
            emails=emails,
            email_subject=config["email_subject"],
            output_dir=output_dir,
        )
    else:
        logging.info("Only resending to selected people")
        resend_people = {}
        for name in resend_to:
            logging.info("Picked %s", name)
            assert name in people
            resend_people[name] = people[name]
        send_all_sms_messages(
            people=resend_people,
            output_dir=output_dir,
            is_live=True,
            aws_config_fname=aws_config_fname,
        )


if __name__ == "__main__":
    year = datetime.now().year
    # these files change from year to year
    people_fname = os.path.join(CONFIG_DIR, f"names_{year}.json")
    email_fname = os.path.join(CONFIG_DIR, f"instructions_email_{year}.md")
    sms_fname = os.path.join(CONFIG_DIR, f"sms_template_{year}.jinja2")

    parser = ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually send the emails. By default dry run",
    )
    parser.add_argument(
        "--sms-fname",
        default=sms_fname,
        help="Filename that contains the jinja2 template for the SMS messages",
    )
    parser.add_argument(
        "--people-file",
        default=people_fname,
        help="Filename that contains people's names and contact info",
    )
    parser.add_argument(
        "--encrypt",
        action="store_true",
        help="Use the boompig encryption/decryption service to encrypt/decrypt the pairings",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output for debugging"
    )
    parser.add_argument(
        "--resend",
        nargs="+",
        default=None,
        help="Resend emails/SMS to the people listed. Can give as many people. Names must match exactly with names file.",
    )
    parser.add_argument(
        "--sanity-check",
        action="store_true",
        help="Checks saved encrypted pairings to verify that the pairings were valid",
    )
    parser.add_argument(
        "--sanity-check-emails",
        action="store_true",
        help="Checks existing emails to verify that the pairings were valid",
    )
    parser.add_argument(
        "--output-dir",
        "-D",
        default=DATA_OUTPUT_DIR,
        help="Directory where to store intermediate values",
    )
    parser.add_argument(
        "-s",
        "--random-seed",
        type=int,
        default=None,
        help="Random seed to use to generate repeatable pairings",
    )
    parser.add_argument(
        "--encrypted-pairings",
        default=None,
        help="Reuse previous encrypted pairings as specified by this file",
    )
    args = parser.parse_args()
    setup_logging(args.verbose)
    # these files do not change from year to year
    config_fname = os.path.join(CONFIG_DIR, "config.json")
    aws_config_fname = os.path.join(CONFIG_DIR, "aws.json")
    assert os.path.exists(args.people_file), f"file {args.people_file} does not exist"
    # assert os.path.exists(email_fname), f"file {email_fname} does not exist"
    logging.debug("Using output directory %s", args.output_dir)
    if args.resend:
        resend(
            aws_config_fname=aws_config_fname,
            people_fname=args.people_file,
            config_fname=config_fname,
            output_dir=args.output_dir,
            resend_to=args.resend,
            encrypt=args.encrypt,
        )
    elif args.sanity_check:
        people = read_people_safe(args.people_file)
        sanity_check_encrypted_pairings(
            data_dir=args.output_dir,
            names=list(people.keys()),
        )
    elif args.sanity_check_emails:
        people = read_people_safe(args.people_file)
        emails = {}
        for name, item in people.items():
            assert "email" in item
            emails[name] = item["email"]
        sanity_check_emails(
            data_dir=args.output_dir,
            emails=emails,
        )
    else:
        main(
            email_fname=email_fname,
            sms_fname=args.sms_fname,
            people_fname=args.people_file,
            config_fname=config_fname,
            aws_config_fname=aws_config_fname,
            output_dir=args.output_dir,
            live=args.live,
            encrypt=args.encrypt,
            random_seed=args.random_seed,
            encrypted_pairings_fname=args.encrypted_pairings,
        )
