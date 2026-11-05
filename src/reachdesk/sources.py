"""Job postings from public, documented job-board endpoints. No account, no scraping.

Hosts are a fixed allow-list and company slugs are validated, so a campaign setting
can never make the app request an arbitrary URL.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request

from .textparse import strip_html

SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
USER_AGENT = "ReachDesk/0.1 (+https://github.com/ParsaVictor/mardani)"
MAX_BYTES = 20_000_000
_last_call: dict[str, float] = {}


def _get_json(url: str, timeout: int = 25):
    host = urllib.parse.urlsplit(url).netloc
    wait = 1.0 - (time.monotonic() - _last_call.get(host, 0.0))
    if wait > 0:  # at most one request per second per host
        time.sleep(wait)
    _last_call[host] = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https hosts only
        return json.loads(response.read(MAX_BYTES))


def parse_greenhouse(data: dict, company: str) -> list[dict]:
    return [
        {
            "title": j.get("title", ""),
            "company": company,
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "body": strip_html(j.get("content", "")),
        }
        for j in data.get("jobs", [])
    ]


def parse_lever(data: list, company: str) -> list[dict]:
    return [
        {
            "title": j.get("text", ""),
            "company": company,
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "body": j.get("descriptionPlain") or strip_html(j.get("description", "")),
        }
        for j in data
    ]


def parse_ashby(data: dict, company: str) -> list[dict]:
    return [
        {
            "title": j.get("title", ""),
            "company": company,
            "location": j.get("location", ""),
            "url": j.get("jobUrl", ""),
            "body": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", "")),
        }
        for j in data.get("jobs", [])
        if j.get("isListed", True)
    ]


def parse_remotive(data: dict) -> list[dict]:
    return [
        {
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("candidate_required_location", ""),
            "url": j.get("url", ""),
            "body": strip_html(j.get("description", "")),
        }
        for j in data.get("jobs", [])
    ]


def parse_arbeitnow(data: dict) -> list[dict]:
    return [
        {
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("location", "") + (" (remote)" if j.get("remote") else ""),
            "url": j.get("url", ""),
            "body": strip_html(j.get("description", "")),
        }
        for j in data.get("data", [])
    ]


def fetch(source: dict) -> list[dict]:
    """source: {"type": "greenhouse", "slug": "acme"} or {"type": "remotive", "query": "python"}."""
    kind = source.get("type", "")
    slug = source.get("slug", "")
    if kind in ("greenhouse", "lever", "ashby") and not SLUG_RE.match(slug):
        raise ValueError(f"invalid company slug: {slug!r}")
    quoted = urllib.parse.quote(slug, safe="")
    if kind == "greenhouse":
        return parse_greenhouse(_get_json(f"https://boards-api.greenhouse.io/v1/boards/{quoted}/jobs?content=true"), slug)
    if kind == "lever":
        return parse_lever(_get_json(f"https://api.lever.co/v0/postings/{quoted}?mode=json"), slug)
    if kind == "ashby":
        return parse_ashby(_get_json(f"https://api.ashbyhq.com/posting-api/job-board/{quoted}"), slug)
    if kind == "remotive":
        query = urllib.parse.urlencode({"search": source.get("query", ""), "limit": 100})
        return parse_remotive(_get_json(f"https://remotive.com/api/remote-jobs?{query}"))
    if kind == "arbeitnow":
        return parse_arbeitnow(_get_json("https://www.arbeitnow.com/api/job-board-api"))
    raise ValueError(f"unknown source type: {kind!r}")
