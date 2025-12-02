import json
import logging
import sys

from typing import TypedDict, cast

# from secret_santa.schemas import Participant
# from schemas import Participant as ParticipantSchema


class ParticipantSchema(TypedDict):
    name: str
    email: str | None
    # phone number
    text: str | None
    is_verified: bool | None


# class ConstraintsSchema(TypedDict):
#     always: list[list[str]]
#     never: list[list[str]]


def read_participants_json(fname: str) -> dict[str, ParticipantSchema]:
    """Read the participants from the given JSON file.
    :returns: A mapping from participant names (must be unique within the file) to the Participant object"""

    assert fname.endswith(".json"), "Must read from JSON"

    d: dict[str, ParticipantSchema] = {}
    try:
        with open(fname) as fp:
            contents = json.load(fp)
            assert isinstance(contents, dict)
            names = contents["names"]
            # the names will ordinarily be stored as a dictionary mapping names to props
            assert isinstance(names, dict)
            for name, p_obj in names.items():
                assert isinstance(name, str)
                assert isinstance(p_obj, dict)

                assert "name" not in p_obj, "Participant name must be stored as the key"
                p_obj["name"] = name

                assert "email" in p_obj or "text" in p_obj, (
                    "Participant must have at least one contact method: email or text"
                )
                if "checked" in p_obj and "is_verified" not in p_obj:
                    p_obj["is_verified"] = p_obj.pop("checked")

                # p = ParticipantSchema.model_validate(p_obj)
                d[name] = cast(ParticipantSchema, p_obj)

        return d
    except FileNotFoundError:
        logging.critical("Failed to read people from file %s", fname)
        sys.exit(1)


def read_constraints_json(fname: str) -> dict[str, list]:
    """
    :returns: A container holding optional constraints.
        There are expected to be two categories: always and never
        Each category is a list of constraints.
        Each constraint is a list of two names, with the first being the giver and the second being the receiver.
    """
    with open(fname) as fp:
        contents = json.load(fp)
        assert isinstance(contents, dict)
        return contents.get("constraints", {})
