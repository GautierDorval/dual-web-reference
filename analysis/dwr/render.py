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
from . import typo, edition_rules
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
    def __init__(self, edition_id: str, directory=None, entry=None):
        self.id = edition_id
        self.dir = directory or REPO_ROOT / "data" / "editions" / edition_id
        self.catalog = load_json(self.dir / "catalog.json")
        self.entry = entry or next(e for e in load_json(REPO_ROOT / "config/editions.json")["editions"] if e["edition_id"] == edition_id)
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


def render_figures(edition: Edition, target=None) -> dict:
    target = target or REPO_ROOT / "figures" / edition.id
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
                              "layouts": "wide 960 px and compact 288 px; English and French"},
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
    status = edition_rules.status_label(edition.entry, lang)
    rows = [
        (t(lang, "Edition", "Édition"), code(edition.id)),
        (t(lang, "Status", "Statut"), status),
        (t(lang, "Availability", "Disponibilité"), code(edition.entry["availability_status"])),
        (t(lang, "Reference approval", "Approbation de référence"), code(edition.entry["reference_release_status"])),
        (t(lang, "Measured period", "Période mesurée"), edition.catalog["labels"][f"period_{lang}"]),
        ("period_start_inclusive", code(d["period_start_inclusive"])),
        ("period_end_exclusive", code(d["period_end_exclusive"])),
        ("last_included_date", code(d["last_included_date"])),
        ("extracted_at", code(f"{d['extracted_at']['start']} / {d['extracted_at']['end']}")),
        ("source_snapshot_at", code(d["source_snapshot_at"])),
        ("graph_snapshot_at", ", ".join(f"{site} {code(value)}" for site, value in d["graph_snapshot_at"].items())),
        ("generated_at", code(d["generated_at"])),
        ("approved_release_at", code(edition.entry.get("approved_release_at") or "null")),
        ("revised_at", code(d.get("revised_at") or "null")),
        ("latest_available_data_date", code(d["latest_available_data_date"])),
        (t(lang, "Updates", "Mises à jour"), t(lang, "periodic update planned; manual preparation (automation not activated)",
                                               "actualisation périodique prévue ; préparation manuelle (automatisation non activée)")),
    ]
    head = t(lang, "| Date or state | Value |\n|---|---|", "| Date ou état | Valeur |\n|---|---|")
    return head + "\n" + "\n".join(f"| {key} | {value} |" for key, value in rows)


