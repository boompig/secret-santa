import logging
import coloredlogs
import json
import smtplib
import sys


def send_secret_santa_email(subject, email_body, giver):
    raise NotImplementedError()


class Mailer:

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def send_mail(self, receiver_email):
        sent_from = self.email  
        to = [receiver_email]
        subject = 'OMG Super Important Message'  
        body = "Hey, what's up?\n\n- You"

        email_text = """\  
        From: %s  
        To: %s  
        Subject: %s

        %s
        """ % (sent_from, ", ".join(to), subject, body)

        try:  
            logging.info("Connecting to gmail...")
            server = smtplib.SMTP_SSL('smtp.gmail.com', 587)
            logging.info("Waiting for response...")
            server.ehlo()
            logging.info("Logging in...")
            server.login(self.email, self.password)
            logging.info("Sending email...")
            server.sendmail(sent_from, to, email_text)
            server.close()

            print('Email sent!')
        except:  
            print('Something went wrong...')



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    coloredlogs.install()
    with open("credentials.json") as fp:
        credentials = json.load(fp)
        mailer = Mailer(credentials["email"], credentials["app_password"])
    mailer.send_mail(sys.argv[1])
