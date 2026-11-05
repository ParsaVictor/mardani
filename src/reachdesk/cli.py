"""Command line: run.py <command>. Everything the dashboard automates can be scheduled."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from . import channels, db, plans, seed, server, service

HOME = Path(os.environ.get("REACHDESK_HOME") or Path.home() / ".reachdesk")
DEFAULT_DB = HOME / "workspace.db"
SIGNING_KEY = HOME / "license_signing_key"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reachdesk", description="Human-sent LinkedIn outreach, automatic email, and a ranking that learns.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="workspace database file (one file per client)")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("serve", help="start the dashboard")
    run.add_argument("--port", type=int, default=8765)
    sub.add_parser("seed", help="create the ready-made campaigns")
    for name, text in (("fetch", "pull jobs from public job boards"), ("queue", "prepare today's messages"), ("dispatch", "send permitted email now")):
        command = sub.add_parser(name, help=text)
        command.add_argument("campaign", help="campaign slug")
    imp = sub.add_parser("import", help="import a CSV (LinkedIn Connections.csv or generic)")
    imp.add_argument("campaign")
    imp.add_argument("file")
    lic = sub.add_parser("license", help="owner license tools")
    lic.add_argument("action", choices=["keygen", "issue", "activate", "show"])
    lic.add_argument("--plan", default="pro")
    lic.add_argument("--customer", default="")
    lic.add_argument("--expires", default="", help="YYYY-MM-DD; empty means no expiry")
    lic.add_argument("--token", default="")

    args = parser.parse_args(argv)
    if args.command == "license" and args.action in ("keygen", "issue"):
        return _license_owner(args)

    conn = db.connect(args.db)
    try:
        if args.command == "serve":
            seed.seed(conn)
            conn.close()
            server.serve(args.db, args.port)
            return 0
        if args.command == "seed":
            print(json.dumps({"created": seed.seed(conn)}))
            return 0
        if args.command == "license":
            if args.action == "activate":
                if not plans.read_license(args.token):
                    print("This license key is not valid or has expired.", file=sys.stderr)
                    return 1
                service.set_setting(conn, "license", args.token)
            print(json.dumps(service.plan(conn), ensure_ascii=False))
            return 0
        campaign = service.get_campaign(conn, slug=args.campaign)
        if not campaign:
            print(f"Unknown campaign: {args.campaign}", file=sys.stderr)
            return 1
        if args.command == "fetch":
            result = service.fetch_sources(conn, campaign["id"])
        elif args.command == "queue":
            result = service.build_queue(conn, campaign["id"])
        elif args.command == "dispatch":
            service.build_queue(conn, campaign["id"])
            result = channels.dispatch_email(conn, campaign["id"])
        else:
            result = service.import_csv(conn, campaign["id"], Path(args.file).read_bytes())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except service.LimitError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        conn.close()


def _license_owner(args) -> int:
    if args.action == "keygen":
        if SIGNING_KEY.exists():
            print(f"A signing key already exists at {SIGNING_KEY}; refusing to overwrite it.", file=sys.stderr)
            return 1
        secret = secrets.token_bytes(32)
        SIGNING_KEY.parent.mkdir(parents=True, exist_ok=True)
        SIGNING_KEY.write_text(secret.hex())
        print(json.dumps({"public_key": plans.public_key(secret).hex(), "secret_file": str(SIGNING_KEY)}))
        return 0
    if not SIGNING_KEY.exists():
        print("Run: license keygen first.", file=sys.stderr)
        return 1
    print(plans.issue_license(bytes.fromhex(SIGNING_KEY.read_text().strip()), args.plan, args.customer, args.expires))
    return 0