def headline(edition: Edition, lang: str, prefix: str = "") -> str:
    total, pairs = edition.m("main.get200"), edition.m("main.site_path_pairs")
    llms, other = edition.m("main.llms_get200"), edition.m("main.other_get200")
    if "main.recorded_pairs" not in edition.metrics:
        return t(lang, "Historical edition: see its frozen metrics.", "Édition historique : voir ses métriques figées.")
    m = lambda key: number(edition.m(key), lang)
    case = prefix + "cases/gautierdorval.com/" + ("README.fr.md" if lang == "fr" else "README.md")
    if lang == "fr":
        lines = [
            f"**{number(pairs, lang)} URL documentaires touchées · {number(total, lang)} accès · {number(len(SITE_IDS), lang)} sites d’un même écosystème.** {cap(edition.catalog['labels']['period_fr'])}.",
            "Sélection principale : requêtes GET 200 de rôles IA, origine fournisseur enregistrée comme vérifiée par correspondance avec des plages IP officielles. **Couverture partielle déclarée.** Une requête ne prouve ni compréhension, ni adoption, ni effet causal.",
            f"[Voir le cas Gautier Dorval]({case}) : partir de la politique IA, distinguer identité, sources et limites, puis examiner les relations de l’instantané.",
            f"**{number(llms, lang)}** accès visaient `llms.txt` et **{number(other, lang)}** les autres fichiers. La part de {percent(edition.m('main.other_share'), lang)} hors `llms.txt` décrit cette sélection ; elle ne mesure pas une préférence. Parmi les {m('main.recorded_pairs')} ressources principales ayant des lignes, tous acteurs, méthodes et statuts confondus, {number(pairs, lang)} ont été touchées dans la sélection principale. Ce dénominateur n’est pas l’inventaire historique complet du Web documentaire.",
            f"Par ressource avec lignes : {m('main.llms_get200')}/{m('main.llms_recorded_pairs')} = {m('main.llms_requests_per_recorded_url')} accès pour `llms.txt`, contre {m('main.other_get200')}/{m('main.other_recorded_pairs')} = {edition.m('main.other_requests_per_recorded_url'):.2f} ailleurs. Disponibilité et exposition ne sont pas contrôlées.",
            f"GPTBot : {m('main.actor_name.GPTBot.get200')} ; OAI-SearchBot : {m('main.actor_name.OAI-SearchBot.get200')} ; PerplexityBot : {m('main.actor_name.PerplexityBot.get200')} ; ChatGPT-User : {m('main.actor_name.ChatGPT-User.get200')}. La famille OpenAI représente {m('main.actor_family.openai.get200')}/{number(total, lang)} accès ; ce n’est pas une part de marché de tous les agents.",
            f"Hors récupérations à la demande : {m('main.daily.sum_check')} accès automatisés sur {m('main.daily.days_with_requests')} jours ; les trois journées les plus actives en portent {m('main.automated.top3_days_get200')}, soit {percent(edition.m('main.automated.top3_days_share'), lang)}. {m('main.recurrence.pairs_with_1_days')} des {number(pairs, lang)} couples ont des accès sur un seul jour.",
            f"Exclusion explicite : {m('main.failed_origin_selected.get200')} requêtes sous ces quatre noms ont une **vérification d’origine échouée selon le producteur**, sur {number(edition.metrics['main.failed_origin_selected.share']['denominator'], lang)} requêtes des seuls niveaux fournisseur vérifié et vérification échouée retenus. Aucune usurpation n’est démontrée. Sur PAGUP : aucun GET 200 de `llms.txt` dans cette sélection et cette fenêtre ; un accès antérieur reste possible.",
        ]
    else:
        lines = [
            f"**{number(pairs, lang)} documentary URLs reached · {number(total, lang)} accesses · {number(len(SITE_IDS), lang)} sites in one ecosystem.** {cap(edition.catalog['labels']['period_en'])}.",
            "Main selection: GET 200 requests from AI roles, with provider origin recorded as verified against official IP ranges. **Declared partial coverage.** A request does not prove understanding, adoption or a causal effect.",
            f"[Explore the Gautier Dorval case]({case}): start at the AI policy, distinguish identity, sources and limits, then examine the snapshot relations.",
            f"**{number(llms, lang)}** accesses went to `llms.txt` and **{number(other, lang)}** to other files. The {percent(edition.m('main.other_share'), lang)} share outside `llms.txt` describes this selection; it does not measure preference. Of {m('main.recorded_pairs')} main resources with rows across all actors, methods and statuses, {number(pairs, lang)} were reached in the main selection. This denominator is not a complete historical documentary-web inventory.",
            f"Per resource with rows: {m('main.llms_get200')}/{m('main.llms_recorded_pairs')} = {m('main.llms_requests_per_recorded_url')} accesses for `llms.txt`, versus {m('main.other_get200')}/{m('main.other_recorded_pairs')} = {edition.m('main.other_requests_per_recorded_url'):.2f} elsewhere. Availability and exposure are not controlled.",
            f"GPTBot: {m('main.actor_name.GPTBot.get200')}; OAI-SearchBot: {m('main.actor_name.OAI-SearchBot.get200')}; PerplexityBot: {m('main.actor_name.PerplexityBot.get200')}; ChatGPT-User: {m('main.actor_name.ChatGPT-User.get200')}. The OpenAI family accounts for {m('main.actor_family.openai.get200')}/{number(total, lang)} accesses; this is not market share across all agents.",
            f"Excluding user-initiated fetches: {m('main.daily.sum_check')} automated accesses on {m('main.daily.days_with_requests')} days; the three busiest days account for {m('main.automated.top3_days_get200')}, or {percent(edition.m('main.automated.top3_days_share'), lang)}. {m('main.recurrence.pairs_with_1_days')} of the {number(pairs, lang)} pairs received requests on only one day.",
            f"Explicit exclusion: {m('main.failed_origin_selected.get200')} requests under those four names have **failed origin verification according to the producer**, among {number(edition.metrics['main.failed_origin_selected.share']['denominator'], lang)} requests in the selected provider-verified and failed-verification tiers only. Spoofing is not demonstrated. On PAGUP: no GET 200 of `llms.txt` in this selection and window; an earlier access remains possible.",
        ]
    lines[1], lines[2] = lines[2], lines[1]
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
                    f"{code(case['start_page']['path'])}" + (f" (EN ; FR : {code(case['start_page']['counterpart'])})" if lang == "fr" and case["site_id"] == "gautierdorval.com" else "") + f" | {len(case['resources'])} | {number(total, lang)} |")
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
    if edition.catalog.get("metrics_version") == "dwr-metrics/2.0.0":
        return t(lang,
                 f"{number(edition.m('coverage.days_observed'), lang)} of {number(days, lang)} days have archived rows; {number(edition.m('coverage.days_partial_declared'), lang)} declared partial. Daily aggregate and V3 margins are withheld, not zero. Historical r1 preserves its two one-request gaps (October 6 and 13). The same observations are used; partial coverage has not been upgraded.",
                 f"{number(edition.m('coverage.days_observed'), lang)} jours sur {number(days, lang)} ont des lignes archivées ; {number(edition.m('coverage.days_partial_declared'), lang)} sont déclarés partiels. Les marges agrégées et V3 quotidiennes sont retenues, pas égales à zéro. r1 conserve ses deux écarts d’une requête (6 et 13 octobre). Les observations restent les mêmes ; la couverture partielle n’est pas requalifiée.")
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
    rows = [f"| `{category}` | {t(lang, en, fr)} | " + t(lang, "; ", "\u202f; ").join(t(lang, v_en, v_fr) for _, v_en, v_fr in variants) + " |"
            for category, en, fr, variants in gate.COVERAGE]
    tested = sum(len(variants) for *_, variants in gate.COVERAGE)
    note = t(lang,
             f"Each of the {tested} counterexamples above is planted by a mutation test in `tests/test_publication_gate.py`, which requires the gate to fail on it with that category; another test requires this table and the mutations to match one to one. A variant that is not listed is not claimed. Not covered: the pixels of a PNG, which render an SVG checked as text but are not read as text themselves, and content crafted on purpose to evade the gate.",
             f"Chacun des {tested} contre-exemples ci-dessus est placé par un test par mutation dans `tests/test_publication_gate.py`, qui exige l’échec de la porte dans cette catégorie ; un autre test exige que ce tableau et les mutations se correspondent un à un. Une variante non listée n’est pas revendiquée. Non couvert : les pixels d’un PNG, qui rendent un SVG contrôlé comme texte mais ne sont pas lus eux-mêmes comme du texte, et un contenu fabriqué exprès pour contourner la porte.")
    return head + "\n" + "\n".join(rows) + "\n\n" + note


