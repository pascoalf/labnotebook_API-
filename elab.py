"""Small eLabFTW API v2 client and command-line entry point."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit

import requests


def normalize_url(url):
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/")
    if path.endswith(".php"):
        path = path.rsplit("/", 1)[0]
    if not path.endswith("/api/v2"):
        path += "/api/v2"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


class ElabClient:
    def __init__(self, url, api_key):
        url = url.strip().rstrip("/")
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.netloc or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or not parsed.path.endswith("/api/v2")):
            raise ValueError("ELABFTW_URL must be an HTTPS API URL ending in /api/v2")
        if not api_key.strip():
            raise ValueError("Set ELABFTW_API_KEY locally before running this command")
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_key.strip(), "Accept": "application/json"})

    def request(self, method, path, *, return_location=False, **kwargs):
        # Refuse redirects so credentials cannot be forwarded to another endpoint.
        response = self.session.request(
            method, f"{self.url}/{path}", timeout=(10, 120),
            allow_redirects=False, **kwargs,
        )
        if not 200 <= response.status_code < 300:
            detail = "Check your API key and permissions."
            if response.status_code == 404:
                detail = (
                    "This endpoint or record was not found. If this was the connection check, "
                    "the server may not expose /info or API v2 at this address. "
                    "Check the eLabFTW version and API routing with your administrator."
                )
            raise RuntimeError(
                f"HTTP {response.status_code} for {method} {self.url}/{path}. {detail}"
            )
        if return_location or not response.content:
            return {"location": response.headers.get("Location")}
        try:
            return response.json()
        except ValueError:
            raise RuntimeError("API returned a non-JSON response; check the API URL") from None

    def upload(self, entity, record_id, path, comment=""):
        with Path(path).open("rb") as handle:
            return self.request(
                "POST", f"{entity}/{record_id}/uploads",
                files={"file": (Path(path).name, handle)}, data={"comment": comment},
            )

    def create_experiment(self, title, body):
        if not title.strip():
            raise ValueError("The experiment title cannot be empty")
        created = self.request("POST", "experiments", json={}, return_location=True)
        location = created.get("location")
        record_id = urlsplit(location or "").path.rstrip("/").rsplit("/", 1)[-1]
        if not record_id.isdigit():
            raise RuntimeError(
                "An experiment was created, but its ID was not returned. "
                "Check eLabFTW before creating another entry."
            )
        try:
            self.request("PATCH", f"experiments/{record_id}", json={"title": title, "body": body})
        except (requests.RequestException, RuntimeError) as exc:
            raise RuntimeError(
                f"Experiment {record_id} was created, but filling its title/text failed. "
                "Open that entry in eLabFTW to finish editing it; do not create a duplicate."
            ) from exc
        return {"id": int(record_id), "location": location, "title": title}


def positive_id(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("record ID must be positive")
    return number


def prompt_choice(prompt, choices):
    while True:
        value = input(prompt).strip()
        if value in choices:
            return choices[value]
        print("Choose one of: " + ", ".join(choices))


def edit_experiment(title="", body=""):
    editor = os.getenv("VISUAL") or os.getenv("EDITOR")
    if editor:
        command = shlex.split(editor)
    else:
        command = next(([name] for name in ("vim", "vi", "nano") if shutil.which(name)), [])
    if not command or not shutil.which(command[0]):
        raise RuntimeError("No text editor found. Set EDITOR, for example: export EDITOR=vim")
    with tempfile.TemporaryDirectory(prefix="elab-draft-") as directory:
        draft = Path(directory) / "experiment.txt"
        draft.write_text(f"Title: {title}\n\n{body}", encoding="utf-8")
        print("Write the title after 'Title:' on the first line, then the body below it.")
        print("Save and quit to review. Leave the title empty to cancel.")
        result = subprocess.run([*command, str(draft)], check=False)
        if result.returncode != 0:
            print("Editor exited unsuccessfully; no experiment created.")
            return None
        text = draft.read_text(encoding="utf-8")
    first, _, body = text.partition("\n")
    if not first.startswith("Title:"):
        raise ValueError("The first line must start with 'Title:'. No experiment created.")
    title = first.removeprefix("Title:").strip()
    if not title:
        print("Creation cancelled: no title entered.")
        return None
    return title, body.removeprefix("\n")


def interactive_action():
    print("\n1. Check connection\n2. Read a record\n3. Upload a file\n4. Exit\n5. Create an experiment\n6. Edit an experiment")
    command = prompt_choice("Action [1-6]: ", {
        "1": "info", "2": "get", "3": "upload", "4": "exit", "5": "create",
        "6": "edit",
    })
    args = argparse.Namespace(command=command)
    if command == "create":
        draft = edit_experiment()
        if draft is None:
            args.command = "cancel"
            return args
        args.title, args.body = draft
        print(f"\nTitle: {args.title}\nText:\n{args.body}")
        if input("Create this experiment? [y/N]: ").strip().lower() not in ("y", "yes"):
            args.command = "cancel"
    if command in ("get", "upload", "edit"):
        if command != "edit":
            args.entity = prompt_choice("Record type (1 = experiment, 2 = resource): ", {
                "1": "experiments", "2": "items",
            })
        while True:
            try:
                args.id = positive_id(input("Record ID: ").strip())
                break
            except (ValueError, argparse.ArgumentTypeError):
                print("Enter a positive numeric record ID.")
    if command == "upload":
        while True:
            args.file = Path(input("File path: ").strip()).expanduser()
            if args.file.is_file():
                break
            print("Enter the path to an existing file.")
        args.comment = input("Comment (optional): ").strip()
        print(f"Upload {args.file} to {args.entity}/{args.id}")
        if input("Proceed? [y/N]: ").strip().lower() not in ("y", "yes"):
            args.command = "cancel"
    return args


def execute(client, args):
    if args.command == "edit":
        path = f"experiments/{args.id}"
        original = client.request("GET", path)
        before = (original["title"], original.get("body") or "")
        print("The editor shows the stored body, which may contain HTML formatting.")
        draft = edit_experiment(*before)
        if draft is None or draft == before:
            return {"message": "No changes saved"}
        title, body = draft
        print(f"\nExperiment ID: {args.id}\nTitle: {title}\nText:\n{body}")
        if input("Replace this experiment's title and text? [y/N]: ").strip().lower() not in ("y", "yes"):
            return {"message": "Edit cancelled; no changes saved"}
        current = client.request("GET", path)
        if (current["title"], current.get("body") or "") != before:
            raise RuntimeError("The experiment changed while you were editing. No changes saved; reopen it to edit the latest version.")
        client.request("PATCH", path, json={"title": title, "body": body})
        return {"id": args.id, "message": "Experiment updated"}
    if args.command == "create":
        return client.create_experiment(args.title, args.body)
    if args.command == "info":
        return client.request("GET", "info")
    if args.command == "get":
        return client.request("GET", f"{args.entity}/{args.id}")
    return client.upload(args.entity, args.id, args.file, args.comment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("info", help="Read server information (connection check)")
    create = commands.add_parser("create", help="Create an experiment")
    create.add_argument("title")
    create.add_argument("--body", default="", help="Experiment text")
    edit = commands.add_parser("edit", help="Edit an existing experiment in your text editor")
    edit.add_argument("id", type=positive_id)
    for command in ("get", "upload"):
        sub = commands.add_parser(command)
        sub.add_argument("entity", choices=("experiments", "items"))
        sub.add_argument("id", type=positive_id)
        if command == "upload":
            sub.add_argument("file", type=Path)
            sub.add_argument("--comment", default="")
    args = parser.parse_args()
    try:
        interactive = args.command is None
        url = os.getenv("ELABFTW_URL", "")
        api_key = os.getenv("ELABFTW_API_KEY", "")
        if interactive:
            print("eLabFTW — your API key identifies your user account.")
            print("Credentials are used for this session only and are not saved.")
            url = input(f"Server URL{f' [{url}]' if url else ''}: ").strip() or url
            url = normalize_url(url)
            print(f"API address: {url}")
            api_key = getpass("API key (hidden; Enter to use environment key): ") or api_key
        client = ElabClient(url, api_key)
        try:
            while True:
                if interactive:
                    args = interactive_action()
                    if args.command == "exit":
                        break
                    if args.command == "cancel":
                        continue
                result = execute(client, args)
                print(json.dumps(result, indent=2))
                if not interactive:
                    break
        finally:
            client.session.close()
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nSession ended.", file=sys.stderr)
        return 0
    except requests.RequestException:
        print("Network request failed. Check connectivity and TLS certificates. If writing data, check eLabFTW before retrying: the operation may have completed.", file=sys.stderr)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
