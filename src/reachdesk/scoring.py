"""Ranking: transparent rules first, then a small model that learns from ratings.

The model is a pure-Python logistic regression (AdaGrad, soft targets). It costs
nothing to run and explains every score. Rejection reasons assign blame: rating a
job one star for "wrong_location" moves location features, and leaves the skill
words alone, so the system does not unlearn what the user actually wants.
"""
from __future__ import annotations

import math
import random
import re
from functools import lru_cache

MAX_TRAINING_SAMPLES = 400
RULE_TEXT_LIMIT = 4000
STOPWORDS = set(
    "a an and are as at be but by for from has have i in is it its of on or our that the their this to us was we "
    "were will with you your my me not if so can all more about who what when how they them there here just".split()
)
WORD_RE = re.compile(r"[^\W\d_][\w+#.-]*", re.UNICODE)

REASON_FOCUS = {
    "wrong_location": ("l:",),
    "wrong_role": ("t:", "b:"),
    "wrong_seniority": ("t:",),
    "wrong_company": ("c:",),
    "spam_or_bait": ("i:", "f:", "b:"),
    "not_hiring": ("i:", "f:", "b:"),
    "great_role": ("t:", "b:"),
    "great_company": ("c:",),
    "great_location": ("l:",),
}
REASONS = sorted(REASON_FOCUS)


def tokens(text: str) -> list[str]:
    found = [w.strip(".-").lower() for w in WORD_RE.findall(text or "")]
    return [w for w in found if len(w) > 1 and w not in STOPWORDS]


def _field(prefix: str, text: str, limit: int, feats: dict[str, float]) -> None:
    words = tokens(text)[:limit]
    if not words:
        return
    grams = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
    value = 1.0 / math.sqrt(len(grams))
    for gram in grams:
        feats[prefix + gram] = value


@lru_cache(maxsize=50_000)
def _features(title: str, company: str, location: str, body: str, intents: tuple, flags: tuple, kind: str) -> dict[str, float]:
    feats: dict[str, float] = {}
    _field("t:", title, 30, feats)
    _field("c:", company, 10, feats)
    _field("l:", location, 10, feats)
    _field("b:", body, 120, feats)
    for intent in intents:
        feats["i:" + intent] = 1.0
    for flag in flags:
        feats["f:" + flag] = 1.0
    feats["k:" + kind] = 1.0
    return feats


