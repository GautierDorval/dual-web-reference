"""render: figures, figures.json, case pages, generated README/doc blocks,
schemas, data/index.json, data/latest.json and data/status.json.

Everything is derived from the public edition files and versioned configuration.
Generated blocks live between `<!-- dwr:begin KEY -->` and `<!-- dwr:end KEY -->`;
`verify` regenerates them and fails on any difference. No number in a generated
block is typed by hand.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from . import figures as F
from . import gate
from . import typo
from .common import REPO_ROOT, SITE_IDS, canonical_json, load_json, read_csv, sha256_bytes, write_json, write_text
from .i18n import cap, number, percent, t

BLOCK = re.compile(r"(<!-- dwr:begin (?P<key>[a-z0-9-]+) -->)(?P<body>.*?)(<!-- dwr:end (?P=key) -->)", re.DOTALL)
SITE_CASE_DIR = {site: f"cases/{site}" for site in SITE_IDS}
FIGURE_IDS = ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09", "G10")


def md_escape(text: str) -> str:
    """Neutralize Markdown/HTML in untrusted text placed in tables and paragraphs."""
    text = str(text).replace("\\", "\\\\")
    for char in "`*_[]<>|#":
        text = text.replace(char, "\\" + char)
    return text.replace("\n", " ")


def code(text: str) -> str:
    text = str(text).replace("`", "'").replace("|", "\\|")
    return f"`{text}`"


class Edition:
    def __init__(self, edition_id: str):
        self.id = edition_id
        self.dir = REPO_ROOT / "data" / "editions" / edition_id
        self.catalog = load_json(self.dir / "catalog.json")
        self.metrics_doc = load_json(self.dir / "metrics.json")
        self.metrics = {m["metric_id"]: m for m in self.metrics_doc["metrics"]}
        self.ctx = F.Context(self.catalog, self.dir, self.metrics_doc)

    def m(self, key):
        return self.metrics[key]["value"]


# ---------------------------------------------------------------- figures


def figure_jobs(edition: Edition) -> list[tuple]:
    cases = load_json(REPO_ROOT / "config" / "cases.json")["cases"]
    resources = {(r["site_id"], r["path"]): r for r in read_csv(edition.dir / "resources.csv")}
    graph_ids = {site: info["graph_snapshot_id"] for site, info in edition.catalog["graph_snapshots"].items()}
    jobs = []
    for figure_id, (function, inputs) in F.FIGURES.items():
        jobs.append((figure_id, function, inputs, None))
    for case in cases:
        nodes = []
        for path, layer in case["graph_layers"].items():
            kind = "html" if (case["site_id"], path) not in resources else "file"
            nodes.append({"path": path, "layer": layer, "kind": kind})
        info = {"site_id": case["site_id"], "nodes": nodes, "graph_snapshot_id": graph_ids[case["site_id"]]}
        jobs.append((f"G09-{case['site_id']}", F.figure_g09, ("links.csv",), info))
    return jobs


def render_figure(edition: Edition, function, extra, lang: str, compact: bool):
    if extra is None:
        return function(edition.ctx, lang, compact)
    return function(edition.ctx, lang, compact, extra)


def render_figures(edition: Edition) -> dict:
    target = REPO_ROOT / "figures" / edition.id
    target.mkdir(parents=True, exist_ok=True)
    registry = []
    for figure_id, function, inputs, extra in figure_jobs(edition):
        outputs = {}
        table = None
        for lang in ("en", "fr"):
            for compact in (False, True):
                text, rows = render_figure(edition, function, extra, lang, compact)
                if lang == "fr":
                    text = typo.fr(text)
                name = f"{figure_id}.{lang}{'.compact' if compact else ''}.svg"
                write_text(target / name, text)
                outputs[name] = sha256_bytes(text.encode("utf-8"))
                if lang == "en" and not compact:
                    # A compact variant may show fewer rows (G06: twelve families); the table stays complete.
                    table = rows
        table_name = f"{figure_id}.csv"
        table_text = F.table_csv(table)
        write_text(target / table_name, table_text)
        wide_en = (target / f"{figure_id}.en.svg").read_text(encoding="utf-8")
        wide_fr = (target / f"{figure_id}.fr.svg").read_text(encoding="utf-8")
        status = "not_available" if table and table[0].get("status") == "not_available" else "rendered"
        registry.append({
            "figure_id": figure_id,
            "status": status,
            "title_en": _between(wide_en, '<title id="title">', "</title>"),
            "title_fr": _between(wide_fr, '<title id="title">', "</title>"),
            "alt_en": _between(wide_en, '<desc id="desc">', "</desc>"),
            "alt_fr": _between(wide_fr, '<desc id="desc">', "</desc>"),
            "files": {name: {"path": f"figures/{edition.id}/{name}", "sha256": digest} for name, digest in sorted(outputs.items())},
            "data_table": {"path": f"figures/{edition.id}/{table_name}", "sha256": sha256_bytes(table_text.encode("utf-8"))},
            "inputs": [{"path": f"data/editions/{edition.id}/{name}", "sha256": sha256_bytes((edition.dir / name).read_bytes())}
                       for name in inputs],
            "script": f"analysis/dwr/figures.py ({function.__name__})",
            "png": {"path": f"figures/{edition.id}/png/{figure_id}.en.png", "status": "optional_fallback_not_bit_reproducible"},
        })
    document = {"schema_version": "dwr-figures/1.0.0", "edition_id": edition.id,
                "rendering": {"engine": "analysis/dwr/svg.py (standard library, deterministic)",
                              "fonts": "system font stack only; no font is redistributed",
                              "layouts": "wide 960 px and compact 420 px; English and French"},
                "figures": registry}
    write_json(edition.dir / "figures.json", document)
    return document


def _between(text, start, end):
    first = text.index(start) + len(start)
    from xml.sax.saxutils import unescape
    return unescape(text[first:text.index(end, first)])


# ---------------------------------------------------------------- generated blocks


def dates_box(edition: Edition, lang: str) -> str:
    d = edition.catalog["dates"]
    status = edition.catalog["status"]
    rows = [
        (t(lang, "Edition", "Édition"), code(edition.id)),
        (t(lang, "Status", "Statut"), t(lang, "candidate, not reviewed, not published", "candidate, non revue, non publiée")
         if status == "candidate_not_reviewed" else status),
        (t(lang, "Measured period", "Période mesurée"), edition.catalog["labels"][f"period_{lang}"]),
        ("period_start_inclusive", code(d["period_start_inclusive"])),
        ("period_end_exclusive", code(d["period_end_exclusive"])),
        ("last_included_date", code(d["last_included_date"])),
        ("extracted_at", code(f"{d['extracted_at']['start']} / {d['extracted_at']['end']}")),
        ("source_snapshot_at", code(d["source_snapshot_at"])),
        ("graph_snapshot_at", ", ".join(f"{site} {code(value)}" for site, value in d["graph_snapshot_at"].items())),
        ("generated_at", code(d["generated_at"])),
        ("published_at", code("null") + t(lang, " (not published)", " (non publiée)")),
        ("revised_at", code("null")),
        ("latest_available_data_date", code(d["latest_available_data_date"])),
        ("next_review_target", t(lang, f"weekly review {code(d['next_review_target']['weekly_review'])}, not guaranteed",
                                 f"revue hebdomadaire {code(d['next_review_target']['weekly_review'])}, non garantie")),
        (t(lang, "Updates", "Mises à jour"), t(lang, "periodic update planned; manual preparation (automation not activated)",
                                               "actualisation périodique prévue ; préparation manuelle (automatisation non activée)")),
    ]
    head = t(lang, "| Date or state | Value |\n|---|---|", "| Date ou état | Valeur |\n|---|---|")
    return head + "\n" + "\n".join(f"| {key} | {value} |" for key, value in rows)


def headline(edition: Edition, lang: str, prefix: str = "") -> str:
    total, pairs = edition.m("main.get200"), edition.m("main.site_path_pairs")
    llms, other = edition.m("main.llms_get200"), edition.m("main.other_get200")
    share = edition.m("main.other_share")
    hist = edition.m("historical.provider_ai.get200")
    by_site = ", ".join(f"{site} {number(edition.m(f'main.site.{site}.get200'), lang)}" for site in SITE_IDS)
    roles = [number(edition.m(f"main.role.{role}.get200"), lang) for role in ("ai_training", "ai_search", "user_initiated_fetch")]
    if lang == "en":
        lines = [
            f"In the main documentary population, the collector recorded **{number(total, lang)} GET 200 requests** from AI roles whose provider origin was recorded as verified by an official IP-range match, on **{number(pairs, lang)} distinct site-path pairs**.",
            f"Of these requests, **{number(llms, lang)}** went to `/llms.txt` and **{number(other, lang)}** to other governance files, that is **{percent(share, lang)}** of the same selection (same period, sites, scope, method, status and identification level). This share describes how recorded requests are distributed; it is not an adoption rate.",
            f"By site: {by_site}. By recorded actor role: collection for training {roles[0]}, AI search {roles[1]}, user-initiated fetch {roles[2]}; without user-initiated fetches, {number(edition.m('main.sensitivity.without_user_fetch.get200'), lang)} requests remain (a sensitivity reading, not evidence of independence).",
            f"Qualification: provider-origin attribution does not use the Cloudflare predicate under review; the levels that do use it are kept apart. The initial internal report counted {number(hist, lang)} such requests on a wider scope that included method, protocol and service-description files; the difference is itemized in [the scope delta]({prefix}docs/en/scope.md).",
        ]
    else:
        lines = [
            f"Dans la population documentaire principale, le collecteur a enregistré **{number(total, lang)} requêtes GET 200** de rôles IA dont l’origine fournisseur a été enregistrée comme vérifiée par correspondance avec des plages IP officielles, sur **{number(pairs, lang)} couples site-chemin distincts**.",
            f"Parmi ces requêtes, **{number(llms, lang)}** visaient `/llms.txt` et **{number(other, lang)}** d’autres fichiers de gouvernance, soit **{percent(share, lang)}** de la même sélection (même période, mêmes sites, même périmètre, même méthode, même statut et même niveau d’identification). Cette part décrit la répartition des requêtes enregistrées ; ce n’est pas un taux d’adoption.",
            f"Par site : {by_site}. Par rôle d’acteur enregistré : collecte pour entraînement {roles[0]}, recherche IA {roles[1]}, récupération à la demande {roles[2]} ; sans les récupérations à la demande, il reste {number(edition.m('main.sensitivity.without_user_fetch.get200'), lang)} requêtes (une lecture de sensibilité, pas une preuve d’indépendance).",
            f"Qualification : l’attribution à origine fournisseur n’utilise pas le prédicat Cloudflare en revue ; les niveaux qui l’utilisent restent à part. Le relevé interne initial comptait {number(hist, lang)} requêtes de cette nature sur un périmètre plus large incluant des fichiers de méthode, de protocole et de description de services ; l’écart est détaillé dans [le delta de périmètre]({prefix}docs/fr/perimetre.md).",
        ]
    return "\n\n".join(lines)


def figures_block(edition: Edition, lang: str, ids=("G02", "G05"), prefix="") -> str:
    figs = {f["figure_id"]: f for f in load_json(edition.dir / "figures.json")["figures"]}
    parts = []
    for figure_id in ids:
        fig = figs[figure_id]
        wide = f"{prefix}figures/{edition.id}/{figure_id}.{lang}.svg"
        compact = f"{prefix}figures/{edition.id}/{figure_id}.{lang}.compact.svg"
        alt = md_escape(fig[f"alt_{lang}"]).replace('"', "'")
        parts.append(f'<picture><source media="(max-width: 640px)" srcset="{compact}">'
                     f'<img src="{wide}" alt="{alt}" width="960"></picture>\n\n'
                     + t(lang, f"Data table: [{figure_id}.csv]({prefix}figures/{edition.id}/{figure_id}.csv)",
                         f"Table de données : [{figure_id}.csv]({prefix}figures/{edition.id}/{figure_id}.csv)"))
    return "\n\n".join(parts)


def case_rows(edition: Edition, lang: str, prefix="") -> str:
    cases = load_json(REPO_ROOT / "config" / "cases.json")["cases"]
    provider = _provider_by_path(edition)
    head = t(lang, "| Site | Angle | Starting page | Resources | Provider-origin AI GET 200 on these resources |\n|---|---|---|---:|---:|",
             "| Site | Angle | Page de départ | Ressources | GET 200 IA à origine fournisseur sur ces ressources |\n|---|---|---|---:|---:|")
    rows = []
    for case in cases:
        total = sum(provider.get((case["site_id"], r["path"]), 0) for r in case["resources"]
                    if r["path"] != "/robots.txt")
        readme = "README.md" if lang == "en" else "README.fr.md"
        rows.append(f"| [{case['site_id']}]({prefix}cases/{case['slug']}/{readme}) | {md_escape(case[f'angle_{lang}'])} | "
                    f"{code(case['start_page']['path'])} | {len(case['resources'])} | {number(total, lang)} |")
    note = t(lang, "The three sites belong to one author's ecosystem: three applications of one approach, not three independent replications. robots.txt is excluded from the last column.",
             "Les trois sites appartiennent à l’écosystème d’un même auteur : trois applications d’une même démarche, pas trois réplications indépendantes. robots.txt est exclu de la dernière colonne.")
    return head + "\n" + "\n".join(rows) + "\n\n" + note


def _provider_by_path(edition: Edition) -> dict:
    out = defaultdict(int)
    for row in read_csv(edition.dir / "consultations.csv"):
        if (row["http_method"] == "GET" and row["http_status"] == "200"
                and row["actor_role"] in ("ai_training", "ai_search", "user_initiated_fetch")
                and row["stored_identity_tier"] == "provider_origin_verified_actor"):
            out[(row["site_id"], row["path"])] += int(row["request_count"])
    return dict(out)


def scope_delta(edition: Edition, lang: str) -> str:
    rows = [r for r in read_csv(edition.dir / "exclusions.csv") if r["dimension"] == "scope"]
    head = t(lang, "| Scope class | Site-path pairs with rows | All requests | Provider-origin AI GET 200 |\n|---|---:|---:|---:|",
             "| Classe de périmètre | Couples site-chemin avec lignes | Toutes requêtes | GET 200 IA à origine fournisseur |\n|---|---:|---:|---:|")
    lines = [f"| {code(r['excluded_value'])} | {number(int(r['site_pairs']), lang)} | {number(int(r['requests_all_actors']), lang)} | "
             f"{number(int(r['provider_origin_ai_get200']), lang)} |" for r in rows]
    summary = t(lang,
                f"Main documentary population: {number(edition.m('main.get200'), lang)} requests on {number(edition.m('main.site_path_pairs'), lang)} pairs. Initial report scope: {number(edition.m('historical.provider_ai.get200'), lang)} on {number(edition.m('historical.provider_ai.site_path_pairs'), lang)}. Removed by the scope review: {number(edition.m('main.scope_delta.provider_ai_get200_excluded'), lang)}. Extended layer with supporting documentation (secondary reading): {number(edition.m('extended.get200'), lang)} on {number(edition.m('extended.site_path_pairs'), lang)} pairs. robots.txt and the undeclared bucket were already outside the initial report scope.",
                f"Population documentaire principale : {number(edition.m('main.get200'), lang)} requêtes sur {number(edition.m('main.site_path_pairs'), lang)} couples. Périmètre du relevé initial : {number(edition.m('historical.provider_ai.get200'), lang)} sur {number(edition.m('historical.provider_ai.site_path_pairs'), lang)}. Retirées par la revue du périmètre : {number(edition.m('main.scope_delta.provider_ai_get200_excluded'), lang)}. Couche élargie avec la documentation de soutien (lecture secondaire) : {number(edition.m('extended.get200'), lang)} sur {number(edition.m('extended.site_path_pairs'), lang)} couples. robots.txt et le compartiment non déclaré étaient déjà hors du périmètre du relevé initial.")
    return head + "\n" + "\n".join(lines) + "\n\n" + summary


def reconciliation_table(edition: Edition, lang: str) -> str:
    doc = load_json(edition.dir / "reconciliation.json")
    head = t(lang, "| Historical figure | Expected | Recomputed | Status |\n|---|---:|---:|---|",
             "| Chiffre historique | Attendu | Recalculé | État |\n|---|---:|---:|---|")
    lines = []
    for line in doc["historical_figures"]["lines"]:
        expected, computed = line["expected"], line["computed"]
        fmt = (lambda v: number(v, lang)) if isinstance(expected, int) else str
        lines.append(f"| {code(line['key'])} | {fmt(expected)} | {fmt(computed)} | {line['status']} |")
    combined = next((line["computed"] for line in doc["historical_figures"]["lines"]
                     if line["key"] == "heterogeneous_provider_plus_network_ai_get200"), None)
    note = t(lang, f"Same exports, same filters, this repository's own code. This is a reproduction of arithmetic, not an independent audit: the exports and the initial report come from the same producer chain. The combined figure of {number(combined, lang)} mixes two identification levels and is never presented as a homogeneous total.",
             f"Mêmes exports, mêmes filtres, code propre à ce dépôt. C’est une reproduction arithmétique, pas un audit indépendant : les exports et le relevé initial viennent de la même chaîne productrice. Le total combiné de {number(combined, lang)} mêle deux niveaux d’identification et n’est jamais présenté comme un total homogène.")
    return head + "\n" + "\n".join(lines) + "\n\n" + note


def coverage_summary(edition: Edition, lang: str) -> str:
    days = edition.m("coverage.days_in_window")
    return t(lang,
             f"{number(edition.m('coverage.days_observed'), lang)} of {number(days, lang)} days have archived rows; all {number(edition.m('coverage.days_partial_declared'), lang)} archive reports are partial (declared), {number(edition.m('coverage.days_attestation_missing'), lang)} with missing collector window attestation and {number(edition.m('coverage.aggregate_v3_mismatch_days'), lang)} with a one-request aggregate/V3 gap ({edition.metrics['coverage.aggregate_v3_mismatch_days']['filters'].replace(';', ', ')}). Archived aggregate sum {number(edition.m('coverage.aggregate_sum'), lang)}, V3 sum {number(edition.m('coverage.v3_sum'), lang)}. Rows on {number(edition.m('coverage.days_observed'), lang)} days do not prove complete coverage.",
             f"{number(edition.m('coverage.days_observed'), lang)} jours sur {number(days, lang)} ont des lignes archivées ; les {number(edition.m('coverage.days_partial_declared'), lang)} rapports d’archive sont partiels (déclarés), {number(edition.m('coverage.days_attestation_missing'), lang)} sans attestation de fenêtre du collecteur et {number(edition.m('coverage.aggregate_v3_mismatch_days'), lang)} avec un écart agrégat/V3 d’une requête ({edition.metrics['coverage.aggregate_v3_mismatch_days']['filters'].replace(';', ', ')}). Somme agrégée archivée {number(edition.m('coverage.aggregate_sum'), lang)}, somme V3 {number(edition.m('coverage.v3_sum'), lang)}. Des lignes sur {number(edition.m('coverage.days_observed'), lang)} jours ne prouvent pas une couverture intégrale.")


def incidence_table(edition: Edition, lang: str) -> str:
    deployments = edition.catalog.get("producer_deployments") or []
    history = edition.catalog.get("producer_deployment_history") or {}
    head = t(lang,
             "| Producer deployment (label) | Effective | Measured days covered | Source code available | Deployment established by | Classifier | Predicate `verifiedBotCategory != null` | Signals kept | Defect applies to | Re-evaluation possible |\n|---|---|---|---|---|---|---|---|---|---|",
             "| Déploiement du producteur (étiquette) | Effectif | Jours mesurés couverts | Code source disponible | Déploiement établi par | Classificateur | Prédicat `verifiedBotCategory != null` | Signaux conservés | Défaut applicable à | Réévaluation possible |\n|---|---|---|---|---|---|---|---|---|---|")
    days = [r for r in read_csv(edition.dir / "coverage.csv")]
    lines = []
    for deployment in deployments:
        covered = [r["date_utc"] for r in days if deployment["label"] in (r["producer_deployment_label"] or "").split("+")]
        span = f"{covered[0]} {t(lang, 'to', 'au')} {covered[-1]}" if covered else t(lang, "none", "aucun")
        share = "+".join(f"{v['percentage']}%" if lang == "en" else f"{v['percentage']} %" for v in deployment["versions"])
        lines.append(t(lang,
                       f"| {deployment['label']} | {deployment['effective_at'][:19]}Z, {share} | {span} | yes (private repository) | producer deployment history, {history.get('observations')} observations, longest gap {history.get('max_gap_hours')} h | 2026-08-24.1 | present (same file blob) | stored tier and role only; no raw Cloudflare signal | `cloudflare_verified_unattributed`, `network_verified_claimed_actor` | no for these two levels; the provider-origin level does not use the predicate |",
                       f"| {deployment['label']} | {deployment['effective_at'][:19]}Z, {share} | du {span} | oui (dépôt privé) | historique de déploiement du producteur, {history.get('observations')} relevés, plus long intervalle {str(history.get('max_gap_hours'))} h | 2026-08-24.1 | présent (même blob de fichier) | niveau et rôle enregistrés seulement ; aucun signal Cloudflare brut | `cloudflare_verified_unattributed`, `network_verified_claimed_actor` | non pour ces deux niveaux ; le niveau à origine fournisseur n’utilise pas le prédicat |"))
    note = t(lang, "Deployment labels replace private identifiers, which are kept in the internal lock. The commit identifiers attached to the archived daily reports change during the window without any deployment in this history; they are not treated as deployed versions. Reproducing the defect locally does not show that an empty category was received in production, nor that it explains the unattributed traffic.",
             "Les étiquettes de déploiement remplacent les identifiants privés, conservés dans le verrou interne. Les identifiants de commit attachés aux rapports quotidiens archivés changent pendant la fenêtre sans aucun déploiement dans cet historique ; ils ne sont pas traités comme des versions déployées. Reproduire le défaut localement ne montre pas qu’une catégorie vide a été reçue en production, ni qu’elle explique le trafic non attribué.")
    return head + "\n" + "\n".join(lines) + "\n\n" + note


def gate_coverage(lang: str) -> str:
    """Generated from gate.COVERAGE, which the mutation tests check one to one."""
    head = t(lang, "| Category | What the gate detects | Counterexamples tested |\n|---|---|---|",
             "| Catégorie | Ce que la porte détecte | Contre-exemples testés |\n|---|---|---|")
    rows = [f"| `{category}` | {t(lang, en, fr)} | " + "; ".join(t(lang, v_en, v_fr) for _, v_en, v_fr in variants) + " |"
            for category, en, fr, variants in gate.COVERAGE]
    tested = sum(len(variants) for *_, variants in gate.COVERAGE)
    note = t(lang,
             f"Each of the {tested} counterexamples above is planted by a mutation test in `tests/test_publication_gate.py`, which requires the gate to fail on it with that category; another test requires this table and the mutations to match one to one. A variant that is not listed is not claimed. Not covered: the pixels of a PNG, which render an SVG checked as text but are not read as text themselves, and content crafted on purpose to evade the gate.",
             f"Chacun des {tested} contre-exemples ci-dessus est placé par un test par mutation dans `tests/test_publication_gate.py`, qui exige l’échec de la porte dans cette catégorie ; un autre test exige que ce tableau et les mutations se correspondent un à un. Une variante non listée n’est pas revendiquée. Non couvert : les pixels d’un PNG, qui rendent un SVG contrôlé comme texte mais ne sont pas lus eux-mêmes comme du texte, et un contenu fabriqué exprès pour contourner la porte.")
    return head + "\n" + "\n".join(rows) + "\n\n" + note


def blocks_for(edition: Edition, lang: str, prefix: str) -> dict:
    return {
        "dates": lambda: dates_box(edition, lang),
        "headline": lambda: headline(edition, lang, prefix),
        "figures-main": lambda: figures_block(edition, lang, prefix=prefix),
        "figures-all": lambda: figures_block(edition, lang, ids=("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G10"), prefix=prefix),
        "cases": lambda: case_rows(edition, lang, prefix=prefix),
        "scope-delta": lambda: scope_delta(edition, lang),
        "reconciliation": lambda: reconciliation_table(edition, lang),
        "coverage": lambda: coverage_summary(edition, lang),
        "incidence": lambda: incidence_table(edition, lang),
        "publication-gate": lambda: gate_coverage(lang),
    }


def fill_blocks(text: str, edition: Edition, lang: str, prefix: str) -> str:
    builders = blocks_for(edition, lang, prefix)

    def replace(match):
        key = match.group("key")
        if key not in builders:
            raise KeyError(f"unknown generated block {key}")
        body = builders[key]()
        return f"{match.group(1)}\n{body}\n{match.group(4)}"

    return BLOCK.sub(replace, text)


def documents() -> list[tuple[Path, str, str]]:
    """(path, language, link prefix to repository root) of every document with blocks."""
    docs = [(REPO_ROOT / "README.md", "en", ""), (REPO_ROOT / "README.fr.md", "fr", "")]
    for lang in ("en", "fr"):
        for path in sorted((REPO_ROOT / "docs" / lang).glob("*.md")):
            docs.append((path, lang, "../../"))
    return docs


def render_documents(edition: Edition, *, write: bool = True) -> list[str]:
    changed = []
    for path, lang, prefix in documents():
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        updated = fill_blocks(original, edition, lang, prefix)
        if lang == "fr":
            updated = typo.fr(updated)
        if updated != original:
            changed.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
            if write:
                write_text(path, updated)
    return changed


# ---------------------------------------------------------------- case pages


def render_cases(edition: Edition, *, write: bool = True) -> dict[str, str]:
    cases = load_json(REPO_ROOT / "config" / "cases.json")["cases"]
    resources = {(r["site_id"], r["path"]): r for r in read_csv(edition.dir / "resources.csv")}
    summary = {(r["site_id"], r["path"]): r for r in read_csv(edition.dir / "resource-summary.csv")}
    checks = {(c["site_id"], c["kind"], c["path"]): c["verified"] for c in load_json(edition.dir / "case-checks.json")["checks"]}
    provider = _provider_by_path(edition)
    outputs = {}
    for case in cases:
        site = case["site_id"]
        for lang in ("en", "fr"):
            text = case_page(edition, case, lang, resources, summary, checks, provider)
            if lang == "fr":
                text = typo.fr(text)
            name = f"cases/{case['slug']}/{'README.md' if lang == 'en' else 'README.fr.md'}"
            outputs[name] = text
            if write:
                write_text(REPO_ROOT / name, text)
    return outputs


def case_page(edition, case, lang, resources, summary, checks, provider) -> str:
    site = case["site_id"]
    p = "../../"
    other = "README.fr.md" if lang == "en" else "README.md"
    d = edition.catalog["dates"]
    lines = [
        f"# {t(lang, 'Case', 'Cas')} : {site}" if lang == "fr" else f"# Case: {site}",
        "",
        t(lang, f"[Français]({other}) · [Repository home]({p}README.md)", f"[English]({other}) · [Accueil du dépôt]({p}README.fr.md)"),
        "",
        f"> {t(lang, 'Edition', 'Édition')} {code(edition.id)} · {edition.catalog['labels'][f'period_{lang}']} · "
        + t(lang, f"graph snapshot {code(d['graph_snapshot_at'][site])} · candidate, not published",
            f"instantané du graphe {code(d['graph_snapshot_at'][site])} · candidate, non publiée"),
        "",
        "## " + t(lang, "Angle", "Angle"),
        "",
        md_escape(case[f"angle_{lang}"]),
        "",
        "## " + t(lang, "Concrete question", "Question concrète"),
        "",
        md_escape(case[f"question_{lang}"]),
        "",
        "## " + t(lang, "Starting page", "Page de départ"),
        "",
        f"{code(case['start_page']['path'])} ({t(lang, 'counterpart', 'équivalent')} {code(case['start_page']['counterpart'])}). "
        + md_escape(case["start_page"][f"why_{lang}"]),
        "",
        "## " + t(lang, "Available documentary path", "Parcours documentaire disponible"),
        "",
        t(lang, "Each step is a reference written in a file of the source snapshot, verified in [links.csv](" + p + f"data/editions/{edition.id}/links.csv). It shows what a reader can follow; it is not an observed robot path.",
          "Chaque étape est une référence écrite dans un fichier de l’instantané source, vérifiée dans [links.csv](" + p + f"data/editions/{edition.id}/links.csv). Elle montre ce qu’un lecteur peut suivre ; ce n’est pas un parcours de robot observé."),
        "",
    ]
    for source, target in case["path_steps"]:
        ok = checks.get((site, "path_step", f"{source} -> {target}"))
        lines.append(f"- {code(source)} → {code(target)}" + ("" if ok else t(lang, " (not verified)", " (non vérifié)")))
    lines += ["",
              "## " + t(lang, "Executed path", "Parcours exécuté"),
              "",
              t(lang, "No qualified execution trace is part of this edition. None is reconstructed from aggregate counts.",
                "Aucune trace d’exécution qualifiée ne fait partie de cette édition. Aucune n’est reconstituée à partir des comptes agrégés."),
              "",
              "## " + t(lang, "Documentary graph", "Graphe documentaire"),
              "",
              f'<picture><source media="(max-width: 640px)" srcset="{p}figures/{edition.id}/G09-{site}.{lang}.compact.svg">'
              f'<img src="{p}figures/{edition.id}/G09-{site}.{lang}.svg" alt="'
              + t(lang, f"Documentary relations between the case resources of {site} in the source snapshot",
                  f"Relations documentaires entre les ressources du cas {site} dans l’instantané source") + '" width="960"></picture>',
              "",
              "## " + t(lang, "Representative resources", "Ressources représentatives"),
              "",
              t(lang, "| Resource | Scope class | Role | Short excerpt (line) | Declared version or dates |\n|---|---|---|---|---|",
                "| Ressource | Classe de périmètre | Rôle | Extrait court (ligne) | Version ou dates déclarées |\n|---|---|---|---|---|")]
    for resource in case["resources"]:
        reg = resources.get((site, resource["path"]), {})
        verified = checks.get((site, "excerpt", resource["path"]))
        excerpt = md_escape(resource["excerpt"])
        mark = "" if verified else t(lang, " (not verified)", " (non vérifié)")
        lines.append(f"| {code(resource['path'])} | {code(reg.get('scope_class', 'n/a'))} | {md_escape(resource[f'role_{lang}'])} | "
                     f"« {excerpt} » ({resource['excerpt_line']}){mark} | {md_escape(resource[f'declared_{lang}'])} |"
                     if lang == "fr" else
                     f"| {code(resource['path'])} | {code(reg.get('scope_class', 'n/a'))} | {md_escape(resource[f'role_{lang}'])} | "
                     f"“{excerpt}” ({resource['excerpt_line']}){mark} | {md_escape(resource[f'declared_{lang}'])} |")
    lines += ["",
              t(lang, "Excerpts are quoted in the language of the file and verified verbatim against the snapshot ([case-checks.json](" + p + f"data/editions/{edition.id}/case-checks.json)). Declared dates are those written in the files; they are not deployment dates.",
                "Les extraits sont cités dans la langue du fichier et vérifiés mot pour mot contre l’instantané ([case-checks.json](" + p + f"data/editions/{edition.id}/case-checks.json)). Les dates déclarées sont celles écrites dans les fichiers ; ce ne sont pas des dates de déploiement."),
              "",
              "## " + t(lang, "Aggregated accesses", "Accès agrégés"),
              "",
              t(lang, f"{cap(edition.catalog['labels']['period_en'])}. Monthly totals per URL; they do not allow any path to be reconstructed.",
                f"{cap(edition.catalog['labels']['period_fr'])}. Totaux mensuels par URL ; ils ne permettent de reconstituer aucun parcours."),
              "",
              t(lang, "| Resource | Provider-origin AI GET 200 | Days with these requests | GET 200, all recorded classifications | HEAD | 304 |\n|---|---:|---:|---:|---:|---:|",
                "| Ressource | GET 200 IA à origine fournisseur | Jours avec ces requêtes | GET 200, toutes classifications enregistrées | HEAD | 304 |\n|---|---:|---:|---:|---:|---:|")]
    for resource in case["resources"]:
        row = summary.get((site, resource["path"]))
        if not row:
            lines.append(f"| {code(resource['path'])} | " + t(lang, "no row in this window", "aucune ligne dans cette fenêtre") + " | | | | |")
            continue
        lines.append(f"| {code(resource['path'])} | {number(int(row['provider_origin_ai_get200']), lang)} | {number(int(row['provider_origin_ai_get200_days']), lang)} | "
                     f"{number(int(row['get200_all_actors']), lang)} | {number(int(row['head_all_actors']), lang)} | {number(int(row['status304_all_actors']), lang)} |")
    lines += ["",
              t(lang, "Filters: GET 200 counts use the recorded method and status. The provider-origin columns keep only AI roles whose origin matched an official registry; “days” counts distinct UTC days with at least one such request, which says nothing about sessions or order. The all-classifications column is dominated by traffic recorded as unattributed, whose label is under review.",
                "Filtres : les GET 200 reprennent la méthode et le statut enregistrés. Les colonnes à origine fournisseur ne gardent que les rôles IA dont l’origine correspondait à un registre officiel ; « jours » compte les jours UTC distincts avec au moins une telle requête, sans rien dire des sessions ni de l’ordre. La colonne toutes classifications est dominée par du trafic enregistré non attribué, dont le libellé est en revue."),
              "",
              "## " + t(lang, "Limits of this case", "Limites propres au cas"),
              ""]
    lines += [f"- {md_escape(limit)}" for limit in case[f"limits_{lang}"]]
    lines += ["",
              "## " + t(lang, "Reproduce", "Reproduire"),
              "",
              t(lang, f"All counts above come from [resource-summary.csv]({p}data/editions/{edition.id}/resource-summary.csv) and [consultations.csv]({p}data/editions/{edition.id}/consultations.csv); relations from [links.csv]({p}data/editions/{edition.id}/links.csv); roles and scope classes from [resources.csv]({p}data/editions/{edition.id}/resources.csv). See [reproduction]({p}docs/en/reproduction.md).",
                f"Tous les comptes ci-dessus viennent de [resource-summary.csv]({p}data/editions/{edition.id}/resource-summary.csv) et [consultations.csv]({p}data/editions/{edition.id}/consultations.csv) ; les relations de [links.csv]({p}data/editions/{edition.id}/links.csv) ; rôles et classes de périmètre de [resources.csv]({p}data/editions/{edition.id}/resources.csv). Voir [reproduction]({p}docs/fr/reproduction.md)."),
              ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- index, latest, status


def render_index(edition: Edition) -> None:
    editions = load_json(REPO_ROOT / "config" / "editions.json")["editions"]
    index = {"schema_version": "dwr-index/1.0.0", "editions": [
        {"edition_id": e["edition_id"], "edition_type": e["edition_type"], "status": e["status"],
         "period_start_inclusive": e["period_start_inclusive"], "period_end_exclusive": e["period_end_exclusive"],
         "revision": e["revision"], "published_at": e["published_at"], "revised_at": e["revised_at"],
         "supersedes": e["supersedes"], "superseded_by": e["superseded_by"],
         "catalog": f"data/editions/{e['edition_id']}/catalog.json"} for e in editions]}
    write_json(REPO_ROOT / "data" / "index.json", index)
    published = [e for e in editions if e["status"] == "published" and e["published_at"]]
    latest = published[-1]["edition_id"] if published else None
    write_json(REPO_ROOT / "data" / "latest.json", {
        "schema_version": "dwr-latest/1.0.0", "latest_published_edition": latest,
        "rule": "points only to a reviewed public edition; never to a draft or to the last successful run",
        "reason": None if latest else "no edition has been reviewed and published yet"})
    operations = load_json(REPO_ROOT / "config" / "operations.json")
    last = operations["reviews"][-1]
    write_json(REPO_ROOT / "data" / "status.json", {
        "schema_version": "dwr-status/1.0.0",
        "realtime": False,
        "automation": operations["automation"],
        "latest_published_edition": latest,
        "candidate_edition": edition.id,
        "candidate_state": last["state"],
        "last_review": {"date": last["date"], "kind": last["kind"], "state": last["state"]},
        "latest_available_data_date": edition.catalog["dates"]["latest_available_data_date"],
        "next_review_target": edition.catalog["dates"]["next_review_target"],
        "freshness_rule": "the date of data never advances on an unchanged run or a failed source",
    })


# ---------------------------------------------------------------- schemas


def render_schemas() -> None:
    from . import project
    types = defaultdict(lambda: "string")
    integer_fields = {"request_count", "requests", "get200", "site_pairs", "requests_all_actors", "get200_all_actors",
                      "provider_origin_ai_get200", "head_all_actors", "status304_all_actors", "status4xx5xx_all_actors",
                      "days_with_rows", "get200_days_all_actors", "provider_origin_ai_get200_days", "outbound_relations",
                      "inbound_relations", "evidence_line", "occurrences", "aggregate_count", "v3_count",
                      "aggregate_minus_v3", "snapshots_for_date", "distinct_paths_in_group"}
    boolean_fields = {"main_population", "llms_txt", "declares_canonical_source", "mentions_runtime_or_mcp",
                      "found_in_snapshot", "export_matches_archive", "joint_matches_archive"}
    keys = {
        "consultations.csv": ["site_id", "path", "http_method", "http_status", "actor_family", "actor_name", "actor_role", "stored_identity_tier"],
        # Every key below is the full grain of its table: no two rows share it (verify checks it).
        "resources.csv": ["resource_id"],
        "links.csv": ["source_site", "source_path", "target_site", "target_path", "relation_type"],
        "resource-summary.csv": ["resource_id"],
        "daily-summary.csv": ["date_utc", "site_id", "population", "actor_role", "stored_identity_tier", "http_method", "http_status"],
        "actor-summary.csv": ["population", "site_id", "actor_family", "actor_name", "actor_role", "stored_identity_tier"],
        "coverage.csv": ["date_utc"],
        "exclusions.csv": ["exclusion_id"],
        "daily-family-summary.csv": ["date_utc", "family", "actor_role"],
    }
    tables = {
        "consultations.csv": project.CONSULTATION_FIELDS, "resources.csv": project.RESOURCE_FIELDS,
        "links.csv": project.LINK_FIELDS, "resource-summary.csv": project.RESOURCE_SUMMARY_FIELDS,
        "daily-summary.csv": project.DAILY_FIELDS, "actor-summary.csv": project.ACTOR_FIELDS,
        "coverage.csv": project.COVERAGE_FIELDS, "exclusions.csv": project.EXCLUSION_FIELDS,
        "daily-family-summary.csv": project.FAMILY_DAILY_FIELDS,
    }
    for name, fields in tables.items():
        schema = {
            "$comment": "Table schema (Frictionless-style). UTF-8, LF, comma, header row, RFC 4180 quoting; decimal point; ISO 8601 dates; empty cell = null (never zero).",
            "schema_version": "dwr-public/1.0.0",
            "name": name,
            "primaryKey": keys[name],
            "fields": [{"name": field, "type": "integer" if field in integer_fields else
                        "boolean" if field in boolean_fields else "string",
                        "constraints": {"minimum": 0} if field in integer_fields else {}} for field in fields],
        }
        write_json(REPO_ROOT / "schemas" / (name.replace(".csv", ".schema.json")), schema)


def cmd(edition_id: str) -> dict:
    edition = Edition(edition_id)
    figures = render_figures(edition)
    cases = render_cases(edition)
    changed = render_documents(edition)
    render_index(edition)
    render_schemas()
    return {"edition_id": edition_id, "figures": len(figures["figures"]), "case_pages": sorted(cases),
            "documents_updated": changed}
