"""Inactive, synthetic-only contract candidate. No CLI, promotion or policy switch.

Filter before deriving every public value. No total, inventory, source hash,
coverage margin or diagnostic from rejected rows enters the returned bundle.
This tests noninterference for the stated selection, not universal anonymity.
"""
from collections import defaultdict
from .common import DwrError
from .measurement import token

CONTRACT = "dwr-future-automated/0.1.0"
ROLES = ("ai_training", "ai_search")
TIER = "provider_origin_verified_actor"


def prepare_synthetic(rows, resources, *, nature):
    if nature != "synthetic_only_not_observed_traffic":
        raise DwrError("future_contract_synthetic_only")
    registry = {(r["site_id"], r["path"]): r for r in resources}
    cells = defaultdict(int)
    for row in rows:
        # Do not validate or count rejected rows into a published diagnostic.
        if (row.get("actor_role") not in ROLES or row.get("stored_identity_tier") != TIER
                or row.get("http_method") != "GET" or str(row.get("http_status")) != "200"):
            continue
        resource = registry.get((row["site_id"], row["path"]))
        if not resource or resource.get("main_population") not in (True, "true"):
            continue
        count = row["request_count"]
        if type(count) is not int or count < 1:
            raise DwrError("future_contract_count_invalid")
        epoch = token(row.get("measurement_epoch_id", "unknown"))
        key = (row["date_utc"], row["site_id"], row["path"], resource["family"],
               row["actor_family"], row["actor_name"], row["actor_role"], epoch)
        cells[key] += count
    fields = ("date_utc", "site_id", "path", "family", "actor_family", "actor_name",
              "actor_role", "measurement_epoch_id")
    observations = [dict(zip(fields, key), request_count=n) for key, n in sorted(cells.items())]
    daily, actors, families = defaultdict(int), defaultdict(int), defaultdict(int)
    paths = set()
    for r in observations:
        n = r["request_count"]
        daily[(r["date_utc"], r["measurement_epoch_id"])] += n
        actors[(r["actor_family"], r["actor_name"], r["actor_role"], r["measurement_epoch_id"])] += n
        families[(r["family"], r["actor_role"], r["measurement_epoch_id"])] += n
        paths.add((r["site_id"], r["path"]))
    def table(counts, keys):
        return [dict(zip(keys, k), request_count=n) for k, n in sorted(counts.items())]
    return {"contract": CONTRACT, "activation": "inactive_requires_owner_decision_and_qualification",
            "nature": nature, "selection": {"roles": list(ROLES), "tier": TIER, "population": "main_documentary",
                                          "http_method": "GET", "http_status": 200},
            "consultations": observations,
            "resources": [{"site_id": s, "path": p} for s, p in sorted(paths)],
            "daily": table(daily, ("date_utc", "measurement_epoch_id")),
            "actors": table(actors, ("actor_family", "actor_name", "actor_role", "measurement_epoch_id")),
            "families": table(families, ("family", "actor_role", "measurement_epoch_id")),
            "metrics": {"selected_requests": sum(cells.values()), "selected_distinct_resources": len(paths)},
            "figure_data": table(daily, ("date_utc", "measurement_epoch_id")),
            "coverage": "not_inferred_from_selection",
            "excluded_surfaces": ["all-source totals", "rejected strata", "full inventory", "private input digests",
                                  "coverage complements", "graph snapshots", "source diagnostics",
                                  "catalog.measurement.days", "catalog.measurement.epoch_definitions",
                                  "all-source coverage epoch fields", "catalog.input_digest", "private_input_digest"],
            "limits": "Conditional selection only; named automated actors and single-resource families can be inferred."}

# A proposal attached to the inactive contract, not an archive-to-public adapter.
# Existing coverage vocabulary is reused; only explicit qualification/evidence
# fields are added. This schema is deliberately not registered for publication.
COVERAGE_CONTRACT = "dwr-future-coverage/0.1.0"
COVERAGE_EVIDENCE_FIELDS = {
    "archive_status": ("archived", "observation_unavailable", "unknown"),
    "observation_status": ("observed", "observation_unavailable"),
    "source_qualification": ("qualified", "not_qualified"),
    "coverage_status": ("complete_declared", "partial_declared", "coverage_unknown", "observation_unavailable", "mixed_coverage"),
    "evidence_status": ("declared", "not_established"),
}
COVERAGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": COVERAGE_CONTRACT,
    "type": "object", "additionalProperties": False,
    "required": ["date_utc", *COVERAGE_EVIDENCE_FIELDS, "request_count", "suppression_status"],
    "properties": {
        "date_utc": {"type": "string", "format": "date"},
        **{name: {"enum": list(values)} for name, values in COVERAGE_EVIDENCE_FIELDS.items()},
        "request_count": {"type": ["integer", "null"], "minimum": 0},
        "suppression_status": {"enum": ["not_suppressed", "withheld_not_zero", "observation_unavailable"]},
    },
}


