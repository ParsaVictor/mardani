"""Deterministic text understanding: names, URLs, post intent, pasted content.

Everything here is rule based on purpose: it is free, fast, offline and testable.
No LLM tokens are spent on any of it.
"""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

ANALYSIS_LIMIT = 3000
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)

HONORIFICS = {"dr", "mr", "mrs", "ms", "miss", "mx", "prof", "professor", "sir", "eng", "engr", "m", "mme"}
CREDENTIALS = {
    "rcic", "rcic-irb", "cic", "mba", "phd", "ph.d", "cpa", "pmp", "cfa", "cfp", "chrp", "chrl", "crhr", "p.eng", "peng",
    "esq", "jr", "sr", "ii", "iii", "msc", "bsc", "ma", "ba", "md", "llb", "jd", "shrm-cp", "shrm-scp", "aca",
}
ORG_WORDS = {
    "inc", "ltd", "llc", "llp", "corp", "corporation", "company", "co", "group", "agency", "services", "solutions",
    "consulting", "consultants", "consultancy", "immigration", "associates", "partners", "recruitment", "recruiting",
    "staffing", "technologies", "technology", "labs", "academy", "university", "college", "institute", "firm",
    "team", "linkedin", "member", "canada", "global", "international",
}


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"(?i)<\s*(br|/p|/div|/li|/h\d)\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def safe_url(url: str) -> str:
    """Return the URL if it is plain http(s); blocks javascript:, data: and the like."""
    url = (url or "").strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return ""
    return url


def normalize_url(url: str) -> str:
    """Canonical form used for de-duplication."""
    url = safe_url(url)
    if not url:
        return ""
    parts = urlsplit(url)
    host = parts.netloc.lower().split("@")[-1]
    path = parts.path.rstrip("/")
    if host.endswith("linkedin.com"):
        host = "www.linkedin.com"
        path = path.lower()
        return urlunsplit(("https", host, path, "", ""))
    return urlunsplit((parts.scheme.lower(), host, path, parts.query, ""))


def linkedin_profile_url(url: str) -> str:
    normal = normalize_url(url)
    return normal if re.match(r"https://www\.linkedin\.com/in/[^/]+$", normal) else ""


def contact_key(url: str = "", email: str = "") -> str:
    """Stable identity for one human, shared across campaigns (suppression, cooldown)."""
    profile = linkedin_profile_url(url)
    if profile:
        return "li:" + profile.rsplit("/", 1)[-1]
    if email:
        return "em:" + email.strip().lower()
    return ""


def stable_key(*parts: str) -> str:
    joined = "\x1f".join(p.strip().lower() for p in parts)
    return "h:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def _strip_symbols(text: str) -> str:
    """Remove emoji and pictographs, keep letters of every script."""
    kept = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "M", "N", "Z") or ch in "-'’.,|()":
            kept.append(ch)
        else:
            kept.append(" ")
    return re.sub(r"\s+", " ", "".join(kept)).strip()


def _proper(word: str) -> str:
    if word.isupper() or word.islower():
        return "-".join(p.capitalize() for p in word.split("-"))
    return word


def parse_name(raw: str) -> dict:
    """Split a display name. Returns full_name, first_name, confidence.

    first_name stays empty unless we are confident, because a wrong name in a
    greeting is far worse than a neutral "Hello".
    """
    text = _strip_symbols(raw or "")
    text = re.split(r"\s[|]\s|[|]|\s-\s|\(", text)[0]
    pieces = [p.strip() for p in text.split(",")]
    text = pieces[0] if pieces else ""
    words = [w for w in text.split() if w.strip(".'’-")]

    while words and words[0].lower().rstrip(".") in HONORIFICS:
        words.pop(0)
    while words and words[-1].lower().rstrip(".") in CREDENTIALS:
        words.pop()

    empty = {"full_name": "", "first_name": "", "confidence": 0.0}
    if not words or len(words) > 5:
        return empty
    lowered = {w.lower().strip(".") for w in words}
    if lowered & ORG_WORDS or any(ch.isdigit() for w in words for ch in w):
        return empty

    words = [_proper(w) for w in words]
    full = " ".join(words)
    first = words[0].strip(".")
    if len(first) < 2:  # an initial such as "J. Smith"
        return {"full_name": full, "first_name": "", "confidence": 0.3}
    confidence = 0.95 if len(words) >= 2 else 0.7
    return {"full_name": full, "first_name": first, "confidence": confidence}


