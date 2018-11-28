import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import logging
import sys

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
CREDENTIALS_FNAME = os.path.join(CONFIG_DIR, "credentials.json")


class Mailer:
    """Use this in a future version to reuse the SMTP connection"""
    def __init__(self) -> None:
        # only read credentials once from disk
        self._credentials = read_credentials(CREDENTIALS_FNAME)
        # reuse server
        self._server = None

    @property
    def server(self) -> smtplib.SMTP:
        # perform server connection only once
        if self._server is None:
            logging.debug("Connecting to Gmail over port 587...")
            self._server = smtplib.SMTP("smtp.gmail.com", 587)  # type: smtplib.SMTP
            assert self._server is not None
            logging.debug("Starting TLS...")
            self._server.starttls()
            logging.debug("Logging into Gmail...")
            self._server.login(self._credentials["email"], self._credentials["application_specific_password"])
        return self._server

    def send_email(self, subject: str, message_body: str, to_addr: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._credentials["email"]
        msg["To"] = to_addr

        mime_msg = MIMEText(message_body, "html")
        msg.attach(mime_msg)

        # The actual mail send
        logging.debug("Sending email...")
        # some python magic here :)
        self.server.sendmail(self._credentials["email"], to_addr, msg.as_string())

    def cleanup(self):
        logging.debug("Closing the connection...")
        if self._server:
            self._server.quit()


def read_credentials(fname: str) -> dict:
    try:
        with open(fname) as fp:
            return json.load(fp)
    except Exception:
        logging.critical("Gmail credentials file %s does not exist", fname)
        sys.exit(1)


def send_secret_santa_email(subject: str, message_body: str, to_addr: str) -> None:
    assert os.path.exists(CREDENTIALS_FNAME)
    credentials = read_credentials(CREDENTIALS_FNAME)
    from_addr = credentials["email"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    gmail_credentials = {
        "username": credentials["email"],
        # application-specific password
        "password": credentials["application_specific_password"]
    }
    mime_msg = MIMEText(message_body, "html")
    msg.attach(mime_msg)

    # The actual mail send
    logging.debug("Connecting to Gmail over port 587...")
    server = smtplib.SMTP("smtp.gmail.com", 587)
    logging.debug("Starting TLS...")
    server.starttls()
    logging.debug("Logging into Gmail...")
    server.login(gmail_credentials["username"], gmail_credentials["password"])
    logging.debug("Sending email...")
    server.sendmail(from_addr, to_addr, msg.as_string())
    logging.debug("Closing the connection...")
    server.quit()
