"""Application logic shared by the dashboard and the CLI."""
from __future__ import annotations

import json
import random
import sqlite3
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import importers, messages, plans, scoring, sources, textparse
from .db import now, row, rows

COOLDOWN_DAYS = 90
# Grounds on which email may go out without a human click. Recorded per contact,
# attested by the operator, and enforced here rather than left to templates.
AUTO_EMAIL_BASES = {"express", "existing_business", "published_business_contact", "invited_by_post"}
CONSENT_BASES = sorted(AUTO_EMAIL_BASES | {"none", "existing_connection"})
CANADA_GEO = "101174742"


class LimitError(Exception):
    """The current plan does not allow this action."""


def audit(conn: sqlite3.Connection, action: str, detail: str = "") -> None:
    conn.execute("INSERT INTO audit (at, action, detail) VALUES (?,?,?)", (now(), action, detail))


# ------------------------------------------------------------------ settings
def get_setting(conn, key: str, default: str = "") -> str:
    found = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return found["value"] if found else default


def set_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)
    )
    conn.commit()


def plan(conn) -> dict:
    return plans.current_plan(get_setting(conn, "license"))


# ----------------------------------------------------------------- campaigns
CAMPAIGN_FIELDS = {
    "name", "commercial", "website", "sender_name", "sender_contact", "keywords", "searches", "sources",
    "daily_cap", "note_limit", "min_score", "followup_days", "followup_body", "auto_email", "email_subject",
}


def create_campaign(conn, slug: str, name: str, enforce: bool = True, **fields) -> dict:
    if enforce:
        limit = plan(conn)["campaigns"]
        if conn.execute("SELECT COUNT(*) c FROM campaigns").fetchone()["c"] >= limit:
            raise LimitError(f"Your plan allows {limit} campaign(s).")
    conn.execute("INSERT INTO campaigns (slug, name, created_at) VALUES (?,?,?)", (slug, name, now()))
    campaign = get_campaign(conn, slug=slug)
    if fields:
        campaign = update_campaign(conn, campaign["id"], fields, enforce=enforce)
    conn.commit()
    return campaign


def get_campaign(conn, campaign_id: int | None = None, slug: str | None = None) -> dict | None:
    if slug is not None:
        return row(conn.execute("SELECT * FROM campaigns WHERE slug=?", (slug,)).fetchone())
    return row(conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone())


def list_campaigns(conn) -> list[dict]:
    return rows(conn.execute("SELECT * FROM campaigns ORDER BY id"))


def update_campaign(conn, campaign_id: int, fields: dict, enforce: bool = True) -> dict:
    current_plan = plan(conn)
    changes = {k: v for k, v in fields.items() if k in CAMPAIGN_FIELDS}
    for key in ("keywords", "searches", "sources"):
        if key in changes and not isinstance(changes[key], str):
            changes[key] = json.dumps(changes[key], ensure_ascii=False)
    if enforce:
        if "daily_cap" in changes:
            changes["daily_cap"] = max(1, min(int(changes["daily_cap"]), current_plan["daily_cap"]))
        if changes.get("auto_email") and not current_plan["auto_email"]:
            raise LimitError("Automatic email needs the Pro plan or higher.")
    if changes:
        assignments = ", ".join(f"{k}=?" for k in changes)  # keys come from CAMPAIGN_FIELDS
        conn.execute(f"UPDATE campaigns SET {assignments} WHERE id=?", (*changes.values(), campaign_id))
    if "keywords" in changes:
        rescore_campaign(conn, campaign_id)
    conn.commit()
    return get_campaign(conn, campaign_id)


def save_variant(conn, campaign_id: int, name: str, body: str, step: str = "message", active: bool = True) -> dict:
    campaign = get_campaign(conn, campaign_id)
    problems = messages.lint(body, campaign, step)
    conn.execute(
        "INSERT INTO variants (campaign_id, name, step, body, active) VALUES (?,?,?,?,?) "
        "ON CONFLICT(campaign_id, name) DO UPDATE SET step=excluded.step, body=excluded.body, active=excluded.active",
        (campaign_id, name, step, body, int(active)),
    )
    conn.commit()
    return {"name": name, "step": step, "problems": problems}


