import json
import random
import subprocess
from gmail import send_secret_santa_email
from BeautifulSoup import BeautifulSoup

def get_random_key(keylen):
    """Return lowercase string, which has same # of bytes as keylen"""
    l = []
    for i in range(keylen):
        c = random.randint(0, 25)
        l.append(chr(c + 97))
    return "".join(l)

def pad_hex(c):
    """c is a number representing a character (0-255)"""
    h = hex(c)[2:]
    while len(h) < 3:
        h = "0" + h
    return h

def encrypt_receiver_name(receiver_name, key):
    """Goal: output should be human-readable.
    One way to do this is to output hex, padded to 3 chars."""
    assert len(receiver_name) == len(key)
    rb = [ord(c) for c in receiver_name]
    kb = [ord(c) for c in key]
    l = []
    for rc, kc in zip(rb, kb):
        v = rc ^ kc
        l.append(pad_hex(v))
    return "".join([c for c in l])

def hex_string_to_byte_list(s):
    l = []
    for i in range(0, len(s), 3):
        c = int("0x" + s[i:i+3], 16)
        l.append(c)
    return l

def decrypt_receiver_name(ciphertext, key):
    """ciphertext is a string of hex, each 3 hex chars are 1 actual byte.
    key is a byte string"""
    # convert ciphertext into a list of chars, same with key
    key_list = [ord(c) for c in key]
    cipher_list = hex_string_to_byte_list(ciphertext)
    l = []
    for cc, kc in zip(cipher_list, key_list):
        v = cc ^ kc
        l.append(chr(v))
    return "".join([c for c in l])

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
    return body.prettify()

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


def create_and_send_pairings_to_me(people_fname, email_fname):
    people = read_people(people_fname)
    names = people.keys()
    pairings = secret_santa_hat(names)
    giver = "Daniel"
    receiver = pairings[giver]
    key = get_random_key(len(receiver))
    enc_receiver_name = encrypt_receiver_name(receiver, key)
    email_format = {
        "enc_receiver_name": enc_receiver_name,
        "enc_key": key,
        "giver_name": giver
    }
    subject = "Secret Santa: Test Email"
    email_body = get_email_text(email_fname, email_format)
    send_secret_santa_email(subject, email_body, people[giver])
