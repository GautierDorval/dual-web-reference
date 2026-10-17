"""Read the pinned archive commit (private repository) for coverage and versions.

Only the governance-visibility source and the tables reports, windows,
governance_daily and site_counts are read. Runtime tables and metrics are out of
scope and never read. Multiple snapshots of one date are detected; only the
current one is used and superseded ones are listed, never added.
"""

from __future__ import annotations

import csv
import io
import subprocess
from collections import defaultdict
from pathlib import Path

from .common import DwrError, SITE_IDS
from .dates import Window

SOURCE_ID = "governance-visibility"
TABLES = ("reports", "windows", "governance_daily", "site_counts")


def _git_show(repository: Path, commit: str, path: str) -> str | None:
    completed = subprocess.run(["git", "-C", str(repository), "show", f"{commit}:{path}"],
                               capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8-sig")


def _months(window: Window) -> list[str]:
    months = sorted({day.strftime("%Y-%m") for day in window.dates()})
    return months


def read_tables(repository: Path, commit: str, window: Window) -> dict[str, list[dict]]:
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise DwrError("archive_commit_not_pinned", commit[:12])
    tables = {}
    for table in TABLES:
        rows = []
        for month in _months(window):
            text = _git_show(repository, commit, f"tables/{month}/{table}.csv")
            if text is None:
                raise DwrError("source_unavailable", f"archive tables/{month}/{table}.csv")
            rows.extend(csv.DictReader(io.StringIO(text, newline="")))
        tables[table] = rows
    return tables


def inventory(repository: Path, commit: str, window: Window) -> dict:
    tables = read_tables(repository, commit, window)
    in_window = lambda value: window.contains(__import__("datetime").date.fromisoformat(value))
    reports = [row for row in tables["reports"] if row["source_id"] == SOURCE_ID and in_window(row["report_date"])]
    by_date = defaultdict(list)
    for row in reports:
        by_date[row["report_date"]].append(row)
    governance = {row["snapshot_id"]: row for row in tables["governance_daily"] if in_window(row["report_date"])}
    windows = defaultdict(list)
    for row in tables["windows"]:
        if row["kind"] == "coverage" and in_window(row["report_date"]):
            windows[row["snapshot_id"]].append(row)
    site_counts = defaultdict(dict)
    for row in tables["site_counts"]:
        if in_window(row["report_date"]) and row["site"] in SITE_IDS:
            site_counts[row["snapshot_id"]][row["site"]] = int(row["count"])
    days = []
    for day in window.dates():
        key = day.isoformat()
        snapshots = by_date.get(key, [])
        current = [row for row in snapshots if row["is_current"] == "true"]
        if not snapshots:
            days.append({"date_utc": key, "archive_status": "observation_unavailable", "snapshots": 0})
            continue
        if len(current) != 1:
            raise DwrError("archive_current_snapshot_ambiguous", key)
        report = current[0]
        detail = governance.get(report["snapshot_id"], {})
        segments = sorted(windows.get(report["snapshot_id"], []), key=lambda r: int(r["window_index"]))
        days.append({
            "date_utc": key,
            "archive_status": "archived",
            "snapshots": len(snapshots),
            "superseded_snapshot_ids": sorted(row["snapshot_id"] for row in snapshots if row is not report),
            "snapshot_id": report["snapshot_id"],
            "captured_at": report["captured_at"],
            "report_status": report["report_status"],
            "report_reason_code": report["reason_code"],
            "producer_commit_observed_at_capture": report["source_commit"],
            "aggregate_count": int(detail["aggregate_count"]) if detail.get("aggregate_count") else None,
            "v3_count": int(detail["v3_count"]) if detail.get("v3_count") else None,
            "governance_reason_code": detail.get("reason_code"),
            "proof_status": detail.get("proof_status"),
            "coverage_segments": [{"start": seg["start"], "end_exclusive": seg["end_exclusive"], "source": seg["source"]}
                                  for seg in segments],
            "site_counts": dict(sorted(site_counts.get(report["snapshot_id"], {}).items())),
        })
    return {"commit": commit, "source_id": SOURCE_ID, "tables_read": list(TABLES), "days": days}
