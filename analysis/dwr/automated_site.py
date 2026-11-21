"""Current M2 routes using the profile B tables and the common bilingual shell."""
from . import automated_public as public, mdlite, typo
from .common import load_json
from .i18n import t


def intro(s, edition_id, lang):
    doc = public.document(s.REPO_ROOT, edition_id)
    return mdlite.render("\n\n".join(public.summary(doc, lang)))


def finish(s, page, lang, title, body, edition_id):
    if lang == "fr":
        body = typo.fr(body)
    other = "fr" if lang == "en" else "en"
    s.emit_text(s.DIST / page, s.layout(page, lang, title, body, other + "/" + page.split("/", 1)[1], edition_id))


def explorer(s, edition_id, lang):
    doc = public.document(s.REPO_ROOT, edition_id)
    page = f"{lang}/explorer.html"
    title = t(lang, "M2: selected automated accesses", "M2 : accès automatisés sélectionnés")
    body = f"<h1>{s.esc(title)}</h1>" + intro(s, edition_id, lang)
    body += f'<p><a href="m1-explorer.html">{s.esc(t(lang, "Open the M1 explorer (different population)", "Ouvrir l’explorateur M1 (population différente)"))}</a></p>'
    sections = [
        ("resources", "resource_summary", "resource-summary.csv", t(lang, "Monthly resource totals", "Totaux mensuels par ressource"),
         [("site_id", "Site", False), ("path", t(lang, "Path", "Chemin"), False), ("family", t(lang, "Family", "Famille"), False), ("request_count", t(lang, "Accesses", "Accès"), True)], ("site_id", "family")),
        ("actors", "actors", "actor-summary.csv", t(lang, "Monthly recorded software actors", "Acteurs logiciels enregistrés, par mois"),
         [("site_id", "Site", False), ("actor_name", t(lang, "Recorded name", "Nom enregistré"), False), ("actor_role", t(lang, "Recorded role", "Rôle enregistré"), False), ("request_count", t(lang, "Accesses", "Accès"), True)], ("site_id", "actor_role")),
    ]
    for identifier, table, file, heading, columns, filters in sections:
        rows = doc["tables"][table]
        labels = {key: label for key, label, _ in columns}
        controls = "".join(s.select(key, labels[key], sorted({r[key] for r in rows}), lang) for key in filters)
        controls += (f'<button type="button" class="reset" disabled>{s.esc(t(lang, "Reset filters", "Réinitialiser"))}</button>'
                     f'<button type="button" class="export" disabled>{s.esc(t(lang, "Export visible rows (spreadsheet-safe CSV)", "Exporter les lignes visibles (CSV pour tableur)"))}</button>')
        body += (f'<section><h2>{s.esc(heading)}</h2><form class="filters" data-table="{identifier}" onsubmit="return false">{controls}<output data-count="{identifier}"></output></form>'
                 + s.table_html(columns, rows, table_id=identifier, filters=filters)
                 + f'<p><a href="{s.esc(s.relative(page, f"data/editions/{edition_id}/{file}"))}">{file}</a></p></section>')
    body += f'<p>{s.esc(t(lang, "All rows are readable without JavaScript. Filters only hide rows; paths are text and never fetched. CSV files retain the canonical column names and exact counts.", "Toutes les lignes restent lisibles sans JavaScript. Les filtres masquent des lignes ; les chemins sont du texte et ne sont jamais consultés. Les CSV conservent les noms canoniques de colonnes et les comptes exacts."))}</p>'
    finish(s, page, lang, title, body, edition_id)


def figures(s, edition_id, lang):
    doc = public.document(s.REPO_ROOT, edition_id)
    registry = load_json(s.REPO_ROOT / "data/editions" / edition_id / "figures.json")
    page = f"{lang}/figures.html"
    title = t(lang, "M2 figures: profile B", "Figures M2 : profil B")
    body = f"<h1>{s.esc(title)}</h1>" + intro(s, edition_id, lang)
    body += f'<p><a href="m1-figures.html">{s.esc(t(lang, "M1 figures (different population)", "Figures M1 (population différente)"))}</a></p>'
    titles = {"G02": ("Recorded roles, monthly", "Rôles enregistrés, par mois"),
              "G03": ("Sites, monthly", "Sites, par mois"),
              "G01": ("Selected accesses by date", "Accès sélectionnés par date"),
              "G06": ("Documentary families, monthly", "Familles documentaires, par mois"),
              "G08": ("Archive coverage", "Couverture des archives")}
    for figure in registry["figures"]:
        fid = figure["figure_id"]
        heading = t(lang, *titles[fid]) if fid in titles else t(lang, "Source graph not available", "Graphe source indisponible")
        prefix = s.relative(page, f"data/editions/{edition_id}/figures/{fid}")
        body += (f'<section class="figure" id="{s.esc(fid)}"><h2>{s.esc(fid + ". " + heading)}</h2>'
                 f'<figure><picture><source media="(max-width:640px)" srcset="{prefix}.{lang}.compact.svg">'
                 f'<img src="{prefix}.{lang}.svg" alt="{s.esc(heading)}" loading="lazy" width="960"></picture>'
                 f'<figcaption>{s.esc(heading)}</figcaption></figure>'
                 f'<p><a href="{prefix}.csv">{s.esc(t(lang, "Exact figure values (CSV)", "Valeurs exactes de la figure (CSV)"))}</a></p></section>')
    finish(s, page, lang, title, body, edition_id)
