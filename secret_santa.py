from __future__ import print_function
import json
import os
import random
import subprocess
from gmail import send_secret_santa_email
from BeautifulSoup import BeautifulSoup
from Crypto.Cipher import AES
from Crypto import Random
from binascii import b2a_base64, a2b_base64
import requests
from argparse import ArgumentParser

def get_random_key():
    """:return A new key, base64 encoded string without trailing newline"""
    # 128-bit key, so 16 bytes
    keylen = 16
    bkey = Random.new().read(keylen)
    # trim trailing newline
    return b2a_base64(bkey)[:-1]


def encrypt_receiver_name(receiver_name, ascii_key):
    """
    :param receiver_name: string
    :param ascii_key: base64-encoded string without trailing newline
    Goal: output should be human-readable."""
    # pad the name with null bytes
    padded_name = receiver_name
    while len(padded_name) % AES.block_size != 0:
        padded_name += chr(0)
    iv = Random.new().read(AES.block_size)
    binary_key = a2b_base64(ascii_key)
    cipher = AES.new(binary_key, AES.MODE_CBC, iv)
    binary_ct = iv + cipher.encrypt(padded_name)
    # remove trailing newline
    msg = b2a_base64(binary_ct)
    return msg[:-1]


def decrypt_receiver_name(ciphertext, key):
    """
    :param ciphertext: base64-encoded string without trailing newline
    :param key: base64-encoded string without trailing newline
    """
    ct_full_bin = a2b_base64(ciphertext)
    # the first BLOCK_SIZE bytes are iv
    iv = ct_full_bin[:AES.block_size]
    binary_ct = ct_full_bin[AES.block_size:]
    binary_key = a2b_base64(key)
    cipher = AES.new(binary_key, AES.MODE_CBC, iv)
    padded_name = cipher.decrypt(binary_ct)
    # remove padding
    name = padded_name[:padded_name.find(chr(0))]
    return name


def get_email_text(format_text_fname, fields_dict):
    # read md and modify template
    with open(format_text_fname) as fp:
        contents = fp.read()
    s = contents.format(**fields_dict)
    # write out result
    new_fname = "/tmp/f.md"
    with open(new_fname, "w") as fp:
        fp.write(s)
    # convert to HTML
    html_fname = "test.html"
    args = ["grip", new_fname, "--user-content", "--export", html_fname]
    exit_status = subprocess.call(args)
    assert exit_status == 0
    with open(html_fname) as fp:
        contents = fp.read()
        soup = BeautifulSoup(contents)
        body = soup.findAll("div", {"id": "grip-content"})[0]
    email_text = body.prettify()
    os.remove(new_fname)
    os.remove(html_fname)
    return email_text


def read_people(fname):
    with open(fname) as fp:
        obj = json.load(fp)
    return obj


def secret_santa_hat(names):
    hat = names[:]
    random.shuffle(hat)
    redo = False
    pairs = {}
    for giver in names:
        getter = hat[-1]
        while giver == getter:
            if len(hat) == 1:
                # no more people in hat
                redo = True
                break
            else:
                random.shuffle(hat)
                getter = hat[-1]
                # draw again
                pass
        pairs[giver] = getter
        # remove that getter from hat
        hat.pop()
    if redo:
        return secret_santa_hat(names)
    else:
        return pairs


def send_pairings(pairings, people_fname, email_fname):
    people = read_people(people_fname)
    for giver in pairings:
        print("Creating email for %s..." % giver)
        # receiver = pairings[giver]["name"]
        key = pairings[giver]["key"]
        enc_receiver_name = pairings[giver]["encrypted_message"]
        email_format = {
            "enc_receiver_name": enc_receiver_name,
            "enc_key": key,
            "giver_name": giver
        }
        subject = "Secret Santa 2016: Pairings and Instructions"
        email_body = get_email_text(email_fname, email_format)
        send_secret_santa_email(subject, email_body, people[giver])
        print("Sent to %s" % giver)


def encrypt_name_with_api(api_base_url, name):
    enc_url = api_base_url + "/encrypt"
    response = requests.post(enc_url, { "name": name })
    r_json = response.json()
    return r_json["key"], r_json["msg"]


def decrypt_with_api(api_base_url, key, msg):
    dec_url = api_base_url + "/decrypt"
    response = requests.post(dec_url, { "key": key, "ciphertext": msg })
    r_json = response.json()
    return r_json["name"]


def create_and_list_pairings(people_fname):
    api_base_url = "http://localhost:9897/secret-santa/2016"
    people = read_people(people_fname)
    names = people.keys()
    pairings = secret_santa_hat(names)
    d = {}
    # check...
    for giver in pairings:
        assert giver in people
    for giver, receiver in pairings.iteritems():
        # print("%s -> %s" % (giver, receiver))
        # create keys
        key, enc_receiver_name = encrypt_name_with_api(api_base_url, receiver)
        r_name = decrypt_with_api(api_base_url, key, enc_receiver_name)
        print("Checking decryption API gives the correct value...")
        assert r_name == receiver
        # key = get_random_key()
        # enc_receiver_name = encrypt_receiver_name(receiver, key)
        # print("key = %s" % key)
        # print("ciphertext = %s" % enc_receiver_name)
        d[giver] = {
            "name": receiver,
            "key": key,
            "encrypted_message": enc_receiver_name
        }
    return d

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--live", action="store_true", default=False,
        help="Actually send the emails. By default dry run")
    args = parser.parse_args()
    people_fname = "names.json"
    email_fname = "instructions_email.md"
    pairings = create_and_list_pairings(people_fname)
    if args.live:
        send_pairings(pairings, people_fname, email_fname)
    else:
        print("Not sending emails since this is a dry run.")
