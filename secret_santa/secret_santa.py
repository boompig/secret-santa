from __future__ import print_function

import json
import logging
import random
import sys
from typing import Dict, List, Optional


def read_constraints(fname: str) -> Dict[str, list]:
    try:
        with open(fname) as fp:
            o = json.load(fp)
            return o.get("constraints", {})
    except FileNotFoundError:
        logging.critical("Failed to read people from file %s", fname)
        sys.exit(1)


def is_derangement(l1: list, l2: list) -> bool:
    assert isinstance(l1, list)
    assert isinstance(l2, list)
    if len(l1) != len(l2):
        return False
    for e1, e2 in zip(l1, l2):
        if e1 == e2:
            return False
    return True


def fisher_yates(l: list) -> None:
    """in-place shuffle of list l"""
    assert isinstance(l, list)
    random.shuffle(l)


def get_derangement(l: list) -> list:
    """Return a derangement of the list l. Expected runtime is e * O(n).
    l is not modified
    https://en.wikipedia.org/wiki/Derangement
    """
    assert isinstance(l, list)
    # necessary because we do not actually want to modify l
    l2 = l[:]
    while not is_derangement(l, l2):
        fisher_yates(l2)
    return l2


def secret_santa_hat_simple(names: List[str]) -> Dict[str, str]:
    """This is the nice and simple way of generating correct pairings"""
    assert isinstance(names, list)
    derangement = get_derangement(names)
    d = {}
    for giver, receiver in zip(names, derangement):
        assert giver != receiver
        d[giver] = receiver
    return d


def secret_santa_search(
    assignments: Dict[str, str],
    available_givers: List[str],
    available_receivers: List[str],
) -> bool:
    """
    This is an implementation of secret santa as a search program.
    This implementation supports pre-existing assignments, just make sure to set other variables correctly
    To support fully random assignments, both arrays should be shuffled prior to running this method
    warning: in-place modification of assignments"""
    assert isinstance(assignments, dict)
    assert isinstance(available_givers, list)
    assert isinstance(available_receivers, list)

    if (
        len(available_givers) == 1
        and len(available_receivers) == 1
        and available_givers[0] == available_receivers[0]
    ):
        # failed to create a full assignment
        return False

    if available_givers == []:
        assert available_receivers == []
        return True

    g = available_givers.pop()
    for r in available_receivers:
        if r != g:
            r2 = available_receivers.copy()
            r2.remove(r)
            assignments[g] = r
            if secret_santa_search(assignments, available_givers, r2):
                return True
            else:
                assignments.pop(g)

    # restore g to its former position
    available_givers.insert(0, g)
    return False


def check_never_constraints(
    assignments: Dict[str, str], never_constraints: List[list]
) -> bool:
    """
    Return true iff the never constraints are all satisfied
    :param never_constraints: List of lists, where each item has 2 values: giver and receiver
    """
    for pair in never_constraints:
        assert len(pair) == 2
        giver, bad_receiver = pair
        assert giver in assignments, f"giver {giver} must be in assignments"
        if assignments[giver] == bad_receiver:
            return False
    return True


def secret_santa_hat(
    names: List[str],
    random_seed: int,
    always_constraints: Optional[List[list]] = None,
    never_constraints: Optional[List[list]] = None,
) -> Dict[str, str]:
    """
    Constraints are expressed with giver first then receiver
    """
    assert isinstance(names, list)
    assert isinstance(random_seed, int)
    logging.debug("Generating new pairings...")
    logging.debug("Using random seed %s", random_seed)
    random.seed(random_seed)
    base_assignments = {}
    if always_constraints is None:
        logging.debug("Using simple solver")
        return secret_santa_hat_simple(names)
    else:
        givers = set(names)
        receivers = set(names)
        # fix the always constraints
        for item in always_constraints:
            assert (
                len(item) == 2
            ), "always constraint must be expressed as a list of lists with each element having 2 items"
            giver, receiver = item
            base_assignments[giver] = receiver
            givers.remove(giver)
            receivers.remove(receiver)

        MAX_FAILURES = 10
        num_failures = 0
        while num_failures < MAX_FAILURES:
            assignments = base_assignments.copy()
            g2 = list(givers)
            random.shuffle(g2)
            r2 = list(receivers)
            random.shuffle(r2)

            # fill the assignments
            assert secret_santa_search(assignments, g2, r2)
            if never_constraints is None:
                logging.debug("No 'never' constraints so assignment is fine")
                break
            elif check_never_constraints(assignments, never_constraints):
                logging.debug("assignment satisfied all 'never' constraints")
                break
            else:
                logging.debug(
                    f"assignment has failed one or more 'never' constraints. # failures is {num_failures}"
                )
                num_failures += 1

        if num_failures >= MAX_FAILURES:
            logging.critical(
                "Exceeded maximum number of failures on satisfying 'never' constraints"
            )
            sys.exit(1)

        return assignments


def read_people(fname: str) -> Dict[str, dict]:
    try:
        with open(fname) as fp:
            return json.load(fp)["names"]
    except FileNotFoundError:
        logging.critical("Failed to read people from file %s", fname)
        sys.exit(1)


def create_pairings_from_file(
    people_fname: str, random_seed: Optional[int] = None
) -> Dict[str, str]:
    """
    Given a file which lists people in a pre-specified format, return a mapping from giver to receiver
    :param people_fname: A file that can be consumed by `read_people`
    :param random_seed: Random seed value for reproducibility. Otherwise completely random.
    """
    if random_seed is None:
        random_seed = random.randrange(1, sys.maxsize)
    people = read_people(people_fname)
    assert isinstance(people, dict)
    constraints = read_constraints(people_fname)
    assert isinstance(constraints, dict)
    names = list(people.keys())
    pairings = secret_santa_hat(
        names,
        always_constraints=constraints.get("always", None),
        never_constraints=constraints.get("never", None),
        random_seed=random_seed,
    )
    sanity_check_pairings(pairings, names)
    return pairings


def sanity_check_pairings(pairings: Dict[str, str], names: List[str]):
    """
    Throws assertion error on failure
    Warning: this method sorts the names array
    """
    names.sort()
    receivers = list(pairings.values())
    receivers.sort()
    givers = list(pairings.keys())
    givers.sort()
    assert givers == names, "Givers should be same list as names"
    assert receivers == names, "Receivers should be same list as names"
    for giver, receiver in pairings.items():
        logging.debug("Checking pairing validity for giver %s...", giver)
        assert giver != receiver, "Giver and receiver cannot be the same"
        assert giver in names
        assert receiver in names
    logging.info("Sanity check complete! Pairings looking good!")