def list_variants(conn, campaign_id: int) -> list[dict]:
    campaign = get_campaign(conn, campaign_id)
    found = rows(conn.execute("SELECT * FROM variants WHERE campaign_id=? ORDER BY id", (campaign_id,)))
    stats = _variant_stats(conn, campaign_id)
    for variant in found:
        variant["problems"] = messages.lint(variant["body"], campaign, variant["step"])
        variant.update(stats.get(variant["id"], {"sent": 0, "replies": 0, "positive": 0}))
    return found


def _variant_stats(conn, campaign_id: int) -> dict[int, dict]:
    result = conn.execute(
        "SELECT variant_id, SUM(status IN ('sent','replied','positive')) sent, "
        "SUM(status IN ('replied','positive')) replies, SUM(status='positive') positive "
        "FROM outreach WHERE campaign_id=? AND variant_id IS NOT NULL GROUP BY variant_id",
        (campaign_id,),
    ).fetchall()
    return {r["variant_id"]: {"sent": r["sent"], "replies": r["replies"], "positive": r["positive"]} for r in result}


# --------------------------------------------------------------------- items
def _load_model(conn, campaign_id: int) -> tuple[dict, float]:
    found = conn.execute("SELECT weights, n FROM models WHERE campaign_id=?", (campaign_id,)).fetchone()
    if not found:
        return {}, 0.0
    data = json.loads(found["weights"])
    return data["weights"], float(data["alpha"])


def _score_item(item: dict, campaign: dict, weights: dict, alpha: float) -> dict:
    rule, why = scoring.rule_score(item, campaign["keywords"] or {})
    ml = scoring.predict(weights, item) if alpha > 0 else None
    final = rule if ml is None else (1 - alpha) * rule + alpha * ml
    explain = why + (scoring.explain_model(weights, item) if alpha > 0 else [])
    return {"rule_score": rule, "rule_why": why, "ml_score": ml, "score": round(final, 4), "explain": explain}


