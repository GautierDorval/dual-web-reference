"""Shared bilingual interpretation blocks derived from public bytes."""
from .common import load_json, read_csv
from .i18n import number


def daily_contract(edition, lang):
    current = read_csv(edition.dir / "daily-summary.csv")
    source = edition.catalog.get("supersedes")
    old = read_csv(edition.dir.parent / source / "daily-summary.csv") if source else current
    a, b = len(old), len(current)
    before, after = sum(int(r["request_count"]) for r in old), sum(int(r["request_count"]) for r in current)
    n = lambda v: number(v, lang)
    if lang == "fr":
        return (f"`daily-summary.csv` passe de {n(a)} lignes et {n(before)} requêtes dans r1 à {n(b)} lignes et "
                f"{n(after)} requêtes dans r2. Les {n(a-b)} lignes protégées sont retenues, pas transformées en zéros. "
                "Une ligne absente peut donc être retenue par la politique de diffusion ; elle ne prouve pas une absence de requête. "
                "`collector.requests` somme les lignes encore publiées, pas le trafic total du collecteur.\n\n"
                "Zéro explicite : aucune ligne enregistrée pour la cellule autorisée, sous la couverture déclarée. "
                "Null : valeur non calculable ou indisponible. Retenue : valeur retirée de la diffusion, y compris "
                "les marges `aggregate_count`, `v3_count` et `aggregate_minus_v3`. Source indisponible : aucune observation de remplacement. "
                "La couverture partielle n’est jamais requalifiée en couverture complète.")
    return (f"`daily-summary.csv` changes from {n(a)} rows and {n(before)} requests in r1 to {n(b)} rows and "
            f"{n(after)} requests in r2. The {n(a-b)} protected rows are withheld, not converted to zeros. "
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
