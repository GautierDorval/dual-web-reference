"""publication-gate: the check of what would actually be published.

It reads the Git objects reachable from the branch to publish: every commit (structural
header lines apart, the rest of the header and the whole message), every entry name of
every tree, trees included, and every blob as raw bytes, binary files included. No path
is excluded. Each file must be of an admitted type; a PNG must have exactly the
structure IHDR, IDAT..., IEND with an empty IEND and image data of exactly the size its
header announces. A 40-character identifier is admitted only as an action pin listed in
config/publication-gate.json, written owner/repository@<commit>. JSON files are also
checked after decoding their strings, and text after decoding percent escapes. Local
paths are checked against the actual local roots of the machine that runs the gate
(home folder in long and short form, private workspace), after folding case and
separators; generic markers of other machines' paths are an additional best effort. Private terms and identifiers are read from the private workspace,
compared without regard to case, and never printed: a finding names a category and a
path, and a path that itself holds a private value or an identifier-like string is
replaced by its position in the listing.

Threat model: private material included by mistake. The gate is not a proof against a
payload crafted to evade it; in particular the pixels of a PNG are not read as text.

COVERAGE is the single list of what the gate detects, with the counterexamples its
tests plant for each category. tests/test_publication_gate.py runs one mutation per
listed counterexample and requires the list and the mutations to match one to one; the
documentation block that describes the gate is generated from this list.
"""

from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import zlib
from pathlib import Path
from urllib.parse import unquote

from .common import DwrError, load_json

