"""The send desk: today's LinkedIn sends as one simple page.

Each card has the person, a clickable profile link and the exact text to paste.
Served live by the dashboard at /desk, or written as one standalone HTML file
with ``run.py desk <campaign>``. Built from the queue by plain Python: no AI model,
no API key, no tokens.
"""
from __future__ import annotations

import json
from importlib import resources

from . import service, textparse

STEPS = ("connect", "message")  # email goes out on its own through the autopilot


def entries(conn, campaign_id: int, prepare: bool = True) -> dict:
    """Today's LinkedIn sends for one campaign, best first."""
    campaign = service.get_campaign(conn, campaign_id)
    if prepare:
        service.build_queue(conn, campaign_id)
    cards = []
    for entry in service.list_queue(conn, campaign_id):
        if entry["step"] not in STEPS:
            continue
        item = service.get_item(conn, entry["item_id"])
        cards.append({
            "id": entry["id"],
            "step": entry["step"],
            "name": entry["full_name"] or "(no name)",
            "title": entry["title"],
            "company": entry["company"],
            "location": entry["location"],
            "url": textparse.linkedin_profile_url(entry["url"]) or entry["url"],
            "score": round(entry["score"] or 0, 2),
            "why": (item or {}).get("rule_why") or [],
            "text": entry["body"],
        })
    return {
        "campaign": {"slug": campaign["slug"], "name": campaign["name"], "note_limit": campaign["note_limit"]},
        "sent_today": service.sent_today(conn, campaign_id),
        "daily_cap": min(campaign["daily_cap"], service.plan(conn)["daily_cap"]),
        "cards": cards,
    }


def standalone_html(data: dict) -> str:
    """One self-contained file: open it in any browser, no server needed."""
    static = resources.files("reachdesk").joinpath("static")
    page = static.joinpath("desk.html").read_text(encoding="utf-8")
    css = static.joinpath("desk.css").read_text(encoding="utf-8")
    js = static.joinpath("desk.js").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace('<link rel="stylesheet" href="/desk.css">', f"<style>{css}</style>")
    return page.replace('<script src="/desk.js"></script>', f"<script>window.DESK_DATA = {payload};</script>\n<script>{js}</script>")
