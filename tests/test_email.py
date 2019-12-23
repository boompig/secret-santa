import json
import os
from unittest.mock import MagicMock

from secret_santa import secret_santa
from secret_santa.config import CONFIG_DIR
from secret_santa.email_utils import (create_emails, get_email_fname,
                                      get_email_text, send_all_emails)

NAMES = {
    "Light Yagami": "kira@deathnote.slav",
    "Eru Roraito": "l@deathnote.slav",
    "Misa Amane": "misamisa@deathnote.slav"
}
SEED = 42
DIR = os.path.dirname(__file__)
EMAIL_TEMPLATE_FNAME = os.path.join(DIR, "instructions_email.md")


def test_get_email_text():
    """Make sure can convert markdown into HTML email and all fields are filled out
    """
    names = list(NAMES.keys())
    pairings = secret_santa.secret_santa_hat(names, random_seed=SEED)
    giver = names[0]
    for giver, receiver in pairings.items():
        format_dict = {
            "giver_name": giver,
            "receiver_name": receiver
        }
        email = get_email_text(EMAIL_TEMPLATE_FNAME, format_dict, "/tmp")
        assert giver in email
        assert receiver in email


def test_create_emails_unencrypted():
    givers = list(NAMES.keys())
    pairings = secret_santa.secret_santa_hat(givers, random_seed=SEED)
    assert isinstance(pairings, dict)
    assert len(pairings) == len(NAMES)
    assert sorted(list(pairings.keys())) == sorted(givers)
    create_emails(
        pairings,
        email_template_fname=EMAIL_TEMPLATE_FNAME,
        output_dir="/tmp"
    )


def test_send_all_emails():
    givers = list(NAMES.keys())
    emails = NAMES.copy()
    mailer = MagicMock()
    email_subject = "Secret Santa 2049"
    output_dir = "/tmp"
    email_contents = {}
    for name in givers:
        fname = get_email_fname(name, output_dir)
        email_contents[name] = f"Hello, {name}."
        with open(fname, "w") as fp:
            fp.write(email_contents[name])
    send_all_emails(
        givers,
        emails,
        email_subject=email_subject,
        output_dir="/tmp",
        mailer=mailer
    )
    for name, email in NAMES.items():
        mailer.send_email.assert_any_call(
            email_subject,
            email_contents[name],
            email
        )
