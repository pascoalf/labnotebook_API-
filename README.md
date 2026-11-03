# eLabFTW CLI

A small Python command-line tool for working with an [eLabFTW](https://www.elabftw.net/)
notebook through its REST API v2. Create and edit experiments in your preferred
text editor, read records, and attach files to experiments or resources.

## Requirements

- Python 3.10 or newer.
- Access to an eLabFTW instance with API v2 enabled.
- An API key from your eLabFTW account's **Settings**. Creating, editing, and
  uploading require a key with write access and permission to modify the record.
- A text editor for creating and editing experiments: Vim, Vi, Nano, or another
  editor configured to wait until you finish editing.

## Quick start

Clone this repository and open its directory, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python elab.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

Enter your server address, for example `https://eln.example.org`, and your API
key when prompted. The key is hidden while typing; it identifies your account,
so no username or password is required. Credentials entered at the prompts are
not saved by the script.

The interactive mode accepts the server's base address or a page URL such as
`https://eln.example.org/login.php` and builds the `/api/v2` address. Keep any
installation subdirectory, for example `https://example.org/elabftw`.

## Interactive menu

| Option | Action |
| --- | --- |
| 1 | Check the connection and show server information. |
| 2 | Read an experiment or resource by ID. |
| 3 | Attach a local file to an existing experiment or resource. |
| 4 | Exit. |
| 5 | Create an experiment in your text editor. |
| 6 | Edit an existing experiment in your text editor. |

A record ID identifies the destination entry. For example, the experiment at
`experiments.php?mode=view&id=42` has ID **42**. Use the same ID to read, edit, or
attach files to that entry. Creating an experiment returns a new ID.

### Create an experiment

Choose **5**. The editor opens a draft in this format:

```text
Title: Sample analysis

Methods, observations, and results go here.
```

Keep `Title:` on the first line. Save and quit, review the preview, then confirm
creation. Leaving the title empty cancels. The new entry uses the server's
default settings; template selection is not supported.

### Choose an editor

The script uses `VISUAL`, then `EDITOR`, then the first available editor among
`vim`, `vi`, and `nano`. For example, on Linux or macOS:

```bash
EDITOR=vim python elab.py
EDITOR=nano python elab.py
VISUAL="code --wait" python elab.py
```

On PowerShell, set `$env:EDITOR = "vim"` before running the script.
For graphical editors, include their wait option. Editor commands support
arguments, but are not executed through a shell.

In Vim, press `i` to write, then `Esc`, type `:wq`, and press Enter to save and
quit. In Nano, use Ctrl+O, Enter, then Ctrl+X. The temporary draft is deleted
when the editor step ends; save a separate copy if you need a local record.

### Edit an experiment

Choose **6** and enter the existing experiment's ID. Its title and body open in
the editor. Save and quit, review the preview, then confirm the update.

**Editing replaces that entry's title and body. Attachments are preserved.**
The body is shown in its stored format, so formatted entries may contain HTML.
There is no automatic Markdown conversion or formatting preview. Declining
confirmation or leaving the contents unchanged sends no update.

The script checks whether the title or body changed while you were editing and
refuses to save if they did. This is a best-effort check, not an atomic lock;
another user could still edit between that check and the final update.

### Attach a file

Choose **3**, select an experiment or resource, enter its ID, and provide a local
file path and optional comment. Confirm to upload.

This adds an attachment; it does not replace existing attachments or the entry's
text. Repeating an upload can create duplicates. The API calls resources `items`.

Uploading an `.eln` export here stores it as an attachment. It does **not**
import the exported experiment's contents or recreate its records.

## Direct commands and scripting

For commands without credential prompts, copy `.env.example` to `.env` and set
your full API URL (ending in `/api/v2`) and API key. The script does not load
`.env` automatically. In Bash, load your locally edited file with:

```bash
set -a
source .env
set +a
```

Use shell-safe quoted values where needed. Alternatively, set `ELABFTW_URL` and
`ELABFTW_API_KEY` directly in your environment.

```bash
python elab.py info
python elab.py get experiments 42
python elab.py get items 17
python elab.py create "Sample analysis" --body "Methods and observations"
python elab.py edit 42
python elab.py upload experiments 42 ./results.csv --comment "Instrument results"
python elab.py upload items 17 ./protocol.pdf
python elab.py --help
```

IDs and filenames above are examples. Direct `create` and `upload` commands
write immediately; `edit` opens the editor and asks for confirmation. Commands
print JSON results. `ElabClient` in `elab.py` can also be imported into scripts.

## Credentials and local data

Treat API keys like passwords. Do not include them in source code, issues, or
screenshots. `.env` files, virtual environments, Python caches, and `.eln`
exports are ignored by Git. Other attachments and laboratory data are not
universally ignored; keep them outside the repository or add suitable ignore
rules before committing. Editor backup or swap files may also contain draft
text; follow your editor's settings for handling them.

## Troubleshooting and limitations

- **HTTP 401/403:** check the API key, its access level, and record permissions.
- **HTTP 404:** check the displayed API URL and record ID. If the connection
  check fails, ask your administrator about the installed version and API routing.
- **Network or TLS errors:** check connectivity and your institution's certificate
  configuration. HTTPS certificate verification is enabled.
- **Timeout during a write:** inspect the entry before retrying. The operation
  may have completed. Requests are not retried automatically.
- **Partially created experiment:** creation and filling the title/body use two
  requests. If filling fails, the error gives the created ID so you can finish
  editing that entry rather than create a duplicate.

This is a small, unofficial client, not a complete eLabFTW SDK. Resource creation,
export import, template selection, and batch operations are not implemented.
Local mocked checks cover core workflows; compatibility depends on your server
version and configuration. Start with a test experiment on your own instance.

## API documentation

- [Authentication and API introduction](https://doc.elabftw.net/docs/usage/api/)
- [API v2 endpoint reference](https://doc.elabftw.net/api/elabapi-html/)
- [Official Python SDK](https://github.com/elabftw/elabapi-python)
