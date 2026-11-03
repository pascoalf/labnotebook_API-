"""Small eLabFTW API v2 client and command-line entry point."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import sys
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

    def request(self, method, path, **kwargs):
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
        if not response.content:
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


def interactive_action():
    print("\n1. Check connection\n2. Read a record\n3. Upload a file\n4. Exit")
    command = prompt_choice("Action [1-4]: ", {
        "1": "info", "2": "get", "3": "upload", "4": "exit",
    })
    args = argparse.Namespace(command=command)
    if command in ("get", "upload"):
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
    if args.command == "info":
        return client.request("GET", "info")
    if args.command == "get":
        return client.request("GET", f"{args.entity}/{args.id}")
    return client.upload(args.entity, args.id, args.file, args.comment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("info", help="Read server information (connection check)")
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
        print("Network request failed. Check connectivity and TLS certificates. If uploading, verify the record before retrying: the upload may have completed.", file=sys.stderr)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
