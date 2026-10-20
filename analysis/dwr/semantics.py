"""Shared bilingual interpretation blocks derived from public bytes."""
from .common import load_json, read_csv
from .i18n import number


def daily_contract(edition, lang):
    current = read_csv(edition.dir / "daily-summary.csv")
    source = edition.catalog.get("supersedes")
    revision = bool(source and edition.catalog.get("revision_kind") == "privacy_revision_same_observations")
    old = read_csv(edition.dir.parent / source / "daily-summary.csv") if revision else current
    a, b = len(old), len(current)
    before, after = sum(int(r["request_count"]) for r in old), sum(int(r["request_count"]) for r in current)
    n = lambda v: number(v, lang)
    prefix = ""
    if revision:
        fields = [k for k in old[0] if k != "edition_id"] if old else []
        remaining = {tuple(row.get(k, "") for k in fields) for row in current}
        removed = [row for row in old if tuple(row.get(k, "") for k in fields) not in remaining]
        grouped = sum(row.get("actor_role") == "protected_strata" for row in removed)
        if lang == "fr":
            prefix = (f"`daily-summary.csv` passe de {n(a)} lignes et {n(before)} requêtes dans `{source}` à {n(b)} lignes et "
                      f"{n(after)} requêtes dans `{edition.id}`. Parmi les {n(len(removed))} lignes retirées, "
                      f"{n(grouped)} étaient déjà regroupées sous `protected_strata` et {n(len(removed)-grouped)} "
                      "relèvent des autres strates désormais protégées par la politique de cette révision. ")
        else:
            prefix = (f"`daily-summary.csv` changes from {n(a)} rows and {n(before)} requests in `{source}` to {n(b)} rows and "
                      f"{n(after)} requests in `{edition.id}`. Of the {n(len(removed))} removed rows, "
                      f"{n(grouped)} were already grouped under `protected_strata` and {n(len(removed)-grouped)} "
                      "belong to other strata now protected by this revision's policy. ")
    elif lang == "fr":
        prefix = f"`daily-summary.csv` contient {n(b)} lignes et {n(after)} requêtes dans `{edition.id}`. "
    else:
        prefix = f"`daily-summary.csv` contains {n(b)} rows and {n(after)} requests in `{edition.id}`. "
    if lang == "fr":
        return (prefix + "Les lignes protégées sont retenues, pas transformées en zéros. "
                "Une ligne absente peut donc être retenue par la politique de diffusion ; elle ne prouve pas une absence de requête. "
                "`collector.requests` somme les lignes encore publiées, pas le trafic total du collecteur.\n\n"
                "Zéro explicite : aucune ligne enregistrée pour la cellule autorisée, sous la couverture déclarée. "
                "Null : valeur non calculable ou indisponible. Retenue : valeur retirée de la diffusion, y compris "
                "les marges `aggregate_count`, `v3_count` et `aggregate_minus_v3`. Source indisponible : aucune observation de remplacement. "
                "La couverture partielle n’est jamais requalifiée en couverture complète.")
    return (prefix + "Protected rows are withheld, not converted to zeros. "
            "An absent row can therefore be withheld by the distribution policy; it does not prove absence of a request. "
            "`collector.requests` sums the remaining published rows, not all collector traffic.\n\n"
            "Explicit zero: no recorded row for the allowed cell, under the declared coverage. "
            "Null: unavailable or not calculable. Withheld: removed from distribution, including "
            "`aggregate_count`, `v3_count` and `aggregate_minus_v3` margins. Source unavailable: no replacement observation. "
            "Partial coverage is never upgraded to complete coverage.")


def inventory_contract(lang, root):
    count = load_json(root / "config/publication-inventory.json")["historical_states_count"]
    if lang == "fr":
        return (f"L’inventaire décrit {count} états historiques nommés, pas {count} commits. "
                "Les octets déclarés sont vérifiés localement ; l’exhaustivité des références Git exige une preuve distincte. "
                "Les copies tierces inconnues et leurs données auxiliaires restent hors de cette preuve.")
    return (f"The inventory describes {count} named historical states, not {count} commits. "
            "Declared bytes are checked locally; completeness of Git references requires separate evidence. "
            "Unknown third-party copies and auxiliary data remain outside that evidence.")
