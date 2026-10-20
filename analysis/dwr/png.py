"""Optional browser fallback, behind the same Python admission and transaction."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from .common import REPO_ROOT, DwrError
from . import pipeline, write_guard


def prepare(edition_id, preview=None):
    entry = pipeline.edition_entry(edition_id)
    eid = entry["edition_id"]
    source = REPO_ROOT / "figures" / eid
    if preview is None:
        # Admission occurs before browser resolution, process launch or output.
        with write_guard.transaction(REPO_ROOT, eid) as stage:
            _render(stage / "figures")
        return {"edition_id": eid, "status": "local_candidate_png_installed"}
    preview = Path(preview).absolute()
    if preview.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise DwrError("png_preview_must_be_outside_repository")
    write_guard.checked_path(preview.anchor, preview)
    if preview.exists():
        raise DwrError("png_preview_destination_exists")
    write_guard.fingerprint(write_guard.checked_path(REPO_ROOT, source))
    preview.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dwr-png-preview-", dir=preview.parent) as tmp:
        staged = Path(tmp) / "figures"
        shutil.copytree(source, staged)
        _render(staged)
        write_guard.checked_path(preview.anchor, preview)
        if preview.exists():
            raise DwrError("png_preview_destination_exists")
        os.rename(staged / "png", preview)
    return {"edition_id": eid, "status": "external_preview_only",
            "historical_png_replaced": False, "engine_equivalence": "not_claimed"}


def _render(figures):
    env = {k: v for k, v in os.environ.items() if k.upper() in (
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA",
        "USERPROFILE", "PROGRAMFILES", "PROGRAMFILES(X86)", "DWR_PLAYWRIGHT_DIR",
        "PLAYWRIGHT_BROWSERS_PATH")}
    result = subprocess.run(["node", str(REPO_ROOT / "scripts/render_png.mjs"),
                             "--worker", str(figures)], env=env, capture_output=True,
                            timeout=180, text=True)
    if result.returncode:
        raise DwrError("png_renderer_failed", "No staged PNGs installed; inspect the local renderer environment.")
