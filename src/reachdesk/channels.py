"""Automatic delivery: email over the user's own SMTP account.

This is the only channel that sends without a click. Every message is checked again
at send time against the suppression list, the daily cap and the consent basis, so a
stale queue can never reach someone who has since opted out.

LinkedIn is deliberately not a channel here: LinkedIn prohibits automating messages
and connection requests, so those are prepared for one-click manual sending instead.
"""
from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from . import service
from .db import now, rows


def smtp_config(conn) -> dict:
    """The password is only ever read from the environment, never stored."""
    return {
        "host": service.get_setting(conn, "smtp_host"),
        "port": int(service.get_setting(conn, "smtp_port", "587") or 587),
        "user": service.get_setting(conn, "smtp_user"),
        "from": service.get_setting(conn, "smtp_from"),
        "password": os.environ.get("REACHDESK_SMTP_PASSWORD", ""),
        "attachment": service.get_setting(conn, "email_attachment"),
    }


def compose(entry: dict, config: dict, campaign: dict) -> EmailMessage:
    message = EmailMessage()
    message["From"] = config["from"] or config["user"]
    message["To"] = entry["email"]
    message["Subject"] = entry["subject"] or "Hello"
    if campaign["sender_contact"] and "@" in campaign["sender_contact"]:
        message["List-Unsubscribe"] = f"<mailto:{campaign['sender_contact']}?subject=stop>"
    message.set_content(entry["body"])
    attachment = config.get("attachment")
    if attachment and not campaign["commercial"]:
        path = Path(attachment)
        if path.is_file():
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            main, sub = ctype.split("/", 1)
            message.add_attachment(path.read_bytes(), maintype=main, subtype=sub, filename=path.name)
    return message


def open_smtp(config: dict) -> smtplib.SMTP:
    client = smtplib.SMTP(config["host"], config["port"], timeout=30)
    client.starttls()
    client.login(config["user"], config["password"])
    return client


def dispatch_email(conn, campaign_id: int, smtp_factory=open_smtp) -> dict:
    """Send every ready email the campaign is allowed to send today."""
    campaign = service.get_campaign(conn, campaign_id)
    plan = service.plan(conn)
    report = {"sent": 0, "failed": 0, "blocked": 0, "reason": ""}
    if not campaign["auto_email"]:
        report["reason"] = "automatic email is off for this campaign"
        return report
    if not plan["auto_email"]:
        report["reason"] = "automatic email needs the Pro plan or higher"
        return report
    config = smtp_config(conn)
    if not (config["host"] and config["user"] and config["password"]):
        report["reason"] = "SMTP is not configured"
        return report

    room = min(campaign["daily_cap"], plan["daily_cap"]) - service.sent_today(conn, campaign_id)
    due = rows(
        conn.execute(
            "SELECT o.*, i.email, i.consent_basis FROM outreach o JOIN items i ON i.id=o.item_id "
            "WHERE o.campaign_id=? AND o.status='ready' AND o.step='email' ORDER BY o.id",
            (campaign_id,),
        )
    )
    if not due or room <= 0:
        report["reason"] = "nothing due" if not due else "daily cap reached"
        return report

    client = smtp_factory(config)
    try:
        for entry in due[:room]:
            if conn.execute("SELECT 1 FROM suppressions WHERE contact_key=?", (entry["contact_key"],)).fetchone() or (
                entry["consent_basis"] not in service.AUTO_EMAIL_BASES
            ):
                conn.execute("UPDATE outreach SET status='skipped', error='blocked at send time' WHERE id=?", (entry["id"],))
                report["blocked"] += 1
                continue
            try:
                client.send_message(compose(entry, config, campaign))
                service.mark_sent(conn, entry["id"])
                report["sent"] += 1
            except (smtplib.SMTPException, OSError) as exc:
                conn.execute("UPDATE outreach SET status='failed', error=? WHERE id=?", (str(exc)[:300], entry["id"]))
                report["failed"] += 1
    finally:
        try:
            client.quit()
        except (smtplib.SMTPException, OSError):
            pass
    service.audit(conn, "dispatch_email", f"campaign={campaign_id} at={now()} {report}")
    conn.commit()
    return report
