"""build-site: static bilingual presentation in site/dist (never deployed by this command).

Pages are rendered from the same public files as the repository: README, docs,
case pages, figures, edition files. All main results are readable without
JavaScript; site/assets/explorer.js only adds filtering, sorting and a shareable
filter state in the URL fragment. No external script, font, CDN, analytics or
visitor tracking. Every link is relative, so the output works under a GitHub
Pages sub-path. Paths of the measured sites are shown as text, not links, so that
browsing the presentation never sends requests to them.
"""

from __future__ import annotations

import html
import posixpath
import shutil
from pathlib import Path

from . import mdlite, typo, edition_rules
from .common import REPO_ROOT, SITE_IDS, load_json, read_csv, write_text
from .i18n import number, t

DIST = REPO_ROOT / "site" / "dist"
DOC_PAGES = {
    "en": ["model", "file-roles", "discovery-and-linking", "methodology", "scope", "attribution", "quality-and-coverage",
           "privacy", "updates", "reproduction", "limits", "llms-txt-studies", "glossary"],
    "fr": ["modele", "roles-des-fichiers", "decouverte-et-maillage", "methode", "perimetre", "attribution",
           "qualite-et-couverture", "confidentialite", "mises-a-jour", "reproduction", "limites", "etudes-llms-txt", "glossaire"],
}
COPIED = ("data", "figures", "schemas", "config")
RAW_FILES = ("CHANGELOG.md", "CITATION.cff", "NOTICE.md", "SECURITY.md", "CONTRIBUTING.md")


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def repo_target(source_rel: str, url: str) -> str | None:
    """Repository-relative path of a link written in the document at source_rel."""
    if url.startswith(("http://", "https://", "#", "mailto:")):
        return None
    path, _, fragment = url.partition("#")
    base = posixpath.dirname(source_rel)
    resolved = posixpath.normpath(posixpath.join(base, path)) if path else source_rel
    return resolved + (f"#{fragment}" if fragment else "")


def site_path(repo_rel: str) -> str:
    path, _, fragment = repo_rel.partition("#")
    suffix = f"#{fragment}" if fragment else ""
    if path == "README.md":
        return "en/index.html" + suffix
    if path == "README.fr.md":
        return "fr/index.html" + suffix
    parts = path.split("/")
    if len(parts) == 3 and parts[0] == "docs" and parts[2].endswith(".md"):
        return f"{parts[1]}/docs/{parts[2][:-3]}.html" + suffix
    if len(parts) == 3 and parts[0] == "cases":
        lang = "fr" if parts[2] == "README.fr.md" else "en"
        return f"{lang}/cases/{parts[1]}.html" + suffix
    if len(parts) >= 2 and parts[0] == "figures" and (path.endswith("/") or len(parts) == 2):
        return "en/figures.html"
    return path + suffix


def relative(from_page: str, to_path: str) -> str:
    target, _, fragment = to_path.partition("#")
    rel = posixpath.relpath(target, posixpath.dirname(from_page) or ".")
    return rel + (f"#{fragment}" if fragment else "")


def rewriter(source_rel: str, page: str):
    def rewrite(url: str) -> str:
        target = repo_target(source_rel, url)
        if target is None:
            return url
        return relative(page, site_path(target))
    return rewrite