# (category, what is detected EN, FR, ((counterexample id, EN, FR), ...))
COVERAGE = (
    ("history_not_single_root", "the branch has more than one commit, or a commit with a parent",
     "la branche compte plus d’un commit, ou un commit avec un parent",
     (("second_commit", "a second commit", "un second commit"),)),
    ("unsupported_entry", "a symbolic link or a submodule in a tree", "un lien symbolique ou un sous-module dans un arbre",
     (("symlink", "a symbolic link", "un lien symbolique"), ("submodule", "a submodule entry", "une entrée de sous-module"))),
    ("file_type_not_admitted", "a file whose type is not in the admitted list",
     "un fichier dont le type n’est pas dans la liste admise",
     (("executable", "an executable file", "un fichier exécutable"),)),
    ("text_not_utf8", "a text file that is not valid UTF-8", "un fichier texte qui n’est pas en UTF-8 valide",
     (("latin1_byte", "a Latin-1 byte in Markdown", "un octet Latin-1 dans un Markdown"),)),
    ("private_term", "a private repository name, private resource name or private label, in any case",
     "un nom de dépôt privé, un nom de ressource privée ou un libellé privé, quelle que soit la casse",
     (("in_file", "in a file", "dans un fichier"), ("uppercase", "in capitals in a file", "en majuscules dans un fichier"),
      ("in_path", "in a file name", "dans un nom de fichier"),
      ("in_empty_tree_name", "in the name of an empty tree", "dans le nom d’un arbre vide"),
      ("in_commit_message", "in the commit message", "dans le message du commit"),
      ("in_png_text_chunk", "in a PNG text chunk", "dans un bloc texte d’un PNG"),
      ("json_unicode_escaped", "written as JSON Unicode escapes", "écrit en échappements Unicode JSON"),
      ("bom_json_escaped", "JSON Unicode escapes in a file that starts with a byte order mark",
       "des échappements Unicode JSON dans un fichier qui commence par une marque d’ordre des octets"),
      ("percent_encoded", "percent-encoded in a URL", "encodé en pourcentage dans une URL"))),
    ("private_identifier", "an account or database identifier of the acquisition configuration, in any case",
     "un identifiant de compte ou de base de données de la configuration d’acquisition, quelle que soit la casse",
     (("in_test_file", "in a test file", "dans un fichier de test"), ("uppercase", "in capitals", "en majuscules"),
      ("in_path", "in a file name, never echoed in the report", "dans un nom de fichier, jamais réaffiché dans le rapport"))),
    ("private_commit", "a full commit identifier of the internal lock, in any case",
     "un identifiant de commit complet du verrou interne, quelle que soit la casse",
     (("in_csv", "in a CSV file", "dans un fichier CSV"), ("uppercase", "in capitals", "en majuscules"))),
    ("private_commit_prefix", "the first seven characters (or more) of a commit identifier of the internal lock",
     "les sept premiers caractères (ou plus) d’un identifiant de commit du verrou interne",
     (("eight_in_markdown", "eight characters in Markdown", "huit caractères dans un Markdown"),
      ("seven_in_log_line", "seven characters at the start of a log line", "sept caractères en tête d’une ligne de journal"),
      ("in_commit_link", "seven characters in a `/commit/` link", "sept caractères dans un lien `/commit/`"))),
    ("local_root", "a local root of the machine that runs the gate (home folder in long or short form, private workspace), in any case and with any separators, also inside JSON strings and percent escapes",
     "une racine locale de la machine qui exécute la porte (dossier personnel en forme longue ou courte, espace privé), quelle que soit la casse et quels que soient les séparateurs, y compris dans des chaînes JSON et des échappements en pourcentage",
     (("lower_case", "the home folder in lower case, as `ntpath.normcase` writes it",
       "le dossier personnel en minuscules, comme l’écrit `ntpath.normcase`"),
      ("upper_case", "the home folder in capitals", "le dossier personnel en majuscules"),
      ("forward_slashes", "the home folder with forward slashes", "le dossier personnel avec des barres obliques"),
      ("canonical_json", "the home folder serialized by `common.canonical_json`",
       "le dossier personnel sérialisé par `common.canonical_json`"),
      ("unix_shell_form", "the `/c/…` form of a Unix-style shell", "la forme `/c/…` d’un shell de type Unix"),
      ("short_name", "the 8.3 short name of the home folder", "le nom court 8.3 du dossier personnel"),
      ("workspace_tail", "the private workspace path without the home prefix",
       "le chemin de l’espace privé sans le préfixe du dossier personnel"),
      ("percent_encoded", "the home folder percent-encoded in a URL", "le dossier personnel encodé en pourcentage dans une URL"))),
    ("local_path", "a generic marker of a local path on any machine, best effort (Windows user folder, `/home/<name>/`, `/Users/<name>/`, Unix-style shell user folder, synchronized folder, application data), in any case",
     "un marqueur générique de chemin local sur n’importe quelle machine, protection d’appoint (dossier utilisateur Windows, `/home/<nom>/`, `/Users/<nom>/`, dossier utilisateur d’un shell de type Unix, dossier synchronisé, données d’application), quelle que soit la casse",
     (("in_markdown", "a user folder in Markdown", "un dossier utilisateur dans un Markdown"),
      ("json_escaped", "a user folder serialized in JSON (doubled separators)",
       "un dossier utilisateur sérialisé en JSON (séparateurs doublés)"),
      ("forward_slashes", "a user folder written with forward slashes", "un dossier utilisateur écrit avec des barres obliques"),
      ("lower_case", "a user folder in lower case", "un dossier utilisateur en minuscules"),
      ("unix_home", "a `/home/<name>/` folder", "un dossier `/home/<nom>/`"),
      ("mac_users", "a `/Users/<name>/` folder", "un dossier `/Users/<nom>/`"))),
    ("ip_address", "an IPv4 address", "une adresse IPv4",
     (("in_markdown", "in Markdown", "dans un Markdown"), ("in_path", "in a file name", "dans un nom de fichier"))),
    ("user_agent", "a browser user-agent string", "une chaîne user agent de navigateur",
     (("in_markdown", "in Markdown", "dans un Markdown"),)),
    ("identifier_32", "a 32-character hexadecimal identifier, in either case",
     "un identifiant hexadécimal de 32 caractères, dans l’une ou l’autre casse",
     (("lowercase", "in lower case in code", "en minuscules dans du code"),
      ("uppercase", "in upper case in code", "en majuscules dans du code"),
      ("in_path", "in a file name", "dans un nom de fichier"))),
    ("identifier_40", "a 40-character hexadecimal identifier, in either case, except an action pin listed in `config/publication-gate.json` and written exactly `owner/repository@<commit>`",
     "un identifiant hexadécimal de 40 caractères, dans l’une ou l’autre casse, sauf un épinglage d’action listé dans `config/publication-gate.json` et écrit exactement `propriétaire/dépôt@<commit>`",
     (("workflow_comment", "in a comment of a workflow template", "dans un commentaire d’un modèle de workflow"),
      ("pin_value_repeated_bare", "an admitted pin value repeated without its `owner/repository@` prefix",
       "la valeur d’un épinglage admis répétée sans son préfixe `propriétaire/dépôt@`"),
      ("unlisted_pin_in_workflow", "a pin that is not in the list, on a `uses:` step",
       "un épinglage absent de la liste, sur une étape `uses:`"),
      ("unlisted_pin_in_run_block", "a pin that is not in the list, inside a `run:` block scalar",
       "un épinglage absent de la liste, dans le bloc scalaire d’une étape `run:`"),
      ("tree_line_in_message", "a `tree` line inside the commit message", "une ligne `tree` dans le message du commit"))),
    ("short_commit", "a short commit reference (`commit` followed by 7 to 12 hexadecimal characters)",
     "une référence courte de commit (`commit` suivi de 7 à 12 caractères hexadécimaux)",
     (("in_markdown", "in Markdown", "dans un Markdown"),)),
    ("png_chunk_not_admitted", "a PNG chunk other than IHDR, IDAT and IEND",
     "un bloc PNG autre que IHDR, IDAT et IEND",
     (("text_chunk", "a text chunk", "un bloc texte"), ("palette_chunk", "a palette chunk", "un bloc de palette"))),
    ("png_malformed", "a PNG whose structure differs from one IHDR of 13 bytes, IDAT chunks, one empty IEND, or whose image data differs from the announced size",
     "un PNG dont la structure diffère d’un IHDR unique de 13 octets, de blocs IDAT et d’un IEND unique et vide, ou dont les données d’image diffèrent de la taille annoncée",
     (("trailing_data", "data after IEND", "des données après IEND"), ("iend_payload", "a non-empty IEND", "un IEND non vide"),
      ("duplicate_ihdr", "a second IHDR", "un second IHDR"), ("idat_extra", "extra image data", "des données d’image en trop"),
      ("truncated", "a truncated file", "un fichier tronqué"), ("bad_crc", "a wrong checksum", "une somme de contrôle fausse"),
      ("extreme_dimensions", "dimensions beyond 16 384 pixels", "des dimensions au-delà de 16 384 pixels"))),
)
CATEGORY_IDS = tuple(entry[0] for entry in COVERAGE)
EXACT_CATEGORIES = ("private_term", "private_identifier", "private_commit", "private_commit_prefix")

