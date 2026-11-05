# Changelog

Notable changes to ReachDesk. Versions follow [semantic versioning](https://semver.org/).

## Unreleased

Nothing yet.

## 0.1.0 (2026-11-04)

First public release.

### Added

- Local dashboard in English and Persian, with campaigns.
- Intake by paste, one-click capture of selected text, LinkedIn's official `Connections.csv` and generic CSV.
- Public job boards: Greenhouse, Lever, Ashby and Arbeitnow.
- First-name extraction, and detection of intent and flags in English, French and Persian.
- A local ranking model that learns from star ratings and reasons, with no LLM or API key.
- Connect-first sequencing for LinkedIn, with one-click human sending.
- Automatic email for contacts with a recorded basis, with daily caps, a 90-day cooldown, opt-out and erasure.
- A/B message variants chosen by Thompson sampling.
- Free, Pro and Agency plans with Ed25519-signed license keys.
- Automated tests and CI on Linux and Windows.

### Fixed

- Refused requests could lose their 403 reply on Windows, because the server closed the connection without reading the request body.

### Not tested yet

- Sending through a real SMTP server. Tests use a simulated one.
- Reply rates with real contacts, and legal review.
