# Security

## Reporting

Please report a vulnerability or an accidental disclosure (a private identifier, an IP address, a user agent, a credential) privately to the repository owner rather than in a public issue. Disclosures are handled as documented exceptions: the affected edition receives a corrected revision, and the reason is recorded.

## Design rules

- The public repository never holds a database credential, an API token or a private source. Public CI runs offline with `contents: read`, no secrets, pinned actions and no step that contacts the measured sites.
- The authenticated, read-only acquisition runs only in a private environment, after an explicit decision, and only with the reviewed SELECT queries of `analysis/dwr/acquire.py` (dry run by default).
- Fetched files, Markdown, JSON, CSV and labels are untrusted data: inputs are size-, depth- and shape-checked; paths are validated; archives are opened with traversal, link and size limits; HTML is escaped in tables, legends and pages; a spreadsheet-safe variant neutralizes formulas.
- The static presentation loads no external script, font or analytics, and shows paths of the measured sites as text, so browsing it sends no request to them.
- A review approves a candidate identified by digest (`SHA256SUMS.txt`, which never includes itself). Any later change invalidates the approval.
