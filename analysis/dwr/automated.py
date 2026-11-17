"""Closed automated-only contract, for private qualification, never publication.

Filtering precedes every observation-derived surface. Categorical coverage comes
from admitted archive evidence, not from the presence or count of rejected rows.
The synthetic proposal and historical disclosure policy remain separate.
"""
from collections import defaultdict
from copy import deepcopy
from . import dates, measurement
from .common import DwrError, SITE_IDS, canonical_json, validate_path, validate_site

CONTRACT = "dwr-automated/1.0.0"
ROLES = ("ai_training", "ai_search")
TIER = "provider_origin_verified_actor"
SELECTION = {"population": "main_documentary", "http_method": "GET", "http_status": 200,
             "stored_identity_tier": TIER, "actor_roles": list(ROLES)}
ON_DEMAND = {"option": "U0", "suppression_status": "withheld_not_zero", "request_count": None,
             "initiation_provenance": "unknown"}
RESIDUAL = ["A sole selected automated actor can be inferred from its role.",
            "A single-resource family can reveal that automated resource's daily count.",
            "Historical releases and unknown auxiliary data remain accessible.",
            "No universal non-reconstruction or person-anonymity guarantee."]

# These ordered fields are the canonical schema for the new contract. Historical
# schemas and readers are not extended. schema_document() exports JSON Schema.
TABLES = {
    "consultations": ("site_id", "path", "family", "actor_family", "actor_name", "actor_role", "request_count"),
    "resources": ("site_id", "path", "family"),
    "resource_summary": ("site_id", "path", "family", "request_count"),
    "actors": ("site_id", "actor_family", "actor_name", "actor_role", "request_count"),
    "families": ("family", "actor_role", "request_count"),
    "daily": ("date_utc", "site_id", "actor_role", "request_count", "observation_status", "coverage_status"),
    "family_daily": ("date_utc", "family", "actor_role", "request_count", "observation_status", "coverage_status"),
    "coverage": ("date_utc", "archive_status", "observation_status", "source_qualification", "coverage_status",
                 "evidence_status", "request_count", "suppression_status"),
}
FILENAMES = {"consultations": "consultations.csv", "resources": "resources.csv",
             "resource_summary": "resource-summary.csv", "actors": "actor-summary.csv",
             "families": "family-summary.csv", "daily": "daily-summary.csv",
             "family_daily": "daily-family-summary.csv", "coverage": "coverage.csv"}
EVIDENCE_FIELDS = ("date_utc", "archive_status", "observation_status", "source_qualification", "coverage_status", "evidence_status")
COVERAGE_STATES = ("partial_declared", "complete_declared", "coverage_unknown", "observation_unavailable")


def _fail(code):
    raise DwrError("automated_" + code)


def _text(value):
    if not isinstance(value, str) or not value or len(value) > 512 or any(ord(c) < 32 for c in value):
        _fail("invalid_label")
    if value[0] in "=+-@":
        _fail("unsafe_csv_label")
    return value


def coverage_evidence(archive_days, window):
    """Minimize already admitted archives. This adapter cannot attest their origin.

    The private preparer must first reconstruct normalized inputs from the native
    receipts and immutable archive manifest. Never call this on a diagnostic ZIP
    as a substitute for admission. Raw counters/reasons/hashes are not copied.
    """
    expected = [str(d) for d in window.dates()]
    if sorted(d["date_utc"] for d in archive_days) != expected:
        _fail("coverage_calendar_invalid")
    result = []
    for day in sorted(archive_days, key=lambda d: d["date_utc"]):
        state = day.get("archive_status")
        if state not in ("archived", "observation_unavailable"):
            _fail("archive_state_invalid")
        available = state == "archived"
        result.append({"date_utc": day["date_utc"], "archive_status": state,
                       "observation_status": "observed" if available else "observation_unavailable",
                       "source_qualification": "qualified" if available else "not_qualified",
                       "coverage_status": measurement.coverage(day),
                       "evidence_status": "declared" if available else "not_established"})
    return result


def provenance_summary(provenance, window):
    """Categorical limitations from admitted provenance, independent of all rows.

    Do not expose epoch identifiers, definitions, day partitions, source hashes or
    versions inferred from the current code. Missing evidence stays unknown.
    """
    epochs = [measurement.epoch({"date_utc": str(day)}, provenance) for day in window.dates()]
    return {"epoch_resolution": measurement.resolution(e["measurement_epoch_id"] for e in epochs),
            "classifier_status": "attested_in_provenance" if all(e["comparable"] for e in epochs) else "unknown",
            "attribution_assessment": "recorded_classification_reliability_under_review",
            "time_grain": "edition_without_epoch_partitions"}


