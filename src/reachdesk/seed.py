"""Ready-made campaigns. Safe to run repeatedly; existing campaigns are left alone."""
from __future__ import annotations

from . import service

CANADA = [
    "canada", "canadian", "ontario", "quebec", "québec", "british columbia", "alberta", "manitoba", "saskatchewan",
    "nova scotia", "new brunswick", "newfoundland", "prince edward island", "yukon", "nunavut", "northwest territories",
    "toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "edmonton", "winnipeg", "halifax", "mississauga",
    "brampton", "hamilton", "kitchener", "waterloo", "victoria", "regina", "saskatoon", "gta", "bc", "on", "ab", "qc",
]
NOT_CANADA = ["washington", "wa", "california", "ca, usa", "usa", "united states", "texas", "uk", "united kingdom", "australia"]

CONSULTANTS = {
    "slug": "ca-consultants",
    "name": "Consultants in Canada",
    "commercial": 1,
    "daily_cap": 25,
    "note_limit": 200,
    "min_score": 0.45,
    "email_subject": "A question about your consulting work",
    "keywords": {
        "core": ["consultant", "advisor", "adviser", "rcic", "conseiller", "مشاور"],
        "title": ["consulting", "advisory"],
        "body": ["immigration", "cicc", "licensed", "clients"],
        "negative": ["student", "intern", "looking for work", "retired"],
        "location": CANADA,
        "location_exclude": NOT_CANADA,
    },
    "searches": [
        {"label": "Consultants in Canada", "query": "consultant", "type": "people", "canada": True},
        {"label": "Advisors in Canada", "query": "advisor", "type": "people", "canada": True},
        {"label": "Immigration consultants (RCIC)", "query": "RCIC immigration consultant", "type": "people", "canada": True},
        {"label": "Business consultants", "query": "business consultant", "type": "people", "canada": True},
    ],
    "variants": [
        ("connect-a", "connect", "{greeting} I work with consultants across Canada and would be glad to connect."),
        ("message-a", "message",
         "{greeting}\n\nThanks for connecting. I'm {sender_name}. We built something for consultants that may be useful in your work, and you can see it here: {website}\n\n"
         "I'd value your opinion if you have a moment.\n\n{sender_name} | {sender_contact}\n{opt_out}"),
        ("email-a", "email",
         "{greeting}\n\nI'm {sender_name}. I found your business contact details and thought this may be relevant to your consulting work: {website}\n\n"
         "I'd value your opinion if you have a moment.\n\n{sender_name} | {sender_contact}\n{opt_out}"),
    ],
}

SENIOR = {
    "slug": "ca-senior",
    "name": "Senior consultants and marketers in Canada",
    "commercial": 1,
    "daily_cap": 20,
    "note_limit": 200,
    "min_score": 0.6,
    "email_subject": "A question about your work",
    "keywords": {
        # Exact senior roles score highest; a plain "consultant" or "marketing" title is adjacent.
        "core": [
            "senior consultant", "principal consultant", "managing consultant", "senior advisor", "senior manager",
            "marketing director", "director of marketing", "head of marketing", "vp marketing", "vp, marketing",
            "vice president, marketing", "vice president of marketing", "cmo", "chief marketing officer",
            "marketing manager", "senior marketing manager", "growth lead", "head of growth", "brand director", "partner",
        ],
        "title": ["consultant", "consulting", "advisor", "marketing", "marketer", "growth", "brand", "director", "head of", "principal"],
        "body": ["b2b", "strategy", "clients", "campaigns", "demand generation", "go-to-market", "brand", "advisory"],
        "negative": ["junior", "intern", "internship", "student", "assistant", "coordinator", "looking for work", "retired"],
        "location": CANADA,
        "location_exclude": NOT_CANADA,
    },
    "searches": [
        {"label": "Senior consultants in Canada", "query": "senior consultant", "type": "people", "canada": True},
        {"label": "Principal and managing consultants", "query": "principal consultant OR managing consultant", "type": "people", "canada": True},
        {"label": "Marketing directors in Canada", "query": "marketing director", "type": "people", "canada": True},
        {"label": "Heads of marketing and CMOs", "query": "\"head of marketing\" OR CMO", "type": "people", "canada": True},
        {"label": "Senior marketing managers", "query": "senior marketing manager", "type": "people", "canada": True},
    ],
    "variants": [
        ("connect-a", "connect", "{greeting} I work with consultants and marketing leaders across Canada and would be glad to connect."),
        ("message-a", "message",
         "{greeting}\n\nThanks for connecting. I'm {sender_name}. We built something that may be useful in your work{at_company}, and you can see it here: {website}\n\n"
         "I'd value your opinion if you have a moment.\n\n{sender_name} | {sender_contact}\n{opt_out}"),
        ("email-a", "email",
         "{greeting}\n\nI'm {sender_name}. I found your business contact details and thought this may be relevant to your work{at_company}: {website}\n\n"
         "I'd value your opinion if you have a moment.\n\n{sender_name} | {sender_contact}\n{opt_out}"),
    ],
}