TEXT_SUFFIXES = (".md", ".csv", ".json", ".svg", ".py", ".yml", ".yml.example", ".txt", ".toml", ".ps1", ".mjs",
                 ".js", ".css", ".cff")
TEXT_NAMES = (".gitignore", ".gitattributes", ".python-version")
BINARY_SUFFIXES = (".png",)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 4: (8, 16), 6: (8, 16)}
PNG_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}
PNG_MAX_SIDE = 16384
PNG_MAX_RAW = 1 << 28
PIN_CONFIG = Path(__file__).resolve().parents[2] / "config" / "publication-gate.json"

# Patterns are written so that they do not match their own source.
LOCAL_PATH = re.compile(r"\b[a-z]:(?:\\{1,2}|/)users(?:\\{1,2}|/)|/[a-z]/users/|(?:^|[\s\"'(=:])/(?:home|users)/[^/\s\"']+/"
                        r"|drop[b]ox|(?:\\{1,2}|/)app[d]ata(?:\\{1,2}|/)", re.IGNORECASE | re.MULTILINE)
IPV4 = re.compile(r"(?<!\d)(?<!\d\.)(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d|\.\d)")
USER_AGENT = re.compile(r"Mozill[a]/\d|AppleWeb[K]it|Chrom[e]/\d")
HEX32 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")
HEX40 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{40}(?![0-9a-fA-F])")
SHORT_COMMIT = re.compile(r"\bcommi[t]\s+[0-9a-fA-F]{7,12}\b", re.IGNORECASE)
PIN = re.compile(r"(?<![\w.-])(?P<pair>[\w.-]+/[\w.-]+)@(?P<sha>[0-9a-fA-F]{40})(?![0-9a-fA-F])")
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def fold_path(text: str) -> str:
    """Lower case, every separator as one forward slash: the form in which local roots are compared."""
    return re.sub(r"/{2,}", "/", text.lower().replace("\\", "/"))


