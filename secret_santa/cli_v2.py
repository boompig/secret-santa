import random
import logging
import os
import sys

from sqlalchemy import create_engine, select, exists, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from . import cli_utils
from . import email_utils
from . import file_utils
import secret_santa
from .db_models import Base, Campaign, Participant, Constraint, ConstraintType, Pairing

DEFAULT_DATA_DIR = "data"


def _create_db_session(data_dir: str) -> Session:
    """
    NOTE: `data_dir` must be an absolute path
    """
    assert data_dir.startswith("/"), "Data dir must be an absolute path"

    sqlalchemy_database_uri = f"sqlite:///{data_dir}/secret_santa.db"
    logging.debug("Connecting to database: %s", sqlalchemy_database_uri)
    engine = create_engine(sqlalchemy_database_uri, future=True)
    SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, future=True
    )
    return SessionLocal()


def _rationalize_data_dir(data_dir: str | None) -> str:
    if data_dir is None:
        data_dir = os.path.abspath(DEFAULT_DATA_DIR)
    else:
        data_dir = os.path.abspath(data_dir)

    if not os.path.exists(data_dir):
        logging.info("Created data dir %s", data_dir)
        os.makedirs(data_dir)

    return data_dir


def create_campaign(name: str, data_dir: str | None = None) -> None:
    """
    :param name: Name of the campaign to create
    """
    assert len(name) > 0
    data_dir = _rationalize_data_dir(data_dir)
    db_session = _create_db_session(data_dir)
    Base.metadata.create_all(bind=db_session.get_bind())

    try:
        campaign = Campaign(name=name)
        db_session.add(campaign)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        logging.error("Campaign with name '%s' already exists", name)


def _get_campaign_or_fail(db_session: Session, campaign_name: str) -> Campaign:
    logging.debug("Looking for campaign '%s'...", campaign_name)
    campaign = db_session.execute(
        select(Campaign).where(Campaign.name == campaign_name)
    ).scalar_one()
    logging.debug("Campaign found with ID %d", campaign.id)
    return campaign


def load_participants_from_json(
    path: str, campaign_name: str, data_dir: str | None = None
) -> None:
    """Read a JSON file of participants and load it into the DB for a given campaign."""

    d = file_utils.read_participants_json(path)
    data_dir = _rationalize_data_dir(data_dir)
    db_session = _create_db_session(data_dir)
    Base.metadata.create_all(bind=db_session.get_bind())

    # find the campaign
    campaign = _get_campaign_or_fail(db_session, campaign_name)

    try:
        for name, p_obj in d.items():
            p = Participant(
                name=p_obj["name"],
                email=p_obj.get("email"),
                text=p_obj.get("text"),
                is_verified=p_obj.get("is_verified"),
                campaign_id=campaign.id,
            )
            db_session.add(p)
        db_session.commit()
        logging.info("Loaded %d participants into campaign %d", len(d), campaign.id)
    except IntegrityError:
        db_session.rollback()
        logging.error("Some of these participants have already been added")


def load_constraints_from_json(
    campaign_name: str, path: str, data_dir: str | None = None, verbose: bool = False
) -> None:
    if verbose:
        cli_utils.setup_logging(verbose=True)

    d = file_utils.read_constraints_json(path)
    data_dir = _rationalize_data_dir(data_dir)
    db_session = _create_db_session(data_dir)
    Base.metadata.create_all(bind=db_session.get_bind())

    # find the campaign
    campaign = _get_campaign_or_fail(db_session, campaign_name)

    try:
        n = 0
        for t in ["always", "never"]:
            l = d.get(t, [])
            for giver_name, receiver_name in l:
                logging.debug(
                    "Adding a %s constraint from %s -> %s", t, giver_name, receiver_name
                )

                giver = db_session.execute(
                    select(Participant).where(
                        Participant.name == giver_name,
                        Participant.campaign_id == campaign.id,
                    )
                ).scalar_one()
                receiver = db_session.execute(
                    select(Participant).where(
                        Participant.name == receiver_name,
                        Participant.campaign_id == campaign.id,
                    )
                ).scalar_one()

                constraint = Constraint(
                    type=t,
                    campaign_id=campaign.id,
                    giver_id=giver.id,
                    receiver_id=receiver.id,
                )
                n += 1

                db_session.add(constraint)
        db_session.commit()
        logging.info("Loaded %d constraints into campaign %d", n, campaign.id)
    except IntegrityError as err:
        db_session.rollback()
        logging.error("Some of these constraints have already been added: %s", err)


def _gen_random_seed() -> int:
    return random.randrange(1, 65536)