def coverage_synthetic(rows, resources, *, window, evidence, nature, withhold_selected=False):
    """Calendar from window bounds; only explicitly scoped synthetic evidence.

    Never accepts archive payloads, reason codes, count differences, captures,
    private digests, or all-row epoch metadata. A claimed source qualification
    here is a fixture input, not independently established real provenance.
    """
    if nature != "synthetic_only_not_observed_traffic":
        raise DwrError("future_contract_synthetic_only")
    if not isinstance(evidence, dict) or type(withhold_selected) is not bool:
        raise DwrError("future_coverage_evidence_invalid")
    days = [day.isoformat() for day in window.dates()]
    if set(evidence) - set(days):
        raise DwrError("future_coverage_evidence_outside_window")
    defaults = {"archive_status": "unknown", "observation_status": "observation_unavailable",
                "source_qualification": "not_qualified", "coverage_status": "coverage_unknown",
                "evidence_status": "not_established"}
    admitted = {}
    for day in days:
        item = evidence.get(day, defaults)
        if (not isinstance(item, dict) or set(item) != set(COVERAGE_EVIDENCE_FIELDS)
                or any(item[key] not in values for key, values in COVERAGE_EVIDENCE_FIELDS.items())):
            raise DwrError("future_coverage_evidence_invalid")
        admitted[day] = dict(item)
    selected = prepare_synthetic(rows, resources, nature=nature)
    totals = defaultdict(int)
    for cell in selected["consultations"]:
        if cell["date_utc"] not in admitted:
            raise DwrError("future_selected_row_outside_window")
        totals[cell["date_utc"]] += cell["request_count"]
    output = []
    for day in days:
        item = admitted[day]
        available = (item["observation_status"] == "observed" and item["source_qualification"] == "qualified"
                     and item["evidence_status"] == "declared" and item["coverage_status"] != "observation_unavailable")
        state = "observation_unavailable" if not available else "withheld_not_zero" if withhold_selected else "not_suppressed"
        output.append({"date_utc": day, **item,
                       "request_count": totals[day] if available and not withhold_selected else None,
                       "suppression_status": state})
    return {"contract": COVERAGE_CONTRACT, "activation": "inactive_requires_owner_decision_and_qualification",
            "nature": nature, "coverage": output,
            "evidence_provenance": "explicit_synthetic_fixture_declarations_not_archive_derived",
            "limits": "Recorded selection only; archive availability does not establish collection completeness. Partial or unknown coverage does not establish absence of access."}


def on_demand_synthetic(rows, *, window, nature, option="U0"):
    """Decision material only; U1 is a private risk probe, never a public series."""
    from .common import IDENTITY_TIERS, SITE_IDS
    from .dates import parse_date
    if nature != "synthetic_only_not_observed_traffic":
        raise DwrError("future_contract_synthetic_only")
    base = {"contract": "dwr-on-demand-options/0.1.0", "nature": nature,
            "activation": "inactive_requires_owner_decision_and_qualification",
            "initiation_provenance": "unknown", "reference_approval": False}
    if option in ("U0", "U2"):
        # Intentionally independent of the existence and number of protected rows.
        return {**base, "option": option, "status": "withheld_not_zero", "request_count": None}
    if option != "U1":
        raise DwrError("future_on_demand_option_invalid")
    counts = defaultdict(int)
    for row in rows:
        if row.get("actor_role") != "user_initiated_fetch" or row.get("http_method") != "GET" or str(row.get("http_status")) != "200":
            continue
        if row.get("site_id") not in SITE_IDS:
            raise DwrError("future_on_demand_site_invalid")
        tier = row.get("stored_identity_tier")
        if tier not in IDENTITY_TIERS:
            raise DwrError("future_on_demand_tier_invalid")
        count = row.get("request_count")
        if type(count) is not int or count < 1:
            raise DwrError("future_contract_count_invalid")
        if window.contains(parse_date(row.get("date_utc"))):
            counts[tier] += count
    return {**base, "option": option, "status": "private_synthetic_risk_evaluation_only",
            "period_start_inclusive": window.start.isoformat(), "period_end_exclusive": window.end_exclusive.isoformat(),
            "by_attribution_tier": dict(sorted(counts.items())), "public_output_approved": False,
            "risks": ["zero_one_transition", "revision_difference", "overlapping_windows", "single_site_removal",
                      "global_total_complement", "other_output_denominators", "previous_public_disclosures"],
            "limits": "Aggregation across sites removes detail but does not establish non-reconstruction. No safe threshold, rounding or count band is selected."}