def features(item: dict) -> dict[str, float]:
    """Cached, because every rating re-ranks the whole campaign. Treat the result as read-only."""
    return _features(
        item.get("title") or "", item.get("company") or "", item.get("location") or "", (item.get("body") or "")[:1500],
        tuple(item.get("intents") or ()), tuple(item.get("flags") or ()), item.get("kind") or "person",
    )


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def train(samples: list[dict], epochs: int = 30, lr: float = 0.5, l2: float = 1e-3, seed: int = 7) -> dict[str, float]:
    """samples: dicts with item fields plus stars and reason. Deterministic for a seed."""
    prepared = []
    epochs = epochs if len(samples) <= 100 else max(8, epochs * 100 // len(samples))  # keeps a rating under a second
    for sample in samples[-MAX_TRAINING_SAMPLES:]:
        focus = REASON_FOCUS.get(sample.get("reason") or "")
        target = (sample["stars"] - 1) / 4.0
        prepared.append((features(sample), target, focus))
    weights: dict[str, float] = {}
    grad_sq: dict[str, float] = {}
    rng = random.Random(seed)
    order = list(range(len(prepared)))
    for _ in range(epochs):
        rng.shuffle(order)
        for index in order:
            feats, target, focus = prepared[index]
            score = weights.get("__bias__", 0.0) + sum(weights.get(k, 0.0) * v for k, v in feats.items())
            error = _sigmoid(score) - target
            for key, value in list(feats.items()) + [("__bias__", 1.0)]:
                blame = 1.0
                if focus:
                    blame = 3.0 if key.startswith(focus) else 0.2
                grad = error * value * blame + l2 * weights.get(key, 0.0)
                grad_sq[key] = grad_sq.get(key, 0.0) + grad * grad
                weights[key] = weights.get(key, 0.0) - lr * grad / math.sqrt(grad_sq[key] + 1e-8)
    return {k: round(v, 5) for k, v in weights.items() if abs(v) > 1e-4}


def predict(weights: dict[str, float], item: dict) -> float:
    feats = features(item)
    score = weights.get("__bias__", 0.0) + sum(weights.get(k, 0.0) * v for k, v in feats.items())
    return _sigmoid(score)


def predict_explain(weights: dict[str, float], item: dict, top: int = 3) -> tuple[float, list[str]]:
    """Prediction and explanation in one pass, touching only features that have a weight."""
    feats = features(item)
    parts = [(weights[k] * feats[k], k) for k in weights.keys() & feats.keys()]
    score = _sigmoid(weights.get("__bias__", 0.0) + sum(c for c, _ in parts))
    parts.sort()
    learned = [f"learned + {k.split(':', 1)[1]}" for c, k in reversed(parts[-top:]) if c > 0.02]
    learned += [f"learned - {k.split(':', 1)[1]}" for c, k in parts[:top] if c < -0.02]
    return score, learned


def explain_model(weights: dict[str, float], item: dict, top: int = 3) -> list[str]:
    feats = features(item)
    parts = sorted(((weights.get(k, 0.0) * v, k) for k, v in feats.items()), key=lambda p: p[0])
    out = [f"learned + {k.split(':', 1)[1]}" for c, k in reversed(parts[-top:]) if c > 0.02]
    out += [f"learned - {k.split(':', 1)[1]}" for c, k in parts[:top] if c < -0.02]
    return out


def blend_weight(n_ratings: int, has_both_classes: bool) -> float:
    """How much to trust the model. Zero until it has seen likes and dislikes."""
    if n_ratings < 6 or not has_both_classes:
        return 0.0
    return min(0.85, n_ratings / (n_ratings + 12.0))


_regex_cache: dict[str, re.Pattern] = {}


def _hit(term: str, text: str) -> bool:
    pattern = _regex_cache.get(term)
    if pattern is None:
        pattern = re.compile(r"(?<![\w])" + re.escape(term.lower()) + r"(?![\w])")
        _regex_cache[term] = pattern
    return bool(pattern.search(text))


def _hits(terms: list[str], text: str) -> list[str]:
    return [t for t in terms or [] if _hit(t, text)]


def rule_score(item: dict, keywords: dict) -> tuple[float, list[str]]:
    title = (item.get("title") or "").lower()
    body = (item.get("body") or "")[:RULE_TEXT_LIMIT].lower()
    location = (item.get("location") or "").lower()
    intents = item.get("intents") or []
    flags = item.get("flags") or []
    why: list[str] = []
    score = 0.0

    # Three tiers keep scores spread out: "core" is exactly what is wanted, "title" is
    # adjacent, and "people_title" only describes a person worth contacting, never a job.
    core = keywords.get("core", [])
    core_title = _hits(core, title)
    adjacent = keywords.get("title", []) + ([] if item.get("kind") == "job" else keywords.get("people_title", []))
    title_hits = _hits(adjacent, title)
    if core_title:
        score += 0.55
        why.append("core title: " + ", ".join(core_title[:3]))
    elif title_hits:
        score += 0.35
        why.append("title: " + ", ".join(title_hits[:3]))
    core_body = _hits(core, body)
    body_hits = _hits(keywords.get("body", []), body)
    if core_body or body_hits:
        score += min(0.25, 0.08 * len(core_body) + 0.03 * len(body_hits))
        why.append("text: " + ", ".join((core_body + body_hits)[:3]))

    wanted = keywords.get("location", [])
    capped = False
    if wanted:
        excluded = _hits(keywords.get("location_exclude", []), location)
        if _hits(wanted, location) and not excluded:
            score += 0.25
            why.append("location match")
        elif location:
            capped = True
            why.append("outside target location")
        elif _hits([w for w in wanted if len(w) > 3], body + " " + title):  # "on" or "bc" mean nothing in prose
            score += 0.1
            why.append("location mentioned in text")
    else:
        score += 0.15

    if "hiring" in intents:
        score += 0.2
        why.append("hiring signal")
    if {"cta_dm", "cta_cv", "cta_comment"} & set(intents):
        score += 0.1
        why.append("asks for a response")

    negative = _hits(keywords.get("negative", []), f"{title} {body}")
    if negative:
        score -= 0.4
        why.append("excluded: " + ", ".join(negative[:3]))
    if "seeker" in flags:
        score -= 0.4
        why.append("author is job seeking")
    if "engagement_bait" in flags:
        score -= 0.15
        why.append("possible engagement bait")

    score = max(0.0, min(1.0, score))
    if capped:
        score = min(score, 0.2)
    return round(score, 4), why
