# Roadmap

Principle: **be the best tool for the human who sends, and automate everything that is not a platform violation.** Each stage has an exit test, so progress is decided by measurements rather than by feature count.

## Stage 0: Foundation (built)

Local dashboard in English and Persian, campaigns, paste, capture and CSV intake, public job boards, intent and name parsing, learning ranker with reasons, connect-first flow, automatic email with consent gates, A/B variants, suppression and erasure, signed license tiers, automated tests and CI.

## Stage 1: Prove it with real use (weeks 1 to 4)

| Work | Exit test |
|---|---|
| Employer pilot: 100 consultants in Canada through the connect-first flow | Measured acceptance and reply rates, by variant |
| Parsa's job search: rate 50 jobs and posts | Saved items rated 4+ stars exceed 50%, and recent accuracy beats early accuracy on real ratings |
| Time each send | Median under 30 seconds per contact |
| Lawyer review of `docs/COMPLIANCE.md` | Written sign-off, or a fixed list of changes |

Do not build Stage 2 until these numbers exist.

## Stage 2: Remove the remaining manual work (months 2 to 3)

- **Inbox sync over IMAP.** Detect replies and "stop" automatically, so opt-outs and reply metrics stop depending on a click.
- **More lawful sources.** Public regulator registers where their terms allow it (for example CICC's register to verify RCICs), CSV exports from data vendors with documented consent practices, and company websites' published business contacts.
- **Sending quality.** SPF and DKIM checks, bounce handling, and warnings when a domain's reputation is at risk.
- **Optional LLM polish, off by default.** Bring your own key, run only on the top-ranked contacts, and cache results, keeping the base product free of token costs.
- **Hash suppression keys.**

## Stage 3: A product people pay for (months 3 to 6)

- Packaged installers for Windows and macOS.
- Payment and automatic license delivery.
- Team workspaces and shared suppression lists for agencies.
- CRM export and webhooks (HubSpot, Pipedrive).
- Ready-made campaign packs by industry and language.

## Stage 4: Hosted and global (months 6 to 12)

- Hosted SaaS with tenant isolation, encryption at rest, and SOC 2 readiness.
- Region-aware compliance profiles: CASL, GDPR, CAN-SPAM, and more.
- Official platform integrations wherever the platform offers them, including becoming a LinkedIn partner if eligible.
- A shared, opt-in, privacy-preserving benchmark of what earns replies, which competitors built on automation cannot easily copy.

## Other uses of the same engine

Recruiting, partnership development, grant and tender discovery, freelance lead finding, and investor outreach: each needs only a campaign pack and intake sources.

## Decisions kept closed

No LinkedIn auto-sending, no crawler, no detection evasion. Reopen only if LinkedIn offers an official API that permits it.