def _evidence(evidence, window):
    expected = [str(d) for d in window.dates()]
    if not isinstance(evidence, list) or [e.get("date_utc") for e in evidence] != expected:
        _fail("coverage_calendar_invalid")
    for row in evidence:
        if set(row) != set(EVIDENCE_FIELDS):
            _fail("unexpected_evidence_field")
        available = row["archive_status"] == "archived"
        if row["archive_status"] not in ("archived", "observation_unavailable"):
            _fail("archive_state_invalid")
        fixed = {"observation_status": "observed" if available else "observation_unavailable",
                 "source_qualification": "qualified" if available else "not_qualified",
                 "evidence_status": "declared" if available else "not_established"}
        if any(row[k] != v for k, v in fixed.items()) or row["coverage_status"] not in COVERAGE_STATES:
            _fail("evidence_state_invalid")
        if (row["coverage_status"] == "observation_unavailable") == available:
            _fail("evidence_state_invalid")
    return {e["date_utc"]: e for e in evidence}


def project(rows, resources, *, window, evidence, provenance):
    """Pure projection after admission; never an alternative source reader.

    Provenance and archive evidence are explicit, separate inputs. Tests of
    rejected-row independence hold these inputs fixed; real admission validates
    their source separately. All returned observation counts use only selection.
    """
    by_day = _evidence(evidence, window)
    registry = {}
    for r in resources:
        key = (r["site_id"], r["path"])
        if key in registry:
            _fail("duplicate_resource")
        registry[key] = r
    cells, daily, family_daily = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in rows:
        # No label, count, epoch, inventory or diagnostic from a rejected row is
        # consulted to construct output metadata. Admission still checks sources.
        if (r.get("actor_role") not in ROLES or r.get("stored_identity_tier") != TIER
                or r.get("http_method") != "GET" or type(r.get("http_status")) is not int or r["http_status"] != 200):
            continue
        resource = registry.get((r["site_id"], r["path"]))
        if resource is None:
            _fail("resource_missing")
        if resource.get("main_population") is not True:
            continue
        stamp = r["date_utc"]
        if stamp not in by_day:
            _fail("row_outside_window")
        if by_day[stamp]["observation_status"] != "observed":
            continue  # retained privately; never counted on an unavailable day
        validate_site(r["site_id"]); validate_path(r["path"])
        if type(r["request_count"]) is not int or r["request_count"] < 1:
            _fail("count_invalid")
        family = _text(resource["family"])
        actor_family, actor_name = _text(r["actor_family"]), _text(r["actor_name"])
        key = (r["site_id"], r["path"], family, actor_family, actor_name, r["actor_role"])
        cells[key] += r["request_count"]
        daily[(stamp, r["site_id"], r["actor_role"])] += r["request_count"]
        family_daily[(stamp, family, r["actor_role"])] += r["request_count"]
    table = lambda counts, fields: [dict(zip(fields, key), request_count=n) for key, n in sorted(counts.items())]
    consultations = table(cells, TABLES["consultations"][:-1])
    resource_counts, actors, families = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in consultations:
        n = r["request_count"]
        resource_counts[(r["site_id"], r["path"], r["family"])] += n
        actors[(r["site_id"], r["actor_family"], r["actor_name"], r["actor_role"])] += n
        families[(r["family"], r["actor_role"])] += n
    selected_families = sorted({k[0] for k in families})
    def calendar_rows(counts, dimensions):
        result = []
        for stamp, e in by_day.items():
            for group in dimensions:
                for role in ROLES:
                    result.append({"date_utc": stamp, "group": group, "actor_role": role,
                                   "request_count": counts[(stamp, group, role)] if e["observation_status"] == "observed" else None,
                                   "observation_status": e["observation_status"], "coverage_status": e["coverage_status"]})
        return result
    daily_rows = [{("site_id" if k == "group" else k): v for k, v in r.items()}
                  for r in calendar_rows(daily, sorted(SITE_IDS))]
    family_rows = [{("family" if k == "group" else k): v for k, v in r.items()}
                   for r in calendar_rows(family_daily, selected_families)]
    coverage = [{**e, "request_count": sum(daily[(stamp, site, role)] for site in SITE_IDS for role in ROLES)
                 if e["observation_status"] == "observed" else None,
                 "suppression_status": "not_suppressed" if e["observation_status"] == "observed" else "observation_unavailable"}
                for stamp, e in by_day.items()]
    result = {"contract": CONTRACT, "nature": "observed_aggregates_private_unapproved",
              "availability_status": "private_candidate", "public_output_approved": False,
              "window": {"start_inclusive": str(window.start), "end_exclusive": str(window.end_exclusive), "timezone": "UTC"},
              "selection": deepcopy(SELECTION), "on_demand": deepcopy(ON_DEMAND),
              "measurement": provenance_summary(provenance, window),
              "comparison": {"comparable": False, "growth": None, "reason": "automated_baseline_not_qualified"},
              "graphs": [{"site_id": s, "status": "not_available", "reason": "source_graph_not_qualified_for_contract"} for s in SITE_IDS],
              "tables": {"consultations": consultations,
                         "resources": [dict(zip(TABLES["resources"], k)) for k in sorted(resource_counts)],
                         "resource_summary": table(resource_counts, TABLES["resource_summary"][:-1]),
                         "actors": table(actors, TABLES["actors"][:-1]),
                         "families": table(families, TABLES["families"][:-1]),
                         "daily": daily_rows, "family_daily": family_rows, "coverage": coverage},
              "metrics": {}, "residual_cases": list(RESIDUAL)}
    result["metrics"] = compute_metrics(result)
    validate(result)
    return result


