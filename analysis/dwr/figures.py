"""render (figures): G01 to G10 from the public edition files only.

Each figure is written in English and French, in a wide (960 px) and a compact
(420 px) layout, with its own data table (CSV) holding exactly the plotted values.
Every visual carries: descriptive title, inclusive period, exclusive end, time
zone, population, filters, unit, extraction date, edition identifier, coverage
state and the path of its source table. A figure whose data is not available is
rendered as an explicit "not available" panel, never with simulated cells.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from . import svg as S
from .common import SITE_IDS, csv_text, read_csv, sha256_bytes
from .i18n import cap, number, percent, short_date, t

SITE_COLOR = {"gautierdorval.com": "var(--s1)", "pagup.com": "var(--s2)", "better-robots.com": "var(--s3)"}
ROLES = ("ai_training", "ai_search", "user_initiated_fetch")
AUTOMATED_ROLES = ("ai_training", "ai_search")
ROLE_LABEL = {
    "ai_training": ("collection for training (ai_training)", "collecte pour entraînement (ai_training)"),
    "ai_search": ("AI search (ai_search)", "recherche IA (ai_search)"),
    "user_initiated_fetch": ("user-initiated fetch (user_initiated_fetch)", "récupération à la demande (user_initiated_fetch)"),
}
TIER_LABEL = {
    "provider_origin_verified_actor": ("provider origin, registry match", "origine fournisseur, registre officiel"),
    "network_verified_claimed_actor": ("declared name + network signal (under review)", "nom déclaré + signal réseau (en revue)"),
    "cloudflare_verified_unattributed": ("unattributed (under review)", "non attribué (en revue)"),
    "spoofed_or_failed_verification": ("failed verification", "vérification échouée"),
}


class Context:
    def __init__(self, catalog: dict, edition_dir, metrics: dict):
        self.catalog = catalog
        self.edition_dir = edition_dir
        self.edition_id = catalog["edition_id"]
        self.metrics = {m["metric_id"]: m for m in metrics["metrics"]}
        self.start = date.fromisoformat(catalog["dates"]["period_start_inclusive"])
        self.end = date.fromisoformat(catalog["dates"]["period_end_exclusive"])

    def m(self, metric_id):
        return self.metrics[metric_id]["value"]

    def period(self, lang):
        return self.catalog["labels"][f"period_{lang}"]

    def footer(self, lang, sources, extra=None):
        dates = self.catalog["dates"]
        extracted = dates["extracted_at"]
        lines = [
            t(lang, f"Edition {self.edition_id}. Data {self.period('en')} (end exclusive {dates['period_end_exclusive']}T00:00:00Z).",
              f"Édition {self.edition_id}. Données {self.period('fr')} (fin exclusive {dates['period_end_exclusive']}T00:00:00Z)."),
            t(lang, f"Extracted {extracted['start'][:16].replace('T', ' ')} to {extracted['end'][11:16]} UTC; coverage: archive reports partial (declared) on {self.m('coverage.days_partial_declared')} of {self.m('coverage.days_in_window')} days.",
              f"Extraction du {extracted['start'][:10]} de {extracted['start'][11:16]} à {extracted['end'][11:16]} UTC ; couverture : rapports d’archive partiels déclarés {self.m('coverage.days_partial_declared')} jours sur {self.m('coverage.days_in_window')}."),
            t(lang, "Source table: ", "Table source : ") + ", ".join(f"data/editions/{self.edition_id}/{name}" for name in sources),
        ]
        if extra:
            lines.insert(0, extra)
        return lines


def _rows(ctx, name):
    return read_csv(ctx.edition_dir / name)


def _bool(value):
    return value == "true"


def _main_provider(ctx):
    """Provider-origin AI-role GET 200 per resource, summed from the exact edition cells."""
    resources = {r["resource_id"]: r for r in _rows(ctx, "resources.csv")}
    provider = defaultdict(int)
    for row in _rows(ctx, "consultations.csv"):
        if (row["http_method"] == "GET" and row["http_status"] == "200" and row["actor_role"] in ROLES
                and row["stored_identity_tier"] == "provider_origin_verified_actor"):
            provider[row["resource_id"]] += int(row["request_count"])
    return resources, dict(provider)


def _hbars(svg, x0, y, width, items, maximum, lang, label_width, bar_h=18, gap=10, fill_of=None):
    """Horizontal bars with category labels on the left and values at the tip."""
    top, grid = S.axis(maximum)
    plot_w = width - label_width - 60
    for value in grid:
        gx = x0 + label_width + plot_w * value / top
        svg.line(gx, y - 4, gx, y + len(items) * (bar_h + gap), "grid")
    for index, (label, value, fill, note) in enumerate(items):
        by = y + index * (bar_h + gap)
        for line_index, line in enumerate(S.wrap(label, 12.5, label_width - 10)[:2]):
            svg.text(x0 + label_width - 8, by + 13 + line_index * 13 - (6 if len(S.wrap(label, 12.5, label_width - 10)) > 1 else 0),
                     line, "lb", "end")
        if value is None:
            svg.rect(x0 + label_width, by, plot_w * 0.3, bar_h, svg.hatch("na"))
            svg.text(x0 + label_width + plot_w * 0.3 + 6, by + 13, note or t(lang, "not available", "non disponible"), "vl")
            continue
        w = plot_w * value / top if top else 0
        svg.bar_h(x0 + label_width, by, w, bar_h, fill, title=f"{label}: {value}")
        svg.text(x0 + label_width + w + 6, by + 13, number(value, lang) + (f" {note}" if note else ""), "vl")
    axis_y = y + len(items) * (bar_h + gap)
    for value in grid:
        gx = x0 + label_width + plot_w * value / top
        svg.text(gx, axis_y + 12, number(value, lang), "ax", "middle")
    return axis_y + 30


def figure_g01(ctx, lang, compact):
    width = 420 if compact else 960
    coverage = {r["date_utc"]: r for r in _rows(ctx, "coverage.csv")}
    days = [d.isoformat() for d in sorted(date.fromisoformat(r["date_utc"]) for r in coverage.values())]
    values = defaultdict(int)
    for r in _rows(ctx, "daily-summary.csv"):
        if (r["population"] == "main_documentary" and r["stored_identity_tier"] == "provider_origin_verified_actor"
                and r["actor_role"] in AUTOMATED_ROLES and r["http_method"] == "GET" and r["http_status"] == "200"):
            values[(r["date_utc"], r["site_id"])] += int(r["request_count"])
    maximum = max(values.values()) if values else 0
    title = t(lang, "Daily GET 200 requests to the main documentary population, provider-origin automated AI roles, by site",
              "Requêtes GET 200 quotidiennes vers la population documentaire principale, rôles IA automatisés à origine fournisseur, par site")
    subtitles = [
        cap(ctx.period(lang)) + ".",
        t(lang, "Population: main documentary population (scope classes core_governance and discovery_index). Filter: stored tier provider_origin_verified_actor; roles ai_training and ai_search. User-initiated fetches are counted for the edition only (G03): the small-cell policy keeps them out of daily views.",
          "Population : population documentaire principale (classes core_governance et discovery_index). Filtre : niveau enregistré provider_origin_verified_actor ; rôles ai_training et ai_search. Les récupérations à la demande sont comptées pour l’édition seulement (G03) : la politique des petites cellules les exclut des vues quotidiennes."),
        t(lang, "Unit: requests per UTC day. Same linear scale for the three panels; no smoothing.",
          "Unité : requêtes par jour UTC. Même échelle linéaire pour les trois panneaux ; aucun lissage."),
    ]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    top, grid = S.axis(maximum, 4)
    left, right = 40, 16
    plot_w = width - left - right
    slot = plot_w / len(days)
    col = min(14 if not compact else 9, slot - 2)
    panel_h = 70 if compact else 90
    table = []
    for site in SITE_IDS:
        total = sum(values.get((d, site), 0) for d in days)
        svg.add(f'<circle cx="{left + 5}" cy="{S.f(y - 4)}" r="5" fill="{SITE_COLOR[site]}"/>')
        svg.text(left + 16, y, f"{site} · " + t(lang, "total ", "total ") + number(total, lang), "lb")
        y += 10
        base = y + panel_h
        for value in grid:
            gy = base - panel_h * value / top
            svg.line(left, gy, width - right, gy, "grid")
            svg.text(left - 6, gy + 4, number(value, lang), "ax", "end")
        for index, day in enumerate(days):
            value = values.get((day, site), 0)
            x = left + index * slot + (slot - col) / 2
            if value:
                svg.bar_v(x, base, col, panel_h * value / top, SITE_COLOR[site], title=f"{site} {day}: {value}")
            else:
                svg.rect(x, base - 1.5, col, 1.5, "var(--neutral2)", title=f"{site} {day}: 0")
            table.append({"date_utc": day, "site_id": site, "get200": value,
                          "coverage_status": coverage.get(day, {}).get("coverage_status", "")})
        svg.line(left, base, width - right, base, "axis")
        y = base + 22
    strip_y = y - 10
    for index, day in enumerate(days):
        x = left + index * slot
        row = coverage.get(day, {})
        fill = svg.hatch("partial") if row.get("coverage_status") == "partial_declared" else "var(--neutral2)"
        svg.rect(x + 0.5, strip_y, slot - 1, 8, fill, title=f"{day}: {row.get('coverage_status', 'unknown')}")
        if row.get("aggregate_minus_v3") not in (None, "", "0"):
            svg.add(f'<path d="M{S.f(x + slot / 2)},{S.f(strip_y + 10)}l4,7h-8z" fill="var(--missing)">'
                    f'<title>{day}: aggregate/V3 gap {row.get("aggregate_minus_v3")}</title></path>')
    every = 7 if not compact else 14
    for index, day in enumerate(days):
        last = index == len(days) - 1 and (index % every) >= every // 2
        if index % every == 0 or last:
            svg.text(left + index * slot + slot / 2, strip_y + 30, short_date(date.fromisoformat(day), lang), "ax", "middle")
    y = strip_y + 44
    legend = t(lang, "Hatched strip: archive report partial (declared) for the day. Triangle: one-request gap between aggregate and V3 counts. A flat tick is a recorded zero: no such request in the producer table that day.",
               "Bande hachurée : rapport d’archive partiel (déclaré) pour la journée. Triangle : écart d’une requête entre comptes agrégés et V3. Un trait plat est un zéro enregistré : aucune requête de ce type dans la table du producteur ce jour-là.")
    for line in S.wrap(legend, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y = S.footer(svg, y, ctx.footer(lang, ["daily-summary.csv", "coverage.csv"]), width)
    svg.desc = t(lang,
                 f"Three column charts, one per site, of daily GET 200 requests to the main documentary population from provider-origin automated AI roles over {len(days)} UTC days; requests occur on {ctx.m('main.daily.days_with_requests')} of these days; all days carry a partial archive report.",
                 f"Trois histogrammes, un par site, des requêtes GET 200 quotidiennes vers la population documentaire principale par des rôles IA automatisés à origine fournisseur sur {len(days)} jours UTC ; des requêtes apparaissent {ctx.m('main.daily.days_with_requests')} de ces jours ; tous les jours portent un rapport d’archive partiel.")
    return svg.render(y), table


def figure_g02(ctx, lang, compact):
    width = 420 if compact else 960
    resources, provider = _main_provider(ctx)
    rows = []
    for site in (None,) + SITE_IDS:
        selected = [rid for rid, r in resources.items() if _bool(r["main_population"]) and rid in provider
                    and (site is None or r["site_id"] == site)]
        llms = sum(provider[rid] for rid in selected if _bool(resources[rid]["llms_txt"]))
        other = sum(provider[rid] for rid in selected if not _bool(resources[rid]["llms_txt"]))
        rows.append((site, llms, other))
    title = t(lang, "llms.txt and the other governance files: GET 200 requests from provider-origin AI roles",
              "llms.txt et les autres fichiers de gouvernance : requêtes GET 200 des rôles IA à origine fournisseur")
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Population: main documentary population (scope classes core_governance and discovery_index), same period, same method and status, same identification level for both segments.",
                   "Population : population documentaire principale (classes core_governance et discovery_index), même période, même méthode et statut, même niveau d’identification pour les deux segments."),
                 t(lang, "Unit: requests. The share describes how recorded requests are distributed; it is not an adoption rate.",
                   "Unité : requêtes. La part décrit la répartition des requêtes enregistrées ; ce n’est pas un taux d’adoption.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    label_w = 150 if not compact else 120
    plot_w = width - label_w - 40
    maximum = max(l + o for _, l, o in rows) or 1
    top, grid = S.axis(maximum, 4)
    bar_h = 20
    table = []
    for index, (site, llms, other) in enumerate(rows):
        total = llms + other
        name = t(lang, "Three sites", "Trois sites") if site is None else site
        pitch = 78 if compact else 58
        by = y + index * pitch
        svg.text(20, by + 14, name, "lb")
        x = 20 + (0 if compact else label_w)
        if compact:
            by += 20
        avail = (width - 40) if compact else plot_w
        w_llms = avail * llms / top
        w_other = avail * other / top
        svg.rect(x, by, w_llms, bar_h, "var(--s5)", title=f"{name} llms.txt: {llms}")
        svg.bar_h(x + w_llms + (2 if llms else 0), by, w_other, bar_h, "var(--s7)", title=f"{name} other: {other}")
        share = other / total if total else None
        label = (f"llms.txt {number(llms, lang)} · " + t(lang, "other ", "autres ") + number(other, lang)
                 + " · " + t(lang, "total ", "total ") + number(total, lang) + " · " + t(lang, "other share ", "part hors llms.txt ")
                 + percent(share, lang))
        svg.text(x, by + bar_h + 15, label, "ax")
        table.append({"site_id": site or "all_sites", "llms_txt_get200": llms, "other_get200": other,
                      "total_get200": total, "other_share": round(share, 6) if share is not None else None})
    y += len(rows) * (78 if compact else 58) + 6
    svg.rect(20, y - 9, 12, 10, "var(--s5)")
    svg.text(38, y, "/llms.txt", "lb")
    svg.rect(120, y - 9, 12, 10, "var(--s7)")
    svg.text(138, y, t(lang, "other main-population resources", "autres ressources de la population principale"), "lb")
    y += 12
    y = S.footer(svg, y, ctx.footer(lang, ["consultations.csv", "resources.csv"]), width)
    svg.desc = t(lang, "Stacked horizontal bars, all sites and per site, splitting provider-origin AI-role GET 200 requests between /llms.txt and the other governance files; counts, totals and shares are written under each bar.",
                 "Barres horizontales empilées, trois sites et par site, répartissant les requêtes GET 200 des rôles IA à origine fournisseur entre /llms.txt et les autres fichiers de gouvernance ; comptes, totaux et parts sont écrits sous chaque barre.")
    return svg.render(y), table


def figure_g03(ctx, lang, compact):
    width = 420 if compact else 960
    title = t(lang, "Provider-origin AI requests by recorded actor role", "Requêtes IA à origine fournisseur selon le rôle enregistré de l’acteur")
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Panel A: main documentary population. Panel B: scope of the initial report, for reconciliation. Both exact, from the joint aggregate.",
                   "Panneau A : population documentaire principale. Panneau B : périmètre du relevé initial, pour le rapprochement. Les deux sont exacts, tirés de l’agrégat conjoint."),
                 t(lang, "Unit: GET 200 requests. Roles stay distinct; a user-initiated fetch can be triggered by anyone, including the site operator.",
                   "Unité : requêtes GET 200. Les rôles restent distincts ; une récupération à la demande peut être déclenchée par n’importe qui, y compris l’exploitant du site.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    label_w = 150 if compact else 330
    table = []
    panels = (("A", "main.role.{}.get200", t(lang, "A. Main documentary population", "A. Population documentaire principale")),
              ("B", "historical.provider_ai.role.{}.get200", t(lang, "B. Scope of the initial report", "B. Périmètre du relevé initial")))
    maximum = max(ctx.m(pattern.format(role)) for _, pattern, _ in panels for role in ROLES)
    for panel, pattern, heading in panels:
        items = []
        for role in ROLES:
            value = ctx.m(pattern.format(role))
            items.append((t(lang, *ROLE_LABEL[role]), value, "var(--s1)" if panel == "A" else "var(--neutral)", None))
            table.append({"panel": panel, "actor_role": role, "get200": value})
        svg.text(20, y, heading, "vl")
        y = _hbars(svg, 20, y + 12, width - 20, items, maximum, lang, label_w) + 6
    note = t(lang, f"Sensitivity without user-initiated fetches (main population): {number(ctx.m('main.sensitivity.without_user_fetch.get200'), lang)} requests on {number(ctx.m('main.sensitivity.without_user_fetch.site_path_pairs'), lang)} pairs. This is a sensitivity analysis, not evidence that the other requests were independent.",
             f"Sensibilité sans récupérations à la demande (population principale) : {number(ctx.m('main.sensitivity.without_user_fetch.get200'), lang)} requêtes sur {number(ctx.m('main.sensitivity.without_user_fetch.site_path_pairs'), lang)} couples. C’est une analyse de sensibilité, pas une preuve que les autres requêtes étaient indépendantes.")
    for line in S.wrap(note, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y = S.footer(svg, y, ctx.footer(lang, ["consultations.csv", "resources.csv"]), width)
    svg.desc = t(lang, "Two panels of horizontal bars of provider-origin AI GET 200 requests per recorded role: main documentary population, then the initial report scope.",
                 "Deux panneaux de barres horizontales des requêtes GET 200 IA à origine fournisseur par rôle enregistré : population documentaire principale, puis périmètre du relevé initial.")
    return svg.render(y), table


def figure_g04(ctx, lang, compact):
    width = 420 if compact else 960
    resources, provider = _main_provider(ctx)
    summary = {r["resource_id"]: r for r in _rows(ctx, "resource-summary.csv")}
    title = t(lang, "Distinct site-path pairs requested, and recurrence", "Couples site-chemin distincts demandés, et récurrence")
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Unit: site-path pairs (URLs), not consumers. Distinct counts are computed on pairs, never by adding per-actor counts.",
                   "Unité : couples site-chemin (URL), pas des consommateurs. Les distincts sont calculés sur les couples, jamais en additionnant des comptes par acteur.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    for line in S.wrap(t(lang, "A. Main documentary population: pairs with rows in the window, and pairs with at least one provider-origin AI GET 200",
                         "A. Population documentaire principale : couples avec lignes dans la fenêtre, et couples avec au moins un GET 200 IA à origine fournisseur"), 12.5, width - 40):
        svg.text(20, y, line, "vl")
        y += 16
    label_w = 150 if not compact else 130
    table = []
    observed = {s: sum(1 for r in resources.values() if r["site_id"] == s and _bool(r["main_population"])
                       and r["window_rows_status"] == "rows_in_window") for s in SITE_IDS}
    with_ai = {s: sum(1 for rid, r in resources.items() if r["site_id"] == s and _bool(r["main_population"])
                      and provider.get(rid, 0) > 0) for s in SITE_IDS}
    top, grid = S.axis(max(observed.values()), 4)
    plot_w = width - label_w - 70
    for index, site in enumerate(SITE_IDS):
        by = y + index * 34
        svg.text(20 + label_w - 8, by + 14, site, "lb", "end")
        svg.rect(20 + label_w, by + 2, plot_w * observed[site] / top, 16, "var(--neutral2)",
                 title=f"{site}: {observed[site]} pairs with rows")
        svg.bar_h(20 + label_w, by + 6, plot_w * with_ai[site] / top, 8, SITE_COLOR[site],
                  title=f"{site}: {with_ai[site]} pairs with provider-origin AI GET 200")
        svg.text(20 + label_w + plot_w * observed[site] / top + 6, by + 14,
                 number(with_ai[site], lang) + t(lang, " of ", " sur ") + number(observed[site], lang), "vl")
        table.append({"panel": "A", "site_id": site, "pairs_with_rows": observed[site],
                      "pairs_with_provider_ai_get200": with_ai[site], "bucket": None, "pairs": None})
    y += 3 * 34 + 4
    key = t(lang, "Wide grey bar: pairs with rows (all recorded classifications). Thin bar: pairs with at least one provider-origin AI GET 200.",
            "Barre grise large : couples avec lignes (toutes classifications enregistrées). Barre fine : couples avec au moins un GET 200 IA à origine fournisseur.")
    for line in S.wrap(key, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y += 10
    for line in S.wrap(t(lang, "B. Recurrence: number of UTC days with at least one provider-origin AI GET 200, per requested pair",
                         "B. Récurrence : nombre de jours UTC avec au moins un GET 200 IA à origine fournisseur, par couple demandé"), 12.5, width - 40):
        svg.text(20, y, line, "vl")
        y += 16
    y += 4
    buckets = (("1", 1, 1), ("2-3", 2, 3), ("4-7", 4, 7), ("8+", 8, 31))
    counts = {(s, b[0]): 0 for s in SITE_IDS for b in buckets}
    for rid, r in summary.items():
        if not _bool(r["main_population"]) or provider.get(rid, 0) == 0:
            continue
        days = int(r["provider_origin_ai_get200_days"])
        for name, low, high in buckets:
            if low <= days <= high:
                counts[(r["site_id"], name)] += 1
    maximum = max(counts.values()) if counts else 1
    top, grid = S.axis(maximum, 4)
    group_w = (width - 60) / len(buckets)
    bar_w = min(22, (group_w - 16) / 3)
    base = y + 120
    for value in grid:
        gy = base - 110 * value / top
        svg.line(40, gy, width - 20, gy, "grid")
        svg.text(36, gy + 4, number(value, lang), "ax", "end")
    for gi, (name, _, _) in enumerate(buckets):
        gx = 44 + gi * group_w + (group_w - 3 * (bar_w + 2)) / 2
        for si, site in enumerate(SITE_IDS):
            value = counts[(site, name)]
            if value:
                svg.bar_v(gx + si * (bar_w + 2), base, bar_w, 110 * value / top, SITE_COLOR[site], title=f"{site} {name}: {value}")
            else:
                svg.rect(gx + si * (bar_w + 2), base - 1.5, bar_w, 1.5, "var(--neutral2)", title=f"{site} {name}: 0")
            table.append({"panel": "B", "site_id": site, "pairs_with_rows": None, "pairs_with_provider_ai_get200": None,
                          "bucket": name, "pairs": value})
        unit = t(lang, " day", " jour") if name == "1" else t(lang, " days", " jours")
        svg.text(44 + gi * group_w + group_w / 2, base + 16, name + unit, "ax", "middle")
    svg.line(40, base, width - 20, base, "axis")
    y = base + 34
    x = 20
    for site in SITE_IDS:
        svg.add(f'<circle cx="{x + 5}" cy="{S.f(y - 4)}" r="5" fill="{SITE_COLOR[site]}"/>')
        svg.text(x + 14, y, site, "lb")
        x += S.text_width(site, 12.5) + 34
        if compact and x > width - 120:
            x, y = 20, y + 18
    y += 8
    y = S.footer(svg, y, ctx.footer(lang, ["resources.csv", "consultations.csv", "resource-summary.csv"]), width)
    svg.desc = t(lang, "Panel A compares, per site, main-population pairs with rows and pairs with provider-origin AI GET 200. Panel B shows how many requested pairs had such requests on 1, 2 to 3, 4 to 7 or 8 or more UTC days.",
                 "Le panneau A compare, par site, les couples de la population principale avec lignes et ceux avec GET 200 IA à origine fournisseur. Le panneau B indique combien de couples demandés ont reçu de telles requêtes sur 1, 2 à 3, 4 à 7 ou 8 jours UTC et plus.")
    return svg.render(y), table


def figure_g05(ctx, lang, compact):
    width = 420 if compact else 960
    resources, provider = _main_provider(ctx)
    title = t(lang, "Most requested governance files per site, provider-origin AI roles only",
              "Fichiers de gouvernance les plus demandés par site, rôles IA à origine fournisseur seulement")
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Population: main documentary population. Filter: stored tier provider_origin_verified_actor, GET 200. Unattributed traffic is not mixed in. Ten highest per site; ties ordered by path.",
                   "Population : population documentaire principale. Filtre : niveau enregistré provider_origin_verified_actor, GET 200. Le trafic non attribué n’y est pas mêlé. Dix plus élevés par site ; ex æquo triés par chemin."),
                 t(lang, "Unit: requests. Mirrors and language versions are separate URLs.", "Unité : requêtes. Miroirs et versions linguistiques sont des URL distinctes.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    table = []
    label_w = 190 if compact else 380
    plotted = [provider[rid] for rid, r in resources.items()
               if _bool(r["main_population"]) and provider.get(rid, 0) > 0]
    overall = max(plotted or [1])
    for site in SITE_IDS:
        everything = sorted(((rid, provider[rid]) for rid, r in resources.items()
                             if r["site_id"] == site and _bool(r["main_population"]) and provider.get(rid, 0) > 0),
                            key=lambda item: (-item[1], resources[item[0]]["path"]))
        ranked = everything[:10]
        tied = sum(1 for _, value in everything[10:] if ranked and value == ranked[-1][1])
        svg.add(f'<circle cx="25" cy="{S.f(y - 4)}" r="5" fill="{SITE_COLOR[site]}"/>')
        svg.text(36, y, site + (t(lang, f" · {tied} more resources tie with the tenth value",
                                  f" · {tied} autres ressources à égalité avec la dixième valeur") if tied else ""), "vl")
        y += 12
        items = [(resources[rid]["path"], value, SITE_COLOR[site], None) for rid, value in ranked]
        y = _hbars(svg, 20, y, width - 20, items, overall, lang, label_w, bar_h=14, gap=8) + 12
        for rank, (rid, value) in enumerate(ranked, start=1):
            table.append({"site_id": site, "rank": rank, "resource_id": rid, "path": resources[rid]["path"],
                          "provider_origin_ai_get200": value})
    y = S.footer(svg, y, ctx.footer(lang, ["consultations.csv", "resources.csv"]), width)
    svg.desc = t(lang, "Three ranked horizontal bar lists, one per site, of the ten main-population files with most provider-origin AI GET 200 requests.",
                 "Trois listes de barres horizontales classées, une par site, des dix fichiers de la population principale ayant le plus de requêtes GET 200 IA à origine fournisseur.")
    return svg.render(y), table


def _not_available(ctx, lang, compact, title, reason, sources):
    width = 420 if compact else 960
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, [cap(ctx.period(lang)) + "."], width, compact)
    svg.rect(20, y, width - 40, 90, svg.hatch("na"))
    svg.text(width / 2, y + 40, t(lang, "Not available in this edition", "Non disponible dans cette édition"), "na", "middle")
    svg.text(width / 2, y + 62, t(lang, "No cell is simulated.", "Aucune cellule n’est simulée."), "lb", "middle")
    y += 110
    for line in S.wrap(reason, 12.5, width - 40):
        svg.text(20, y, line, "lb")
        y += 16
    y = S.footer(svg, y, ctx.footer(lang, sources), width)
    svg.desc = reason
    return svg.render(y), [{"status": "not_available", "reason": reason}]


def figure_g06(ctx, lang, compact):
    width = 420 if compact else 960
    rows = _rows(ctx, "daily-family-summary.csv")
    title = t(lang, "Heat map: day x documentary family, automated provider-origin AI roles",
              "Carte de chaleur : jour x famille documentaire, rôles IA automatisés à origine fournisseur")
    if not rows:
        reason = t(lang, "This map needs the joint aggregate day x path x actor x identification level, which is not part of this edition. No cell is simulated.",
                   "Cette carte exige l’agrégat conjoint jour x chemin x acteur x niveau d’identification, absent de cette édition. Aucune cellule n’est simulée.")
        return _not_available(ctx, lang, compact, title, reason, ["daily-family-summary.csv"])
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Population: main documentary population, GET 200, stored tier provider_origin_verified_actor, roles ai_training and ai_search combined. User-initiated fetches are left out of this daily view by the small-cell policy.",
                   "Population : population documentaire principale, GET 200, niveau enregistré provider_origin_verified_actor, rôles ai_training et ai_search réunis. Les récupérations à la demande sont exclues de cette vue quotidienne par la politique des petites cellules."),
                 t(lang, "Unit: requests per UTC day and family. Built from the joint aggregate, never from marginals.",
                   "Unité : requêtes par jour UTC et par famille. Construite à partir de l’agrégat conjoint, jamais à partir de marges.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    cells = defaultdict(int)
    for r in rows:
        cells[(r["date_utc"], r["family"])] += int(r["request_count"])
    days = sorted({r["date_utc"] for r in rows})
    totals = defaultdict(int)
    for (day, family), value in cells.items():
        totals[family] += value
    families = sorted([f for f in totals if totals[f] > 0], key=lambda f: (-totals[f], f))
    if compact:
        families = families[:12]
    label_w = 120 if compact else 210
    cell_w = (width - 20 - label_w - 50) / len(days)
    cell_h = 16
    maximum = max(cells.values()) if cells else 1
    ramp = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95")
    table = []
    for fi, family in enumerate(families):
        cy = y + fi * (cell_h + 2)
        label = family if S.text_width(family, 12) < label_w - 10 else family[: int((label_w - 14) / (12 * S.CHAR))] + "…"
        svg.text(20 + label_w - 8, cy + 12, label, "lb", "end")
        for di, day in enumerate(days):
            value = cells.get((day, family), 0)
            cx = 20 + label_w + di * cell_w
            if value:
                level = min(len(ramp) - 1, int((value - 1) * len(ramp) / maximum))
                fill = ramp[level]
            else:
                fill = "var(--neutral2)"
            svg.rect(cx + 0.5, cy, max(cell_w - 1, 1), cell_h, fill, title=f"{family} {day}: {value}")
            table.append({"date_utc": day, "family": family, "request_count": value})
        svg.text(20 + label_w + len(days) * cell_w + 6, cy + 12, number(totals[family], lang), "ax")
    y += len(families) * (cell_h + 2) + 16
    every = 7 if not compact else 14
    for di, day in enumerate(days):
        if di % every == 0:
            svg.text(20 + label_w + di * cell_w + cell_w / 2, y, short_date(date.fromisoformat(day), lang), "ax", "middle")
    y += 22
    x = 20
    svg.rect(x, y - 10, 14, 12, "var(--neutral2)")
    svg.text(x + 20, y, t(lang, "recorded zero", "zéro enregistré"), "ax")
    x += 130
    for level, colour in enumerate(ramp):
        svg.rect(x + level * 16, y - 10, 14, 12, colour)
    svg.text(x + len(ramp) * 16 + 6, y, t(lang, f"1 to {maximum} requests (linear steps)", f"1 à {maximum} requêtes (paliers linéaires)"), "ax")
    y += 18
    note = t(lang, "Every day of the window has rows; no cell is unknown. Families are those of the scope registry; the right-hand number is the family total for the window.",
             "Chaque jour de la fenêtre a des lignes ; aucune cellule n’est inconnue. Les familles sont celles du registre de périmètre ; le nombre à droite est le total de la famille sur la fenêtre.")
    if compact:
        note += t(lang, " Compact view: the twelve largest families.", " Vue compacte : les douze familles les plus importantes.")
    for line in S.wrap(note, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y = S.footer(svg, y, ctx.footer(lang, ["daily-family-summary.csv"]), width)
    svg.desc = t(lang, f"A grid of {len(families)} documentary families by {len(days)} UTC days, shaded by the number of automated provider-origin AI GET 200 requests.",
                 f"Une grille de {len(families)} familles documentaires sur {len(days)} jours UTC, colorée selon le nombre de requêtes GET 200 IA automatisées à origine fournisseur.")
    return svg.render(y), table


def figure_g07(ctx, lang, compact):
    width = 420 if compact else 960
    title = t(lang, "What the main result leaves out: HTTP volume by identification level, method and status, and perimeter",
              "Ce que le résultat principal laisse de côté : volume HTTP par niveau d’identification, méthode et statut, et périmètre")
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Secondary figure. Panels A and B cover the main documentary population, all roles; panel C covers everything the collector recorded. Unit: requests.",
                   "Figure secondaire. Les panneaux A et B couvrent la population documentaire principale, tous rôles confondus ; le panneau C couvre tout ce que le collecteur a enregistré. Unité : requêtes.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    label_w = 170 if compact else 330
    table = []
    svg.text(20, y, t(lang, "A. GET 200 by stored identification level", "A. GET 200 par niveau d’identification enregistré"), "vl")
    tiers = ("provider_origin_verified_actor", "network_verified_claimed_actor", "cloudflare_verified_unattributed",
             "spoofed_or_failed_verification")
    items = []
    for tier in tiers:
        value = ctx.metrics.get(f"main_population.tier.{tier}.get200", {}).get("value", 0)
        fill = "var(--s1)" if tier == "provider_origin_verified_actor" else "var(--neutral)"
        items.append((t(lang, *TIER_LABEL[tier]), value, fill, None))
        table.append({"panel": "A", "category": tier, "requests": value})
    y = _hbars(svg, 20, y + 12, width - 20, items, max(v for _, v, _, _ in items), lang, label_w) + 6
    svg.text(20, y, t(lang, "B. Requests by method and status", "B. Requêtes par méthode et statut"), "vl")
    sums = defaultdict(int)
    resources = {r["resource_id"]: r for r in _rows(ctx, "resources.csv")}
    for row in _rows(ctx, "consultations.csv"):
        if _bool(resources[row["resource_id"]]["main_population"]):
            sums[f"{row['http_method']} {row['http_status']}"] += int(row["request_count"])
    ordered = sorted(sums, key=lambda k: (-sums[k], k))
    items = [(label, sums[label], "var(--s7)" if label == "GET 200" else "var(--neutral)", None) for label in ordered]
    for label, value, _, _ in items:
        table.append({"panel": "B", "category": label, "requests": value})
    y = _hbars(svg, 20, y + 12, width - 20, items, max(v for _, v, _, _ in items), lang, label_w) + 6
    svg.text(20, y, t(lang, "C. All requests recorded by the collector, by population", "C. Toutes les requêtes enregistrées par le collecteur, par population"), "vl")
    populations = defaultdict(int)
    for row in _rows(ctx, "daily-summary.csv"):
        populations[row["population"]] += int(row["request_count"])
    names = {"main_documentary": ("main documentary population", "population documentaire principale"),
             "other_documentary": ("other documentary files (supporting, descriptors, technical)", "autres fichiers (soutien, descripteurs, techniques)"),
             "robots_control": ("robots.txt (control)", "robots.txt (contrôle)"),
             "undeclared_bucket": ("undeclared well-known bucket", "compartiment well-known non déclaré")}
    items = [(t(lang, *names[key]), populations.get(key, 0), "var(--neutral)", None) for key in names]
    for (label, value, _, _), key in zip(items, names):
        table.append({"panel": "C", "category": key, "requests": value})
    y = _hbars(svg, 20, y + 12, width - 20, items, max(v for _, v, _, _ in items), lang, label_w) + 8
    note = t(lang, "HEAD, 304, 3xx and 4xx responses are not successful document bodies. Unattributed and network-claimed levels depend on a Cloudflare predicate under review.",
             "Les réponses HEAD, 304, 3xx et 4xx ne sont pas des corps de documents récupérés avec succès. Les niveaux non attribué et réseau déclaré dépendent d’un prédicat Cloudflare en revue.")
    for line in S.wrap(note, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y = S.footer(svg, y, ctx.footer(lang, ["consultations.csv", "resources.csv", "daily-summary.csv"]), width)
    svg.desc = t(lang, "Three horizontal bar panels: GET 200 of the main population by identification level, its requests by method and status, and all collector requests by population.",
                 "Trois panneaux de barres horizontales : GET 200 de la population principale par niveau d’identification, ses requêtes par méthode et statut, et toutes les requêtes du collecteur par population.")
    return svg.render(y), table


def figure_g08(ctx, lang, compact):
    width = 420 if compact else 960
    coverage = _rows(ctx, "coverage.csv")
    title = t(lang, "Coverage calendar and measurement versions", "Calendrier de couverture et versions de mesure")
    subtitles = [cap(ctx.period(lang)) + ".",
                 t(lang, "Each cell is one UTC day. Status comes from the archived daily report; agreement of counts is not proof of complete coverage.",
                   "Chaque cellule est un jour UTC. Le statut vient du rapport quotidien archivé ; la concordance des comptes ne prouve pas une couverture complète.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    per_row = 10 if compact else 30
    cell = (width - 40) / per_row
    table = []
    for index, row in enumerate(coverage):
        cx = 20 + (index % per_row) * cell
        cy = y + (index // per_row) * (cell + 22)
        status = row["coverage_status"]
        fill = (svg.hatch("partial") if status == "partial_declared" else "var(--neutral2)" if row["observation_status"] == "observed"
                else svg.hatch("na"))
        svg.rect(cx + 1, cy, cell - 2, cell - 2, fill, rx=3, title=f"{row['date_utc']}: {status}; {row['archive_reason_code']}")
        if row["aggregate_minus_v3"] not in ("", "0"):
            svg.add(f'<circle cx="{S.f(cx + cell / 2)}" cy="{S.f(cy + cell / 2 - 1)}" r="4" fill="var(--missing)"/>')
        svg.text(cx + cell / 2, cy + cell + 10, str(date.fromisoformat(row["date_utc"]).day), "ax", "middle")
        table.append({k: row[k] for k in ("date_utc", "observation_status", "coverage_status", "archive_reason_code",
                                          "aggregate_minus_v3", "classifier_version", "producer_deployment_label")})
    rows_used = (len(coverage) + per_row - 1) // per_row
    y += rows_used * (cell + 22) + 6
    for line in S.wrap(t(lang, "Producer deployment active during the day (from the producer's deployment history) and classifier version",
                         "Déploiement du producteur actif pendant la journée (historique de déploiement du producteur) et version du classificateur"), 12.5, width - 40):
        svg.text(20, y, line, "vl")
        y += 16
    segments = []
    for index, row in enumerate(coverage):
        label = row["producer_deployment_label"] or t(lang, "unknown", "inconnu")
        if segments and segments[-1][0] == label:
            segments[-1][2] = index
        else:
            segments.append([label, index, index])
    band = (width - 40) / len(coverage)
    for si, (label, first, last) in enumerate(segments):
        x = 20 + first * band
        w = (last - first + 1) * band
        svg.rect(x + 1, y, w - 2, 18, "var(--neutral2)" if si % 2 else "var(--band)", rx=3,
                 title=f"{label}: {coverage[first]['date_utc']} to {coverage[last]['date_utc']}")
        if w > 30:
            svg.text(x + w / 2, y + 13, label + t(lang, " (100%, effective before the window)", " (100 %, effectif avant la fenêtre)") if len(segments) == 1 and not compact else label, "ax", "middle")
    y += 26
    svg.rect(21, y, width - 42, 18, "var(--band)", rx=3)
    svg.text(width / 2, y + 13, t(lang, "classifier 2026-08-24.1 throughout (predicate under review)", "classificateur 2026-08-24.1 sur toute la période (prédicat en revue)"), "ax", "middle")
    y += 34
    legend = t(lang, "Hatched cell: archive report partial (declared). Dot: aggregate/V3 gap of one request. No day is missing; every daily total of the joint aggregate equals the archived aggregate count. The deployment history was observed about every 6 hours; a deployment shorter than the longest gap between observations cannot be excluded.",
               "Cellule hachurée : rapport d’archive partiel (déclaré). Point : écart agrégat/V3 d’une requête. Aucun jour manquant ; chaque total quotidien de l’agrégat conjoint égale le compte agrégé archivé. L’historique de déploiement a été relevé environ toutes les 6 heures ; un déploiement plus court que le plus long intervalle entre deux relevés ne peut pas être exclu.")
    for line in S.wrap(legend, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y = S.footer(svg, y, ctx.footer(lang, ["coverage.csv", "catalog.json"]), width)
    svg.desc = t(lang, "A calendar of 30 day cells, all hatched as partial reports, two marked with an aggregate/V3 gap, above the producer deployment active during the window and the classifier version.",
                 "Un calendrier de 30 cellules journalières, toutes hachurées comme rapports partiels, deux marquées d’un écart agrégat/V3, au-dessus du déploiement du producteur actif pendant la fenêtre et de la version du classificateur.")
    return svg.render(y), table


def figure_g09(ctx, lang, compact, case):
    width = 420 if compact else 960
    links = [r for r in _rows(ctx, "links.csv") if r["source_site"] == case["site_id"]]
    nodes = case["nodes"]
    layer_of = {node["path"]: node["layer"] for node in nodes}
    strength = {"html_anchor": 0, "markdown_link": 1, "json_reference": 2, "declared_relation": 3, "plain_url_mention": 4}
    best = {}
    for r in links:
        source, target = r["source_path"], r["target_path"]
        if r["target_site"] != case["site_id"] or source not in layer_of or target not in layer_of or source == target:
            continue
        current = best.get((source, target))
        if current is None or strength[r["relation_type"]] < strength[current]:
            best[(source, target)] = r["relation_type"]
    # Drawn: relations from one layer to the next. The others are counted, not hidden.
    edges = sorted((s, tg, rel) for (s, tg), rel in best.items() if layer_of[tg] == layer_of[s] + 1)
    other_edges = len(best) - len(edges)
    title = t(lang, f"Documentary relations verified in the source snapshot: {case['site_id']}",
              f"Relations documentaires vérifiées dans l’instantané source : {case['site_id']}")
    snapshot = next((r["graph_snapshot_at"] for r in links), "")
    subtitles = [t(lang, f"Graph snapshot {case['graph_snapshot_id']} ({snapshot}). Arrows mean “this file references that file”. They are not observed robot paths.",
                   f"Instantané du graphe {case['graph_snapshot_id']} ({snapshot}). Une flèche signifie « ce fichier mentionne ce fichier ». Ce ne sont pas des parcours de robots observés."),
                 t(lang, "Selection: the case's starting page and representative resources; relations from one column to the next are drawn, the others are counted below.",
                   "Sélection : page de départ du cas et ressources représentatives ; les relations d’une colonne à la suivante sont tracées, les autres sont comptées plus bas.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    layers = defaultdict(list)
    for node in nodes:
        layers[node["layer"]].append(node)
    layer_count = max(layers) + 1
    positions = {}
    if compact:
        row_h = 34
        current = y
        for layer in range(layer_count):
            for node in layers[layer]:
                positions[node["path"]] = (40 + layer * 30, current)
                current += row_h
        height_nodes = current
    else:
        col_w = (width - 60) / layer_count
        max_rows = max(len(v) for v in layers.values())
        for layer in range(layer_count):
            for index, node in enumerate(layers[layer]):
                positions[node["path"]] = (30 + layer * col_w, y + 10 + index * 46)
        height_nodes = y + 10 + max_rows * 46
    svg.defs.append('<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="var(--ink2)"/></marker>')
    box_w = min(210, (width - 60) / layer_count - 50) if not compact else 300
    for source, target, relation in edges:
        (x1, y1), (x2, y2) = positions[source], positions[target]
        if compact:
            sx, sy, tx, ty = x1 - 8, y1 + 10, x2 - 8, y2 + 6
            path = f"M{S.f(sx)},{S.f(sy)}C{S.f(sx - 24)},{S.f(sy)} {S.f(tx - 24)},{S.f(ty)} {S.f(tx)},{S.f(ty)}"
        else:
            sx, sy, tx, ty = x1 + box_w, y1 + 14, x2, y2 + 14
            if tx <= sx:
                path = f"M{S.f(x1 + box_w / 2)},{S.f(y1 + 28)}C{S.f(x1 + box_w / 2)},{S.f(y1 + 50)} {S.f(x2 + box_w / 2)},{S.f(y2 - 20)} {S.f(x2 + box_w / 2)},{S.f(y2)}"
            else:
                bend = (tx - sx) / 2
                path = f"M{S.f(sx)},{S.f(sy)}C{S.f(sx + bend)},{S.f(sy)} {S.f(tx - bend)},{S.f(ty)} {S.f(tx)},{S.f(ty)}"
        dash = ' stroke-dasharray="4 3"' if relation in ("plain_url_mention", "declared_relation") else ""
        svg.add(f'<path d="{path}" fill="none" stroke="var(--ink2)" stroke-width="1.5" marker-end="url(#arrow)"{dash}>'
                f"<title>{source} → {target} ({relation})</title></path>")
    for node in nodes:
        x, ny = positions[node["path"]]
        fill = "var(--band)" if node.get("kind") == "html" else "var(--surface)"
        svg.rect(x, ny, box_w if not compact else width - x - 20, 28, fill, rx=6,
                 extra=f' stroke="{SITE_COLOR[case["site_id"]]}" stroke-width="1.5"', title=node["path"])
        room = (box_w if not compact else width - x - 20) - 16
        fits = int(room / (11.5 * S.CHAR))
        label = node["path"] if len(node["path"]) <= fits else node["path"][:max(fits - 1, 4)] + "…"
        svg.text(x + 8, ny + 18, label, "lb", extra=' style="font-size:11.5px"')
    y = height_nodes + 14
    legend = t(lang, f"Drawn: {len(edges)} relations from one column to the next, between {len(nodes)} resources; {other_edges} other relations between the same resources are listed in links.csv. Solid: link or reference written in the file (html_anchor, markdown_link, json_reference). Dashed: plain URL mention or declared relation. Absence of an arrow means “not drawn or not found in this graph”, not “never referenced”.",
               f"Tracées : {len(edges)} relations d’une colonne à la suivante, entre {len(nodes)} ressources ; {other_edges} autres relations entre ces mêmes ressources figurent dans links.csv. Trait plein : lien ou référence écrit dans le fichier (html_anchor, markdown_link, json_reference). Pointillé : mention d’URL ou relation déclarée. L’absence de flèche signifie « non tracé ou non trouvé dans ce graphe », pas « jamais référencé ».")
    for line in S.wrap(legend, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    dates = ctx.catalog["dates"]
    extracted = dates["extracted_at"]
    y = S.footer(svg, y, [
        t(lang, f"Edition {ctx.edition_id}. Graph: source snapshot of {snapshot} (UTC date), not request data. Measurement window of the edition: {ctx.period('en')} (end exclusive {dates['period_end_exclusive']}T00:00:00Z).",
          f"Édition {ctx.edition_id}. Graphe : instantané source du {snapshot} (date UTC), pas des données de requêtes. Fenêtre de mesure de l’édition : {ctx.period('fr')} (fin exclusive {dates['period_end_exclusive']}T00:00:00Z)."),
        t(lang, f"Request data of the edition extracted {extracted['start'][:16].replace('T', ' ')} UTC. Coverage: relations written in the snapshot files only (anchors for HTML pages); deployment of this exact version during the window is not established.",
          f"Données de requêtes de l’édition extraites le {extracted['start'][:10]} à {extracted['start'][11:16]} UTC. Couverture : relations écrites dans les fichiers de l’instantané seulement (ancres pour les pages HTML) ; le déploiement de cette version exacte pendant la fenêtre n’est pas établi."),
        t(lang, "Source table: ", "Table source : ") + f"data/editions/{ctx.edition_id}/links.csv"], width)
    svg.desc = t(lang, f"Node-link diagram of {len(nodes)} documents of {case['site_id']} and the {len(edges)} references written between them in the source snapshot.",
                 f"Diagramme nœuds-liens de {len(nodes)} documents de {case['site_id']} et des {len(edges)} références écrites entre eux dans l’instantané source.")
    table = [{"source_path": s, "target_path": tg, "relation_type": rel} for s, tg, rel in edges]
    return svg.render(y), table


def figure_g10(ctx, lang, compact):
    width = 420 if compact else 960
    title = t(lang, "Edition history", "Historique des éditions")
    subtitles = [t(lang, "Monthly reference editions, windows anchored on the 15th (UTC). Only one edition exists: no trend is computed.",
                   "Éditions mensuelles de référence, fenêtres ancrées le 15 (UTC). Une seule édition existe : aucune tendance n’est calculée.")]
    svg = S.Svg(width, title, "")
    y = S.header(svg, title, subtitles, width, compact)
    value = ctx.m("main.get200")
    svg.line(40, y + 60, width - 30, y + 60, "axis")
    svg.add(f'<circle cx="{S.f(80)}" cy="{S.f(y + 60)}" r="6" fill="var(--s1)"><title>{ctx.edition_id}: {value}</title></circle>')
    svg.text(80, y + 40, number(value, lang) + t(lang, " requests", " requêtes"), "vl", "middle")
    svg.text(80, y + 82, ctx.edition_id, "ax", "start" if compact else "middle")
    svg.text(width - 30, y + 82, t(lang, "next window: Oct 15 to Nov 14, 2026 (31 days), not yet available",
                                   "fenêtre suivante : du 15 octobre au 14 novembre 2026 (31 jours), pas encore disponible") if not compact else "",
             "ax", "end")
    y += 104
    note = t(lang, "Value: GET 200 requests, main documentary population, provider-origin AI roles. Two editions are compared only when windows, definitions, coverage, registries, classifications and scope rules allow it.",
             "Valeur : requêtes GET 200, population documentaire principale, rôles IA à origine fournisseur. Deux éditions ne sont comparées que si fenêtres, définitions, couverture, registres, classifications et règles de périmètre le permettent.")
    for line in S.wrap(note, 12, width - 40):
        svg.text(20, y, line, "ax")
        y += 15
    y = S.footer(svg, y, ctx.footer(lang, ["metrics.json"]), width)
    svg.desc = t(lang, "A single point for the only existing edition; no trend.", "Un seul point pour l’unique édition existante ; aucune tendance.")
    return svg.render(y), [{"edition_id": ctx.edition_id, "main_get200": value, "comparable_previous": None}]


FIGURES = {
    "G01": (figure_g01, ("daily-summary.csv", "coverage.csv")),
    "G02": (figure_g02, ("consultations.csv", "resources.csv")),
    "G03": (figure_g03, ("consultations.csv", "resources.csv")),
    "G04": (figure_g04, ("resources.csv", "consultations.csv", "resource-summary.csv")),
    "G05": (figure_g05, ("consultations.csv", "resources.csv")),
    "G06": (figure_g06, ("daily-family-summary.csv",)),
    "G07": (figure_g07, ("consultations.csv", "resources.csv", "daily-summary.csv")),
    "G08": (figure_g08, ("coverage.csv", "catalog.json")),
    "G10": (figure_g10, ("metrics.json",)),
}


def table_csv(rows: list[dict]) -> str:
    if not rows:
        return "status\nno_rows\n"
    fields = list(rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return csv_text(fields, rows)


def digest(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))
