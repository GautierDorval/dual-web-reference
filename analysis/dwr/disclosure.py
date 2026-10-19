"""Conservative combined-release gate. No universal anonymity claim.

The historical monthly path threshold is not an inference defence. New protected
fine cells are blocked unless they are an exact re-presentation of inventoried
public cells. Daily protected counts and coverage complements are withheld.
This evaluates specified aggregate inference surfaces, not identification of people.
"""
from copy import deepcopy
from .common import REPO_ROOT, DwrError, load_json, read_csv, sha256_file, safe_relative, canonical_json

TABLES = {"consultations": "consultations.csv", "resources": "resources.csv", "daily": "daily-summary.csv",
          "coverage": "coverage.csv", "family_daily": "daily-family-summary.csv",
          "resource_summary": "resource-summary.csv", "actors": "actor-summary.csv", "exclusions": "exclusions.csv"}
COVERAGE_COUNTS = ("aggregate_count", "v3_count", "aggregate_minus_v3")


def protected(row, policy):
    spec = policy["protected_strata"]
    return (row.get("actor_role") in spec["actor_roles"] or
            row.get("stored_identity_tier") in spec["stored_identity_tiers"] or
            row.get("actor_role") == "protected_strata" or row.get("stored_identity_tier") == "protected_strata")


def tables(directory):
    return {key: read_csv(directory / name) for key, name in TABLES.items()}


def inventory(root=REPO_ROOT):
    """Authenticate every inventoried public file, including superseded accessible releases."""
    path = root / "config/publication-inventory.json"
    if not path.is_file():
        return {"status": "not_assessed", "releases": [], "reason": "public_history_inventory_missing"}
    document = load_json(path)
    if document.get("status") != "complete_for_named_repository_history" or not document.get("releases"):
        return {"status": "not_assessed", "releases": [], "reason": "public_history_inventory_incomplete"}
    releases = []
    try:
        states = document.get("historical_states")
        if not states or len(states) != document.get("historical_states_count") or len({s.get("public_ref") for s in states}) != len(states) or not any(s.get("public_ref") == document.get("public_head_verified", "")[:7] for s in states):
            raise DwrError("public_history_inventory_incomplete")
        for state in states:
            if not state.get("accessible") or set(state.get("canonical_table_hashes", {})) != set(TABLES.values()):
                raise DwrError("public_history_inventory_incomplete")
            for name, digest in state["canonical_table_hashes"].items():
                if sha256_file(safe_relative(root, "data/editions/" + state["edition_id"] + "/" + name)) != digest:
                    raise DwrError("historical_table_revision_requires_separate_inventory")
        for release in document["releases"]:
            if not release.get("files") or not release.get("accessible"):
                raise DwrError("public_history_inventory_incomplete")
            for name, digest in release["files"].items():
                p = safe_relative(root, name)
                if not p.is_file() or sha256_file(p) != digest:
                    raise DwrError("public_history_inventory_bytes_changed")
            releases.append({"edition_id": release["edition_id"], "tables": tables(root / "data/editions" / release["edition_id"]),
                             "accessible": True, "superseded": release.get("superseded", False)})
    except (DwrError, OSError, KeyError, TypeError):
        return {"status": "not_assessed", "releases": [], "reason": "public_history_inventory_invalid"}
    return {"status": "assessed", "releases": releases,
            "scope": "Named repository releases only; no claim about unknown third-party auxiliary data."}


def signature(rows):
    # Edition identifiers change on a correction, observation cells must not.
    return sorted(canonical_json({k: ("" if v is None else str(v).lower() if isinstance(v, bool) else str(v)) for k, v in row.items() if k != "edition_id"}) for row in rows)


def coarsen(candidate, policy):
    """Remove daily protected margins AND coverage complements; never insert observed zeros."""
    result = deepcopy(candidate)
    result["daily"] = [r for r in result["daily"] if not protected(r, policy)]
    for row in result["coverage"]:
        for key in COVERAGE_COUNTS:
            row[key] = None
    return result


def assess(candidate, history, policy):
    reasons, residual = [], []
    if history.get("status") != "assessed" or not history.get("releases"):
        return {"status": "not_assessed", "allowed": False, "reasons": [history.get("reason", "public_history_inventory_missing")],
                "policy_id": policy["policy_id"]}
    if set(candidate) != set(TABLES):
        reasons.append("unassessed_projection_surface")
    monthly = [r for r in candidate.get("consultations", []) if protected(r, policy)]
    daily = [r for r in candidate.get("daily", []) if protected(r, policy)]
    if daily:
        reasons.append("protected_daily_margin_blocked_including_single_active_day")
    if any(row.get(k) not in (None, "") for row in candidate.get("coverage", []) for k in COVERAGE_COUNTS):
        reasons.append("coverage_complement_can_recover_protected_daily_counts")
    # Named-agent, recurrence and resource marginals also carry inference information.
    # For this revision they may only repeat exact historical evidence. A new period
    # needs a separately qualified coarser contract, not a warning beside fine output.
    sensitive = ("consultations", "resource_summary", "actors", "exclusions", "resources")
    matched_history = [r for r in history.get("releases", []) if r.get("accessible") and
                       all(signature(candidate.get(k, [])) == signature(r["tables"].get(k, [])) for k in sensitive)]
    if (monthly or any(protected(r, policy) for r in candidate.get("actors", []))) and not matched_history:
        reasons.append("new_or_revised_protected_fine_cells_not_assessed")
    for row in candidate.get("daily", []):
        if row.get("stored_identity_tier") != "provider_origin_verified_actor" or row.get("actor_role") not in ("ai_training", "ai_search", "search_indexing"):
            reasons.append("daily_stratum_not_qualified")
    if any(r.get("actor_role") not in ("ai_training", "ai_search") for r in candidate.get("family_daily", [])):
        reasons.append("family_role_not_qualified")
    # Superseded releases remain in history; deletion of a current pointer is not withdrawal.
    for key in ("family_daily", "daily"):
        if any(protected(r, policy) for r in candidate.get(key, [])):
            reasons.append("protected_daily_surface_blocked:" + key)
    residual.extend(["A sole automated provider-origin actor can be inferred from its role.",
                     "A single-resource family can reveal that automated resource's daily count.",
                     "Already public historical margins remain accessible; this revision cannot erase them.",
                     "The gate does not prove universal non-reconstruction or person anonymity."])
    return {"status": "not_assessed" if reasons else "assessed_limited_no_new_protected_detail",
            "allowed": not reasons, "reasons": sorted(set(reasons)), "residual_cases": residual,
            "policy_id": policy["policy_id"], "historical_releases_considered": len(history.get("releases", [])),
            "withheld": {"coverage_daily_counts": "withheld_not_zero", "protected_daily_rows": "withheld_not_zero"},
            "scope": "Canonical source tables plus deterministic derivatives verified against them; any new output surface needs a new contract."}


def enforce(candidate, history, policy):
    result = assess(candidate, history, policy)
    if not result["allowed"]:
        raise DwrError("combined_disclosure_blocked", ";".join(result["reasons"]))
    return result
