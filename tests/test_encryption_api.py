import json
from typing import Dict, Tuple
from unittest.mock import MagicMock, patch, mock_open

from secret_santa import secret_santa
from secret_santa.encryption_api import (SITE_URL, create_decryption_url,
                                         encrypt_pairings,
                                         sanity_check_encrypted_pairings)

from .test_secret_santa import _get_random_names

API_BASE_URL = "not a real URL"
SEED = 42
NAMES = {
    "Light Yagami": "kira@deathnote.slav",
    "Eru Roraito": "l@deathnote.slav",
    "Misa Amane": "misamisa@deathnote.slav"
}


def fake_encrypt_pairings(pairings: Dict[str, str]) -> Dict[str, dict]:
    enc_pairings = {}
    for giver, receiver in pairings.items():
        key, msg = fake_encrypt(receiver, API_BASE_URL)
        enc_pairings[giver] = {
            "key": key,
            "encrypted_message": msg
        }
    return enc_pairings


def fake_encrypt(name: str, api_base_url: str) -> Tuple[str, str]:
    return f"key_{name}", f"msg_{name}"


def fake_decrypt(key: str, msg: str, api_base_url: str) -> str:
    assert len(key) > 4
    return key[4:]


def test_encrypt_pairings():
    pairings = {
        "Alice": "Bob"
    }
    m_enc = MagicMock(side_effect=fake_encrypt)
    m_dec = MagicMock(side_effect=fake_decrypt)
    with patch("secret_santa.encryption_api.encrypt_name_with_api", m_enc):
        with patch("secret_santa.encryption_api.decrypt_with_api", m_dec):
            enc_pairings = encrypt_pairings(pairings, API_BASE_URL)
            assert len(enc_pairings) == len(pairings)
            m_enc.assert_called_once_with("Bob", API_BASE_URL)
            key, msg = fake_encrypt("Bob", API_BASE_URL)
            m_dec.assert_called_once_with(key, msg, API_BASE_URL)


def test_create_decryption_url():
    msg = "enc_Bob"
    key = "key_Bob"
    url = create_decryption_url(msg, key)
    assert url.startswith(SITE_URL)


def test_sanity_check_encrypted_pairings():
    names = _get_random_names(50)
    assert isinstance(names, list)
    assert len(names) == 50
    pairings = secret_santa.secret_santa_hat(names, SEED)
    enc_pairings = fake_encrypt_pairings(pairings)
    assert isinstance(enc_pairings, dict)
    assert len(enc_pairings) == len(pairings)
    s = json.dumps(enc_pairings, indent=4)
    assert isinstance(s, str)
    # print(s)

    m_dec = MagicMock(side_effect=fake_decrypt)
    with patch("secret_santa.encryption_api.decrypt_with_api", m_dec):
        with patch("builtins.open", mock_open(read_data=s)):
            sanity_check_encrypted_pairings("/tmp", names, API_BASE_URL)

    for name in names:
        key, msg = fake_encrypt(name, API_BASE_URL)
        m_dec.assert_any_call(key=key, msg=msg, api_base_url=API_BASE_URL)
