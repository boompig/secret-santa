# About

Run this script to create secret Santa pairings.

## How to run

Install all packages listed in `requirements.txt` in a virtualenv. 

1. create file `credentials.json` which contains `email` and `app_password` fields for Gmail.
2. create file `names.json` whose contents should be a map of names to emails
3. create file `instructions_email.md` whose contents are the text of the email. Use python-format style formatting for string substitutions.
