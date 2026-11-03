# Team eLabFTW scripts

Python foundation for future team automation using the eLabFTW REST API v2.
Requires Python 3.10 or newer.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` locally with your server's full API URL and API key. Include any
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
the CLI supports server information, fetching one record, and single-file
uploads; batch operations and record creation can be added as workflows emerge.

## References

- [API introduction and authentication](https://doc.elabftw.net/docs/usage/api/)
- [API v2 endpoint reference](https://doc.elabftw.net/api/elabapi-html/)
- [Official Python SDK, an alternative for broader API coverage](https://github.com/elabftw/elabapi-python)

Prepared against the public documentation. Compatibility with the team's
installed eLabFTW version and live access still need to be verified.
