# Security policy

## Reporting a vulnerability

Please don't open a public issue. Use [private vulnerability reporting](https://github.com/ParsaVictor/mardani/security/advisories/new) instead, with the steps to reproduce the problem and its likely impact.

This is a small project maintained by one person, so no response time is guaranteed.

## Supported versions

Only the latest release receives security fixes.

## What is in scope

ReachDesk runs on your own computer and binds to `127.0.0.1`. These are the most useful reports:

- A website you visit being able to read or change the local dashboard's data
- Imported contact data running as script in the dashboard
- A setting or imported file making the app send requests to arbitrary hosts
- A message reaching someone who opted out
- A way to forge license keys

Removing plan checks from your own copy of the source is not a vulnerability. [Business model](docs/BUSINESS.md) explains why.

## Protecting your own data

- `~/.reachdesk/workspace.db` holds your contacts, so treat it as confidential.
- `~/.reachdesk/license_signing_key` issues license keys. Back it up privately and never publish it.
- Set the SMTP password through the `REACHDESK_SMTP_PASSWORD` environment variable.
