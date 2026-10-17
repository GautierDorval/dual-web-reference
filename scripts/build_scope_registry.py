"""Build config/scope-registry.csv from reviewed content proposals (private input).

Usage: python -I scripts/build_scope_registry.py <private-root>

The proposals are content reviews of the source snapshots (one CSV per site under
<private-root>/sources/<site>/scope-proposals.csv). This script applies the
precedence of config/scope-rules.json: R01 to R03 are mechanical and override any
proposal; R04 keeps the content-based class; R05 marks content not found. The
output is the versioned registry; it is reviewed and edited as a public file
afterwards, and qualify never reads the proposals.
"""

import csv
import json
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITES = ("gautierdorval.com", "pagup.com", "better-robots.com")
COLUMNS = ("site_id", "path", "scope_class", "scope_rule_id", "family", "format", "language", "role_en", "role_fr",
           "declares_canonical_source", "mentions_runtime_or_mcp", "found_in_snapshot", "review_status", "justification")
TECHNICAL = re.compile(r"(^/sitemap[^/]*\.xml$)|(/security\.txt$)|(^/version\.json$)|(^/governance-fingerprint\.json$)")
CONTENT_CLASSES = {"core_governance", "discovery_index", "supporting_documentation", "operational_descriptor"}
# A source file of a site repository (code or build configuration). The word boundary keeps .json, a public format,
# out of the .js match.
SOURCE_FILE = re.compile(r"[\w./@-]*\.(?:ts|astro|mjs|cjs|js|toml|jsonc|py)\b(?::\d+(?:-\d+)?)?")
# A path inside a site repository (not a served URL path, which starts with a slash).
SOURCE_LAYOUT = re.compile(r"(?<![\w/.])(?:docs|src|public|content|snapshot|deploy-config)/[\w./-]*[\w-](?::\d+(?:-\d+)?)?")
PRIVATE_REPOSITORIES: tuple[str, ...] = ()
COMMIT_LIKE = re.compile(r"\b(?:commit\s+)?[0-9a-f]{7,40}\b")


def public_justification(text: str) -> str:
    """Keep the content-based reason only: no private repository name, source file or build detail."""
    reason = " ".join(text.split()).split(" | ")[0]
    for name in PRIVATE_REPOSITORIES:
        reason = reason.replace("GautierDorval/" + name, "source repository").replace(name, "source repository")
    reason = SOURCE_FILE.sub("source file", reason)
    reason = reason.replace("Not in docs/public", "Not a static file of the site sources")
    reason = SOURCE_LAYOUT.sub("a site source file", reason)
    reason = COMMIT_LIKE.sub(lambda m: "a source commit" if not m.group(0).isdigit() else m.group(0), reason)
    return reason[:400]


def boolean(value: str) -> str:
    value = (value or "").strip().lower()
    return "true" if value in ("true", "yes") else "false" if value in ("false", "no") else ""


def main(private_root: str) -> int:
    global PRIVATE_REPOSITORIES
    terms = json.loads((Path(private_root) / "lock" / "private-terms.json").read_text(encoding="utf-8"))
    PRIVATE_REPOSITORIES = tuple(terms["private_repository_names"])
    rows, overrides = [], []
    for site in SITES:
        path = Path(private_root) / "sources" / site / "scope-proposals.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            proposals = list(csv.DictReader(stream))
        seen = set()
        for proposal in proposals:
            if proposal["domain"] != site:
                raise SystemExit(f"domain mismatch in {path}")
            key = proposal["path"]
            if key in seen:
                raise SystemExit(f"duplicate path {site}{key}")
            seen.add(key)
            proposed = proposal["proposed_scope_class"]
            found = boolean(proposal["found_in_snapshot"])
            if key == "/robots.txt":
                scope, rule = "control_resource", "R01"
            elif key == "/.well-known/__undeclared__":
                scope, rule = "undeclared_bucket", "R02"
            elif TECHNICAL.search(key) or (proposed == "technical_resource" and found == "true"):
                scope, rule = "technical_resource", "R03"
            elif found != "true":
                scope, rule = "unresolved_scope", "R05"
            elif proposed in CONTENT_CLASSES:
                scope, rule = proposed, "R04"
            else:
                scope, rule = "unresolved_scope", "R05"
            if scope != proposed:
                overrides.append(f"{site}{key}: proposed {proposed} -> {scope} ({rule})")
            rows.append({
                "site_id": site, "path": key, "scope_class": scope, "scope_rule_id": rule,
                "family": proposal["family"].strip().lower(), "format": proposal["format"].strip().lower(),
                "language": proposal["language"].strip(), "role_en": proposal["role_en"].strip(),
                "role_fr": proposal["role_fr"].strip(),
                "declares_canonical_source": boolean(proposal["declares_canonical_source"]),
                "mentions_runtime_or_mcp": boolean(proposal["mentions_runtime_or_mcp"]),
                "found_in_snapshot": found,
                "review_status": "rule_based" if rule in ("R01", "R02") or (rule == "R03" and TECHNICAL.search(key)) else
                                 "content_reviewed_in_snapshot" if rule in ("R03", "R04") else "content_not_found",
                "justification": public_justification(proposal["justification"]),
            })
    rows.sort(key=lambda r: (SITES.index(r["site_id"]), r["path"]))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (ROOT / "config" / "scope-registry.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="\n")
    print(f"{len(rows)} registry rows; {len(overrides)} rule overrides")
    for line in overrides:
        print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