def add_item(conn, campaign_id: int, record: dict, enforce: bool = True, commit: bool = True) -> tuple[dict, bool]:
    """Insert or refresh an item. Returns (item, created). Ratings are preserved."""
    campaign = get_campaign(conn, campaign_id)
    item = dict(record)
    item["url"] = textparse.safe_url(item.get("url", ""))
    kind = item.get("kind") or "person"
    body = item.get("body", "") or ""

    if not item.get("first_name") and item.get("full_name"):
        parsed = textparse.parse_name(item["full_name"])
        item.update(full_name=parsed["full_name"] or item["full_name"], first_name=parsed["first_name"], name_confidence=parsed["confidence"])
    if not item.get("first_name") and item["url"] and kind != "job":
        parsed = textparse.name_from_profile_url(item["url"])
        if parsed["confidence"]:
            item.update(full_name=item.get("full_name") or parsed["full_name"], first_name=parsed["first_name"], name_confidence=parsed["confidence"])

    analysis = textparse.analyze_post(body)
    item.setdefault("intents", analysis["intents"])
    item.setdefault("flags", analysis["flags"])
    item["role_hint"] = item.get("role_hint") or analysis["role_hint"] or (item.get("title", "") if kind == "job" else "")
    item["email"] = item.get("email") or analysis["email"]
    # A post or job ad that publishes an address and asks for CVs there invites exactly this email.
    if kind in ("post", "job") and item["email"] and "cta_cv" in item["intents"] and not campaign["commercial"]:
        item["consent_basis"] = item.get("consent_basis") or "invited_by_post"

    key = textparse.normalize_url(item["url"]) or textparse.stable_key(item.get("full_name", ""), item.get("company", ""), body[:300], item.get("email", ""))
    contact = textparse.contact_key(item["url"], item["email"]) or (key if kind == "post" else "")

    weights, alpha = _load_model(conn, campaign_id)
    scored = _score_item({**item, "kind": kind}, campaign, weights, alpha)
    existing = row(conn.execute("SELECT * FROM items WHERE campaign_id=? AND external_key=?", (campaign_id, key)).fetchone())
    stamp = now()
    state = item.get("connection_state") or "none"

    if existing:
        merged_state = "connected" if "connected" in (state, existing["connection_state"]) else existing["connection_state"]
        conn.execute(
            "UPDATE items SET full_name=COALESCE(NULLIF(?,''),full_name), first_name=COALESCE(NULLIF(?,''),first_name), "
            "name_confidence=MAX(name_confidence,?), title=COALESCE(NULLIF(?,''),title), company=COALESCE(NULLIF(?,''),company), "
            "location=COALESCE(NULLIF(?,''),location), body=COALESCE(NULLIF(?,''),body), email=COALESCE(NULLIF(?,''),email), "
            "consent_basis=CASE WHEN consent_basis='none' THEN ? ELSE consent_basis END, connection_state=?, updated_at=? WHERE id=?",
            (item.get("full_name", ""), item.get("first_name", ""), float(item.get("name_confidence") or 0), item.get("title", ""),
             item.get("company", ""), item.get("location", ""), body, item["email"], item.get("consent_basis") or "none", merged_state, stamp, existing["id"]),
        )
        just_connected = merged_state == "connected" and existing["connection_state"] == "pending"
        if just_connected:
            _after_connected(conn, existing["id"], campaign)
        if commit:
            conn.commit()
        return get_item(conn, existing["id"]), False

    if enforce:
        limit = plan(conn)["items"]
        if conn.execute("SELECT COUNT(*) c FROM items").fetchone()["c"] >= limit:
            raise LimitError(f"Your plan allows {limit} saved items.")
    status = "saved" if kind == "post" and item["intents"] else "new"
    cursor = conn.execute(
        "INSERT INTO items (campaign_id, kind, external_key, contact_key, full_name, first_name, name_confidence, title, company, "
        "location, url, body, source, consent_basis, connection_state, email, intents, flags, role_hint, status, rule_score, ml_score, score, "
        "rule_why, explain, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (campaign_id, kind, key, contact, item.get("full_name", ""), item.get("first_name", ""), float(item.get("name_confidence") or 0),
         item.get("title", ""), item.get("company", ""), item.get("location", ""), item["url"], body, item.get("source", "manual"),
         item.get("consent_basis") or "none", state, item["email"], json.dumps(item["intents"]), json.dumps(item["flags"]),
         item["role_hint"], status, scored["rule_score"], scored["ml_score"], scored["score"], json.dumps(scored["rule_why"], ensure_ascii=False),
         json.dumps(scored["explain"], ensure_ascii=False), stamp, stamp),
    )
    if commit:
        conn.commit()
    return get_item(conn, cursor.lastrowid), True


def get_item(conn, item_id: int) -> dict | None:
    return row(conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone())


def list_items(conn, campaign_id: int, kind: str = "", status: str = "", query: str = "", min_score: float = 0, limit: int = 100, offset: int = 0) -> list[dict]:
    sql = "SELECT * FROM items WHERE campaign_id=? AND score>=?"
    args: list = [campaign_id, min_score]
    if kind:
        sql += " AND kind=?"
        args.append(kind)
    if status:
        sql += " AND status=?"
        args.append(status)
    if query:
        sql += " AND (full_name LIKE ? OR title LIKE ? OR company LIKE ? OR body LIKE ? OR location LIKE ?)"
        args += [f"%{query}%"] * 5
    sql += " ORDER BY score DESC, id DESC LIMIT ? OFFSET ?"
    return rows(conn.execute(sql, (*args, min(limit, 500), offset)))


def paste_item(conn, campaign_id: int, text: str, url: str = "", location: str = "", kind: str = "") -> tuple[dict, bool]:
    parsed = textparse.parse_paste(text, url)
    parsed["source"] = "paste"
    parsed["location"] = location
    if kind:
        parsed["kind"] = kind
    return add_item(conn, campaign_id, parsed)