def local_roots(paths=()) -> frozenset[str]:
    """Folded local roots: the home folder (long form, and the short form seen in the temporary folder variables),
    the other given paths cut to their home folder, and the `/c/...` form of each Windows root."""
    candidates = [str(Path.home()), *(os.environ.get(k) for k in ("USERPROFILE", "HOME", "TEMP", "TMP", "LOCALAPPDATA",
                                                                    "APPDATA")), *map(str, paths)]
    roots = set()
    for candidate in candidates:
        if not candidate:
            continue
        folded = fold_path(candidate).rstrip("/")
        home = re.match(r"^(?:[a-z]:/user[s]/[^/]+|/hom[e]/[^/]+|/user[s]/[^/]+)", folded)
        root = home.group(0) if home else folded
        if len(root) < 8:
            continue
        roots.add(root)
        drive = re.match(r"^([a-z]):(/.+)$", root)
        if drive:
            roots.add(f"/{drive.group(1)}{drive.group(2)}")
    return frozenset(roots)


class Secrets:
    """Private values to look for, kept in lower case in memory only; never written or printed."""

    def __init__(self, terms=(), identifiers=(), commits=(), roots=None):
        self.terms = tuple(t.lower() for t in terms)
        self.identifiers = tuple(v.lower() for v in identifiers)
        self.commits = tuple(c.lower() for c in commits)
        self.prefixes = tuple(sorted({c[:7] for c in self.commits}))
        self.roots = frozenset(roots) if roots is not None else local_roots()


def load_secrets(private_root: Path) -> Secrets:
    lock = Path(private_root) / "lock"
    paths = {name: lock / name for name in ("private-terms.json", "acquisition-config.json", "private-lock.json")}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise DwrError("private_secrets_unavailable", ", ".join(missing))
    spec = load_json(paths["private-terms.json"])
    terms = [t for key in ("private_repository_names", "private_resource_names", "private_labels") for t in spec[key]]
    identifiers = [v for v in load_json(paths["acquisition-config.json"]).values()
                   if isinstance(v, str) and (re.fullmatch(r"[0-9a-fA-F]{32}", v) or UUID.fullmatch(v))]
    commits = sorted(set(HEX40.findall(paths["private-lock.json"].read_text(encoding="utf-8"))))
    roots = set(local_roots([private_root]))
    home = fold_path(str(Path.home())).rstrip("/") + "/"
    workspace = fold_path(str(Path(private_root).resolve())).rstrip("/")
    if workspace.startswith(home):
        roots.add(workspace[len(home):])
    return Secrets(terms, identifiers, commits, roots)


def admitted(path: str) -> str | None:
    """'text', 'binary' or None for a file type that is not admitted."""
    name = path.rsplit("/", 1)[-1]
    if name in TEXT_NAMES or any(name.endswith(s) for s in TEXT_SUFFIXES):
        return "text"
    if any(name.endswith(s) for s in BINARY_SUFFIXES):
        return "binary"
    return None