def blocks_for(edition: Edition, lang: str, prefix: str) -> dict:
    return {
        "dates": lambda: dates_box(edition, lang),
        "edition-state": lambda: t(lang, "Edition r", "Édition r") + str(edition.entry["revision"]) + t(lang, ": ", " : ") + edition_rules.status_label(edition.entry, lang) + ". " + t(lang, "r1 remains public and byte-frozen.", "r1 demeure publique et figée."),
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
        + t(lang, f"graph snapshot {code(d['graph_snapshot_at'][site])} · ",
            f"instantané du graphe {code(d['graph_snapshot_at'][site])} · ") + edition_rules.status_label(edition.entry, lang, scientific=False),
        "",
        t(lang, f"**{number(edition.m('main.site.' + site + '.site_path_pairs'), lang)} documentary URLs; {number(edition.m('main.site.' + site + '.get200'), lang)} provider-origin AI GET 200 on this site.** Partial coverage; one of three cases in the same author's ecosystem, not an independent replication.",
                f"**{number(edition.m('main.site.' + site + '.site_path_pairs'), lang)} URL documentaires ; {number(edition.m('main.site.' + site + '.get200'), lang)} GET 200 IA à origine fournisseur sur ce site.** Couverture partielle ; un des trois cas du même écosystème d’auteur, pas une réplication indépendante."),
        "",
        "## " + t(lang, "Question and scope", "Question et portée"),
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
    lines += [t(lang, "Copyable paths only. A manually visited online resource may differ from the dated snapshot; full private snapshot bytes are not distributed.",
                     "Chemins copiables seulement. Une ressource visitée manuellement en ligne peut différer de l’instantané daté ; les octets complets de l’instantané privé ne sont pas distribués."), ""]
    lines += ["## " + t(lang, "Read by function", "Lire par fonction"), ""]
    for resource in case["resources"][:7]:
        lines.append("- " + code(resource["path"]) + " : " + md_escape(resource[f"role_{lang}"]))
    lines += ["", t(lang, "These seven reading landmarks introduce the full source and count tables below; no observation or scope is removed.",
                         "Ces sept repères de lecture introduisent les tables complètes de sources et de comptes ci-dessous ; aucune observation ni classe de périmètre n’est retirée."), ""]
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
              t(lang, f"{cap(edition.catalog['labels']['period_en'])}. Monthly totals per URL; they do not establish an executed session or navigation order.",
                f"{cap(edition.catalog['labels']['period_fr'])}. Totaux mensuels par URL ; ils n’établissent aucune session exécutée ni ordre de navigation."),
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
         **{k: e.get(k) for k in ("availability_status", "review_status", "reference_release_status", "scientific_review_status", "public_availability_evidence", "approved_release_at")},
         "declared_reference_release_status": e.get("reference_release_status"),
         "reference_release_status": edition_rules.reference_state(e),
         "catalog": f"data/editions/{e['edition_id']}/catalog.json"} for e in editions]}
    write_json(REPO_ROOT / "data" / "index.json", index)
    from .edition_rules import latest_pointer
    latest = latest_pointer(editions)
    write_json(REPO_ROOT / "data" / "latest.json", {
        "schema_version": "dwr-latest/1.0.0", "latest_published_edition": latest,
        "rule": "shared latest_pointer selects an externally approved public payload with a matching receipt; never a candidate or a successful run",
        "reason": None if latest else "no publicly accessible edition has a matching approved reference receipt"})
    operations = load_json(REPO_ROOT / "config" / "operations.json")
    last = next(row for row in reversed(operations["reviews"]) if row["edition_id"] == edition.id)
    effective = edition_rules.reference_state(edition.entry)
    current_state = {"approved": "approved_reference", "approval_invalid": "approval_invalid"}.get(effective, last["state"])
    review_record = {"date": last["date"], "kind": last["kind"], "state": last["state"]}
    if effective == "approved":
        review_record = {"date": edition.entry["approval_receipt"]["reviewed_at"], "kind": "reference_approval", "state": "approved"}
    from .dates import window_from_strings, next_monthly_window
    from datetime import datetime, timezone, timedelta
    calendar = load_json(REPO_ROOT / "config/edition-calendar.json")
    window = next_monthly_window(window_from_strings(edition.entry["period_start_inclusive"], edition.entry["period_end_exclusive"]), calendar["monthly_anchor_day"])
    ready = datetime.combine(window.end_exclusive, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=calendar["consolidation_delay_hours"])
    target = {"weekly_review": None, "weekly_review_template": calendar["weekly_review"],
              "next_monthly_window": {"start_inclusive":window.start.isoformat(),"end_exclusive":window.end_exclusive.isoformat(),"days":window.days},
              "earliest_monthly_preparation":ready.isoformat().replace("+00:00","Z"),
              "guarantee":"none; inactive planning template"}

    write_json(REPO_ROOT / "data" / "status.json", {
        "schema_version": "dwr-status/1.0.0",
        "realtime": False,
        "automation": operations["automation"],
        "preparation": operations.get("preparation"),
        "latest_published_edition": latest,
        "candidate_edition": edition.id,
        "candidate_state": current_state,
        "reference_approval_state": effective,
        "last_review": review_record,
        "latest_available_data_date": edition.catalog["dates"]["latest_available_data_date"],
        "next_review_target": target,
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
        "consultations.csv": ["measurement_epoch_id", "site_id", "path", "http_method", "http_status", "actor_family", "actor_name", "actor_role", "stored_identity_tier"],
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
    from .frozen import verify as verify_frozen
    historical = verify_frozen(edition_id)
    if historical:
        return historical
    edition = Edition(edition_id)
    figures = render_figures(edition)
    cases = render_cases(edition)
    changed = render_documents(edition)
    render_index(edition)
    render_schemas()
    return {"edition_id": edition_id, "figures": len(figures["figures"]), "case_pages": sorted(cases),
            "documents_updated": changed}