def import_csv(conn, campaign_id: int, data: bytes | str) -> dict:
    created = updated = 0
    for record in importers.parse_csv(data):
        _, was_created = add_item(conn, campaign_id, record, commit=False)
        if was_created:
            created += 1
        else:
            updated += 1
    audit(conn, "import_csv", f"campaign={campaign_id} created={created} updated={updated}")
    conn.commit()
    return {"created": created, "updated": updated}


def fetch_sources(conn, campaign_id: int) -> dict:
    if not plan(conn)["job_sources"]:
        raise LimitError("Job sources need the Pro plan or higher.")
    campaign = get_campaign(conn, campaign_id)
    report = {"created": 0, "updated": 0, "errors": []}
    for source in campaign["sources"] or []:
        try:
            jobs = sources.fetch(source)
        except Exception as exc:  # one broken board must not stop the others
            report["errors"].append(f"{source.get('type')}:{source.get('slug') or source.get('query', '')}: {exc}")
            continue
        for job in jobs:
            job.update(kind="job", source=source["type"])
            _, was_created = add_item(conn, campaign_id, job, commit=False)
            report["created" if was_created else "updated"] += 1
        conn.commit()
    audit(conn, "fetch_sources", json.dumps(report, ensure_ascii=False))
    conn.commit()
    return report


def rescore_campaign(conn, campaign_id: int) -> int:
    campaign = get_campaign(conn, campaign_id)
    weights, alpha = _load_model(conn, campaign_id)
    items = rows(conn.execute("SELECT * FROM items WHERE campaign_id=?", (campaign_id,)))
    updates = []
    for item in items:
        scored = _score_item(item, campaign, weights, alpha)
        updates.append((scored["rule_score"], json.dumps(scored["rule_why"], ensure_ascii=False), scored["ml_score"], scored["score"], json.dumps(scored["explain"], ensure_ascii=False), item["id"]))
    conn.executemany("UPDATE items SET rule_score=?, rule_why=?, ml_score=?, score=?, explain=? WHERE id=?", updates)
    conn.commit()
    return len(items)


def _apply_model(conn, campaign_id: int, weights: dict, alpha: float) -> None:
    """Re-rank after a rating. Rule results are stored, so only the model part is recomputed."""
    updates = []
    for r in conn.execute("SELECT id, kind, title, company, location, body, intents, flags, rule_score, rule_why FROM items WHERE campaign_id=?", (campaign_id,)):
        item = {"kind": r["kind"], "title": r["title"], "company": r["company"], "location": r["location"], "body": r["body"], "intents": json.loads(r["intents"]), "flags": json.loads(r["flags"])}
        ml, learned = scoring.predict_explain(weights, item) if alpha > 0 else (None, [])
        final = r["rule_score"] if ml is None else (1 - alpha) * r["rule_score"] + alpha * ml
        updates.append((ml, round(final, 4), json.dumps(json.loads(r["rule_why"]) + learned, ensure_ascii=False), r["id"]))
    conn.executemany("UPDATE items SET ml_score=?, score=?, explain=? WHERE id=?", updates)
    conn.commit()


# ------------------------------------------------------------------ learning
def rate_item(conn, item_id: int, stars: int, reason: str = "", retrain_now: bool = True) -> dict:
    """Store a rating. The dashboard passes retrain_now=False and re-ranks in the background."""
    if not 1 <= int(stars) <= 5:
        raise ValueError("stars must be 1 to 5")
    if reason and reason not in scoring.REASON_FOCUS:
        raise ValueError(f"unknown reason: {reason}")
    item = get_item(conn, item_id)
    if not item:
        raise KeyError(item_id)
    conn.execute(
        "INSERT INTO rating_events (item_id, campaign_id, stars, reason, predicted, created_at) VALUES (?,?,?,?,?,?)",
        (item_id, item["campaign_id"], stars, reason, item["score"], now()),
    )
    conn.execute("UPDATE items SET stars=?, reason=?, updated_at=? WHERE id=?", (stars, reason, now(), item_id))
    conn.commit()
    if retrain_now:
        retrain(conn, item["campaign_id"])
    return get_item(conn, item_id)