def png_findings(data: bytes) -> list[str]:
    """A PNG is admitted only as IHDR (13 bytes, valid parameters), one or more IDAT, then one empty IEND, with nothing
    after it, valid checksums, and image data that decompresses to exactly the size announced by IHDR."""
    if not data.startswith(PNG_SIGNATURE):
        return ["png_malformed"]
    chunks, position, found = [], len(PNG_SIGNATURE), set()
    while position < len(data):
        if position + 8 > len(data):
            return sorted(found | {"png_malformed"})
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        payload = data[position + 8:position + 8 + length]
        crc = data[position + 8 + length:position + 12 + length]
        if len(payload) != length or len(crc) != 4 or struct.unpack(">I", crc)[0] != zlib.crc32(kind + payload):
            return sorted(found | {"png_malformed"})
        chunks.append((kind, payload))
        position += 12 + length
        if kind == b"IEND":
            break
    if position != len(data):
        found.add("png_malformed")
    kinds = [kind for kind, _ in chunks]
    if any(kind not in (b"IHDR", b"IDAT", b"IEND") for kind in kinds):
        found.add("png_chunk_not_admitted")
    if (len(kinds) < 3 or kinds[0] != b"IHDR" or kinds[-1] != b"IEND" or kinds.count(b"IHDR") != 1
            or kinds.count(b"IEND") != 1 or chunks[-1][1] != b"" or len(chunks[0][1]) != 13
            or any(kind != b"IDAT" for kind in kinds[1:-1])):
        return sorted(found | {"png_malformed"})
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    if (not 0 < width <= PNG_MAX_SIDE or not 0 < height <= PNG_MAX_SIDE or depth not in PNG_DEPTHS.get(color, ())
            or (compression, filtering, interlace) != (0, 0, 0)):
        return sorted(found | {"png_malformed"})
    row = -(-width * PNG_CHANNELS[color] * depth // 8)
    expected = height * (1 + row)
    if expected > PNG_MAX_RAW:
        return sorted(found | {"png_malformed"})
    stream = zlib.decompressobj()
    try:
        raw = stream.decompress(b"".join(p for k, p in chunks if k == b"IDAT"), expected + 1)
    except (zlib.error, OverflowError, MemoryError, ValueError):
        return sorted(found | {"png_malformed"})
    if (len(raw) != expected or not stream.eof or stream.unused_data or stream.unconsumed_tail
            or any(raw[i * (1 + row)] > 4 for i in range(height))):
        found.add("png_malformed")
    return sorted(found)


def admitted_pins(config: Path = PIN_CONFIG) -> frozenset[str]:
    """owner/repository@<commit> values listed in config/publication-gate.json (public action commits)."""
    if not config.is_file():
        return frozenset()
    return frozenset(load_json(config)["admitted_action_pins"])


def pattern_findings(path: str, text: str, pins: frozenset[str] | None = None) -> list[str]:
    found = []
    if LOCAL_PATH.search(text):
        found.append("local_path")
    if IPV4.search(text):
        found.append("ip_address")
    if USER_AGENT.search(text):
        found.append("user_agent")
    if HEX32.search(text):
        found.append("identifier_32")
    pins = admitted_pins() if pins is None else pins
    admitted_spans = {(m.start("sha"), m.end("sha")) for m in PIN.finditer(text)
                      if f"{m.group('pair')}@{m.group('sha')}" in pins}
    if any((m.start(), m.end()) not in admitted_spans for m in HEX40.finditer(text)):
        found.append("identifier_40")
    if SHORT_COMMIT.search(text):
        found.append("short_commit")
    return found


def root_findings(text: str, secrets: Secrets | None) -> list[str]:
    roots = secrets.roots if secrets is not None else default_roots()
    folded = fold_path(text)
    if "%" in text:
        folded += "\n" + fold_path(unquote(text))
    return ["local_root"] if any(root in folded for root in roots) else []


_DEFAULT_ROOTS: list[frozenset[str]] = []


def default_roots() -> frozenset[str]:
    if not _DEFAULT_ROOTS:
        _DEFAULT_ROOTS.append(local_roots())
    return _DEFAULT_ROOTS[0]


def exact_findings(text: str, secrets: Secrets | None) -> list[str]:
    if secrets is None:
        return []
    lowered = text.lower()
    if "%" in text:
        lowered += "\n" + unquote(text).lower()
    found = []
    if any(term in lowered for term in secrets.terms):
        found.append("private_term")
    if any(value in lowered for value in secrets.identifiers):
        found.append("private_identifier")
    if any(commit in lowered for commit in secrets.commits):
        found.append("private_commit")
    elif any(re.search(rf"(?<![0-9a-f]){prefix}", lowered) for prefix in secrets.prefixes):
        found.append("private_commit_prefix")
    return found


def name_findings(path: str, secrets: Secrets | None) -> list[str]:
    """Checks of an entry name itself (file or tree). No action pin is admitted in a name."""
    return sorted(set(exact_findings(path, secrets)) | set(root_findings(path, secrets))
                  | set(pattern_findings("", path, frozenset())))


def json_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for key, item in value.items() for s in [key, *json_strings(item)]]
    if isinstance(value, list):
        return [s for item in value for s in json_strings(item)]
    return []


def scan_bytes(path: str, data: bytes, secrets: Secrets | None, pins: frozenset[str] | None = None) -> list[str]:
    """Finding categories for the content of one file. Exact private values are searched in every byte of every
    file; patterns are applied to text files, and to the decoded strings of a JSON file as well. A PNG may not hold
    any text: its structure is checked instead."""
    found = []
    if path.endswith(".png"):
        found += png_findings(data)
        found += exact_findings(data.decode("latin-1"), secrets)
        found += root_findings(data.decode("latin-1"), secrets)
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            found.append("text_not_utf8")
            text = data.decode("utf-8", errors="replace")
        found += exact_findings(text, secrets)
        found += root_findings(text, secrets)
        found += pattern_findings(path, text, pins)
        if path.endswith(".json"):
            try:
                decoded = "\n".join(json_strings(json.loads(text.lstrip("\ufeff"))))
            except (ValueError, RecursionError):
                decoded = ""
            found += exact_findings(decoded, secrets)
            found += root_findings(decoded, secrets)
            found += pattern_findings(path, decoded, pins)
    return sorted(set(found))


