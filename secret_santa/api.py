from typing import Tuple
import requests


def encrypt_name_with_api(name: str, api_base_url: str) -> Tuple[str, str]:
    enc_url = api_base_url + "/encrypt"
    response = requests.post(enc_url, { "name": name })
    r_json = response.json()
    return r_json["key"], r_json["msg"]


def decrypt_with_api(key: str, msg: str, api_base_url: str) -> str:
    dec_url = api_base_url + "/decrypt"
    response = requests.post(dec_url, { "key": key, "ciphertext": msg })
    r_json = response.json()
    return r_json["name"]