INTRO = (
    "I'm Mohammad Parsa Karkooti, a Computer Vision and Deep Learning engineer with Full-Stack skills and good intermediate English. "
    "{role_hook}I would be very glad if you visited my website: {website}\n\n"
    "Thank you for your time. It would be an honour to work together."
)
CAREER = {
    "slug": "parsa-career",
    "name": "Parsa: hiring managers, posts and jobs",
    "commercial": 0,
    "website": "https://parsavictor.github.io/",
    "sender_name": "Mohammad Parsa Karkooti",
    "daily_cap": 25,
    "note_limit": 200,
    "min_score": 0.4,
    "email_subject": "Computer Vision and Deep Learning engineer: Mohammad Parsa Karkooti",
    "keywords": {
        "core": ["computer vision", "deep learning", "image processing", "perception", "opencv"],
        "title": ["machine learning", "ml engineer", "ai engineer", "research engineer", "full stack", "full-stack", "fullstack"],
        "people_title": ["recruiter", "talent acquisition", "hiring manager", "cto", "head of ai", "engineering manager"],
        "body": ["pytorch", "tensorflow", "machine learning", "full stack", "full-stack", "python", "neural network"],
        "negative": ["unpaid", "commission only", "sales representative", "account executive"],
    },
    "searches": [
        {"label": "Recruiters: computer vision", "query": "recruiter computer vision", "type": "people"},
        {"label": "Hiring posts: deep learning", "query": "hiring \"deep learning engineer\"", "type": "posts"},
        {"label": "Hiring posts: computer vision", "query": "hiring \"computer vision\" send resume", "type": "posts"},
        {"label": "Posts asking for a DM or CV", "query": "\"send your resume\" machine learning", "type": "posts"},
        {"label": "Jobs: computer vision", "query": "computer vision engineer", "type": "jobs"},
        {"label": "Jobs: full stack AI", "query": "full stack AI engineer", "type": "jobs"},
    ],
    "sources": [
        {"type": "arbeitnow"},
        {"type": "greenhouse", "slug": "anthropic"},
        {"type": "greenhouse", "slug": "databricks"},
        {"type": "ashby", "slug": "openai"},
        {"type": "ashby", "slug": "cohere"},
    ],
    "variants": [
        ("connect-a", "connect", "{greeting} I'm a Computer Vision and Deep Learning engineer. I'd be glad to connect{at_company_note}."),
        ("message-a", "message", "{greeting}\n\n" + INTRO),
        ("message-b", "message",
         "{greeting}\n\n{role_hook}I'm Mohammad Parsa Karkooti: image processing, deep learning and full-stack engineering. My work is here: {website}\n\nThank you for your time."),
        ("email-a", "email", "{greeting}\n\n" + INTRO + "\n\nMohammad Parsa Karkooti"),
    ],
}


def seed(conn) -> list[str]:
    created = []
    for spec in (CONSULTANTS, CAREER, SENIOR):
        if service.get_campaign(conn, slug=spec["slug"]):
            continue
        spec = dict(spec)
        slug, name = spec.pop("slug"), spec.pop("name")
        variants = spec.pop("variants")
        campaign = service.create_campaign(conn, slug, name, enforce=False, **spec)
        for variant_name, step, body in variants:
            service.save_variant(conn, campaign["id"], variant_name, body.replace("{at_company_note}", ""), step)
        created.append(slug)
    return created
