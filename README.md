# Team eLabFTW scripts

Python foundation for future team automation using the eLabFTW REST API v2.
Requires Python 3.10 or newer.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python elab.py
```

The interactive mode asks for your server URL and API key (hidden while typing),
then offers a menu to check the connection, read a record, upload a file, or exit.
You can enter the server's base URL; `/api/v2` is appended automatically.
No username or password is needed: the API key identifies your account.
Credentials stay in memory for the session and are not saved to disk.
Uploads ask for the record type, record ID, file path, optional comment, and
confirmation before sending. You can perform several actions in one session.

## Optional configuration for direct commands

Copy `.env.example` to `.env` and edit it locally with your full API URL and API key. Include any
installation subpath before `/api/v2`. Create the key in eLabFTW Settings;
uploads require write access and permission to edit the target record.
Keep the key out of chat, source code, and commits. `.env` is ignored by Git.

Load the configuration in Bash (the Python script does not auto-load `.env`):

```bash
set -a
source .env
set +a
python elab.py info
python elab.py get experiments 42
```

Use shell-safe quoted values in `.env` if they contain special characters.
The `info` and `get` commands only read data. The IDs below are examples;
replace them with IDs from your own instance.

## Create an experiment

Run `python elab.py`, log in, and choose **5. Create an experiment**. Your text
editor opens a temporary draft. Write the title after `Title:` on the first line
and the experiment text below the blank line. Save and quit, review the text in
the terminal, then confirm creation. In Vim, press `i` to edit, then `Esc` and
`:wq` followed by Enter to save and quit. Leave the title empty to cancel.
The script prints the new experiment's
`id`; use that ID with **3. Upload a file** to attach results to the entry.
Your API key needs write access. This creates an experiment using the server's
defaults; selecting a template or creating resources is not yet supported.

The editor is selected from `VISUAL`, then `EDITOR`, then the first installed
of `vim`, `vi`, and `nano`. For example:

```bash
EDITOR=vim python elab.py
EDITOR=nano python elab.py
VISUAL="code --wait" python elab.py
```

GUI editors need a wait option so the script waits until editing is finished.
The temporary draft is deleted when the editor step ends; keep a separate copy
in your editor if you want a local record. No entry is sent until you confirm.

For direct commands with environment credentials:

```bash
python elab.py create "Water sample analysis" --body "Methods and observations"
```

Creation and filling the entry are two API calls. If filling fails, the error
reports the already-created ID so you can finish editing it in eLabFTW.

## Edit an experiment

Choose **6. Edit an experiment** and enter its ID. The current title and body
open in your editor. Save and quit, review the preview, and confirm to replace
the title and body of that same experiment. Attachments are preserved.
The body is shown as stored, so an existing formatted entry may contain HTML.
Leaving the text unchanged or declining confirmation sends no update.
The script checks for title/body changes made during editing before saving;
this check cannot prevent an edit made at the exact moment of the final update.

With environment credentials you can also run `python elab.py edit 42`.

## Upload a file

This command immediately attaches a file to an existing record:

```bash
python elab.py upload experiments 42 ./results.csv --comment "Instrument results"
python elab.py upload items 17 ./protocol.pdf
```

`items` is the API name for resources. Uploads print the API response or the
created upload's location when the response body is empty. Repeating the command
can create another attachment. There are no automatic retries; after a timeout,
check the record before trying again. TLS certificate verification stays enabled.

`ElabClient` in `elab.py` can also be imported into future scripts. Currently
the CLI supports server information, fetching one record, creating experiments,
and single-file uploads; batch operations can be added as workflows emerge.

## References

- [API introduction and authentication](https://doc.elabftw.net/docs/usage/api/)
- [API v2 endpoint reference](https://doc.elabftw.net/api/elabapi-html/)
- [Official Python SDK, an alternative for broader API coverage](https://github.com/elabftw/elabapi-python)

Prepared against the public documentation. Compatibility with the team's
installed eLabFTW version and live access still need to be verified.
