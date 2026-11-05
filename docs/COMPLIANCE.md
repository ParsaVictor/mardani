# Compliance

This is engineering documentation, not legal advice. Have a Canadian lawyer review your use before running a commercial campaign. The sources behind this page are mostly law-firm summaries, some several years old, so confirm against the current statute and regulator guidance.

## LinkedIn

LinkedIn prohibits third-party software that scrapes its site or automates activity on it, and says accounts using such tools may be restricted or shut down ([Prohibited software and extensions](https://www.linkedin.com/help/linkedin/answer/a1341387), [Automated activity](https://www.linkedin.com/help/linkedin/answer/90586)).

| ReachDesk does | ReachDesk does not |
|---|---|
| Build search links that you open yourself | Crawl, browse or fetch LinkedIn |
| Read text you select, when you click a bookmark | Read LinkedIn pages in the background |
| Import LinkedIn's official data export | Call private LinkedIn APIs |
| Copy a message and open a profile on your click | Press send or connect, or inject anything into LinkedIn's pages |

**There is no stealth mode, on purpose.** Randomized delays, spun text, fingerprint masking and proxy rotation exist to get around enforcement, and none of them will be added. Selling them would also make customers' accounts the product's failure mode. Daily caps exist to protect message quality and the reader's attention.

The quick-capture bookmarklet and copy-and-open flow are designed as manual actions, but LinkedIn's rules are LinkedIn's to interpret. Using them is your decision.

## Canada's anti-spam law (CASL)

Sources: [Mondaq overview](https://www.mondaq.com/canada/advertising-marketing-branding/738840/canadas-anti-spam-law), [Torys on the 2020 Federal Court of Appeal decision](https://www.torys.com/en/our-latest-thinking/publications/2020/06/fca-confirms-casl-is-constitutional-but-limits-business-communications-exemption).

As summarized by those sources, a commercial electronic message includes email and direct messages on social networks, generally needs consent, and must identify the sender and offer an easy unsubscribe. Implied consent through "conspicuous publication" is narrow: the address must be published by the person, without a statement declining messages, and the message must relate to their business role.

How the product applies this:

| Rule | Enforcement |
|---|---|
| Consent basis recorded per contact | `consent_basis`, attested by the operator |
| No commercial message without a basis | `service.skip_reason` blocks it as `no_consent_basis` |
| Automatic email only with a qualifying basis | `AUTO_EMAIL_BASES`, checked when queueing and again at send time |
| Sender identity, contact and opt-out in every commercial message | Template lint blocks a template without them |
| Connection note carries no link or pitch | Template lint |
| Opt-out honoured everywhere | Suppression by person across all campaigns, re-checked at send time |
| Records | Audit log of imports, exports, sends, suppressions and erasures |

**Known limits, for your lawyer:**

- `existing_connection` is treated as permitting a LinkedIn message after someone accepts a request. Accepting a connection may not amount to consent under CASL.
- `published_business_contact` is your own attestation. The software does not verify it.
- Opt-out is by reply, and you record it by pressing **Opted out**. Inbound replies are not processed automatically yet. Act on them promptly.

## Privacy

- Data stays in a local SQLite file, one per workspace. The app binds to loopback only.
- **Delete data** erases a contact and keeps only an opaque key so they are not contacted again. A LinkedIn-derived key contains the profile slug, and an email-derived key contains the address: hashing these is on the roadmap.
- Before selling a hosted version, add a privacy policy, a data processing agreement, and a PIPEDA and GDPR review.
- The SMTP password is read from the environment and never stored. Signing keys live outside the repository.
