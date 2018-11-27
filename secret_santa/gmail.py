import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

from_addr = "dbkats@gmail.com"
credentials_fname = "credentials.json"

def read_credentials(fname):
    with open(fname) as fp:
        return json.load(fp)


def send_secret_santa_email(subject, message_body, to_addr):
    credentials = read_credentials(credentials_fname)
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
