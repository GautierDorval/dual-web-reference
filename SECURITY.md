# Security

## Private reporting

Send sensitive reports to [info@pagup.com](mailto:info@pagup.com), the private contact explicitly approved by the owner for this repository. Include the affected edition or code revision, a minimal description and reproduction steps. Do not post credentials, request addresses, raw logs, private source names or conversation histories in a public issue. Send only the minimum evidence needed; do not send a complete private export.

A report is assessed privately. A confirmed disclosure requires an owner decision on correction or withdrawal. Neither deleting a current file nor making a replacement removes copies already obtained by others. No withdrawal is inferred from a synthetic counterexample.

## Design and limits

The public calculation chain uses no secret and makes no network request. Public CI has read-only permissions, pinned actions and no acquisition or publication step. Authenticated acquisition is a separate, explicitly authorized private operation.

Inputs are untrusted: bounded readers reject malformed JSON/CSV, duplicate keys and unsafe archive paths. HTML is escaped and spreadsheet-safe exports remain distinct from canonical CSV. Existing tests describe the protections actually exercised, not universal resistance to all encodings or auxiliary information.

The static presentation uses local assets without telemetry. Measured resources remain **copyable paths**, by owner decision; there is no prefetch, remote preview or automatic validation of their URLs. A reader who manually visits a copied address can create future traffic. The recorded-row denominator is always tied to its closed historical window; it is not an exhaustive web inventory.

A review receipt lives outside the deterministic payload it approves. Its scope is the edition payload and figures; it does not approve an unbounded website or the collection system. A payload change invalidates the receipt. Public availability, a green CI and scientific review are separate states.

The [privacy policy](docs/en/privacy.md) explains combined-release restrictions. GitHub private vulnerability reporting is not claimed to be activated; this repository uses the approved email channel. See [GitHub's distinction between policy and private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
