# ReachDesk

[![CI](https://github.com/ParsaVictor/mardani/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ParsaVictor/mardani/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ParsaVictor/mardani)](https://github.com/ParsaVictor/mardani/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)

**A self-learning outreach and opportunity desk.** ReachDesk ranks people, posts and jobs by what you actually want, writes a personal message for each one, handles connect-first sequencing, and sends email automatically where you have grounds to. It runs on your own computer, needs no API keys, and spends no LLM tokens.

[فارسی](README.fa.md) · [Roadmap](docs/ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Compliance](docs/COMPLIANCE.md) · [Business model](docs/BUSINESS.md) · [Project status](STATUS.md) · [Changelog](CHANGELOG.md)

## What it does

| Area | Behaviour |
|---|---|
| **Find** | Saved LinkedIn searches you open yourself, one-click capture of text you select, LinkedIn's official `Connections.csv`, any CSV, and public job boards (Greenhouse, Lever, Ashby, Arbeitnow) |
| **Understand** | Extracts the first name, and falls back to "Hello," rather than guess. Detects "comment", "DM me", "send your CV" and "we're hiring" in English, French and Persian. Flags "no recruiters", job seekers and engagement bait |
| **Learn** | Rate anything 1 to 5 stars and say why. A small local model re-ranks everything, and the reason assigns blame: "wrong location" lowers location features and leaves your skills alone |
| **Connect first** | Strangers get a short note with no link. Once they accept, the full message is created automatically. A fresh `Connections.csv` detects acceptances in bulk |
| **Send** | **Email goes out automatically** for contacts with a recorded basis. **LinkedIn is one click per person:** the text is copied and the profile opens, and you press send |
| **Protect** | Daily caps, 90-day cooldown across campaigns, permanent opt-out, erasure, and a re-check of all of this at send time |
| **Measure** | Requests, acceptances, replies, A/B variants chosen by Thompson sampling, and whether the ranking is actually improving |

## Why LinkedIn sending is not automated

LinkedIn's [rules](https://www.linkedin.com/help/linkedin/answer/a1341387) prohibit software that automates activity or scrapes the site, and accounts that use it get restricted. ReachDesk therefore has no crawler, no auto-sender and no detection evasion, and that is a deliberate product decision rather than a missing feature. See [Compliance](docs/COMPLIANCE.md).

## Quick start

Python 3.10 or newer. Nothing else to install.

```bash
git clone https://github.com/ParsaVictor/mardani.git
```

```bash
cd mardani
```

```bash
python run.py serve
```

Open <http://127.0.0.1:8765/>. Two campaigns are ready: **Consultants in Canada**, and a career campaign you can adapt.

1. Open **Settings** and set the campaign's website, sender name and contact. Messages stay blocked until these are set.
2. Open **Find**, run a search, and add results through **Add** by paste, quick capture or CSV.
3. Press **Prepare today's messages** on **Today**, and work through the list.
4. Rate what you see. After about ten mixed ratings the ranking has learned your taste.

### Automatic email

Set the SMTP account in **Settings**, put the password in the `REACHDESK_SMTP_PASSWORD` environment variable, and enable automatic email on the campaign (Pro plan or higher). While the dashboard runs it prepares and sends every 15 minutes. To use the operating system's scheduler instead:

```bash
python run.py dispatch ca-consultants
```

## Plans

| | Free | Pro | Agency |
|---|---|---|---|
| Campaigns | 1 | 5 | 50 |
| Saved items | 200 | 5,000 | 100,000 |
| Daily limit | 10 | 50 | 100 |
| Automatic email, job boards, CSV export | | ✓ | ✓ |

License keys are Ed25519-signed by the owner, so only the owner can issue them:

```bash
python run.py license issue --plan pro --customer "Acme" --expires 2027-12-31
```

## Testing

```bash
python run.py test
```

CI runs this on Linux and Windows for Python 3.10 and 3.12. The suite includes a held-out benchmark where the keyword rules cannot separate good from bad, so any gain comes from learning. See [Architecture](docs/ARCHITECTURE.md#evidence).

## Contributing and security

See [Contributing](CONTRIBUTING.md) and the [Code of conduct](CODE_OF_CONDUCT.md). Report vulnerabilities privately, as described in the [Security policy](SECURITY.md).

## License

[AGPL-3.0](LICENSE). Commercial licensing is available from the copyright holder. ReachDesk is not legal advice; you are responsible for how you use it.
