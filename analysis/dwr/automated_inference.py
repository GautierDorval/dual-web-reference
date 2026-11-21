"""Exact marginal bounds for profile B; private diagnosis, never anonymity proof.

Within each site/role, rows are observed days and columns are monthly
resource/actor cells. With no forbidden cell, integer transportation tables
have exact per-cell bounds max(0, column + row - total) and min(column, row).
No observed day/resource assignment or auxiliary support restriction is read.
"""
from collections import defaultdict
from . import automated as A
from .common import DwrError


def assess(document):
    A.validate(document)
    if document["contract"] != A.PROFILE_B_CONTRACT:
        raise DwrError("profile_b_inference_contract_required")
    tables = document["tables"]
    columns = defaultdict(list)
    for row in tables["consultations"]:
        columns[(row["site_id"], row["actor_role"])].append(row)
    bounds = []
    for day in tables["daily"]:
        if day["request_count"] is None:
            continue
        group = columns[(day["site_id"], day["actor_role"])]
        total = sum(row["request_count"] for row in group)
        for row in group:
            lower = max(0, row["request_count"] + day["request_count"] - total)
            upper = min(row["request_count"], day["request_count"])
            bounds.append({**{key: row[key] for key in A.TABLES["consultations"][:-1]},
                           "date_utc": day["date_utc"], "lower": lower, "upper": upper})
    return {"contract": A.PROFILE_B_CONTRACT,
            "model": "complete_nonnegative_integer_transport_tables_by_site_and_role",
            "inputs": "canonical_profile_b_margins_only",
            "available_days": sum(row["observation_status"] == "observed" for row in tables["coverage"]),
            "variables": len(bounds),
            "fixed_positive_cells": sum(r["lower"] == r["upper"] and r["lower"] > 0 for r in bounds),
            "fixed_zero_cells": sum(r["upper"] == 0 for r in bounds),
            "unfixed_cells": sum(r["lower"] != r["upper"] for r in bounds),
            "bounds": bounds,
            "limits": ["No auxiliary or semantic support restrictions are modelled.",
                       "Zero positive fixed cells here is not a claim for every dataset or future release.",
                       "Zeros, role identities and other group facts can remain inferable.",
                       "No person-anonymity or universal non-reconstruction guarantee."]}
