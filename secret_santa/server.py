from json.decoder import JSONDecodeError
from typing import Dict, List
import json
import logging
import os
import random

from flask import Flask, render_template, session, request, flash, redirect, url_for

from .secret_santa import read_people, secret_santa_hat


app = Flask(__name__, static_folder="./public", static_url_path="/public")
app.secret_key = 'temp key for debugging'


def discover_people_files() -> List[str]:
    json_files = []
    for file in os.listdir("./config"):
        if file.endswith(".json"):
            try:
                path = "./config/" + file
                # make sure that this is a valid people file
                read_people(path)
                json_files.append(path)
            except Exception:
                pass
    return json_files


def discover_past_campaigns() -> Dict[str, str]:
    """Discover past campaigns that have been sent"""
    campaigns = {}
    for file in os.listdir("./archive"):
        path = "./archive/" + file
        if os.path.isdir(path) and file != "sms":
            campaigns[file] = path
    return campaigns


def read_unencrypted_pairings_from_file(path: str) -> Dict[str, str]:
    with open(path) as fp:
        pairings = json.load(fp)
        return pairings


@app.route("/", methods=["GET"])
def index():
    people_files = discover_people_files()
    past_campaigns = discover_past_campaigns()
    return render_template("index.jinja2",
        pairings=None,
        people_files=people_files,
        past_campaigns=past_campaigns,
    )


@app.route("/new-campaign", methods=["GET"])
def view_new_campaign():
    if "people" not in session:
        return redirect(url_for("index"))
    return render_template("new_campaign.jinja2",
        pairings=None
    )


@app.route("/past-campaign", methods=["GET"])
def view_past_campaign():
    campaign_name = request.args.get("campaign_name" )
    if not campaign_name:
        flash("campaign name must be an argument")
        return redirect(url_for("index"))
    show_assignment = request.args.get("show_assignment", 0, type=int)
    # find the details of that campaign
    # bring up the names file
    path = "./archive/" + campaign_name
    assert os.path.exists(path)
    people_path = path + "/names.json"
    people = read_people(people_path)
    pairings_path = path + "/unencrypted_pairings.json"
    pairings = read_unencrypted_pairings_from_file(pairings_path)
    return render_template("past_campaign.jinja2",
        campaign_name=campaign_name,
        people=people,
        show_assignment=show_assignment,
        pairings=pairings,
    )


@app.route("/submit/people", methods=["POST"])
def handle_submit_people():
    """Receive selection of people filename as first step to creating new campaign"""
    assert "people_file_path" in request.form
    logging.info("Received file path %s", request.form["people_file_path"])
    try:
        people = read_people(request.form["people_file_path"])
        session["people"] = people
        session["people_file_path"] = request.form["people_file_path"]
        return redirect(url_for("view_new_campaign"))
    except FileNotFoundError as err:
        logging.error(err)
        flash("file not found")
        return render_template("index.jinja2",
            pairings=None
        )
    except KeyError as err:
        logging.error(err)
        flash("JSON file must have 'names' key")
        return render_template("index.jinja2",
            pairings=None
        )
    except JSONDecodeError as err:
        logging.error(err)
        flash("must be a JSON file")
        return render_template("index.jinja2",
            pairings=None
        )


@app.route("/submit/reset-people", methods=["POST"])
def handle_reset_people():
    """Reset all variables to go back"""
    if "people" in session:
        session.pop("people")
    if "people_file_path" in session:
        session.pop("people_file_path")
    return redirect(url_for("index"))


@app.route("/submit/assignment", methods=["POST"])
def handle_submit_assignment():
    """Simulate creating a secret santa assignment as part of a new campaign"""
    assert "people" in session
    # create a new random seed each time
    seed = int(random.random() * 100_000)
    names = list(session["people"].keys())
    pairings = secret_santa_hat(
        names=names,
        random_seed=seed,
    )
    return render_template("new_campaign.jinja2",
        pairings=pairings,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8080)

