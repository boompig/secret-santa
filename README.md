# About

Run this script to create secret Santa pairings.

## How to run

Install all packages listed in `requirements.txt` in a virtualenv.

1. create file `config/credentials.json` which contains `email`, `password`, and `application_specific_password` fields for Gmail.
2. create file `config/names.json` whose contents should two keys:
    - `names`: map from names to emails
    - `constraints` (optional): has keys `always` and `never`. Each is a list, where each item is a list of two names
3. create file `config/instructions_email.md` whose contents are the text of the email. Use python-format style formatting for string substitutions. Available variables are `giver_name` and `link`.
4. create file `config/config.json` which has these keys:
    - `email_subject` - the email subject
    - `year` - current year

Run (inside virtualenv) with:

```
python -m secret_santa --encrypt --live
```

The `--help` switch is also available and gives additional options. A directory called `data` will be created with files for debugging.

## Development

Create virtualenv and install dependencies

```
virtualenv venv3 --python=$(which python3)
source venv3/bin/activate
pip install -r requirements.txt
```

## Testing

- specify the correct `API_BASE_URL` in the test script
- run `tox` *outside* the virtualenv

## Debugging

Emails are saved to `data/emails/<giver_name>.html` before they are sent.
Markdown files for emails are also created before being converted into HTML and are saved in `data/markdown`.
The `data/html` directory contains identical data to `data/emails` unless something has gone very wrong.