def layout(page: str, lang: str, title: str, body: str, counterpart: str | None, edition_id: str) -> str:
    root = relative(page, "index.html").rsplit("index.html", 1)[0]
    nav = [
        (t(lang, "Home", "Accueil"), f"{lang}/index.html"),
        (t(lang, "Understand", "Comprendre"), f"{lang}/docs/{'file-roles' if lang == 'en' else 'roles-des-fichiers'}.html"),
        (t(lang, "Explorer", "Explorateur"), f"{lang}/explorer.html"),
        (t(lang, "Figures", "Figures"), f"{lang}/figures.html"),
        (t(lang, "Cases", "Cas"), f"{lang}/cases.html"),
        (t(lang, "Method", "Méthode"), f"{lang}/docs/{'methodology' if lang == 'en' else 'methode'}.html"),
        (t(lang, "Editions", "Éditions"), f"{lang}/editions.html"),
    ]
    current = ' aria-current="page"'
    links = "".join(f'<a href="{esc(relative(page, href))}"{current if href == page else ""}>{esc(label)}</a>'
                    for label, href in nav)
    switch = (f'<a class="lang" href="{esc(relative(page, counterpart))}" hreflang="{"fr" if lang == "en" else "en"}">'
              f'{"Français" if lang == "en" else "English"}</a>') if counterpart else ""
    from . import edition_rules
    entry = next(e for e in load_json(REPO_ROOT / "config/editions.json")["editions"] if e["edition_id"] == edition_id)
    banner = edition_rules.status_label(entry, lang, scientific=False) + "."
    if lang == "fr":
        banner = typo.fr(banner)
    return (f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex"><meta name="referrer" content="no-referrer">'
            f'<title>{esc(title)} · Dual Web Reference</title>'
            f'<link rel="stylesheet" href="{esc(root)}assets/style.css"></head>'
            f'<body><a class="skip" href="#main">{esc(t(lang, "Skip to content", "Aller au contenu"))}</a><header class="site"><div class="wrap"><a class="brand" href="{esc(relative(page, lang + "/index.html"))}">Dual Web Reference</a>'
            f'<nav aria-label="{esc(t(lang, "Main", "Principale"))}">{links}</nav>{switch}</div>'
            f'<p class="banner wrap">{esc(banner)}</p></header>'
            f'<main id="main" class="wrap" tabindex="-1">{body}</main>'
            f'<footer class="wrap"><p><a href="{esc(root)}CITATION.cff">Citation</a> · <a href="{esc(root)}CONTRIBUTING.md">Contribution</a> · <a href="{esc(root)}SECURITY.md">{esc(t(lang, "Security", "Sécurité"))}</a></p><p>{esc(t(lang, "Static presentation. Availability and approval are recorded in the edition registry. No tracking or external assets.", "Présentation statique. Disponibilité et approbation figurent au registre des éditions. Aucun traçage ni actif externe."))}</p></footer>'
            f'<script src="{esc(root)}assets/explorer.js" defer></script></body></html>\n')


def markdown_page(source_rel: str, page: str, lang: str, counterpart: str | None, edition_id: str) -> None:
    text = (REPO_ROOT / source_rel).read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), "Dual Web Reference")
    body = mdlite.render(text, rewriter(source_rel, page))
    write_text(DIST / page, layout(page, lang, title, body, counterpart, edition_id))


