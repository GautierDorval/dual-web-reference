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