def compute_metrics(document):
    rows = document["tables"]["consultations"]
    return {"selected_requests": sum(r["request_count"] for r in rows),
            "selected_distinct_resources": len({(r["site_id"], r["path"]) for r in rows}),
            "selected_distinct_software_actors": len({(r["actor_family"], r["actor_name"], r["actor_role"]) for r in rows}),
            "by_role": {role: sum(r["request_count"] for r in rows if r["actor_role"] == role) for role in ROLES},
            "by_site": {site: sum(r["request_count"] for r in rows if r["site_id"] == site) for site in SITE_IDS}}


def _object(properties):
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


def _fixed(value):
    return {"const": value}


def schema_document():
    label = {"type": "string", "minLength": 1, "maxLength": 512}
    count = {"type": "integer", "minimum": 0}
    optional_count = {"type": ["integer", "null"], "minimum": 0}
    field = {"site_id": {"enum": list(SITE_IDS)}, "actor_role": {"enum": list(ROLES)},
             "date_utc": {"type": "string", "format": "date"}, "request_count": optional_count,
             "archive_status": {"enum": ["archived", "observation_unavailable"]},
             "observation_status": {"enum": ["observed", "observation_unavailable"]},
             "source_qualification": {"enum": ["qualified", "not_qualified"]},
             "coverage_status": {"enum": list(COVERAGE_STATES)},
             "evidence_status": {"enum": ["declared", "not_established"]},
             "suppression_status": {"enum": ["not_suppressed", "observation_unavailable"]}}
    tables = {}
    for name, fields in TABLES.items():
        props = {k: field.get(k, label) for k in fields}
        if name not in ("daily", "family_daily", "coverage") and "request_count" in props:
            props["request_count"] = {"type": "integer", "minimum": 1}
        tables[name] = {"type": "array", "items": _object(props)}
    schema = _object({"contract": _fixed(CONTRACT), "nature": _fixed("observed_aggregates_private_unapproved"),
        "availability_status": _fixed("private_candidate"), "public_output_approved": _fixed(False),
        "window": _object({"start_inclusive": field["date_utc"], "end_exclusive": field["date_utc"], "timezone": _fixed("UTC")}),
        "selection": _fixed(SELECTION), "on_demand": _fixed(ON_DEMAND),
        "measurement": _object({"epoch_resolution": {"enum": list(measurement.RESOLUTIONS)},
            "classifier_status": {"enum": ["unknown", "attested_in_provenance"]},
            "attribution_assessment": _fixed("recorded_classification_reliability_under_review"),
            "time_grain": _fixed("edition_without_epoch_partitions")}),
        "comparison": _fixed({"comparable": False, "growth": None, "reason": "automated_baseline_not_qualified"}),
        "graphs": _fixed([{"site_id": s, "status": "not_available", "reason": "source_graph_not_qualified_for_contract"} for s in SITE_IDS]),
        "tables": _object(tables), "metrics": _object({"selected_requests": count, "selected_distinct_resources": count,
            "selected_distinct_software_actors": count, "by_role": _object({r: count for r in ROLES}),
            "by_site": _object({s: count for s in SITE_IDS})}), "residual_cases": _fixed(RESIDUAL)})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": CONTRACT, **schema}