def safe_path(path: str, index: int, secrets: Secrets | None) -> str:
    """The path as printed in a report: replaced by its position when it holds a private value or an identifier."""
    return f"<entry {index} withheld>" if name_findings(path, secrets) else path


def commit_findings(raw: bytes, secrets: Secrets | None) -> list[str]:
    """A commit object: the structural tree and parent lines of the header are skipped by the patterns, nothing else;
    the message is checked whole, including any line that looks like a header."""
    text = raw.decode("utf-8", errors="replace")
    header, _, message = text.partition("\n\n")
    kept = [line for line in header.split("\n") if not re.match(r"^(?:tree|parent) [0-9a-f]{40}$", line)]
    found = (set(exact_findings(text, secrets)) | set(root_findings(text, secrets))
             | set(pattern_findings("", "\n".join(kept) + "\n\n" + message, frozenset())))
    return sorted(found)


def _git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, check=False)
    if result.returncode != 0:
        raise DwrError("git_failed", " ".join(args[:2]) + ": " + result.stderr.decode("utf-8", "replace").strip()[:200])
    return result.stdout


def _read_objects(repo: Path, shas: list[str]) -> dict[str, bytes]:
    if not shas:
        return {}
    out = _git(repo, "cat-file", "--batch", data=("\n".join(shas) + "\n").encode())
    objects, position = {}, 0
    for sha in shas:
        header_end = out.index(b"\n", position)
        _, kind, size = out[position:header_end].split(b" ")
        start = header_end + 1
        objects[sha] = out[start:start + int(size)]
        position = start + int(size) + 1
    return objects


def check_ref(repo: Path, ref: str, secrets: Secrets, *, require_single_root: bool = True,
              pins: frozenset[str] | None = None) -> dict:
    commit = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    lines = _git(repo, "rev-list", "--parents", commit).decode().split("\n")
    history = [line.split() for line in lines if line.strip()]
    raw = []
    if require_single_root and (len(history) != 1 or len(history[0]) != 1):
        raw.append(("history_not_single_root", None))
    for sha, content in _read_objects(repo, [h[0] for h in history]).items():
        raw += [(category, f"commit {sha[:12]}") for category in commit_findings(content, secrets)]
    entries = {}
    for sha, *_ in history:
        for item in _git(repo, "ls-tree", "-r", "-t", "-z", "--full-tree", sha).split(b"\0"):
            if not item:
                continue
            meta, path = item.split(b"\t", 1)
            mode, kind, obj = meta.decode().split()
            entries.setdefault((path.decode("utf-8", "replace"), obj), (mode, kind))
    ordered = sorted(entries.items())
    blobs = sorted({obj for (_, obj), (mode, kind) in ordered if kind == "blob"})
    contents = _read_objects(repo, blobs)
    for index, ((path, obj), (mode, kind)) in enumerate(ordered):
        where = ("entry", index, path)
        raw += [(category, where) for category in name_findings(path, secrets)]
        if kind == "tree":
            continue
        if kind != "blob" or mode in ("120000", "160000"):
            raw.append(("unsupported_entry", where))
            continue
        if admitted(path) is None:
            raw.append(("file_type_not_admitted", where))
        raw += [(category, where) for category in scan_bytes(path, contents[obj], secrets, pins)]
    printed = set()
    for category, where in raw:
        if where is None:
            label = ref if not name_findings(ref, secrets) else "<ref withheld>"
        elif isinstance(where, str):
            label = where
        else:
            label = safe_path(where[2], where[1], secrets)
        printed.add((category, label))
    files = sum(1 for _, (mode, kind) in ordered if kind != "tree")
    return {"commit": commit, "commits": len(history), "files": files, "trees": len(ordered) - files,
            "blobs": len(blobs), "passed": not printed,
            "findings": [{"category": c, "path": p} for c, p in sorted(printed)], "coverage": list(CATEGORY_IDS)}
