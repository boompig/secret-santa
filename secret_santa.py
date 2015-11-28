import json
import random

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
        return secret_santa_hat()
    else:
        return pairs