def retrain(conn, campaign_id: int) -> dict:
    samples = rows(conn.execute("SELECT * FROM items WHERE campaign_id=? AND stars IS NOT NULL", (campaign_id,)))
    both = any(s["stars"] >= 4 for s in samples) and any(s["stars"] <= 2 for s in samples)
    alpha = scoring.blend_weight(len(samples), both)
    weights = scoring.train(samples) if alpha > 0 else {}
    conn.execute(
        "INSERT INTO models (campaign_id, weights, n, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(campaign_id) DO UPDATE SET weights=excluded.weights, n=excluded.n, updated_at=excluded.updated_at",
        (campaign_id, json.dumps({"weights": weights, "alpha": alpha}), len(samples), now()),
    )
    _apply_model(conn, campaign_id, weights, alpha)
    return {"n": len(samples), "alpha": alpha}


# ------------------------------------------------------------------ outreach
def _suppressed(conn, key: str) -> bool:
    return bool(key) and conn.execute("SELECT 1 FROM suppressions WHERE contact_key=?", (key,)).fetchone() is not None


def _recent_contact(conn, key: str) -> bool:
    if not key:
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(days=COOLDOWN_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        conn.execute(
            "SELECT 1 FROM outreach WHERE contact_key=? AND (status='ready' OR (sent_at IS NOT NULL AND sent_at>=?)) LIMIT 1",
            (key, cutoff),
        ).fetchone()
        is not None
    )


def choose_step(item: dict, campaign: dict) -> str:
    """Decide the channel for a contact, or '' if there is no permitted route."""
    has_profile = bool(textparse.linkedin_profile_url(item["url"]))
    if campaign["auto_email"] and item["email"] and item["consent_basis"] in AUTO_EMAIL_BASES:
        return "email"
    if item["kind"] == "post":
        return "message" if {"cta_dm"} & set(item["intents"] or []) else ""
    if item["connection_state"] == "connected":
        return "message" if has_profile else ""
    if item["connection_state"] == "pending":
        return ""
    return "connect" if has_profile else ""


def skip_reason(conn, item: dict, campaign: dict) -> str:
    flags = item["flags"] or []
    if _suppressed(conn, item["contact_key"]):
        return "suppressed"
    if "no_contact" in flags:
        return "asked_not_to_be_contacted"
    if "seeker" in flags:
        return "job_seeker"
    if _recent_contact(conn, item["contact_key"]):
        return "recently_contacted"
    step = choose_step(item, campaign)
    if not step:
        return "waiting_for_acceptance" if item["connection_state"] == "pending" else "no_permitted_route"
    if campaign["commercial"] and step == "message" and item["consent_basis"] == "none":
        return "no_consent_basis"
    return ""


def _sendable_variants(conn, campaign: dict, step: str) -> list[dict]:
    found = rows(conn.execute("SELECT * FROM variants WHERE campaign_id=? AND step=? AND active=1", (campaign["id"], step)))
    return [v for v in found if not messages.lint(v["body"], campaign, step)]


def _create_draft(conn, item: dict, campaign: dict, step: str, rng: random.Random | None = None) -> int | None:
    variants = _sendable_variants(conn, campaign, step)
    if not variants:
        return None
    variant = messages.pick_variant(variants, _variant_stats(conn, campaign["id"]), rng)
    ctx = messages.context(item, campaign)
    body = messages.render(variant["body"], ctx)
    subject = messages.render(campaign["email_subject"] or "Hello", ctx) if step == "email" else ""
    cursor = conn.execute(
        "INSERT INTO outreach (item_id, campaign_id, contact_key, variant_id, step, body, subject, status, created_at) VALUES (?,?,?,?,?,?,?,'ready',?)",
        (item["id"], campaign["id"], item["contact_key"], variant["id"], step, body, subject, now()),
    )
    conn.execute("UPDATE items SET status='queued', updated_at=? WHERE id=?", (now(), item["id"]))
    return cursor.lastrowid


def sent_today(conn, campaign_id: int) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return conn.execute(
        "SELECT COUNT(*) c FROM outreach WHERE campaign_id=? AND sent_at LIKE ?", (campaign_id, today + "%")
    ).fetchone()["c"]