def name_from_profile_url(url: str) -> dict:
    """Derive a name from /in/jane-doe-12a3b. Lower confidence than a real name."""
    profile = linkedin_profile_url(url)
    empty = {"full_name": "", "first_name": "", "confidence": 0.0}
    if not profile:
        return empty
    slug = profile.rsplit("/", 1)[-1]
    words = [w for w in slug.split("-") if w and not re.search(r"\d", w)]
    if len(words) < 2 or any(len(w) > 15 for w in words):
        return empty
    parsed = parse_name(" ".join(w.capitalize() for w in words))
    if parsed["confidence"]:
        parsed["confidence"] = min(parsed["confidence"], 0.6)
    return parsed


# ---------------------------------------------------------------- post intent
_PATTERNS = {
    "cta_comment": [
        r"\bcomment\s+(?:below|down|here|with|your|on this|if|and)\b",
        r"\bcomment\s+[\"“'‘]?\w+[\"”'’]?\s+(?:below|and|for|to|if)\b",
        r"\b(?:drop|leave|write|put|add)\s+(?:a|your|an)\s+(?:\w+\s+)?comment\b",
        r"\b(?:interested|apply)\b[^.\n]{0,20}\bcomment\b",
        r"\bin the comments\b",
        r"\bcommentez\b|\blaissez un commentaire\b",
        r"کامنت\s*(?:بذار|بگذار|بزار|کنید|بدید|بدهید)",
    ],
    "cta_dm": [
        r"\b(?:dm|pm|inbox|message)\s+(?:me|us)\b",
        r"\bsend\s+(?:me\s+|us\s+)?(?:a\s+)?(?:dm|pm|direct message|private message|message)\b",
        r"\bdm\s+(?:your|for|if|to)\b",
        r"\bdrop\s+(?:me|us)\s+a\s+(?:line|message|dm|note)\b",
        r"\breach out\s+(?:to\s+)?(?:me|us)\b|\bfeel free to\s+(?:reach out|message|contact)\b",
        r"\bécrivez[- ]moi\b|\benvoyez[- ]moi un message\b|\bcontactez[- ]moi\b",
        r"دایرکت|پیام\s*(?:بدید|بدهید|دهید|بده)",
    ],
    "cta_cv": [
        r"\b(?:send|share|email|e-mail|drop|forward|submit)\s+(?:me\s+|us\s+)?(?:your|ur|a|an)\s+(?:updated\s+|latest\s+)?(?:cv|resume|résumé|portfolio)\b",
        r"\b(?:cvs?|resumes?|résumés?)\s+(?:to|at)\s+\S*@",
        r"\benvoyez\s+(?:moi\s+)?votre\s+cv\b",
        r"رزومه",
    ],
    "hiring": [
        r"\b(?:we(?:'|’)?re|we are|i(?:'|’)?m|i am|am|is|are|now|currently|actively)\s+hiring\b",
        r"#hiring\b",
        r"(?m)^\W*(?:now\s+)?hiring\b",
        r"\b(?:we(?:'|’)?re|we are|team is|company is)\s+(?:looking for|seeking|searching for)\b",
        r"\b(?:i(?:'|’)?m|i am)\s+(?:looking for|seeking)\s+(?:a|an)\s+(?:\w+\s+){0,4}(?:engineer|developer|scientist|designer|manager|consultant|advisor|analyst|intern)\b",
        r"\b(?:open|new)\s+(?:role|position|vacancy)\b|\bjob opening\b|\bjoin our team\b",
        r"\bnous recrutons\b|\bon embauche\b|\bnous embauchons\b",
        r"استخدام|جذب نیرو",
    ],
}
_FLAGS = {
    "no_contact": [
        r"\b(?:no|don(?:'|’)?t|do not|please don(?:'|’)?t)\s+(?:dms?|pms?|messages?|message me|dm me|solicit\w*|recruiters?|agencies)\b",
        r"\bnot accepting\s+(?:dms?|messages|solicitations?)\b",
        r"\bno\s+(?:unsolicited|cold)\b",
        r"\bpas de (?:démarchage|sollicitation)\b",
    ],
    "seeker": [
        r"\bopen to work\b|#opentowork\b",
        r"\b(?:i(?:'|’)?m|i am|currently)\s+(?:looking for|seeking)\s+(?:a\s+|an\s+|my\s+|new\s+)*(?:job|work|role|position|opportunit\w+|employment)\b",
        r"\bin search of (?:a )?(?:job|work|new role)\b",
    ],
    "engagement_bait": [
        r"\bcomment\s+[\"“'‘]?(?:yes|interested|guide|pdf|link|send|me|info)[\"”'’]?\b(?!\s+(?:below with your))",
        r"\b(?:like|repost|share)\b[^.\n]{0,30}\b(?:comment|follow)\b",
        r"\bfollow me\b",
        r"\bfree (?:guide|pdf|template|checklist)\b",
    ],
}
_COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in {**_PATTERNS, **_FLAGS}.items()}
_ROLE_RE = re.compile(
    r"\b(?:hiring|looking for|seeking|searching for)\s+(?:an?\s+|our\s+next\s+|the\s+|\d+\s+)?"
    r"((?:[A-Za-z+#./-]+\s+){0,4}?(?:engineers?|developers?|scientists?|researchers?|designers?|managers?|"
    r"consultants?|advisors?|analysts?|interns?|architects?|specialists?|leads?))\b",
    re.I,
)


