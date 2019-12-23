import copy
import json
import logging
import os.path
import sys
from argparse import ArgumentParser
from typing import Dict, List, Optional

import coloredlogs

from .config import CONFIG_DIR, read_config
from .email_utils import create_emails, sanity_check_emails, send_all_emails
from .encryption_api import (
    create_decryption_url,
    encrypt_pairings,
    sanity_check_encrypted_pairings,
)
from .secret_santa import DATA_OUTPUT_DIR, create_pairings_from_file, read_people


def setup_logging(verbose: bool):
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)
    coloredlogs.install(level=log_level)
    for module in ["urllib3"]:
        logging.getLogger(module).setLevel(logging.WARNING)


def save_encrypted_pairings(enc_pairings: Dict[str, dict], output_dir: str):
    logging.debug("Saving encrypted pairings (without receiver name)...")
    p2 = copy.deepcopy(enc_pairings)
    for d in p2.values():
        d.pop("name", None)
    fname = os.path.join(output_dir, "encrypted_pairings.json")
    with open(fname, "w") as fp:
        json.dump(p2, fp, sort_keys=True, indent=4)


def main(
    people_fname: str,
    email_fname: str,
    config_fname: str,
    live: bool,
    encrypt: bool,
    random_seed: Optional[int],
) -> None:
    pairings = create_pairings_from_file(people_fname, random_seed=random_seed)
    if not live:
        logging.warning("Not sending emails since this is a dry run.")
        print("Pairings:")
        for i, (g, r) in enumerate(pairings.items()):
            print(f"\t{i + 1}. {g} -> {r}")
    config = read_config(config_fname)
    people = read_people(people_fname)
    if encrypt:
        enc_pairings = encrypt_pairings(pairings)
        save_encrypted_pairings(enc_pairings, output_dir=DATA_OUTPUT_DIR)
        create_emails(
            pairings=enc_pairings,
            email_template_fname=email_fname,
            output_dir=DATA_OUTPUT_DIR,
        )
        if live:
            givers = list(enc_pairings.keys())
            send_all_emails(
                givers=givers,
                emails=people,
                email_subject=config["email_subject"],
                output_dir=DATA_OUTPUT_DIR,
            )
        else:
            # print the decryption URLs
            for g, d in enc_pairings.items():
                url = create_decryption_url(
                    encrypted_msg=d["encrypted_message"], key=d["key"]
                )
                print(f"Giver = {g}")
                print(f"Decryption URL = {url}")
    else:
        logging.critical("Unencrypted pairings no longer supported")
        sys.exit(1)


def resend(
    people_fname: str, email_fname: str, config_fname: str, resend_to: List[str]
) -> None:
    assert isinstance(resend_to, list)
    config = read_config(config_fname)
    people = read_people(people_fname)
    send_all_emails(
        givers=resend_to,
        emails=people,
        email_subject=config["email_subject"],
        output_dir=DATA_OUTPUT_DIR,
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually send the emails. By default dry run",
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
        help="Resend emails to the people listed. Can give as many people. Names must match exactly with names file.",
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
        "-s",
        "--random-seed",
        type=int,
        default=None,
        help="Random seed to use to generate repeatable pairings",
    )
    args = parser.parse_args()
    setup_logging(args.verbose)
    people_fname = os.path.join(CONFIG_DIR, "names.json")
    email_fname = os.path.join(CONFIG_DIR, "instructions_email.md")
    config_fname = os.path.join(CONFIG_DIR, "config.json")
    assert os.path.exists(people_fname), f"file {people_fname} does not exist"
    assert os.path.exists(email_fname), f"file {email_fname} does not exist"
    if args.resend:
        resend(
            email_fname=email_fname,
            people_fname=people_fname,
            config_fname=config_fname,
            resend_to=args.resend,
        )
    elif args.sanity_check:
        people = read_people(people_fname)
        sanity_check_encrypted_pairings(
            data_dir=DATA_OUTPUT_DIR, emails=people,
        )
    elif args.sanity_check_emails:
        people = read_people(people_fname)
        sanity_check_emails(
            data_dir=DATA_OUTPUT_DIR, emails=people,
        )
    else:
        main(
            email_fname=email_fname,
            people_fname=people_fname,
            config_fname=config_fname,
            live=args.live,
            encrypt=args.encrypt,
            random_seed=args.random_seed,
        )
