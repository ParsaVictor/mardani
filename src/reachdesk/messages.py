"""Message templates, linting and variant selection (Thompson sampling)."""
from __future__ import annotations

import random
import re

OPT_OUT = 'Reply "stop" and I will not contact you again.'
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
ALLOWED = {
    "greeting", "first_name", "title", "company", "at_company", "role_hint", "role_hook",
    "website", "sender_name", "sender_contact", "opt_out",
}


def context(item: dict, campaign: dict) -> dict[str, str]:
    first = item.get("first_name") or ""
    confident = first and float(item.get("name_confidence") or 0) >= 0.6
    company = item.get("company") or ""
    role = item.get("role_hint") or ""
    return {
        "greeting": f"Hi {first}," if confident else "Hello,",
        "first_name": first if confident else "",
        "title": item.get("title") or "",
        "company": company,
        "at_company": f" at {company}" if company else "",
        "role_hint": role,
        "role_hook": f"I saw you are looking for a {role}. " if role else "",
        "website": campaign.get("website") or "",
        "sender_name": campaign.get("sender_name") or "",
        "sender_contact": campaign.get("sender_contact") or "",
        "opt_out": OPT_OUT,
    }


def render(template: str, ctx: dict[str, str]) -> str:
    text = PLACEHOLDER_RE.sub(lambda m: ctx.get(m.group(1), m.group(0)), template)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def lint(template: str, campaign: dict, step: str = "message") -> list[str]:
    """Problems that must block a template. Empty list means it may be used."""
    problems = []
    used = set(PLACEHOLDER_RE.findall(template))
    unknown = used - ALLOWED
    if unknown:
        problems.append("unknown placeholder: " + ", ".join(sorted(unknown)))
    if "website" in used and not campaign.get("website"):
        problems.append("campaign website is not set")
    if "sender_name" in used and not campaign.get("sender_name"):
        problems.append("campaign sender name is not set")
    if "sender_contact" in used and not campaign.get("sender_contact"):
        problems.append("campaign sender contact is not set")
    if step == "connect":
        limit = int(campaign.get("note_limit") or 200)
        worst = render(template, _longest_ctx(campaign))
        if len(worst) > limit:
            problems.append(f"connection note can reach {len(worst)} characters, limit is {limit}")
        if "website" in used or re.search(r"https?://", template):
            problems.append("connection note must not contain a link or a pitch")
    elif campaign.get("commercial"):
        for needed in ("sender_name", "sender_contact", "opt_out"):
            if needed not in used:
                problems.append(f"commercial message must include {{{needed}}}")
    return problems


def _longest_ctx(campaign: dict) -> dict[str, str]:
    return context(
        {"first_name": "Maximiliano", "name_confidence": 1, "company": "A Fairly Long Company Name", "role_hint": "Senior Machine Learning Engineer"},
        campaign,
    )


def pick_variant(variants: list[dict], stats: dict[int, dict], rng: random.Random | None = None) -> dict:
    """Thompson sampling: favour what earns replies, keep testing the rest."""
    rng = rng or random.Random()
    best, best_draw = None, -1.0
    for variant in variants:
        s = stats.get(variant["id"], {})
        sent = s.get("sent", 0)
        replies = s.get("replies", 0)
        draw = rng.betavariate(1 + replies, 1 + max(0, sent - replies))
        if draw > best_draw:
            best, best_draw = variant, draw
    return best
