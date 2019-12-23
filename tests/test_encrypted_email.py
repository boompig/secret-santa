import os
import tempfile
from typing import Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest

from secret_santa import secret_santa
from secret_santa.email_utils import (create_emails, get_email_text,
                                      sanity_check_emails)

from .test_encryption_api import fake_decrypt, fake_encrypt_pairings
from .test_secret_santa import _get_random_names

NAMES = {
    "Light Yagami": "kira@deathnote.slav",
    "Eru Roraito": "l@deathnote.slav",
    "Misa Amane": "misamisa@deathnote.slav"
}
SEED = 42
DIR = os.path.dirname(__file__)
EMAIL_TEMPLATE_FNAME = os.path.join(DIR, "instructions_email_enc.md")


def test_create_emails_encrypted():
    givers = list(NAMES.keys())
    pairings = secret_santa.secret_santa_hat(givers, random_seed=SEED)
    assert isinstance(pairings, dict)
    assert len(pairings) == len(NAMES)
    assert sorted(list(pairings.keys())) == sorted(givers)
    enc_pairings = fake_encrypt_pairings(pairings)
    with tempfile.TemporaryDirectory() as output_dir:
        create_emails(
            enc_pairings,
            email_template_fname=EMAIL_TEMPLATE_FNAME,
            output_dir=output_dir
        )


def test_sanity_check_emails_encrypted_fails():
    names = _get_random_names(50)
    pairings = secret_santa.secret_santa_hat(names, SEED)
    enc_pairings = fake_encrypt_pairings(pairings)
    m_dec = MagicMock(side_effect=fake_decrypt)

    with tempfile.TemporaryDirectory() as output_dir:
        create_emails(enc_pairings, EMAIL_TEMPLATE_FNAME, output_dir)

        with pytest.raises(AssertionError):
            with patch("secret_santa.email_utils.decrypt_with_api", m_dec):
                # with patch("builtins.open", mock_open(read_data=s)):
                sanity_check_emails(output_dir, emails={
                    "Light": "light@deathnote.slav"
                })
                m_dec.assert_called_once()