def _check(value, schema):
    """Validate the deliberately small, closed JSON Schema subset emitted above."""
    if "const" in schema and canonical_json(value) != canonical_json(schema["const"]):
        _fail("schema_constant")
    if "enum" in schema and value not in schema["enum"]:
        _fail("schema_enum")
    kind = schema.get("type")
    types = kind if isinstance(kind, list) else [kind]
    valid_type = {"null": value is None, "integer": type(value) is int, "string": type(value) is str,
                  "object": type(value) is dict, "array": type(value) is list}
    if kind and not any(valid_type[t] for t in types):
        _fail("schema_type")
    if type(value) is int and "minimum" in schema and value < schema["minimum"]:
        _fail("schema_minimum")
    if kind == "string":
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 4096):
            _fail("schema_string_length")
        if schema.get("format") == "date":
            dates.parse_date(value)
        if any(ord(c) < 32 for c in value):
            _fail("schema_control_character")
    if kind == "object":
        if set(value) != set(schema["properties"]):
            _fail("schema_fields")
        for k, spec in schema["properties"].items():
            _check(value[k], spec)
    if kind == "array":
        for item in value:
            _check(item, schema["items"])


def validate(document):
    """Reject extra surfaces/columns and reconcile every released marginal."""
    _check(document, schema_document())
    period = dates.window_from_strings(document["window"]["start_inclusive"], document["window"]["end_exclusive"])
    tables = document["tables"]
    by_day = _evidence([{k: r[k] for k in EVIDENCE_FIELDS} for r in tables["coverage"]], period)
    for name, rows in tables.items():
        keys = [tuple(r[k] for k in TABLES[name] if k not in ("request_count", "observation_status", "coverage_status",
                                                           "source_qualification", "evidence_status", "suppression_status", "archive_status")) for r in rows]
        if len(keys) != len(set(keys)):
            _fail("duplicate_output_cell")
        for r in rows:
            if "path" in r:
                validate_path(r["path"])
            if "date_utc" in r:
                e = by_day.get(r["date_utc"])
                if e is None or r["coverage_status"] != e["coverage_status"] or r["observation_status"] != e["observation_status"]:
                    _fail("calendar_state_mismatch")
                if (r["request_count"] is None) != (e["observation_status"] == "observation_unavailable"):
                    _fail("calendar_null_mismatch")
    def aggregate(rows, keys):
        result = defaultdict(int)
        for r in rows:
            result[tuple(r[k] for k in keys)] += r["request_count"] or 0
        return dict(result)
    source = tables["consultations"]
    path_families = defaultdict(set)
    for row in source:
        path_families[(row["site_id"], row["path"])].add(row["family"])
        for key in ("family", "actor_family", "actor_name"):
            _text(row[key])
    if any(len(values) != 1 for values in path_families.values()):
        _fail("resource_family_ambiguous")
    for name in ("resource_summary", "actors", "families"):
        keys = TABLES[name][:-1]
        if aggregate(source, keys) != aggregate(tables[name], keys):
            _fail("monthly_marginal_mismatch")
    resource_keys = [tuple(r[k] for k in TABLES["resources"]) for r in tables["resources"]]
    if set(resource_keys) != set(aggregate(source, TABLES["resources"])):
        _fail("inventory_not_from_selection")
    selected_families = sorted({r["family"] for r in source})
    for name, group, groups in (("daily", "site_id", sorted(SITE_IDS)), ("family_daily", "family", selected_families)):
        expected = {(day, g, role) for day in by_day for g in groups for role in ROLES}
        if {(r["date_utc"], r[group], r["actor_role"]) for r in tables[name]} != expected:
            _fail("daily_calendar_incomplete")
        actual = {k: n for k, n in aggregate(tables[name], (group, "actor_role")).items() if n}
        if actual != aggregate(source, (group, "actor_role")):
            _fail("daily_monthly_marginal_mismatch")
    per_day = aggregate(tables["daily"], ("date_utc",))
    if per_day != aggregate(tables["coverage"], ("date_utc",)):
        _fail("coverage_selected_mismatch")
    if selected_families and aggregate(tables["daily"], ("date_utc", "actor_role")) != aggregate(tables["family_daily"], ("date_utc", "actor_role")):
        _fail("daily_family_mismatch")
    for r in tables["coverage"]:
        expected = "not_suppressed" if r["observation_status"] == "observed" else "observation_unavailable"
        if r["suppression_status"] != expected:
            _fail("coverage_suppression_mismatch")
    if document["metrics"] != compute_metrics(document):
        _fail("metrics_not_from_selection")
    return {"structural_contract_passed": True, "public_output_approved": False,
            "status": "private_contract_qualified_pending_release_review", "contract": CONTRACT,
            "scope": "Closed selection-only tables, marginals and categorical evidence; not general anonymity or source independence.",
            "residual_cases": list(RESIDUAL)}