def build_queue(conn, campaign_id: int, rng: random.Random | None = None) -> dict:
    """Prepare messages for the best contacts. No approval step: they are ready at once."""
    campaign = get_campaign(conn, campaign_id)
    cap = min(campaign["daily_cap"], plan(conn)["daily_cap"])
    pending = conn.execute("SELECT COUNT(*) c FROM outreach WHERE campaign_id=? AND status='ready'", (campaign_id,)).fetchone()["c"]
    room = max(0, cap - sent_today(conn, campaign_id) - pending)
    report = {"created": 0, "skipped": {}, "room": room, "template_problems": []}

    for step in ("connect", "message", "email"):
        all_variants = rows(conn.execute("SELECT * FROM variants WHERE campaign_id=? AND step=? AND active=1", (campaign_id, step)))
        for variant in all_variants:
            for problem in messages.lint(variant["body"], campaign, step):
                report["template_problems"].append(f"{variant['name']}: {problem}")

    candidates = rows(
        conn.execute(
            "SELECT * FROM items WHERE campaign_id=? AND (kind IN ('person','post') OR (kind='job' AND email!='')) "
            "AND status IN ('new','saved') AND score>=? ORDER BY score DESC",
            (campaign_id, campaign["min_score"]),
        )
    )
    for item in candidates:
        if report["created"] >= room:
            break
        reason = skip_reason(conn, item, campaign)
        if reason:
            report["skipped"][reason] = report["skipped"].get(reason, 0) + 1
            continue
        draft = _create_draft(conn, item, campaign, choose_step(item, campaign), rng)
        if draft is None:
            report["skipped"]["no_valid_template"] = report["skipped"].get("no_valid_template", 0) + 1
            continue
        report["created"] += 1
    followups = _due_followups(conn, campaign)
    report["followups"] = followups
    conn.commit()
    return report


def _due_followups(conn, campaign: dict) -> int:
    body = campaign["followup_body"]
    if not body or messages.lint(body, campaign, "message"):
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=campaign["followup_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    due = conn.execute(
        "SELECT o.item_id FROM outreach o WHERE o.campaign_id=? AND o.step='message' AND o.status='sent' AND o.sent_at<=? "
        "AND NOT EXISTS (SELECT 1 FROM outreach f WHERE f.item_id=o.item_id AND f.step='followup')",
        (campaign["id"], cutoff),
    ).fetchall()
    created = 0
    for entry in due:
        item = get_item(conn, entry["item_id"])
        if _suppressed(conn, item["contact_key"]):
            continue
        text = messages.render(body, messages.context(item, campaign))
        conn.execute(
            "INSERT INTO outreach (item_id, campaign_id, contact_key, step, body, status, created_at) VALUES (?,?,?,'followup',?,'ready',?)",
            (item["id"], campaign["id"], item["contact_key"], text, now()),
        )
        created += 1
    return created


def list_queue(conn, campaign_id: int, status: str = "ready") -> list[dict]:
    return rows(
        conn.execute(
            "SELECT o.*, i.full_name, i.first_name, i.title, i.company, i.location, i.url, i.email, i.kind, i.score, i.connection_state "
            "FROM outreach o JOIN items i ON i.id=o.item_id WHERE o.campaign_id=? AND o.status=? ORDER BY i.score DESC",
            (campaign_id, status),
        )
    )


def get_outreach(conn, outreach_id: int) -> dict | None:
    return row(conn.execute("SELECT * FROM outreach WHERE id=?", (outreach_id,)).fetchone())


def edit_draft(conn, outreach_id: int, body: str) -> None:
    conn.execute("UPDATE outreach SET body=? WHERE id=? AND status='ready'", (body, outreach_id))
    conn.commit()


def mark_sent(conn, outreach_id: int) -> dict:
    entry = get_outreach(conn, outreach_id)
    if not entry or entry["status"] != "ready":
        raise ValueError("this message is not ready to be marked sent")
    conn.execute("UPDATE outreach SET status='sent', sent_at=?, error='' WHERE id=?", (now(), outreach_id))
    state = ", connection_state='pending'" if entry["step"] == "connect" else ""
    conn.execute(f"UPDATE items SET status='contacted'{state}, updated_at=? WHERE id=?", (now(), entry["item_id"]))
    conn.commit()
    return get_outreach(conn, outreach_id)


