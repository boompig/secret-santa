import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
CREDENTIALS_FNAME = os.path.join(CONFIG_DIR, "credentials.json")

def read_credentials(fname: str) -> dict:
    with open(fname) as fp:
        return json.load(fp)


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
    server = smtplib.SMTP("smtp.gmail.com:587")
    server.starttls()
    server.login(gmail_credentials["username"], gmail_credentials["password"])
    server.sendmail(from_addr, to_addr, msg.as_string())
    server.quit()
