# Contributing

Contributions to the method, the code and the documentation are welcome once the repository is public.

- Run `python -I -m unittest discover -s tests -t .` and `python -I scripts/dwr.py verify` before proposing a change. Both are offline.
- Never type a measured number in a document: use a generated block (`<!-- dwr:begin KEY -->` / `<!-- dwr:end KEY -->`) filled by `render`.
- Do not change a filter, a rule or a test to reach a desired number. A change of scope, attribution or privacy rule needs a new rules version and, for a published edition, a new revision with its delta.
- English pages use Canadian English; French pages use Canadian French and keep the same meaning and structure as their English counterpart.
- Contributions run in CI without secrets and with read-only permissions. A contribution can never trigger an acquisition or a publication.
