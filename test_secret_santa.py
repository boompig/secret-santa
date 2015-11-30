from secret_santa import *
import nose
import os

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
    names = _get_random_names(50)
    pairs = secret_santa_hat(names)
    getter_set = set([])
    for giver, getter in pairs.iteritems():
        getter_set.add(getter)
    assert len(getter_set) == len(names)

def test_not_self():
    names = _get_random_names(50)
    pairs = secret_santa_hat(names)
    for giver, getter in pairs.iteritems():
        assert giver != getter

def test_all_names_are_givers():
    names = _get_random_names(50)
    orig_name_set = set([name for name in names])
    pairs = secret_santa_hat(names)
    giver_name_set = set([giver for giver in pairs])
    assert len(orig_name_set) == len(giver_name_set)
    for a, b in zip(sorted(orig_name_set), sorted(giver_name_set)):
        assert a == b

def test_read_people():
    fname = "names.json"
    assert os.path.exists(fname)
    people = read_people(fname)
    assert len(people) > 0

def test_get_random_key():
    key = get_random_key(100)
    assert len(key) == 100
    for c in key:
        assert ord(c) >= ord("a") and ord(c) <= ord("z")

def test_encrypt_decrypt_receiver_name():
    name = "Alice Liu"
    key = get_random_key(len(name))
    ciphertext = encrypt_receiver_name(name, key)
    dec_name = decrypt_receiver_name(ciphertext, key)
    assert len(dec_name) == len(name)
    assert name == dec_name

def test_get_email_text():
    fname = "instructions_email.txt"
    people_fname = "names.json"
    assert os.path.exists(fname)
    people = read_people(people_fname)
    names = people.keys()
    pairs = secret_santa_hat(names)

    giver = names[0]
    assert giver in pairs
    receiver_name = pairs[giver]
    key = get_random_key(len(receiver_name))
    enc_receiver_name = encrypt_receiver_name(receiver_name, key)

    format_dict = {
        "giver_name": giver,
        "enc_receiver_name": enc_receiver_name,
        "enc_key": key
    }
    email = get_email_text(fname, format_dict)
    print email
    assert email is not None


if __name__ == "__main__":
    nose.run()

