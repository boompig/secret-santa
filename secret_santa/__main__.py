import logging
from argparse import ArgumentParser
from .secret_santa import main, resend, CONFIG_DIR
import os.path
import coloredlogs


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
    args = parser.parse_args()
    setup_logging(args.verbose)
    people_fname = os.path.join(CONFIG_DIR, "names.json")
    email_fname = os.path.join(CONFIG_DIR, "instructions_email.md")
    config_fname = os.path.join(CONFIG_DIR, "config.json")
    assert os.path.exists(people_fname)
    assert os.path.exists(email_fname)
    if args.resend:
        resend(
            email_fname=email_fname,
            people_fname=people_fname,
            config_fname=config_fname,
            resend_to=args.resend
        )
    else:
        main(
            email_fname=email_fname,
            people_fname=people_fname,
            config_fname=config_fname,
            live=args.live,
            encrypt=args.encrypt
        )