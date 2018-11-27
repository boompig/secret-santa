from binascii import b2a_base64

from Crypto import Random


def get_random_key() -> bytes:
    """:return A new key, base64 encoded string without trailing newline"""
    # 128-bit key, so 16 bytes
    keylen = 16
    bkey = Random.new().read(keylen)
    # trim trailing newline
    return b2a_base64(bkey)[:-1]
