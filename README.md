# About

Run this script to create secret Santa pairings.

## What Does It Do?

1. Create Secret Santa pairings from a pre-defined group of people (participants), with support for direction pairing exclusions.
2. Distribute the pairings to the participants either via SMS or via email. Supports custom messages that can be formatted with some variables.
    * Can encrypt/obfuscate the pairings behind a link such that the email inbox of the person sending the pairings will not leak the pairings by accident.
3. Save pairings such that they can be resent if needed, or for later analysis or sanity checking.

Supports running multiple "campaigns" at once that can contain the same or different group of participants.

## Setup (Installation)

This project uses the `uv` package manager. Run `uv sync` to install deps.

## How to Run


1. create file `config/credentials.json` which contains `email` and `application_specific_password` fields for Gmail.
2. create file `config/names.json` whose contents should two keys:
    - `names`: map from names to object with key `email` (mapping to email) or `text` (mapping to number to use for SMS)
    - `constraints` (optional): has keys `always` and `never`. Each is a list, where each item is a list of two names. First name is giver and second name is receiver.
3. create file `config/instructions_email.md` whose contents are the text of the email. Use python-format style formatting for string substitutions. Available variables are `giver_name` and `link`.
4. create file `config/config.json` which has these keys:
    - `email_subject` - the email subject
    - `year` - current year

```bash
uv run -m secret_santa --encrypt --live
```

The `--help` switch is also available and gives additional options. A directory called `data` will be created with files for debugging.

## Development

`uv` to install deps, point your IDE at the `.venv` folder created by `uv`.

## Testing

This project previously used `tox` but now uses `task`. See `Taskfile.yml`.

## Debugging

Emails are saved to `data/emails/<giver_name>.html` before they are sent.
Markdown files for emails are also created before being converted into HTML and are saved in `data/markdown`.
The `data/html` directory contains identical data to `data/emails` unless something has gone very wrong.
