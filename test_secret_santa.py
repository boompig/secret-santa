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

if __name__ == "__main__":
    nose.run()

