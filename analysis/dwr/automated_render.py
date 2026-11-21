"""Deterministic files from the closed automated projection, no private inputs.

The historical renderer is deliberately not invoked: its catalogue, totals,
cases and figures have a different disclosure contract. SVG primitives are shared.
"""
from collections import defaultdict
from datetime import timedelta
from html import escape
from pathlib import Path
import re
from . import automated as A, svg as S, typo
from .common import canonical_json, csv_text, sha256_bytes, DwrError


def text(lang, en, fr):
    return fr if lang == "fr" else en


def _typography(markup, lang):
    # French percentage spacing is prose typography, never CSS syntax.
    if lang != "fr":
        return markup
    return "".join(part if i % 2 else typo.fr(part)
                   for i, part in enumerate(re.split(r"(<style>.*?</style>)", markup, flags=re.S)))


def _period(doc, lang):
    start, end = doc["window"]["start_inclusive"], doc["window"]["end_exclusive"]
    last = str(A.dates.parse_date(end) - timedelta(days=1))
    return text(lang, f"{start} to {last} inclusive, UTC; end exclusive {end}.",
                f"Du {start} au {last} inclus, UTC ; fin exclusive {end}.")


def _base(doc, lang, compact, title):
    width = 360 if compact else 960
    subtitle = text(lang, "Recorded main-documentary GET 200; provider-origin tier; automated roles only.",
                    "Accès consignés GET 200 aux documents principaux ; niveau provider-origin ; rôles automatisés seulement.")
    figure = S.Svg(width, title, title + ". " + _period(doc, lang) + " " + subtitle)
    y = S.header(figure, title, [_period(doc, lang), subtitle], width, compact)
    return figure, y


def _finish(figure, y, doc, lang, source, note=None):
    missing = sum(r["observation_status"] != "observed" for r in doc["tables"]["coverage"])
    partial = sum(r["coverage_status"] == "partial_declared" for r in doc["tables"]["coverage"])
    lines = [text(lang, f"{partial} partial archive days; {missing} unavailable days. Unavailable is not zero.",
                  f"{partial} jours archivés partiels ; {missing} jours indisponibles. Indisponible ne signifie pas zéro."),
             text(lang, "Recorded roles do not prove training use or citation. On-demand accesses withheld (U0).",
                  "Les rôles consignés ne prouvent ni entraînement ni citation. Accès à la demande retenus (U0)."),
             (text(lang, "Local profile B candidate. Source: ", "Candidate locale du profil B. Source : ")
              if doc["contract"] == A.PROFILE_B_CONTRACT else
              text(lang, "Private unapproved candidate. Source: ", "Candidate privée non approuvée. Source : ")) + source]
    if note:
        lines.insert(0, note)
    output = figure.render(S.footer(figure, y, lines, figure.width))
    return _typography(output, lang)


def _bars(doc, lang, compact, title, rows, source):
    figure, y = _base(doc, lang, compact, title)
    width = figure.width - 40
    maximum = max((r["request_count"] for r in rows), default=0) or 1
    if not rows:
        for line in S.wrap(text(lang, "No selected observations recorded under the stated coverage.",
                                "Aucune observation sélectionnée consignée sous la couverture indiquée."), 13, width):
            figure.text(20, y + 16, line, "st"); y += 18
    for row in rows:
        for line in S.wrap(row["label"], 12.5, width - 44):
            figure.text(20, y + 14, line, "lb"); y += 17
        figure.text(figure.width - 20, y - 3, row["request_count"], "vl", anchor="end")
        figure.bar_h(20, y + 3, width * row["request_count"] / maximum, 12, "var(--s1)")
        y += 31
    return _finish(figure, y, doc, lang, source)


