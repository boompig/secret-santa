import logging
import os.path
from argparse import ArgumentParser

import coloredlogs

from .secret_santa import (CONFIG_DIR, DATA_OUTPUT_DIR, main, resend,
                           sanity_check_emails,
                           sanity_check_encrypted_pairings)


def setup_logging(verbose: bool):
    log_level = (logging.DEBUG if verbose else logging.INFO)
    logging.basicConfig(level=log_level)
    coloredlogs.install(level=log_level)
    for module in ["urllib3"]:
        logging.getLogger(module).setLevel(logging.WARNING)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--live", action="store_true",
        help="Actually send the emails. By default dry run")
    parser.add_argument("--encrypt", action="store_true",
        help="Use the boompig encryption/decryption service to encrypt/decrypt the pairings")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Verbose output for debugging")
    parser.add_argument("--resend", nargs="+", default=None,
        help="Resend emails to the people listed. Can give as many people. Names must match exactly with names file.")
    parser.add_argument("--sanity-check", action="store_true",
        help="Checks saved encrypted pairings to verify that the pairings were valid")
    parser.add_argument("--sanity-check-emails", action="store_true",
        help="Checks existing emails to verify that the pairings were valid")
    parser.add_argument("-s", "--random-seed", type=int, default=None,
        help="Random seed to use")
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
            resend_to=args.resend
        )
    elif args.sanity_check:
        sanity_check_encrypted_pairings(
            data_dir=DATA_OUTPUT_DIR,
            people_fname=people_fname,
        )
    elif args.sanity_check_emails:
        sanity_check_emails(
            data_dir=DATA_OUTPUT_DIR,
            people_fname=people_fname,
        )
    else:
        main(
            email_fname=email_fname,
            people_fname=people_fname,
            config_fname=config_fname,
            live=args.live,
            encrypt=args.encrypt,
            random_seed=args.random_seed
        )
