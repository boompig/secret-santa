import logging
from argparse import ArgumentParser
from .secret_santa import main, CONFIG_DIR
import os.path
import coloredlogs


def setup_logging(verbose: bool):
    log_level = (logging.DEBUG if verbose else logging.INFO)
    logging.basicConfig(level=log_level)
    coloredlogs.install(level=log_level)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--live", action="store_true",
        help="Actually send the emails. By default dry run")
    parser.add_argument("--encrypt", action="store_true",
        help="Use the boompig encryption/decryption service to encrypt/decrypt the pairings")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Verbose output for debugging")
    args = parser.parse_args()
    setup_logging(args.verbose)
    people_fname = os.path.join(CONFIG_DIR, "names.json")
    email_fname = os.path.join(CONFIG_DIR, "instructions_email.md")
    assert os.path.exists(people_fname)
    assert os.path.exists(email_fname)
    main(
        email_fname=email_fname,
        people_fname=people_fname,
        live=args.live,
        encrypt=args.encrypt
    )