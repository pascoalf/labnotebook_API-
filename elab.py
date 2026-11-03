"""Small eLabFTW API v2 client and command-line entry point."""

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

import requests


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
            raise RuntimeError(f"API returned HTTP {response.status_code}; check URL, key, permissions and record ID")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
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
        client = ElabClient(os.getenv("ELABFTW_URL", ""), os.getenv("ELABFTW_API_KEY", ""))
        try:
            if args.command == "info":
                result = client.request("GET", "info")
            elif args.command == "get":
                result = client.request("GET", f"{args.entity}/{args.id}")
            else:
                result = client.upload(args.entity, args.id, args.file, args.comment)
        finally:
            client.session.close()
        print(json.dumps(result, indent=2))
        return 0
    except requests.RequestException:
        print("Network request failed. Check connectivity and TLS certificates. If uploading, verify the record before retrying: the upload may have completed.", file=sys.stderr)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