def _daily(doc, lang, compact):
    title = text(lang, "Daily selected automated requests", "Accès automatisés sélectionnés par jour")
    figure, y = _base(doc, lang, compact, title)
    top, left, height = y + 15, 44, 170
    width = figure.width - left - 20
    rows = doc["tables"]["coverage"]
    maximum, ticks = S.axis(max((r["request_count"] or 0 for r in rows), default=0))
    for tick in ticks:
        yy = top + height - height * tick / maximum
        figure.line(left, yy, left + width, yy)
        figure.text(left - 7, yy + 4, tick, "ax", anchor="end")
    step = width / len(rows)
    for i, row in enumerate(rows):
        x = left + step * i
        if row["request_count"] is None:
            figure.rect(x + 1, top, max(2, step - 2), height, figure.hatch("unavailable"), title=row["date_utc"] + " unavailable")
        else:
            figure.bar_v(x + 1, top + height, max(2, step - 2), height * row["request_count"] / maximum,
                         "var(--s1)", title=f"{row['date_utc']}: {row['request_count']}")
            if row["request_count"] == 0:
                figure.rect(x + step / 2 - 1, top + height - 2, 2, 2, "var(--s1)", title="0")
        if i in (0, len(rows) // 4, len(rows) // 2, 3 * len(rows) // 4, len(rows) - 1):
            figure.text(x + step / 2, top + height + 18, row["date_utc"][5:], "ax", anchor="middle")
    legend = text(lang, "Hatched bands: unavailable observations. Dots: recorded zero.",
                  "Zones hachurées : observations indisponibles. Points : zéro consigné.")
    return _finish(figure, top + height + 35, doc, lang, "coverage.csv; daily-summary.csv", legend)


def _coverage(doc, lang, compact):
    title = text(lang, "Archive coverage and observation availability", "Couverture des archives et disponibilité des observations")
    figure, y = _base(doc, lang, compact, title)
    states = {"partial_declared": ("Partial archive", "Archive partielle"),
              "complete_declared": ("Declared complete", "Déclarée complète"),
              "coverage_unknown": ("Coverage unknown", "Couverture inconnue"),
              "observation_unavailable": ("Unavailable", "Indisponible")}
    for row in doc["tables"]["coverage"]:
        label = text(lang, *states[row["coverage_status"]])
        figure.text(20, y + 15, row["date_utc"], "lb")
        figure.text(figure.width - 20, y + 15, label, "lb", anchor="end")
        y += 26
    return _finish(figure, y, doc, lang, "coverage.csv")


def _graph(doc, lang, compact, site):
    title = text(lang, "Documentary graph unavailable", "Graphe documentaire indisponible")
    figure, y = _base(doc, lang, compact, title)
    for message in (site, text(lang, "No qualified documentary snapshot in this contract. No graph or case evidence is inferred.",
                              "Aucun instantané documentaire qualifié dans ce contrat. Aucun graphe ni élément de cas n'est déduit.")):
        for line in S.wrap(message, 13, figure.width - 40):
            figure.text(20, y + 18, line, "st"); y += 20
    return _finish(figure, y + 12, doc, lang, "projection.json: graphs")


def _jobs(doc):
    family = defaultdict(int)
    for r in doc["tables"]["families"]:
        family[r["family"]] += r["request_count"]
    return {"G01": [{"date_utc": r["date_utc"], "request_count": r["request_count"], "coverage_status": r["coverage_status"]} for r in doc["tables"]["coverage"]],
            "G02": [{"actor_role": k, "request_count": doc["metrics"]["by_role"][k]} for k in A.ROLES],
            "G03": [{"site_id": k, "request_count": doc["metrics"]["by_site"][k]} for k in A.SITE_IDS],
            "G06": [{"family": k, "request_count": v} for k, v in sorted(family.items())],
            "G08": doc["tables"]["coverage"],
            **{"G09-" + r["site_id"]: [r] for r in doc["graphs"]}}


def _figure(doc, identifier, rows, lang, compact):
    if identifier == "G01":
        return _daily(doc, lang, compact)
    if identifier == "G08":
        return _coverage(doc, lang, compact)
    if identifier.startswith("G09-"):
        return _graph(doc, lang, compact, identifier[4:])
    titles = {"G02": ("Selected requests by recorded role", "Accès sélectionnés par rôle consigné"),
              "G03": ("Selected requests by site", "Accès sélectionnés par site"),
              "G06": ("Selected requests by documentary family", "Accès sélectionnés par famille documentaire")}
    key = {"G02": "actor_role", "G03": "site_id", "G06": "family"}[identifier]
    source = {"G02": "actor-summary.csv", "G03": "resource-summary.csv", "G06": "family-summary.csv"}[identifier]
    values = [{"label": r[key], "request_count": r["request_count"]} for r in rows]
    return _bars(doc, lang, compact, text(lang, *titles[identifier]), values, source)


def _report(doc, lang, jobs):
    title = (text(lang, "Automated accesses: profile B candidate", "Accès automatisés : candidate du profil B")
             if doc["contract"] == A.PROFILE_B_CONTRACT else
             text(lang, "Automated-only private candidate", "Candidate privée : accès automatisés seulement"))
    other = "en" if lang == "fr" else "fr"
    cov = doc["tables"]["coverage"]
    missing = ", ".join(r["date_utc"] for r in cov if r["observation_status"] != "observed") or text(lang, "none", "aucune")
    paragraph = text(lang,
        "This is a private, unapproved descriptive subset of recorded accesses. The provider-origin tier and actor roles are recorded classifications under review; they do not establish actual training, citations or human initiation.",
        "Cette sélection descriptive d'accès consignés reste privée et non approuvée. Le niveau provider-origin et les rôles sont des classifications enregistrées sous examen ; ils ne démontrent ni entraînement effectif, ni citation, ni initiative humaine.")
    limits = text(lang,
        "On-demand access: withheld (U0), count null. M1/M2 growth: not qualified, null. Unavailable dates are not zeros. A zero only means no selected row recorded under the stated coverage. Monthly resource/actor details contain no daily or epoch partitions. Automated actors or resources may still be inferred from small groups.",
        "Accès à la demande : retenus (U0), compte null. Croissance M1/M2 : non qualifiée, null. Une date indisponible ne vaut pas zéro. Un zéro signifie seulement aucune ligne sélectionnée consignée sous la couverture indiquée. Les détails mensuels de ressources et d'acteurs n'ont aucune partition quotidienne ou par époque. De petits groupes peuvent néanmoins révéler un acteur ou une ressource automatisée.")
    if doc["contract"] == A.PROFILE_B_CONTRACT:
        paragraph = text(lang,
            "This descriptive subset of recorded accesses is a local release candidate. Publication has not been authorized. The provider-origin tier and actor roles are recorded classifications under review; they do not establish actual training, citations or human initiation.",
            "Cette sélection descriptive d'accès consignés est une candidate locale de diffusion. La publication n'est pas autorisée. Le niveau provider-origin et les rôles sont des classifications enregistrées sous examen ; ils ne démontrent ni entraînement effectif, ni citation, ni initiative humaine.")
        limits += text(lang,
            " Daily margins are limited to site and role; documentary family totals are monthly only. These margins can still constrain individual automated cells. Historical releases and auxiliary information remain available; this profile is not anonymization.",
            " Les marges quotidiennes se limitent au site et au rôle ; les totaux par famille documentaire sont uniquement mensuels. Ces marges peuvent encore contraindre des cellules automatisées individuelles. Les publications historiques et les informations auxiliaires demeurent accessibles ; ce profil n'est pas une anonymisation.")
    classifier = {"unknown": ("unattested", "non attesté"), "attested_in_provenance": ("attested in provenance", "attesté dans la provenance")}
    epochs = {"unknown": ("unknown", "inconnue"), "mixed_epoch_unresolved": ("unresolved intraday transition", "transition intrajournalière non résolue"),
              "single_epoch_resolved": ("single resolved epoch", "époque unique résolue"), "multiple_epochs_resolved": ("multiple resolved epochs", "plusieurs époques résolues")}
    qualification = text(lang, "Classifier status", "Statut du classificateur") + ": " + text(lang, *classifier[doc["measurement"]["classifier_status"]]) + "; " + text(lang, "measurement epoch", "époque de mesure") + ": " + text(lang, *epochs[doc["measurement"]["epoch_resolution"]]) + "."
    links = " ".join(f'<a href="{escape(name)}">{escape(name)}</a>' for name in (*A.filenames(doc["contract"]).values(), "projection.json", "catalog.json", "schema.json", "manifest.json"))
    figures = []
    for identifier in jobs:
        figures.append(f'<section><h2>{escape(identifier)}</h2><picture><source media="(max-width:600px)" srcset="figures/{identifier}.{lang}.compact.svg"><img src="figures/{identifier}.{lang}.svg" alt="{escape(identifier)}" width="960"></picture><p><a href="figures/{identifier}.csv">{text(lang,"Figure data (CSV)","Données de la figure (CSV)")}</a></p></section>')
    summary = f'<div class="counts"><p><strong>{doc["metrics"]["selected_requests"]}</strong> {text(lang,"selected requests","accès sélectionnés")}</p><p><strong>{doc["metrics"]["selected_distinct_resources"]}</strong> {text(lang,"distinct site/path resources","ressources distinctes site/chemin")}</p></div>'
    html = f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"><title>{title}</title><style>
*{{box-sizing:border-box}}body{{margin:0;color:#172b37;background:#f4f6f8;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1040px;margin:auto;padding:28px;background:white;overflow-wrap:anywhere}}h1{{line-height:1.2}}a{{color:#005c7b}}nav{{display:flex;gap:20px;flex-wrap:wrap}}.counts{{display:flex;gap:24px;flex-wrap:wrap;background:#edf4f8;padding:12px 20px}}.counts strong{{font-size:1.5rem}}img{{max-width:100%;height:auto;display:block}}section{{border-top:1px solid #ccd7df;margin-top:28px;padding-top:8px}}.files a{{display:inline-block;margin:0 14px 12px 0}}@media(max-width:600px){{main{{padding:16px}}h1{{font-size:1.8rem}}.counts{{gap:0;display:block}}}}
</style></head><body><main><nav><a href="report.{other}.html" hreflang="{other}">{"English" if other == "en" else "Français"}</a><a href="#files">{text(lang,"Read the data","Consulter les données")}</a></nav><h1>{title}</h1><p>{escape(_period(doc,lang))}</p><p>{escape(paragraph)}</p>{summary}<p>{escape(limits)}</p><p>{escape(qualification)}</p><p>{text(lang,"Unavailable dates","Dates indisponibles")} : {escape(missing)}.</p><section id="files"><h2>{text(lang,"Selected data and closed schema","Données sélectionnées et schéma fermé")}</h2><p class="files">{links}</p></section>{''.join(figures)}<p>{escape(doc["contract"])} · {text(lang,"No publication authorized. No tracking or external assets.","Aucune publication autorisée. Aucun suivi ni actif externe.")}</p></main></body></html>'''
    return _typography(html, lang)


def files(document):
    """Complete allowlist of output bytes. No arbitrary catalogue or extra file."""
    A.validate(document)
    contract = document["contract"]
    fields_by_table = A.table_fields(contract)
    names = A.filenames(contract)
    result = {"projection.json": canonical_json(document), "schema.json": canonical_json(A.schema_document(contract)),
              "metrics.json": canonical_json(document["metrics"]), "on-demand.json": canonical_json(document["on_demand"])}
    for key, name in names.items():
        result[name] = csv_text(fields_by_table[key], document["tables"][key])
    result["catalog.json"] = canonical_json({"contract": contract, "canonical_document": "projection.json",
        "schema": "schema.json", "manifest": "manifest.json", "availability_status": document["availability_status"],
        "tables": {key: {"path": name, "columns": list(fields_by_table[key])} for key, name in names.items()},
        "reports": {lang: f"report.{lang}.html" for lang in ("en", "fr")}, "figures": "figures.json"})
    jobs = _jobs(document)
    registry = []
    for identifier, rows in jobs.items():
        # Persisted JSON object order is not semantic. Preserve the contract's CSV order.
        if identifier == "G08":
            fields = A.TABLES["coverage"]
        elif identifier.startswith("G09-"):
            fields = ("site_id", "status", "reason")
        else:
            fields = list(rows[0]) if rows else ["family", "request_count"]
        result[f"figures/{identifier}.csv"] = csv_text(fields, rows)
        for lang in ("en", "fr"):
            for compact in (False, True):
                suffix = ".compact" if compact else ""
                result[f"figures/{identifier}.{lang}{suffix}.svg"] = _figure(document, identifier, rows, lang, compact)
        registry.append({"figure_id": identifier, "status": "not_available" if identifier.startswith("G09-") else "rendered",
                         "data_table": f"figures/{identifier}.csv"})
    result["figures.json"] = canonical_json({"contract": contract, "figures": registry})
    for lang in ("en", "fr"):
        result[f"report.{lang}.html"] = _report(document, lang, jobs)
    encoded = {name: value.encode("utf-8") for name, value in sorted(result.items())}
    encoded["manifest.json"] = canonical_json({"contract": contract, "canonical_document": "projection.json",
        "public_output_approved": False, "files": {name: sha256_bytes(value) for name, value in encoded.items()},
        "self_excluded": "manifest.json"}).encode("utf-8")
    return encoded


def verify(directory, document):
    from .write_guard import checked_path, fingerprint
    expected = {name: sha256_bytes(value) for name, value in files(document).items()}
    directory = Path(directory)
    allowed_dirs = {p.as_posix() for name in expected for p in Path(name).parents if p != Path('.')}
    for path in directory.rglob('*'):
        checked_path(directory, path)
        if path.is_dir() and path.relative_to(directory).as_posix() not in allowed_dirs:
            raise DwrError("automated_unexpected_output_directory")
    if fingerprint(directory) != expected:
        raise DwrError("automated_output_bytes_or_surfaces_changed")
    return {"passed": True, "files": len(expected), "contract": document["contract"], "public_output_approved": False}
