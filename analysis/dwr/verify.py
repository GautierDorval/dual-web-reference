"""verify: replay every offline check on the public repository. No network.

Each check returns (name, passed, detail). The command fails if any check fails.
It regenerates metrics, figures, case pages and generated blocks in memory and
compares them byte for byte with the committed files (determinism and
consistency), and scans every public output for material that must never be
published.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from . import figures as F
from . import frozen, disclosure
from . import gate
from . import pipeline
from . import project
from . import metrics as M
from . import render as R
from . import typo
from .common import DwrError, REPO_ROOT, SITE_IDS, canonical_json, load_json, read_csv, sha256_bytes, sha256_file

# Private names and identifiers live in the private workspace and are read by gate.load_secrets, never written
# here. The patterns are those of the publication gate, so that verify and the gate cannot diverge.
LOCAL_PATH, IPV4, UA, HEX32, HEX40 = gate.LOCAL_PATH, gate.IPV4, gate.USER_AGENT, gate.HEX32, gate.HEX40
SCAN_EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".dwr-work"}
FORBIDDEN_COLUMNS = ("ip", "client_ip", "user_agent", "ua", "cookie", "session", "referrer", "referer", "first_seen",
                     "last_seen", "query_string", "token", "first_date", "last_date")


def tracked_files() -> list[Path]:
    """Every file of the working tree that could be published (source, tests, data, docs, figures with their PNG,
    built site), with no exclusion by file type."""
    out = []
    for path in REPO_ROOT.rglob("*"):
        parts = set(path.relative_to(REPO_ROOT).parts)
        if path.is_file() and not parts & SCAN_EXCLUDED_DIRS:
            out.append(path)
    return sorted(out)


def private_secrets(private_lock: Path | None):
    if not private_lock or not private_lock.is_file():
        return None
    try:
        return gate.load_secrets(private_lock.parent.parent)
    except DwrError:
        return None


class Report:
    def __init__(self):
        self.checks = []
        self.skipped = []

    def add(self, name, passed, detail=""):
        self.checks.append({"check": name, "passed": bool(passed), "detail": detail})

    def skip(self, name, reason):
        self.skipped.append({"check": name, "reason": reason})

    def result(self):
        failed = [c for c in self.checks if not c["passed"]]
        return {"passed": not failed, "checks": len(self.checks), "failed": failed, "skipped": self.skipped,
                "summary": {c["check"]: c["passed"] for c in self.checks}}


def check_catalog(report, edition_dir):
    catalog = load_json(edition_dir / "catalog.json")
    bad = [f["path"] for f in catalog["files"] if sha256_file(edition_dir / f["path"]) != f["sha256"]
           or (edition_dir / f["path"]).stat().st_size != f["bytes"]]
    report.add("catalog_digests_match_files", not bad, ", ".join(bad))
    empties = [f for f in catalog["files"] if f["rows"] == 0]
    report.add("empty_tables_carry_a_reason", all(f["empty_reason"] for f in empties), ", ".join(f["path"] for f in empties))
    dates = catalog["dates"]
    from .dates import window_from_strings
    window = window_from_strings(dates["period_start_inclusive"], dates["period_end_exclusive"])
    entry = next(e for e in load_json(REPO_ROOT / "config" / "editions.json")["editions"] if e["edition_id"] == catalog["edition_id"])
    historical = bool(frozen.entry(catalog["edition_id"]))
    state_free = historical or (not any(k in catalog for k in pipeline.edition_rules.MUTABLE_CATALOG_FIELDS)
                               and not any(k in dates for k in ("published_at", "next_review_target")))
    report.add("observation_dates_valid_and_operational_state_external", state_free
               and dates["period_end_exclusive"] > dates["last_included_date"] == window.last_included.isoformat()
               and dates["latest_available_data_date"] <= dates["last_included_date"], json.dumps(dates)[:200])
    report.add("window_label_and_length_derived_from_bounds", catalog["labels"]["period_fr"] == window.label_fr()
               and catalog["labels"]["period_en"] == window.label_en() and dates["calendar_days"] == window.days,
               catalog["labels"]["period_fr"])
    report.add("rule_versions_match_configuration",
               all(catalog["versions"].get(key) == value for key, value in pipeline.rule_versions(catalog["edition_id"]).items()),
               json.dumps(catalog["versions"])[:200])


def check_tables(report, edition_dir):
    expected = {"consultations.csv": project.CONSULTATION_FIELDS, "resources.csv": project.RESOURCE_FIELDS,
                "links.csv": project.LINK_FIELDS, "resource-summary.csv": project.RESOURCE_SUMMARY_FIELDS,
                "daily-summary.csv": project.DAILY_FIELDS, "actor-summary.csv": project.ACTOR_FIELDS,
                "coverage.csv": project.COVERAGE_FIELDS, "exclusions.csv": project.EXCLUSION_FIELDS,
                "daily-family-summary.csv": project.FAMILY_DAILY_FIELDS}
    problems = []
    for name, fields in expected.items():
        data = (edition_dir / name).read_bytes()
        if b"\r" in data or data.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{name}: CR or BOM")
        header = data.decode("utf-8").split("\n", 1)[0].split(",")
        legacy = tuple(header) == tuple(project.LEGACY_FIELDS.get(name, fields))
        if tuple(header) != tuple(fields) and not legacy:
            problems.append(f"{name}: header differs from schema")
        if any(column in FORBIDDEN_COLUMNS for column in header):
            problems.append(f"{name}: forbidden column")
        schema_root = frozen.rule_path(edition_dir.name, "schemas") if frozen.entry(edition_dir.name) else REPO_ROOT / "schemas"
        if not legacy and name in project.LEGACY_FIELDS:
            schema_root = REPO_ROOT / "schemas/v2"
        schema = load_json(schema_root / name.replace(".csv", ".schema.json"))
        rows = read_csv(edition_dir / name)
        keys = [tuple(row[k] for k in schema["primaryKey"]) for row in rows]
        if len(keys) != len(set(keys)):
            problems.append(f"{name}: duplicate primary key")
        for field in schema["fields"]:
            for row in rows:
                value = row[field["name"]]
                if "enum" in field.get("constraints", {}) and value not in field["constraints"]["enum"]:
                    problems.append(f"{name}: {field['name']} invalid state")
                if field.get("format") == "json-array-of-strings":
                    try:
                        array = json.loads(value)
                        if (not isinstance(array, list) or any(not isinstance(v, str) or not v for v in array)
                                or array != sorted(set(array))):
                            raise ValueError()
                        if field["name"] == "classifier_versions" and any(v in ("unknown", "mixed_epoch_unresolved") for v in array):
                            raise ValueError()
                    except (ValueError, TypeError):
                        problems.append(f"{name}: {field['name']} invalid JSON array")
            if field["type"] == "integer":
                for row in rows:
                    value = row[field["name"]]
                    if value != "" and (not value.isdigit()):
                        problems.append(f"{name}: {field['name']} not a non-negative integer: {value!r}")
                        break
    report.add("tables_match_schemas_utf8_lf_unique_keys", not problems, "; ".join(problems[:6]))


def check_semantics(report, edition_dir):
    resources = read_csv(edition_dir / "resources.csv")
    by_path = {(r["site_id"], r["path"]): r for r in resources}
    llms = [r for r in resources if r["path"] == "/llms.txt"]
    report.add("llms_txt_isolated_in_main_population",
               len(llms) == 3 and all(r["llms_txt"] == "true" and r["main_population"] == "true" for r in llms))
    report.add("robots_and_undeclared_outside_main",
               all(r["main_population"] == "false" for r in resources
                   if r["scope_class"] in ("control_resource", "undeclared_bucket", "operational_descriptor",
                                           "technical_resource", "unresolved_scope")))
    report.add("robots_txt_is_control_resource",
               all(r["scope_class"] == "control_resource" for r in resources if r["path"] == "/robots.txt"))
    consultations = read_csv(edition_dir / "consultations.csv")
    report.add("consultations_edition_grain_only",
               all(r["time_grain"] == "edition" and r["date_utc"] == "" for r in consultations))
    report.add("cells_declare_joint_derivation", all(r["cell_derivation"] == "joint_exact" for r in consultations)
               and load_json(edition_dir / "catalog.json")["source_mode"] == "joint_acquisition")
    report.add("unknown_never_becomes_provider_origin",
               not any(r["stored_identity_tier"] == "provider_origin_verified_actor"
                       and (r["actor_family"] in ("unknown", "generic-automation") or r["actor_name"] in ("unknown", "cloudflare-verified-bot"))
                       for r in consultations))
    report.add("initiation_never_inferred",
               all(r["initiation_provenance"] == "unknown" and r["initiation_evidence_status"] == "not_established"
                   for r in consultations))
    daily = read_csv(edition_dir / "daily-summary.csv")
    report.add("daily_outputs_carry_no_path_or_actor",
               not any(column in ("path", "actor_name", "resource_id") for column in (daily[0].keys() if daily else [])))
    isolated = isolated_protected_daily_groups(consultations, read_csv(edition_dir / "resources.csv"), daily,
                                               load_json(frozen.rule_path(edition_dir.name, "small-cell-policy.json")))
    report.add("protected_strata_combined_in_daily_outputs", not isolated["detailed_protected_rows"],
               f"{isolated['detailed_protected_rows']} detailed protected daily rows")
    report.add("historical_monthly_path_count_threshold_only", not isolated["groups_below_minimum"],
               "; ".join(f"{s} {p}: {n} paths" for s, p, n in isolated["groups_below_minimum"]))
    family = read_csv(edition_dir / "daily-family-summary.csv")
    resources = {r["resource_id"]: r for r in read_csv(edition_dir / "resources.csv")}
    automated = sum(int(r["request_count"]) for r in consultations
                    if resources[r["resource_id"]]["main_population"] == "true" and r["http_method"] == "GET"
                    and r["http_status"] == "200" and r["stored_identity_tier"] == "provider_origin_verified_actor"
                    and r["actor_role"] in ("ai_training", "ai_search"))
    report.add("heat_map_built_from_joint_cells_and_reconciled",
               bool(family) and sum(int(r["request_count"]) for r in family) == automated
               and all(r["actor_role"] in ("ai_training", "ai_search") for r in family))
    if frozen.entry(edition_dir.name):
        report.add("historical_daily_and_edition_totals_agree",
                   sum(int(r["request_count"]) for r in daily) == sum(int(r["request_count"]) for r in consultations)
                   == sum(int(r["aggregate_count"]) for r in read_csv(edition_dir / "coverage.csv")))
    else:
        policy = load_json(REPO_ROOT / "config/small-cell-policy.json")
        decision = disclosure.assess(disclosure.tables(edition_dir), disclosure.inventory(), policy)
        report.add("combined_disclosure_gate", decision["allowed"], ";".join(decision["reasons"]))
        report.add("daily_nonprotected_totals_match_edition_cells",
                   sum(int(r["request_count"]) for r in daily) ==
                   sum(int(r["request_count"]) for r in consultations if not disclosure.protected(r, policy)))
        report.add("withheld_coverage_is_null_not_zero", all(r[k] == "" for r in read_csv(edition_dir / "coverage.csv") for k in disclosure.COVERAGE_COUNTS))
    from .public_checks import reconcile_tables
    for name, passed in reconcile_tables(edition_dir).items():
        report.add(name, passed)
    actors = read_csv(edition_dir / "actor-summary.csv")
    attribution = load_json(frozen.rule_path(edition_dir.name, "attribution-rules.json"))["assessments"]
    report.add("stored_tiers_kept_and_assessed_separately",
               all(r["attribution_assessment"] == attribution[r["stored_identity_tier"]]["attribution_assessment"] for r in actors))
    under_review = {t for t, spec in attribution.items() if spec["depends_on_cloudflare_predicate"]}
    report.add("predicate_dependent_levels_not_eligible",
               all(not attribution[t]["eligible_for_main_population"] for t in under_review))
    coverage = read_csv(edition_dir / "coverage.csv")
    catalog = load_json(edition_dir / "catalog.json")
    report.add("every_day_of_the_window_has_a_coverage_row",
               len(coverage) == catalog["dates"]["calendar_days"] and len({r["date_utc"] for r in coverage}) == len(coverage))
    report.add("partial_reports_and_v3_gaps_kept",
               all(r["coverage_status"] in ("partial_declared", "complete_declared", "observation_unavailable", "coverage_unknown") for r in coverage)
               and all(r["aggregate_minus_v3"] == "" or r["aggregate_minus_v3"].lstrip("-").isdigit() for r in coverage))
    report.add("one_snapshot_per_day_no_double_count", all(r["snapshots_for_date"] == "1" for r in coverage))
    links = read_csv(edition_dir / "links.csv")
    report.add("links_only_snapshot_relations", all(r["relation_type"] in (
        "html_anchor", "markdown_link", "json_reference", "sitemap_entry", "declared_relation", "plain_url_mention") for r in links))
    checks = load_json(edition_dir / "case-checks.json")
    report.add("case_snapshot_verification_receipt_declares_success", checks["all_verified"])


def isolated_protected_daily_groups(consultations, resources, daily, policy) -> dict:
    """Historical structural check only: monthly path count does not prove non-reconstruction.
    Kept to reproduce B1/B2; new diffusion uses disclosure.assess.
    """
    roles = set(policy["protected_strata"]["actor_roles"])
    tiers = set(policy["protected_strata"]["stored_identity_tiers"])
    group = policy["daily_protected_group"]
    by_key = {(r["site_id"], r["path"]): r for r in resources}
    paths = defaultdict(set)
    for r in consultations:
        if (r["actor_role"] in roles or r["stored_identity_tier"] in tiers) and int(r["request_count"]) > 0:
            paths[(r["site_id"], project.population_of(
                {k: _bool_field(v) if k == "main_population" else v for k, v in by_key[(r["site_id"], r["path"])].items()}))].add(r["path"])
    detailed = sum(1 for r in daily if (r["actor_role"] in roles or r["stored_identity_tier"] in tiers))
    malformed = sum(1 for r in daily if (r["actor_role"] == group["label"]) != (r["stored_identity_tier"] == group["label"])
                    or (r["actor_role"] == group["label"] and (r["http_method"], r["http_status"]) != (group["any"], group["any"])))
    present = {(r["site_id"], r["population"]) for r in daily if r["actor_role"] == group["label"] and int(r["request_count"]) > 0}
    below = sorted((site, population, len(paths.get((site, population), ())))
                   for site, population in present
                   if population not in group["single_path_populations"]
                   and len(paths.get((site, population), ())) < group["minimum_paths"])
    return {"detailed_protected_rows": detailed + malformed, "groups_below_minimum": below}


def _bool_field(value) -> bool:
    return value in (True, "true", "True", "1")


def check_metrics(report, edition_dir):
    recomputed = canonical_json({"schema_version": "dwr-metrics/1.0.0", "edition_id": edition_dir.name, **M.compute(edition_dir)})
    report.add("metrics_reproducible", recomputed == (edition_dir / "metrics.json").read_text(encoding="utf-8"))
    metrics = {m["metric_id"]: m for m in load_json(edition_dir / "metrics.json")["metrics"]}
    value = lambda key: metrics[key]["value"]
    report.add("llms_plus_other_equals_total", value("main.llms_get200") + value("main.other_get200") == value("main.get200"))
    report.add("sites_add_up_to_total", sum(value(f"main.site.{s}.get200") for s in SITE_IDS) == value("main.get200"))
    report.add("share_is_ratio_of_same_selection",
               ((value("main.get200") == 0 and value("main.other_share") is None) or (value("main.get200") > 0 and value("main.other_share") is not None and abs(value("main.other_share") - value("main.other_get200") / value("main.get200")) < 1e-6)))
    report.add("pairs_counted_on_pairs", sum(value(f"main.site.{s}.site_path_pairs") for s in SITE_IDS) == value("main.site_path_pairs")
               and value("main.site_path_pairs") <= len(read_csv(edition_dir / "resources.csv")))
    report.add("scope_delta_explained",
               value("historical.provider_ai.get200") - value("main.get200") == value("main.scope_delta.provider_ai_get200_excluded")
               and sum(m["value"] for k, m in metrics.items() if k.startswith("scope_delta.") and k.split(".")[1] not in (
                   "control_resource", "undeclared_bucket")) == value("main.scope_delta.provider_ai_get200_excluded"))
    reconciliation = load_json(edition_dir / "reconciliation.json")
    report.add("historical_reconciliation_receipt_declares_match", reconciliation["historical_figures"]["all_match"])
    report.add("private_joint_reconciliation_receipt_declares_consistency", reconciliation["joint_aggregate_vs_exports"]["all_consistent"])
    report.add("daily_series_and_roles_add_up_to_total",
               value("main.daily.sum_check") == value("main.get200") - value("main.role.user_initiated_fetch.get200")
               and sum(value(f"main.role.{r}.get200") for r in ("ai_training", "ai_search", "user_initiated_fetch")) == value("main.get200")
               and value("main.sensitivity.without_user_fetch.get200") == value("main.get200") - value("main.role.user_initiated_fetch.get200"))
    not_available = [k for k, m in metrics.items() if m["status"] == "not_available"]
    report.add("not_available_metrics_have_reason", all(metrics[k].get("reason") for k in not_available), ", ".join(not_available))


def check_rendering(report, edition_id):
    historical = frozen.verify(edition_id)
    if historical:
        report.add("historical_figures_original_bytes_preserved", True, str(historical["files"]))
        return
    edition = R.Edition(edition_id)
    directory = REPO_ROOT / "figures" / edition_id
    registry = load_json(edition.dir / "figures.json")
    catalog_dates = edition.catalog["dates"]
    incomplete = []
    for figure_id, function, _, extra in R.figure_jobs(edition):
        _, rows = R.render_figure(edition, function, extra, "en", False)
        if F.table_csv(rows) != (directory / f"{figure_id}.csv").read_text(encoding="utf-8"):
            incomplete.append(figure_id)
    report.add("figure_tables_are_complete_wide_tables", not incomplete, ", ".join(incomplete))
    mismatched, missing_meta, unsafe = [], [], []
    for figure in registry["figures"]:
        for name, info in figure["files"].items():
            text = (REPO_ROOT / info["path"]).read_text(encoding="utf-8")
            if sha256_bytes(text.encode("utf-8")) != info["sha256"]:
                mismatched.append(name)
            if "<script" in text or "href=\"http" in text or "xlink:href=\"http" in text:
                unsafe.append(name)
            needs = [edition_id, "UTC", f"{catalog_dates['period_end_exclusive']}T00:00:00Z",
                     catalog_dates["extracted_at"]["start"][:10], f"data/editions/{edition_id}/"]
            # Narrow layouts wrap long paths over several visible text nodes.
            # Check their visible characters, not a contiguous raw XML substring.
            from xml.etree import ElementTree
            svg_root = ElementTree.fromstring(text)
            visible = "".join("".join(node.itertext()) for node in svg_root.iter("{http://www.w3.org/2000/svg}text"))
            visible = re.sub(r"\s+", "", visible)
            if not all(re.sub(r"\s+", "", token) in visible for token in needs) or "<desc" not in text:
                missing_meta.append(name)
    report.add("figure_files_match_registry", not mismatched, ", ".join(mismatched))
    report.add("figures_carry_dates_edition_source_and_alt", not missing_meta, ", ".join(missing_meta))
    report.add("figures_have_no_script_or_external_reference", not unsafe, ", ".join(unsafe))
    differences = []
    for figure_id, function, _, extra in R.figure_jobs(edition):
        for lang in ("en", "fr"):
            for compact in (False, True):
                generated, _ = R.render_figure(edition, function, extra, lang, compact)
                if lang == "fr":
                    generated = typo.fr(generated)
                name = f"{figure_id}.{lang}{'.compact' if compact else ''}.svg"
                if generated != (directory / name).read_text(encoding="utf-8"):
                    differences.append(name)
    report.add("all_canonical_figure_variants_recomputed", not differences, ", ".join(differences))
    table = read_csv(directory / "G02.csv")
    total = next(r for r in table if r["site_id"] == "all_sites")
    svg_en = (directory / "G02.en.svg").read_text(encoding="utf-8")
    report.add("legend_numbers_recomputed_from_table",
               int(total["total_get200"]) == edition.m("main.get200") and f"total {total['total_get200']}" in svg_en)
    case_pages = R.render_cases(edition, write=False)
    report.add("case_pages_match_data", all((REPO_ROOT / name).read_text(encoding="utf-8") == text
                                            for name, text in case_pages.items()))
    stale = R.render_documents(edition, write=False)
    report.add("generated_blocks_up_to_date", not stale, ", ".join(stale))
    en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    fr = (REPO_ROOT / "README.fr.md").read_text(encoding="utf-8")
    numbers = lambda text: sorted(re.sub(r"[\u202f\u00a0,]", "", n) for n in re.findall(
        r"\*\*([\d\u202f\u00a0,.]+)", R.BLOCK.search(text[text.index("dwr:begin headline") - 5:]).group("body")))
    report.add("readme_en_fr_same_headline_numbers", numbers(en) == numbers(fr), f"{numbers(en)} vs {numbers(fr)}")


def check_french(report):
    files = [REPO_ROOT / "README.fr.md"] + sorted((REPO_ROOT / "docs" / "fr").glob("*.md")) + sorted(
        (REPO_ROOT / "cases").glob("*/README.fr.md"))
    dashes = [str(p.relative_to(REPO_ROOT)) for p in files if typo.dash_violations(p.read_text(encoding="utf-8"))]
    report.add("french_has_no_en_or_em_dash", not dashes, ", ".join(dashes))
    unstable = [str(p.relative_to(REPO_ROOT)) for p in files
                if typo.fr(p.read_text(encoding="utf-8")) != p.read_text(encoding="utf-8")]
    report.add("french_typography_applied", not unstable, ", ".join(unstable))
    unspaced = [str(p.relative_to(REPO_ROOT)) for p in files if typo.punctuation_violations(p.read_text(encoding="utf-8"))]
    report.add("french_punctuation_has_required_spacing", not unspaced, ", ".join(unspaced))
    escaped = [str(p.relative_to(REPO_ROOT)) for p in files if re.search(r"\\u00[ce][0-9a-f]", p.read_text(encoding="utf-8"))]
    report.add("french_accents_not_escaped", not escaped, ", ".join(escaped))


def check_privacy(report, private_lock: Path | None):
    """The working tree, file by file, through the same examination as the publication gate (gate.scan_bytes).
    The gate itself (dwr.py publication-gate) also covers history, commit messages and file types of the branch."""
    secrets = private_secrets(private_lock)
    exact, patterns = [], []
    for index, path in enumerate(tracked_files()):
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        categories = set(gate.scan_bytes(rel, path.read_bytes(), secrets)) | set(gate.name_findings(rel, secrets))
        label = gate.safe_path(rel, index, secrets)
        for category in sorted(categories):
            (exact if category in gate.EXACT_CATEGORIES else patterns).append(f"{label}: {category}")
    if secrets is None:
        report.skip("no_private_terms_in_any_tracked_file",
                    "needs lock/private-terms.json, lock/acquisition-config.json and lock/private-lock.json")
    else:
        report.add("no_private_terms_in_any_tracked_file", not exact, "; ".join(exact[:8]))
    report.add("no_private_identifiers_ips_or_user_agents_in_public_files", not patterns, "; ".join(patterns[:8]))
    policy = load_json(REPO_ROOT / "config" / "small-cell-policy.json")
    report.add("corrected_policy_has_explicit_limited_contract", policy["policy_id"] == "small-cell-policy/2.0.0" and not policy["fixed_before_results"] and "withheld" in policy["numeric_suppression"])


def check_maintenance(report):
    latest = load_json(REPO_ROOT / "data" / "latest.json")
    editions = load_json(REPO_ROOT / "config" / "editions.json")["editions"]
    from .edition_rules import approved, latest_pointer
    report.add("declared_approvals_have_valid_receipts",
               all(e.get("reference_release_status") != "approved" or approved(e) for e in editions))
    report.add("latest_points_only_to_reviewed_publication", latest["latest_published_edition"] == latest_pointer(editions))
    status = load_json(REPO_ROOT / "data" / "status.json")
    report.add("status_not_realtime_and_automation_inactive",
               status["realtime"] is False and all(v != "active" for k, v in status["automation"].items() if not k.startswith("label")))
    workflows = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    problems = []
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        if "secrets." in text or "pull_request_target" in text or re.search(r"^\s*schedule\s*:", text, re.M):
            problems.append(f"{workflow.name}: secret, pull_request_target or schedule")
        if "contents: read" not in text or re.search(r"(contents|pages|id-token|actions)\s*:\s*write", text):
            problems.append(f"{workflow.name}: permissions")
        for use in re.findall(r"uses:\s*([^\s]+)", text):
            if not re.search(r"@[0-9a-f]{40}$", use):
                problems.append(f"{workflow.name}: unpinned {use}")
        for site in SITE_IDS:
            if re.search(r"(curl|wget|Invoke-WebRequest).*" + re.escape(site), text):
                problems.append(f"{workflow.name}: fetches {site}")
    report.add("ci_offline_pinned_read_only_without_secrets", bool(workflows) and not problems, "; ".join(problems))
    templates = sorted((REPO_ROOT / "config" / "workflow-templates").glob("*"))
    report.add("schedules_are_inactive_templates", all(p.name.endswith(".yml.example") for p in templates) and bool(templates))


def check_code(report):
    network_modules = ("urllib.request", "http.client", "socket", "requests", "httpx")
    offenders = []
    for path in (REPO_ROOT / "analysis" / "dwr").glob("*.py"):
        if path.name == "acquire.py":
            continue
        text = path.read_text(encoding="utf-8")
        for module in network_modules:
            if re.search(rf"^\s*(import|from)\s+{re.escape(module)}\b", text, re.M):
                offenders.append(f"{path.name}: {module}")
    report.add("public_stages_have_no_network_code", not offenders, ", ".join(offenders))


def check_site(report):
    dist = REPO_ROOT / "site" / "dist"
    if not dist.is_dir():
        report.add("site_built", False, "run build-site first")
        return
    broken, external, unspaced = [], [], []
    for page in dist.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        if page.relative_to(dist).parts[0] == "fr" and typo.html_punctuation_violations(text):
            unspaced.append(page.relative_to(dist).as_posix())
        for match in re.findall(r'<script[^>]+src="([^"]+)"|<link[^>]+href="([^"]+)"', text):
            target = match[0] or match[1]
            if target.startswith(("http://", "https://", "//")):
                external.append(f"{page.relative_to(dist)}: {target}")
        for href in re.findall(r'(?:href|src|srcset)="([^"#]+)', text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            if not (page.parent / href).resolve().exists():
                broken.append(f"{page.relative_to(dist)} -> {href}")
    report.add("french_site_punctuation_has_required_spacing", not unspaced, "; ".join(unspaced))
    report.add("site_has_no_external_resources", not external, "; ".join(external[:5]))
    report.add("site_internal_links_resolve", not broken, "; ".join(broken[:8]))


def cmd(edition_id: str, private_lock: Path | None = None) -> dict:
    report = Report()
    # Stop before any generic scanner follows an unadmitted path or prints its name.
    from . import distribution, site_build
    try:
        distribution.check_sources(REPO_ROOT)
        report.add("distribution_source_exact_set_and_bytes", True)
        plan, _ = site_build.output_plan(edition_id)
        distribution.check_output(REPO_ROOT / "site/dist", plan)
        report.add("distribution_site_exact_set_and_bytes", True)
    except DwrError as error:
        report.add("distribution_closed_contract", False, error.code)
        return report.result()
    except (OSError, ValueError, KeyError, TypeError):
        report.add("distribution_closed_contract", False, "distribution_contract_unreadable")
        return report.result()
    edition_dir = REPO_ROOT / "data" / "editions" / edition_id
    for check in (lambda: check_catalog(report, edition_dir), lambda: check_tables(report, edition_dir),
                  lambda: check_semantics(report, edition_dir), lambda: check_metrics(report, edition_dir),
                  lambda: check_rendering(report, edition_id), lambda: check_french(report),
                  lambda: check_privacy(report, private_lock), lambda: check_maintenance(report),
                  lambda: check_code(report), lambda: check_site(report)):
        try:
            check()
        except Exception as error:  # a crash in a check is a failed check, never a pass
            report.add(f"check_crashed:{getattr(check, '__name__', 'check')}", False, f"{type(error).__name__}: {error}")
    return report.result()