def create_pairings(
    campaign_name: str,
    data_dir: str | None = None,
    random_seed: int | None = None,
    overwrite: bool = False,
) -> None:
    """
    Create pairings for the given campaign and save them to the database.
    :param campaign_name: Name of the campaign to create pairings for
    """
    data_dir = _rationalize_data_dir(data_dir)
    if random_seed is None:
        random_seed = _gen_random_seed()

    db_session = _create_db_session(data_dir)
    Base.metadata.create_all(bind=db_session.get_bind())

    # find the campaign
    campaign = _get_campaign_or_fail(db_session, campaign_name)

    if not overwrite:
        # check if existing
        pairings_exist = db_session.execute(
            select(exists(Pairing.id).where(Pairing.campaign_id == campaign.id))
        ).scalar_one()
        if pairings_exist:
            logging.error(
                "Pairings already exists for campaign %d. Specify --overwrite to overwrite.",
                campaign.id,
            )
            sys.exit(1)

    # fetch participants
    participants = _read_participants_from_db(db_session, campaign_id)
    logging.debug("Fetched %d participants", len(participants))
    p_map = {p.id: p.name for p in participants}

    always_constraints = db_session.scalars(
        select(Constraint).where(
            Constraint.campaign_id == campaign.id,
            Constraint.type == ConstraintType.ALWAYS,
        )
    ).all()
    never_constraints = db_session.scalars(
        select(Constraint).where(
            Constraint.campaign_id == campaign.id,
            Constraint.type == ConstraintType.NEVER,
        )
    ).all()

    assignments = secret_santa.secret_santa_hat(
        names=[p.name for p in participants],
        random_seed=random_seed,
        always_constraints=[
            [p_map[a.giver_id], p_map[a.receiver_id]] for a in always_constraints
        ],
        never_constraints=[
            [p_map[n.giver_id], p_map[n.receiver_id]] for n in never_constraints
        ],
    )
    print(assignments)

    if overwrite:
        # delete the pairings
        db_session.execute(delete(Pairing).where(Pairing.campaign_id == campaign.id))
        campaign.random_seed = None
        db_session.commit()
        logging.info("Deleted existing pairing for campaign %d", campaign.id)

    # save the pairings
    p_map_r = {p.name: p.id for p in participants}
    for giver_name, receiver_name in assignments.items():
        g_id = p_map_r[giver_name]
        r_id = p_map_r[receiver_name]
        pair = Pairing(
            campaign_id=campaign.id,
            giver_id=g_id,
            receiver_id=r_id,
        )
        db_session.add(pair)
    campaign.random_seed = random_seed
    db_session.commit()


def _create_campaign_data_dir(data_dir: str, campaign_name: str) -> str:
    tail = campaign_name.replace(" ", "_")
    path = os.path.join(data_dir, tail)
    try:
        os.makedirs(path)
    except FileExistsError:
        logging.info("Campaign data directory already exists: %s", path)
    return path


def _read_participants_from_db(
    db_session: Session, campaign_id: int
) -> list[Participant]:
    participants = db_session.scalars(
        select(Participant).where(Participant.campaign_id == campaign_id)
    ).all()
    return list(participants)


def _read_pairings_from_db(db_session: Session, campaign_id: int) -> dict[str, str]:
    participants = _read_participants_from_db(db_session, campaign_id)
    p_map: dict[int, str] = {p.id: p.name for p in participants}
    pairings = db_session.scalars(
        select(Pairing).where(Pairing.campaign_id == campaign_id)
    ).all()
    d: dict[str, str] = {}
    for pair in pairings:
        d[p_map[pair.giver_id]] = p_map[pair.receiver_id]
    return d


def send_pairings_via_email(
    campaign_name: str,
    email_template_path: str,
    email_subject: str,
    data_dir: str | None = None,
    encrypt: bool = False,
    live: bool = False,
) -> None:
    """
    :param encrypt: Instead of sending the name of the recipient, instead send a link
    """

    data_dir = _rationalize_data_dir(data_dir)
    campaign_data_dir = _create_campaign_data_dir(data_dir, campaign_name)
    if encrypt:
        raise NotImplementedError

    # template_path = _find_email_template_for_campaign(campaign_data_dir)
    db_session = _create_db_session(data_dir)
    campaign = _get_campaign_or_fail(db_session, campaign_name)

    assert campaign.is_pairings_sent is False, (
        f"Pairings are already sent: {campaign.is_pairings_sent}."
    )

    assert len(email_subject) > 0

    pairings = _read_pairings_from_db(db_session, campaign_id=campaign.id)
    email_utils.create_emails(
        pairings=pairings,
        email_template_fname=email_template_path,
        output_dir=campaign_data_dir,
    )
    send_all_emails()

    raise NotImplementedError


if __name__ == "__main__":
    import fire

    cli_utils.setup_logging(verbose=False)

    fire.Fire()
