"""
This file contains everything necessary to send secret santa pairings by text.

Written by Daniel Kats
2020
"""

import json
import logging
import os
import requests
from typing import Dict

import boto3
import jinja2


def read_aws_config(fname: str) -> dict:
    with open(fname) as fp:
        obj = json.load(fp)
        return obj


def create_text_messages(pairings: Dict[str, str], template_file: str, output_dir: str):
    d = os.path.join(output_dir, "sms")
    if not os.path.exists(d):
        os.makedirs(d)
    template_contents = ""
    with open(template_file) as fp:
        template_contents = fp.read()
    logging.debug("Creating SMS template docs...")
    for giver, receiver in pairings.items():
        logging.debug(f"Creating SMS template for {giver}...")
        assert isinstance(giver, str)
        assert isinstance(receiver, str)
        template = jinja2.Template(template_contents)
        s = template.render({"giver": giver, "receiver": receiver})
        out_fname = os.path.join(d, giver + ".txt")
        with open(out_fname, "w") as fp:
            fp.write(s)
    logging.debug("All SMS templates created")


def clicksend_send_sms(to_phone_number: str, message: str):
    from pprint import pprint

    session = requests.Session()
    session.auth = ("dbkats@gmail.com", "D19044A5-C13E-697E-F740-0B1C1C0611D6")
    data = {
        "messages": [
            {
                "body": message,
                "to": to_phone_number.replace(" ", ""),
            }
        ]
    }
    # send a text message
    res = session.post(
        "https://rest.clicksend.com/v3/sms/send",
        json=data,
    )
    pprint(res)


def send_all_sms_messages(
    people: Dict[str, dict], output_dir: str, is_live: bool, aws_config_fname: str
):
    """
    Use AWS SNS to send an SMS message to each person in `people`.
    Assume SMS text already exists in `output_dir`
    :param people: output of read_people
    :param output_dir:  Directory with SMS text contents.
                        Each SMS text will have the person's name attached.
    :param is_live:     If false, then this will merely be a dry run
    """
    aws_config = read_aws_config(aws_config_fname)
    # Create an SNS client
    client = boto3.client(
        "sns",
        aws_access_key_id=aws_config["aws_access_key_id"],
        aws_secret_access_key=aws_config["aws_secret_access_key"],
        region_name=aws_config["region"],
    )

    messages = {}

    use_clicksend = True
    # collect all the messages first
    # this is done to make sure we can send messages to everyone
    for giver, notify_methods in people.items():
        assert "text" in notify_methods, f"no text notification set for {giver}"
        number = notify_methods["text"].replace(" ", "")
        assert "-" not in number
        message_fname = os.path.join(output_dir, "sms", giver + ".txt")
        with open(message_fname) as fp:
            message = fp.read()
            messages[giver] = {"message": message, "number": number}
    for giver, o in messages.items():
        if is_live:
            logging.info(f"Sending SMS message to {giver}...")
            if use_clicksend:
                clicksend_send_sms(o["number"], o["message"])
            else:
                client.publish(PhoneNumber=o["number"], Message=o["message"])
        else:
            print(o["number"])
            print(o["message"])
            logging.warning("This is a dry run. Not sending message.")
    logging.info("All SMS messages sent.")


if __name__ == "__main__":
    clicksend_send_sms("+12134369175", "test message, please ignore")
