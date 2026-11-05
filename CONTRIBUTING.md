# Contributing

Bug reports and ideas are welcome through [issues](https://github.com/ParsaVictor/mardani/issues). Report security problems privately, as described in [SECURITY.md](SECURITY.md).

## Set up

You need Python 3.10 or newer. The project has no dependencies, so there is nothing else to install.

```bash
git clone https://github.com/ParsaVictor/mardani.git
```

```bash
cd mardani
```

```bash
python run.py test
```

```bash
python run.py serve
```

## Rules for changes

- **Standard library only.** A new dependency needs a strong reason, stated in the pull request.
- **Add a test.** A bug fix needs a test that fails without the fix.
- **Keep safety checks in `service.py` and `channels.py`.** Templates and the dashboard must not be able to bypass them.
- **Never commit real contact data, keys or passwords.** Test data must be clearly fictional.
- **Update the docs** when behaviour changes, and add a line to [CHANGELOG.md](CHANGELOG.md).

## What will not be accepted

LinkedIn auto-sending, crawling or scraping, and anything that evades bot detection, including randomized delays, spun text, fingerprint masking and proxy rotation. [Compliance](docs/COMPLIANCE.md) explains why.

## Code contributions from outside the project

ReachDesk is offered under AGPL-3.0 and also commercially, so outside contributions need a contributor license agreement. That agreement has not been published yet, so please open an issue before writing code. Pull requests from outside contributors can't be merged until it exists.

## Pull requests

1. Branch from `main`.
2. Keep each pull request to one change.
3. Make sure `python run.py test` passes. CI runs it on Linux and Windows, for Python 3.10 and 3.12.
