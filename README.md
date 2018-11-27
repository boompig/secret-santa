# About

Run this script to create secret Santa pairings.

## How to run

Install all packages listed in `requirements.txt` in a virtualenv.

1. create file `config/credentials.json` which contains `email` and `app_password` fields for Gmail.
2. create file `config/names.json` whose contents should be a map of names to emails
3. create file `config/instructions_email.md` whose contents are the text of the email. Use python-format style formatting for string substitutions.

Run (inside virtualenv) with:

```
python -m secret_santa --encrypt --live
```

The `--help` is also available and gives additional options. A directory called `data` will be created with files for debugging.

## How to test

- specify the correct `API_BASE_URL` in the test script
- run `tox` inside the virtualenv