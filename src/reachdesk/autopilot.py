"""Unattended runs: find, write and send with nobody at the computer.

One pass, for every campaign that has automatic email turned on:

1. fetch new job postings from the campaign's public job-board sources;
2. build today's queue (the best-scored contacts, each with a personal message);
3. send the permitted emails, spaced out with a random pause between them,
   only inside the sending window (weekdays, working hours by default).

Run one pass from a scheduler (Windows Task Scheduler, cron) with
``run.py autopilot``, or keep it running with ``run.py autopilot --loop``.

Only email is sent here. LinkedIn messages and connection requests stay one-click
manual: LinkedIn prohibits automating them, and accounts that do it get restricted.
"""
from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone

from . import channels, service
from .db import now

DEFAULTS = {
    "autopilot_days": "0,1,2,3,4",  # Monday=0. Business email lands best on weekdays.
    "autopilot_hours": "9-17",  # local time, start inclusive, end exclusive
    "autopilot_gap_min": "45",  # seconds between two emails
    "autopilot_gap_max": "150",
}
SETTING_KEYS = tuple(DEFAULTS)
FETCH_EVERY = timedelta(hours=6)  # job boards change slowly; be a polite client


def config(conn) -> dict:
    raw = {key: service.get_setting(conn, key) or default for key, default in DEFAULTS.items()}
    try:
        days = {int(d) for d in raw["autopilot_days"].split(",") if d.strip() != ""}
    except ValueError:
        days = {0, 1, 2, 3, 4}
    try:
        start, end = (int(x) for x in raw["autopilot_hours"].split("-", 1))
    except ValueError:
        start, end = 9, 17
    try:
        gap_min, gap_max = float(raw["autopilot_gap_min"]), float(raw["autopilot_gap_max"])
    except ValueError:
        gap_min, gap_max = 45.0, 150.0
    gap_min = max(0.0, gap_min)
    return {"days": days, "start": start, "end": end, "gap_min": gap_min, "gap_max": max(gap_min, gap_max)}


def in_window(cfg: dict, moment: datetime) -> bool:
    return moment.weekday() in cfg["days"] and cfg["start"] <= moment.hour < cfg["end"]


def run_once(conn, smtp_factory=channels.open_smtp, sleep=time.sleep, clock=datetime.now, rng: random.Random | None = None, fetch: bool = True) -> dict:
    """One full pass over every campaign with automatic email on."""
    rng = rng or random.Random()
    cfg = config(conn)
    sending = in_window(cfg, clock())
    report = {"at": now(), "in_window": sending, "campaigns": {}}

    def pause() -> None:
        sleep(rng.uniform(cfg["gap_min"], cfg["gap_max"]))

    for campaign in service.list_campaigns(conn):
        if not campaign["auto_email"]:
            continue
        entry: dict = {}
        if fetch and campaign.get("sources") and _fetch_due(conn, campaign["id"]):
            try:
                entry["fetch"] = service.fetch_sources(conn, campaign["id"])
                service.set_setting(conn, f"last_fetch_{campaign['id']}", now())
            except Exception as exc:  # a job board being down must not stop sending
                entry["fetch"] = {"error": str(exc)[:200]}
        try:
            entry["queue"] = service.build_queue(conn, campaign["id"], rng)
        except service.LimitError as exc:
            entry["queue"] = {"error": str(exc)}
        if sending:
            entry["email"] = channels.dispatch_email(conn, campaign["id"], smtp_factory, pause=pause)
        else:
            entry["email"] = {"sent": 0, "reason": "outside the sending window"}
        report["campaigns"][campaign["slug"]] = entry
    service.audit(conn, "autopilot", f"in_window={sending} campaigns={list(report['campaigns'])}")
    conn.commit()
    return report


def _fetch_due(conn, campaign_id: int) -> bool:
    last = service.get_setting(conn, f"last_fetch_{campaign_id}")
    if not last:
        return True
    try:
        stamp = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return datetime.now(timezone.utc) - stamp >= FETCH_EVERY


def run_loop(conn, every_minutes: int = 30, on_report=print, sleep=time.sleep, **kwargs) -> None:
    """Keep running passes. Stop with Ctrl+C."""
    while True:
        on_report(run_once(conn, sleep=sleep, **kwargs))
        sleep(max(1, every_minutes) * 60)


def schedule_commands(python: str, run_py: str, db_path: str) -> dict:
    """Ready-to-paste commands that run one pass every 30 minutes."""
    cmd = f'"{python}" "{run_py}" --db "{db_path}" autopilot'
    return {
        "windows": f'schtasks /Create /TN ReachDeskAutopilot /SC MINUTE /MO 30 /TR "{cmd.replace(chr(34), chr(92) + chr(34))}" /F',
        "linux_mac_cron": f"*/30 * * * * {cmd} >> ~/.reachdesk/autopilot.log 2>&1",
    }