def skip_draft(conn, outreach_id: int) -> None:
    entry = get_outreach(conn, outreach_id)
    if entry and entry["status"] == "ready":
        conn.execute("UPDATE outreach SET status='skipped' WHERE id=?", (outreach_id,))
        conn.execute("UPDATE items SET status='archived', updated_at=? WHERE id=?", (now(), entry["item_id"]))
        conn.commit()


def _after_connected(conn, item_id: int, campaign: dict) -> None:
    """Acceptance is what unlocks the real message, so it is created straight away."""
    conn.execute(
        "UPDATE items SET connection_state='connected', consent_basis=CASE WHEN consent_basis='none' THEN 'existing_connection' ELSE consent_basis END, updated_at=? WHERE id=?",
        (now(), item_id),
    )
    item = get_item(conn, item_id)
    if not _suppressed(conn, item["contact_key"]):
        _create_draft(conn, item, campaign, "message")


def mark_accepted(conn, item_id: int) -> dict:
    item = get_item(conn, item_id)
    if not item:
        raise KeyError(item_id)
    if item["connection_state"] != "connected":
        _after_connected(conn, item_id, get_campaign(conn, item["campaign_id"]))
    conn.commit()
    return get_item(conn, item_id)


def record_reply(conn, outreach_id: int, positive: bool = False, opt_out: bool = False) -> None:
    entry = get_outreach(conn, outreach_id)
    if not entry:
        raise KeyError(outreach_id)
    conn.execute(
        "UPDATE outreach SET status=?, replied_at=? WHERE id=?", ("positive" if positive else "replied", now(), outreach_id)
    )
    if opt_out:
        suppress(conn, entry["contact_key"], "opted_out")
    else:
        conn.execute("DELETE FROM outreach WHERE item_id=? AND step='followup' AND status='ready'", (entry["item_id"],))
    conn.commit()


def suppress(conn, key: str, reason: str = "manual") -> None:
    """Permanent do-not-contact, across every campaign."""
    if not key:
        return
    conn.execute(
        "INSERT INTO suppressions (contact_key, reason, created_at) VALUES (?,?,?) ON CONFLICT(contact_key) DO UPDATE SET reason=excluded.reason",
        (key, reason, now()),
    )
    conn.execute("UPDATE outreach SET status='skipped' WHERE contact_key=? AND status='ready'", (key,))
    audit(conn, "suppress", reason)
    conn.commit()


def forget_item(conn, item_id: int, keep_suppressed: bool = True) -> None:
    """Erase a person's data. The opaque suppression key stays so they are never contacted again."""
    item = get_item(conn, item_id)
    if not item:
        return
    if keep_suppressed and item["contact_key"]:
        suppress(conn, item["contact_key"], "erased")
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.execute("DELETE FROM rating_events WHERE item_id=?", (item_id,))
    audit(conn, "forget", f"item={item_id}")
    conn.commit()


def set_item_status(conn, item_id: int, status: str) -> None:
    if status not in ("new", "saved", "archived", "rejected", "done"):
        raise ValueError("unknown status")
    conn.execute("UPDATE items SET status=?, updated_at=? WHERE id=?", (status, now(), item_id))
    conn.commit()


def set_item_fields(conn, item_id: int, fields: dict) -> dict:
    allowed = {k: v for k, v in fields.items() if k in ("consent_basis", "location", "email", "first_name", "full_name", "title", "company")}
    if allowed.get("consent_basis", "none") not in CONSENT_BASES:
        raise ValueError("unknown consent basis")
    if "first_name" in allowed:
        allowed["name_confidence"] = 1.0
    if allowed:
        conn.execute(f"UPDATE items SET {', '.join(k + '=?' for k in allowed)} WHERE id=?", (*allowed.values(), item_id))
        conn.commit()
    return get_item(conn, item_id)