def table_html(columns, rows, *, table_id, filters=()) -> str:
    head = "".join(f'<th scope="col" data-key="{esc(key)}"><button type="button" class="sort" disabled>{esc(label)}</button></th>'
                   for key, label, _ in columns)
    body = []
    for row in rows:
        attrs = "".join(f' data-{esc(key)}="{esc(row.get(key, ""))}"' for key in filters)
        cells = "".join(f'<td class="{"num" if numeric else ""}" data-value="{esc(row.get(key, ""))}">{esc(row.get(key + "__display", row.get(key, "")))}</td>'
                        for key, _, numeric in columns)
        body.append(f"<tr{attrs}>{cells}</tr>")
    return (f'<div class="table-wrap" tabindex="0" role="region" aria-label="{esc(table_id)}"><table id="{esc(table_id)}" class="data"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def select(name, label, values, lang) -> str:
    options = f'<option value="">{esc(t(lang, "all", "tous"))}</option>' + "".join(
        f'<option value="{esc(value)}">{esc(value)}</option>' for value in values)
    return f'<label>{esc(label)} <select disabled data-filter="{esc(name)}">{options}</select></label>'


def explorer_page(edition_id: str, lang: str) -> None:
    edition = REPO_ROOT / "data" / "editions" / edition_id
    page = f"{lang}/explorer.html"
    resources = read_csv(edition / "resources.csv")
    summary = {r["resource_id"]: r for r in read_csv(edition / "resource-summary.csv")}
    rows = []
    for resource in resources:
        s = summary.get(resource["resource_id"], {})
        provider = s.get("provider_origin_ai_get200", "")
        rows.append({
            "site": resource["site_id"], "path": resource["path"], "scope": resource["scope_class"],
            "family": resource["family"], "format": resource["format"], "language": resource["language"],
            "main": "yes" if resource["main_population"] == "true" else "no",
            "provider": provider, "provider__display": number(int(provider), lang) if provider != "" else t(lang, "no row", "aucune ligne"),
            "get200": s.get("get200_all_actors", ""), "get200__display": number(int(s["get200_all_actors"]), lang) if s else "",
            "days": s.get("get200_days_all_actors", ""), "rows": resource["window_rows_status"],
        })
    columns = [("site", "Site", False), ("path", t(lang, "Path", "Chemin"), False),
               ("scope", t(lang, "Scope class", "Classe"), False), ("family", t(lang, "Family", "Famille"), False),
               ("format", "Format", False), ("main", t(lang, "Main population", "Population principale"), False),
               ("provider", t(lang, "Provider-origin AI GET 200", "GET 200 IA origine fournisseur"), True),
               ("get200", t(lang, "GET 200, all classifications", "GET 200, toutes classifications"), True),
               ("days", t(lang, "Days with GET 200 (all)", "Jours avec GET 200 (tous)"), True)]
    filters = ("site", "scope", "format", "family", "main")
    controls = "".join([
        select("site", "Site", SITE_IDS, lang),
        select("scope", t(lang, "Scope class", "Classe de périmètre"), sorted({r["scope"] for r in rows}), lang),
        select("family", t(lang, "Documentary family", "Famille documentaire"), sorted({r["family"] for r in rows}), lang),
        select("format", "Format", sorted({r["format"] for r in rows}), lang),
        select("main", t(lang, "Main population", "Population principale"), ["yes", "no"], lang),
    ])
    actors = read_csv(edition / "actor-summary.csv")
    actor_rows = [{"site": a["site_id"], "name": a["actor_name"], "role": a["actor_role"], "tier": a["stored_identity_tier"],
                   "assessment": a["attribution_assessment"], "get200": a["get200"],
                   "get200__display": number(int(a["get200"]), lang), "requests": a["requests"],
                   "requests__display": number(int(a["requests"]), lang), "paths": a["distinct_paths_in_group"]} for a in actors]
    actor_columns = [("site", "Site", False), ("name", t(lang, "Recorded actor name", "Nom d’acteur enregistré"), False),
                     ("role", t(lang, "Actor role", "Rôle d’acteur"), False), ("tier", t(lang, "Stored level", "Niveau enregistré"), False),
                     ("assessment", t(lang, "Assessment", "Appréciation"), False), ("get200", "GET 200", True),
                     ("requests", t(lang, "All requests", "Toutes requêtes"), True),
                     ("paths", t(lang, "Distinct paths in this group (not additive)", "Chemins distincts de ce groupe (non additifs)"), True)]
    actor_controls = "".join([
        select("site", "Site", SITE_IDS, lang),
        select("role", t(lang, "Actor role", "Rôle d’acteur"), sorted({r["role"] for r in actor_rows}), lang),
        select("tier", t(lang, "Identification level", "Niveau d’identification"), sorted({r["tier"] for r in actor_rows}), lang),
    ])
    actions = (f'<button type="button" class="reset" disabled>{esc(t(lang, "Reset filters", "Réinitialiser"))}</button>'
               f'<button type="button" class="export" disabled>{esc(t(lang, "Export visible rows (spreadsheet-safe CSV)", "Exporter les lignes visibles (CSV pour tableur)"))}</button>')
    controls += actions
    actor_controls += actions
    intro = t(lang,
              "Every table below is complete without JavaScript. Filters and sorting only hide or reorder rows; the filter state is kept in the address so it can be shared. Counts are those of the edition files; paths are shown as text and never fetched.",
              "Chaque tableau ci-dessous est complet sans JavaScript. Les filtres et le tri ne font que masquer ou réordonner des lignes ; l’état des filtres est conservé dans l’adresse et peut être partagé. Les comptes sont ceux des fichiers de l’édition ; les chemins sont affichés comme texte et jamais consultés.")
    body = (f"<h1>{esc(t(lang, 'Resource and data explorer', 'Explorateur des ressources et des données'))}</h1>"
            f"<p>{esc(intro)}</p>"
            f"<p>{esc(t(lang, 'Edition', 'Édition'))} <code>{esc(edition_id)}</code> · "
            f"{esc(load_json(edition / 'catalog.json')['labels']['period_' + lang])}</p>"
            f'<h2 id="resources-section">{esc(t(lang, "Resources", "Ressources"))}</h2>'
            f'<form class="filters" data-table="resources" onsubmit="return false">{controls}<output data-count="resources"></output></form>'
            + table_html(columns, rows, table_id="resources", filters=filters)
            + f'<p>{esc(t(lang, "Source:", "Source :"))} <a href="{esc(relative(page, f"data/editions/{edition_id}/resources.csv"))}">resources.csv</a>, '
              f'<a href="{esc(relative(page, f"data/editions/{edition_id}/resource-summary.csv"))}">resource-summary.csv</a></p>'
            + f'<h2 id="actors-section">{esc(t(lang, "Recorded actors (scope of the initial report)", "Acteurs enregistrés (périmètre du relevé initial)"))}</h2>'
            + f'<p>{esc(t(lang, "Levels under review are shown as recorded; they are never merged with the provider-origin level.", "Les niveaux en revue sont présentés tels qu’enregistrés ; ils ne sont jamais fusionnés avec le niveau à origine fournisseur."))}</p>'
            + f'<form class="filters" data-table="actors" onsubmit="return false">{actor_controls}<output data-count="actors"></output></form>'
            + table_html(actor_columns, actor_rows, table_id="actors", filters=("site", "role", "tier"))
            + f'<p>{esc(t(lang, "Source:", "Source :"))} <a href="{esc(relative(page, f"data/editions/{edition_id}/actor-summary.csv"))}">actor-summary.csv</a></p>')
    if lang == "fr":
        body = typo.fr(body)
    write_text(DIST / page, layout(page, lang, t(lang, "Explorer", "Explorateur"), body,
                                   f"{'fr' if lang == 'en' else 'en'}/explorer.html", edition_id))


def figures_page(edition_id: str, lang: str) -> None:
    page = f"{lang}/figures.html"
    document = load_json(REPO_ROOT / "data" / "editions" / edition_id / "figures.json")
    parts = [f"<h1>{esc(t(lang, 'Figures', 'Figures'))}</h1>",
             f"<p>{esc(t(lang, 'Each figure carries its period, population, unit, extraction date, edition and coverage. The table under each figure holds exactly the plotted values.', 'Chaque figure porte sa période, sa population, son unité, sa date d’extraction, son édition et sa couverture. Le tableau sous chaque figure contient exactement les valeurs tracées.'))}</p>"]
    for figure in document["figures"]:
        fid = figure["figure_id"]
        wide = relative(page, f"figures/{edition_id}/{fid}.{lang}.svg")
        compact = relative(page, f"figures/{edition_id}/{fid}.{lang}.compact.svg")
        rows = read_csv(REPO_ROOT / "figures" / edition_id / f"{fid}.csv")
        columns = [(key, key, all(r[key].lstrip("-").replace(".", "", 1).isdigit() for r in rows if r[key])) for key in rows[0].keys()] if rows else []
        parts.append(f'<section class="figure" id="{esc(fid)}"><h2>{esc(fid)}. {esc(figure["title_" + lang])}</h2>'
                     f'<figure><div class="plot-wrap" tabindex="0" role="region" aria-label="{esc(fid)}"><picture><source media="(max-width: 640px)" srcset="{esc(compact)}">'
                     f'<img src="{esc(wide)}" alt="{esc(figure["alt_" + lang])}" loading="lazy" width="960"></picture></div>'
                     f'<figcaption>{esc(figure["alt_" + lang])}</figcaption></figure>'
                     f'<details><summary>{esc(t(lang, "Data table", "Tableau de données"))}</summary>'
                     + table_html(columns, rows, table_id=f"table-{fid}")
                     + f'</details><p><a href="{esc(relative(page, figure["data_table"]["path"]))}">{esc(fid)}.csv</a></p></section>')
    body = "".join(parts)
    if lang == "fr":
        body = typo.fr(body)
    write_text(DIST / page, layout(page, lang, "Figures", body, f"{'fr' if lang == 'en' else 'en'}/figures.html", edition_id))


def cases_index(edition_id: str, lang: str) -> None:
    page = f"{lang}/cases.html"
    cases = load_json(REPO_ROOT / "config" / "cases.json")["cases"]
    items = "".join(f'<li><a href="{esc(relative(page, f"{lang}/cases/{c["slug"]}.html"))}">{esc(c["site_id"])}</a>: '
                    f'{esc(c["angle_" + lang])}</li>' for c in cases)
    note = load_json(REPO_ROOT / "config" / "sites.json")[f"ecosystem_note_{lang}"]
    body = f"<h1>{esc(t(lang, 'Three cases', 'Trois cas'))}</h1><p>{esc(note)}</p><ul>{items}</ul>"
    if lang == "fr":
        body = typo.fr(body)
    write_text(DIST / page, layout(page, lang, t(lang, "Cases", "Cas"), body, f"{'fr' if lang == 'en' else 'en'}/cases.html", edition_id))


def editions_page(edition_id: str, lang: str) -> None:
    page = f"{lang}/editions.html"
    index = load_json(REPO_ROOT / "data" / "index.json")
    latest = load_json(REPO_ROOT / "data" / "latest.json")
    status = load_json(REPO_ROOT / "data" / "status.json")
    entries = load_json(REPO_ROOT / "config/editions.json")["editions"]
    reference_labels = {"approved": ("approved", "approuvée"), "approval_invalid": ("approval invalid", "approbation invalide"),
                        "not_approved": ("not approved", "non approuvée")}
    availability = {"publicly_accessible": ("publicly accessible", "accessible publiquement"),
                    "local_candidate": ("local candidate", "candidate locale"), "private_candidate": ("private candidate", "candidate privée")}
    review_states = {"approved": ("approved", "approuvée"), "awaiting_review": ("awaiting review", "en attente de revue"),
                     "approval_invalid": ("approval invalid", "approbation invalide")}
    latest_label = latest["latest_published_edition"] or t(lang, "none", "aucune")
    review_state = review_states.get(status["last_review"]["state"], ("see registry", "voir le registre"))[lang == "fr"]
    rows = []
    for e in entries:
        effective = edition_rules.reference_state(e)
        rows.append({"edition": e["edition_id"], "type": t(lang, "Monthly reference", "Référence mensuelle") if e["edition_type"] == "monthly_reference" else e["edition_type"],
                     "status": availability.get(e["availability_status"], ("unknown", "inconnue"))[lang == "fr"],
                     "reference": reference_labels[effective][lang == "fr"], "review": edition_rules.review_label(e, lang),
                     "start": e["period_start_inclusive"], "end": e["period_end_exclusive"], "revision": e["revision"],
                     "published": e["approved_release_at"] if effective == "approved" else t(lang, "not approved", "non approuvée"),
                     "revised": e["revised_at"] or "null"})
    columns = [("edition", t(lang, "Edition", "Édition"), False), ("type", "Type", False), ("status", t(lang, "Status", "Statut"), False),
               ("reference", t(lang, "Reference", "Référence"), False), ("review", t(lang, "Declared review decisions", "Décisions de revue déclarées"), False),
               ("start", t(lang, "Start included (UTC)", "Début inclus (UTC)"), False), ("end", t(lang, "End excluded (UTC)", "Fin exclue (UTC)"), False), ("revision", t(lang, "Revision", "Révision"), True),
               ("published", t(lang, "Approval date", "Date d’approbation"), False), ("revised", t(lang, "Revised on", "Révisée le"), False)]
    body = (f"<h1>{esc(t(lang, 'Editions', 'Éditions'))}</h1>"
            f"<p>{esc(t(lang, 'Latest approved reference: ', 'Dernière référence approuvée : '))}<code>{esc(latest_label)}</code> "
            f"</p>"
            f"<p>{esc(status['automation']['label_' + lang])} "
            f"{esc(t(lang, 'Last review: ', 'Dernière revue : '))}<code>{esc(status['last_review']['date'])}</code> ({esc(review_state)}). "
            f"{esc(t(lang, 'Latest available data date: ', 'Dernière date de données disponible : '))}<code>{esc(status['latest_available_data_date'])}</code>.</p>"
            + table_html(columns, rows, table_id="editions")
            + f"<p>{esc(t(lang, 'One observed window, two revisions. r1 remains publicly accessible with its original bytes; r2 is a privacy revision; its current state appears above. No trend between periods is computed.', 'Une fenêtre observée, deux révisions. r1 reste accessible publiquement avec ses octets d’origine ; r2 est une révision de confidentialité ; son état courant figure ci-dessus. Aucune tendance entre périodes n’est calculée.'))}</p>")
    if lang == "fr":
        body = typo.fr(body)
    write_text(DIST / page, layout(page, lang, t(lang, "Editions", "Éditions"), body, f"{'fr' if lang == 'en' else 'en'}/editions.html", edition_id))


def cmd(edition_id: str) -> dict:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    for folder in COPIED:
        shutil.copytree(REPO_ROOT / folder, DIST / folder, ignore=shutil.ignore_patterns("*.example"))
    for name in RAW_FILES:
        if (REPO_ROOT / name).is_file():
            shutil.copy2(REPO_ROOT / name, DIST / name)
    (DIST / "assets").mkdir()
    for asset in ("style.css", "explorer.js"):
        shutil.copy2(REPO_ROOT / "site" / "assets" / asset, DIST / "assets" / asset)
    markdown_page("README.md", "en/index.html", "en", "fr/index.html", edition_id)
    markdown_page("README.fr.md", "fr/index.html", "fr", "en/index.html", edition_id)
    for lang in ("en", "fr"):
        other = "fr" if lang == "en" else "en"
        for position, name in enumerate(DOC_PAGES[lang]):
            source = f"docs/{lang}/{name}.md"
            if (REPO_ROOT / source).is_file():
                markdown_page(source, f"{lang}/docs/{name}.html", lang, f"{other}/docs/{DOC_PAGES[other][position]}.html", edition_id)
        for case in load_json(REPO_ROOT / "config" / "cases.json")["cases"]:
            source = f"cases/{case['slug']}/{'README.md' if lang == 'en' else 'README.fr.md'}"
            markdown_page(source, f"{lang}/cases/{case['slug']}.html", lang, f"{other}/cases/{case['slug']}.html", edition_id)
        explorer_page(edition_id, lang)
        figures_page(edition_id, lang)
        cases_index(edition_id, lang)
        editions_page(edition_id, lang)
    landing = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
               '<meta name="robots" content="noindex"><title>Dual Web Reference</title><link rel="stylesheet" href="assets/style.css"></head>'
               '<body><main class="wrap landing"><h1>Dual Web Reference</h1>'
               '<p><a href="en/index.html" hreflang="en">English</a> · <a href="fr/index.html" hreflang="fr">Français</a></p>'
               f'<p>{esc(edition_id + "; availability and approval: see the edition registry via either language above.")}</p></main></body></html>\n')
    write_text(DIST / "index.html", landing)
    pages = sorted(str(p.relative_to(DIST)).replace("\\", "/") for p in DIST.rglob("*.html"))
    return {"output": "site/dist", "pages": len(pages)}
