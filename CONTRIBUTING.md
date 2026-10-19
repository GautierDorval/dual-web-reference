# Contributing

This is a public repository. Contributions can address data errors, documentary corrections or reproducibility problems. Identify the edition and code revision, expected and observed behavior, minimal reproduction and supporting sources. Use the short issue templates; sensitive reports go through [SECURITY.md](SECURITY.md).

Never include credentials, IP addresses, raw request logs, private source names or conversation histories in a public report. Synthetic fixtures should use artificial values. Do not visit measured sites as part of an automated test.

Run the offline commands in [reproduction](docs/en/reproduction.md), including tests, analysis, rendering, build and verification. A successful public run verifies the distributed arithmetic and artifacts; it cannot recreate private collection evidence.

- Compute measured values centrally in `analysis/dwr/metrics.py`; use generated document blocks.
- Preserve frozen editions. Corrections require an identifiable revision and an explained delta; changing scope to improve a result is not acceptable.
- Keep French and English facts, populations, limitations and navigation equivalent.
- Contributor CI uses no private secrets, cannot acquire data and cannot publish.
- Propose a completed, reviewable change. An automated or AI-assisted review is not independent scientific peer review.

Gautier Dorval is responsible for the proposal and publication decisions. AI assistance is used in programming, analysis and technical review, including this correction. These tools are not scientific validators or additional authors of the underlying observations.