# ------------------------------------------------------------ search launcher
def search_links(campaign: dict) -> list[dict]:
    """Links the user opens themselves. Nothing is fetched by the app."""
    links = []
    base = "https://www.linkedin.com"
    for entry in campaign["searches"] or []:
        query = urllib.parse.quote(entry["query"])
        kind = entry.get("type", "people")
        if kind == "people":
            url = f"{base}/search/results/people/?keywords={query}"
            if entry.get("canada"):
                url += "&geoUrn=" + urllib.parse.quote(f'["{CANADA_GEO}"]')
        elif kind == "posts":
            url = f"{base}/search/results/content/?keywords={query}&sortBy=" + urllib.parse.quote('"date_posted"')
        else:
            url = f"{base}/jobs/search/?keywords={query}" + ("&location=Canada" if entry.get("canada") else "")
        links.append({"label": entry.get("label") or entry["query"], "type": kind, "url": url})
    return links


# ------------------------------------------------------------------- insights
def insights(conn, campaign_id: int) -> dict:
    funnel = {
        "items": conn.execute("SELECT COUNT(*) c FROM items WHERE campaign_id=?", (campaign_id,)).fetchone()["c"],
        "ready": 0, "connect_sent": 0, "accepted": 0, "messages_sent": 0, "replies": 0, "positive": 0,
    }
    funnel["accepted"] = conn.execute(
        "SELECT COUNT(*) c FROM items WHERE campaign_id=? AND connection_state='connected' AND source!='linkedin_export'", (campaign_id,)
    ).fetchone()["c"]
    for entry in conn.execute("SELECT step, status, COUNT(*) c FROM outreach WHERE campaign_id=? GROUP BY step, status", (campaign_id,)):
        delivered = entry["status"] in ("sent", "replied", "positive")
        if entry["status"] == "ready":
            funnel["ready"] += entry["c"]
        if delivered and entry["step"] == "connect":
            funnel["connect_sent"] += entry["c"]
        if delivered and entry["step"] != "connect":
            funnel["messages_sent"] += entry["c"]
        if entry["status"] in ("replied", "positive"):
            funnel["replies"] += entry["c"]
        if entry["status"] == "positive":
            funnel["positive"] += entry["c"]

    events = rows(conn.execute("SELECT stars, predicted, reason FROM rating_events WHERE campaign_id=? ORDER BY id", (campaign_id,)))
    hits = [abs(e["predicted"] - (e["stars"] - 1) / 4) < 0.5 for e in events]
    half = len(hits) // 2
    learning = {
        "ratings": len(events),
        "early_accuracy": round(sum(hits[:half]) / half, 3) if half else None,
        "recent_accuracy": round(sum(hits[half:]) / (len(hits) - half), 3) if len(hits) - half and half else None,
    }
    reasons: dict[str, int] = {}
    for event in events:
        if event["reason"]:
            reasons[event["reason"]] = reasons.get(event["reason"], 0) + 1
    weights, alpha = _load_model(conn, campaign_id)
    ranked = sorted(((v, k) for k, v in weights.items() if k != "__bias__"), reverse=True)
    learning.update(
        alpha=alpha,
        reasons=reasons,
        likes=[k for v, k in ranked[:10] if v > 0],
        dislikes=[k for v, k in ranked[::-1][:10] if v < 0],
    )
    return {"funnel": funnel, "learning": learning, "variants": list_variants(conn, campaign_id), "sent_today": sent_today(conn, campaign_id)}


EXPORT_COLUMNS = ["kind", "full_name", "first_name", "title", "company", "location", "url", "email", "score", "stars", "reason", "status", "consent_basis", "connection_state", "source"]


def export_items(conn, campaign_id: int) -> str:
    if not plan(conn)["export"]:
        raise LimitError("Export needs the Pro plan or higher.")
    audit(conn, "export", f"campaign={campaign_id}")
    everything = rows(conn.execute("SELECT * FROM items WHERE campaign_id=? ORDER BY score DESC", (campaign_id,)))
    return importers.export_csv(everything, EXPORT_COLUMNS)
