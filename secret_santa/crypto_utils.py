from binascii import b2a_base64

import secrets


def get_random_key() -> bytes:
    """
    :return: A new key, base64 encoded string without trailing newline"""
    # 128-bit key, so 16 bytes
    keylen = 16
    bkey = secrets.token_bytes(keylen)
    assert isinstance(bkey, bytes)
    # trim trailing newline
    return b2a_base64(bkey)[:-1]
