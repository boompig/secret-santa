import json
import os
from unittest.mock import mock_open, patch

from secret_santa import secret_santa
from secret_santa.config import CONFIG_DIR
from secret_santa.crypto_utils import get_random_key
from secret_santa.email_utils import get_email_text
from secret_santa.encryption_api import API_BASE_URL, encrypt_name_with_api

NAMES = {
    "Light Yagami": "kira@deathnote.slav",
    "Eru Roraito": "l@deathnote.slav",
    "Misa Amane": "misamisa@deathnote.slav"
}
SEED = 42


def test_get_email_text():
    """Make sure can convert markdown into HTML email and all fields are filled out
    """
    fname = os.path.join(CONFIG_DIR, "instructions_email.md")
    people_fname = os.path.join(CONFIG_DIR, "names.json")
    people_data = json.dumps({"names": NAMES})
    with patch("builtins.open", mock_open(read_data=people_data)) as mock_file:
        people = secret_santa.read_people(people_fname)
        mock_file.assert_called_once()
    assert os.path.exists(fname)
    names = list(people.keys())
    pairs = secret_santa.secret_santa_hat(names, random_seed=SEED)
    giver = names[0]
    assert giver in pairs
    receiver_name = pairs[giver]
    key = get_random_key()
    key, enc_receiver_name = encrypt_name_with_api(receiver_name, API_BASE_URL)
    format_dict = {
        "giver_name": giver,
        "link": "sample link here"
    }
    email = get_email_text(fname, format_dict, "/tmp")
    assert email is not None
    mock_file.assert_called_once()