def analyze_post(text: str) -> dict:
    """Detect what a post asks the reader to do, and whether outreach is unwanted."""
    # The ask is near the top of a post, and job descriptions run to many kilobytes.
    text = (text or "")[:ANALYSIS_LIMIT]
    found = {k: any(p.search(text) for p in _COMPILED[k]) for k in _COMPILED}
    intents = [k for k in _PATTERNS if found[k]]
    flags = [k for k in _FLAGS if found[k]]
    # A person looking for work is not a hiring signal, even when phrased alike.
    if "seeker" in flags and "hiring" in intents and not re.search(r"\b(?:we(?:'|’)?re|we are)\b", text, re.I):
        intents.remove("hiring")
    role = _ROLE_RE.search(text)
    emails = EMAIL_RE.findall(text)
    return {
        "intents": intents,
        "flags": flags,
        "email": emails[0] if emails else "",
        "role_hint": re.sub(r"\s+", " ", role.group(1)).strip() if role else "",
    }


# ------------------------------------------------------------- pasted content
_NOISE = re.compile(
    r"^(?:feed post(?: number \d+)?|follow(?:ing)?|connect|message|like|comment|repost|send|share|"
    r"\+ ?follow|view profile|visible to .*|promoted|suggested|…\s*more|\.\.\.\s*more|see more|"
    r"\d+\s*(?:comments?|reposts?|likes?)|•.*|\d+[smhdwy]o?\s*•?.*|edited.*|verified|premium|"
    r"(?:1st|2nd|3rd\+?)(?:\s+degree connection)?)$",
    re.I,
)


def parse_paste(text: str, url: str = "") -> dict:
    """Turn text a user copied from a post or profile into structured fields."""
    text = (text or "").replace("\r\n", "\n").strip()
    urls = [safe_url(u.rstrip(".,")) for u in URL_RE.findall(text)]
    url = safe_url(url) or next(
        (u for u in urls if "linkedin.com/in/" in u or "linkedin.com/posts/" in u or "linkedin.com/feed/" in u), ""
    )

    lines: list[str] = []
    for line in (ln.strip() for ln in text.split("\n")):
        if not line or _NOISE.match(line):
            continue
        if lines and line == lines[-1]:  # LinkedIn repeats the author's name when copied
            continue
        lines.append(line)

    name = {"full_name": "", "first_name": "", "confidence": 0.0}
    title = ""
    body_lines = lines
    if lines:
        candidate = parse_name(lines[0])
        looks_like_name = candidate["confidence"] > 0 and len(lines[0]) <= 60 and not re.search(r"[.!?:]$", lines[0])
        if looks_like_name and len(lines) >= 2:
            name = candidate
            title = lines[1] if len(lines[1]) <= 120 else ""
            body_lines = lines[2:] if title else lines[1:]
    if not name["confidence"] and url:
        name = name_from_profile_url(url)

    body = "\n".join(body_lines).strip()
    company = ""
    match = re.search(r"\b(?:at|@)\s+([^|•,\n]+)", title)
    if match:
        company = match.group(1).strip()
    analysis = analyze_post(body or text)
    is_post = bool(analysis["intents"]) or len(body) > 200 or "/posts/" in url or "/feed/" in url
    return {
        "kind": "post" if is_post else "person",
        "url": url,
        "full_name": name["full_name"],
        "first_name": name["first_name"],
        "name_confidence": name["confidence"],
        "title": title,
        "company": company,
        "body": body,
        **analysis,
    }
