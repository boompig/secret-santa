import json
import os
from unittest.mock import patch, mock_open

from secret_santa.crypto_utils import get_random_key
from secret_santa import secret_santa

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
NAMES = {
    "Light Yagami": "kira@deathnote.slav",
    "Eru Roraito": "l@deathnote.slav",
    "Misa Amane": "misamisa@deathnote.slav"
}


def _get_random_names(num_names):
    assert num_names > 0
    assert num_names < 255
    names = []
    for i in range(num_names):
        names.append(chr(i))
    return names


def test_get_random_names():
    names = _get_random_names(50)
    assert len(names) == 50


def test_unique_pairs():
    """Make sure each secret-pair is unique"""
    names = _get_random_names(50)
    pairs = secret_santa.secret_santa_hat(names)
    giver_set = set([])
    getter_set = set([])
    for giver, getter in pairs.items():
        giver_set.add(giver)
        getter_set.add(getter)
    assert len(giver_set) == len(names)
    assert len(getter_set) == len(names)


def test_not_self():
    """Make sure you never get yourself in secret santa"""
    names = _get_random_names(50)
    pairs = secret_santa.secret_santa_hat(names)
    for giver, getter in pairs.items():
        assert giver != getter


def test_all_names_are_givers():
    """Make sure each person is a giver"""
    names = _get_random_names(50)
    orig_name_set = set([name for name in names])
    pairs = secret_santa.secret_santa_hat(names)
    giver_name_set = set([giver for giver in pairs])
    assert len(orig_name_set) == len(giver_name_set)
    for a, b in zip(sorted(orig_name_set), sorted(giver_name_set)):
        assert a == b


def test_read_people():
    s = json.dumps(NAMES)
    fname = os.path.join(CONFIG_DIR, "names.json")
    with patch("builtins.open", mock_open(read_data=s)) as mock_file:
        people = secret_santa.read_people(fname)
        assert len(people) > 0
        mock_file.assert_called_once()



def test_get_random_key():
    key = get_random_key()
    assert key[-2:] == b"=="


def test_get_email_text():
    """Make sure can convert markdown into HTML email and all fields are filled out
    """
    fname = os.path.join(CONFIG_DIR, "instructions_email.md")
    people_fname = os.path.join(CONFIG_DIR, "names.json")
    people_data = json.dumps(NAMES)
    with patch("builtins.open", mock_open(read_data=people_data)) as mock_file:
        people = secret_santa.read_people(people_fname)
        mock_file.assert_called_once()
    assert os.path.exists(fname)
    names = list(people.keys())
    pairs = secret_santa.secret_santa_hat(names)
    giver = names[0]
    assert giver in pairs
    receiver_name = pairs[giver]
    key = get_random_key()
    key, enc_receiver_name = secret_santa.encrypt_name_with_api(receiver_name)
    format_dict = {
        "giver_name": giver,
        "enc_receiver_name": enc_receiver_name,
        "enc_key": key,
        "link": "sample link here"
    }
    email = secret_santa.get_email_text(fname, format_dict)
    assert email is not None
    mock_file.assert_called_once()
