#!/usr/bin/env python3
"""The product notebooks gate (CAOS_MANAGE ``conventions/product-notebooks.md``, template 0.10.000): the didactic layer is
laid out, mirrored, ordered, covered, annotated, clean and pinned, on committed files, in seconds.

Static, standard library only (CI installs nothing). It never executes a notebook: ``scripts/run_notebooks.py --check`` does,
as a local release gate (ADR-0074). It fails, naming the file and the rule, on

- **layout**: a missing ``notebooks/README.md``, ``notebooks/requirements.txt``, ``notebooks/en/README.md`` or
  ``notebooks/es/README.md``; a stray file in a topic folder (only ``*.ipynb``); a notebook anywhere but
  ``notebooks/<language>/<topic>/<notebook>.ipynb`` (loose at a root or nested deeper: it would be neither checked nor run);
- **mirror**: a path of one language tree absent from the other; counterparts that differ in level, packages, data, beyond
  claims or number of cells;
- **numbering**: topics and notebooks are ``NN-slug``, two digits, contiguous from 01;
- **levels**: a level that decreases inside a topic; a topic without levels 1 and 2; a topic without level 3 whose index row
  (``notebooks/<language>/README.md``) gives no reason (``No level 3: <why>`` / ``Sin nivel 3: <why>``); a notebook the
  index does not list;
- **beyond the state of the art**: a ``BS-`` identifier of the SDD section ``## Beyond the state of the art`` that no level 4
  notebook covers in each language, or a notebook claiming one the SDD does not list;
- **anatomy**: the second-level sections of the tree's language, in order, as the level requires; a first cell that is not
  markdown; a code cell not directly preceded by a markdown cell, or without a comment;
- **metadata**: the ``caos`` block (language, topic, level, title, packages, data, sources, beyond) must agree with the
  tree, the folder, ``notebooks/requirements.txt`` (each package an exact line of it, ``name==version`` or
  ``name @ git+https://github.com/<owner>/<repo>.git@<tag>``, shown in the Setup text as its ``pip install`` line; the second
  form also with the sentence "not yet published on PyPI; installed from its release tag") and the repository (every data
  path exists); notebook metadata beyond kernelspec, language_info and caos, and cell metadata beyond tags;
- **references**: every link of ``caos.sources`` appears in the notebook's References section;
- **sources**: every link of ``caos.sources`` must be a source the SDD lists (its research basis summarises the persisted
  research claim by claim, each with its source; a notebook cites nothing else);
- **no re-implementation**: a code cell that defines a function or a class the pipeline's engine modules
  (``data-pipeline/**/model/*.py``) or oracles (``data-pipeline/**/oracles.py``) already define, or that a method package of
  the product (``product.json`` ``method_packages``, a PyPI distribution) already defines (a notebook imports a method,
  never copies it; a method package not installed here is an info line, ``run_notebooks.py`` checks its names; one with no
  exact ``name==version`` line in ``notebooks/requirements.txt`` is a finding); a code cell that runs ``pip`` or ``conda`` (the Setup text shows the install command, a notebook never
  runs it);
- **clean**: execution counts that are not 1, 2, 3 in order; an error output, a traceback printed to stdout or a stderr
  stream; an absolute or machine path (a drive letter in any literal form, a home folder, the POSIX roots ``/opt/``,
  ``/tmp/``, ``/root/``, ``/var/``, ``/srv/``) or a token pattern in any cell or output; a notebook or an image above the
  limits. A user name is not statically decidable (the template holds no deny-list of names): a product reviews it itself
  (guide 08, section 5);
- **CI**: ``.github/workflows/ci.yml`` runs this check and ``check_readme_areas.py``, and no workflow executes the notebooks.

Usage: ``python scripts/check_notebooks.py [repo_root] [--pypi]``. Exit 0 clean, 1 on any finding. ``--pypi`` is opt-in and never
runs in CI (ADR-0074): it reads ``https://pypi.org/pypi/<name>/<version>/json`` for the pin of each method package and fails on
anything but HTTP 200, so a Setup cell never tells a reader to install a version that is not published.
"""
from __future__ import annotations

import argparse
import ast
import importlib.metadata
import importlib.util
import io
import json
import re
import sys
import tokenize
import urllib.error
import urllib.request
from pathlib import Path

# the size limits of a committed notebook: the whole file (outputs included) and each embedded image, so the set stays
# readable on GitHub and cheap to clone (the convention's section 6; the template's proposal, 2026-10-20)
MAX_NOTEBOOK_BYTES = 3_000_000
MAX_IMAGE_BYTES = 400_000

LANGS = ("en", "es")
# (English heading, Spanish heading, lowest level that requires it): the anatomy of convention section 4, in order
SECTIONS = (
    ("Objectives", "Objetivos", 1),
    ("Setup", "Preparación", 1),
    ("Data", "Datos", 1),
    ("Method", "Método", 1),
    ("State of the art", "Estado del arte", 3),
    ("Beyond the state of the art", "Más allá del estado del arte", 4),
    ("Results", "Resultados", 1),
    ("Summary", "Resumen", 1),
    ("References", "Referencias", 1),
)
NO_LEVEL_3 = {"en": "No level 3:", "es": "Sin nivel 3:"}
MIN_REASON_WORDS = 4
NOTEBOOK_KEYS = {"kernelspec", "language_info", "caos"}
CAOS_KEYS = ("language", "topic", "level", "title", "packages", "data", "sources", "beyond")
BEYOND_SECTION = "Beyond the state of the art"
SLUG = re.compile(r"^(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
NOTEBOOK = re.compile(r"^(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.ipynb$")
BS_ID = re.compile(r"\bBS-\d+\b")
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[A-Za-z0-9._,-]+\])?==(\d[0-9A-Za-z.+!_-]*)$")
# a package installed from its release tag (convention section 5, decided 2026-10-20): name @ git+https://github.com/<owner>/<repo>.git@<tag>
GIT_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*) @ (git\+https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\.git)@(v?\d[0-9A-Za-z.+_-]*)$")
TAG_SENTENCE = {"en": "not yet published on PyPI; installed from its release tag",
                "es": "todavía no publicado en PyPI; instalado desde su etiqueta de versión"}
# a drive letter (one or two backslashes, as a Python literal or a repr, or a slash), a home folder, an absolute POSIX root:
# a machine path never belongs in a committed notebook (convention section 6)
MACHINE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\{1,2}|/(?!/))|/home/|/Users/|\\Users\\|/mnt/[a-z]/|(?<![\w.~-])/(?:opt|tmp|root|var|srv)/")
# a notebook that installs: a pip or conda magic or shell line, `-m pip`, or a `pip install`, outside a comment
RUNS_PIP = re.compile(r"^\s*[%!]\s*(?:pip|conda|mamba)\b|-m['\"]?\s*,?\s*['\"]?pip\b|\bpip\s+install\b", re.M)
TRACEBACK = "Traceback (most recent call last)"
NOTEBOOK_PATH = "notebooks/<language>/<topic>/<notebook>.ipynb"
TOKENS = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"), re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), re.compile(r"\bAKIA[0-9A-Z]{16}\b"), re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
)
HEADING2 = re.compile(r"^##\s+(?!#)(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```+|~~~+)")
CI = ".github/workflows"


def text_of(source) -> str:
    return "".join(source) if isinstance(source, list) else (source if isinstance(source, str) else "")


def has_comment(code: str) -> bool:
    """A comment token (never a ``#`` inside a string); an unparsable cell falls back to a line that starts with ``#``."""
    try:
        return any(t.type == tokenize.COMMENT for t in tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return any(ln.strip().startswith("#") for ln in code.splitlines())


def headings(markdown: str) -> list[str]:
    """The second-level headings of a markdown text, outside code fences."""
    out: list[str] = []
    fenced = False
    for line in markdown.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced and (m := HEADING2.match(line)):
            out.append(m[1].strip())
    return out


def output_texts(cell: dict) -> list[str]:
    """Every text a cell's outputs carry (images are measured, not read)."""
    out: list[str] = []
    for o in cell.get("outputs", []) or []:
        if not isinstance(o, dict):
            continue
        out.append(text_of(o.get("text", "")))
        out.append(str(o.get("ename", "")) + " " + str(o.get("evalue", "")) + " " + text_of(o.get("traceback", "")))
        for mime, value in (o.get("data") or {}).items():
            if not mime.startswith("image/") or mime == "image/svg+xml":
                out.append(text_of(value) if not isinstance(value, (dict, list)) else json.dumps(value))
    return out


def image_sizes(cell: dict) -> list[tuple[str, int]]:
    sizes: list[tuple[str, int]] = []
    for o in cell.get("outputs", []) or []:
        for mime, value in ((o.get("data") or {}).items() if isinstance(o, dict) else []):
            if mime.startswith("image/"):
                raw = text_of(value)
                sizes.append((mime, len(raw) if mime == "image/svg+xml" else len(raw.rstrip("=\n")) * 3 // 4))
    return sizes


def engine_names(root: Path) -> set[str]:
    """The public functions and classes the pipeline's methods define: the engine (``data-pipeline/**/model/*.py``) and the
    oracles (``data-pipeline/**/oracles.py``); a notebook imports them and never defines its own."""
    names: set[str] = set()
    pipeline = root / "data-pipeline"
    for path in sorted([*pipeline.glob("**/model/*.py"), *pipeline.glob("**/oracles.py")]) if pipeline.is_dir() else []:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        names.update(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"))
    return names


def defined_names(code: str) -> set[str]:
    """The functions and classes a code cell defines at its top level (IPython magics and shell lines are dropped)."""
    clean = "\n".join("" if ln.lstrip().startswith(("%", "!")) else ln for ln in code.splitlines())
    try:
        return {n.name for n in ast.parse(clean).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    except SyntaxError:
        return set()


PYPI_TIMEOUT_SECONDS = 20
PYPI_URL = "https://pypi.org/pypi/{name}/{version}/json"


def normalized(name: str) -> str:
    """A distribution name as PEP 503 compares it."""
    return re.sub(r"[-_.]+", "-", name).lower()


def method_packages(root: Path, findings: list[str] | None = None) -> list[str]:
    """The distributions ``product.json`` declares as the product's method packages (optional key ``method_packages``, a list of
    names; absent or empty: none). A key of another shape is a finding; a missing or unreadable file declares none."""
    try:
        doc = json.loads((root / "product.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    value = doc.get("method_packages") if isinstance(doc, dict) else None
    if value is None:
        return []
    if not (isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)):
        if findings is not None:
            findings.append("product.json: method_packages: must be a list of strings (PyPI distribution names)")
        return []
    return list(dict.fromkeys(x.strip() for x in value))


def import_name(dist: str) -> str:
    """The top-level module of a distribution: its ``top_level.txt``, else the first folder or module of its files, else the
    distribution name with ``-`` read as ``_``."""
    try:
        d = importlib.metadata.distribution(dist)
    except importlib.metadata.PackageNotFoundError:
        return dist.replace("-", "_")
    top = (d.read_text("top_level.txt") or "").split()
    if top:
        return top[0]
    for f in d.files or []:
        first = f.parts[0] if f.parts else ""
        if first and first != ".." and not first.endswith((".dist-info", ".egg-info", ".data")) and first != "__pycache__":
            return first[:-3] if first.endswith(".py") else first
    return dist.replace("-", "_")


def package_public_names(module: str) -> set[str] | None:
    """The top-level ``def``, ``async def`` and ``class`` names, not starting with ``_``, of every ``.py`` file under the
    installed folder of ``module``; None when it is not installed. Files under a ``tests`` folder and modules whose name starts
    with ``_`` are left out (``__init__.py`` stays). The folder is found without importing the package and its source is read
    with ``ast``, never executed."""
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        return None
    if spec.submodule_search_locations:
        bases = [Path(loc) for loc in spec.submodule_search_locations]
        files = [p for b in bases for p in sorted(b.rglob("*.py"))]
    elif spec.origin and spec.origin.endswith(".py"):
        bases, files = [Path(spec.origin).parent], [Path(spec.origin)]
    else:
        return None
    names: set[str] = set()
    for path in files:
        rel = next((path.relative_to(b) for b in bases if b in path.parents), Path(path.name))
        if "tests" in rel.parts[:-1] or (path.stem.startswith("_") and path.name != "__init__.py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        names.update(n.name for n in tree.body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_"))
    return names


def method_pin(root: Path, dist: str) -> str | None:
    """The version of the exact ``name==version`` line (extras allowed) that pins ``dist`` in ``notebooks/requirements.txt``."""
    for line in requirement_lines(root):
        m = PIN.match(line)
        if m and normalized(m[1]) == normalized(dist):
            return m[2]
    return None


def method_state(root: Path, infos: list[str] | None = None, strict: bool = False) -> tuple[dict[str, str], list[str]]:
    """The names the method packages define (name to distribution) and the findings about the packages themselves: a package
    with no exact pin and, when ``strict`` (the runner), a package not installed. The static check reports the latter as an
    info line and leaves its names to ``run_notebooks.py``."""
    findings: list[str] = []
    names: dict[str, str] = {}
    for dist in method_packages(root, findings):
        if method_pin(root, dist) is None:
            findings.append(f"notebooks/requirements.txt: pins: method package {dist!r} (product.json method_packages) has no exact pin "
                            f"({dist}==version)")
        public = package_public_names(import_name(dist))
        if public is None:
            if strict:
                findings.append(f"product.json: method_packages: {dist!r} is not installed in this environment; build it from "
                                "notebooks/requirements.txt (scripts/setup.sh --notebooks)")
            elif infos is not None:
                infos.append(f"check_notebooks: {dist} not installed here; its names are checked by run_notebooks.py")
            continue
        for name in public:
            names.setdefault(name, dist)
    return names, findings


def http_status(url: str) -> int:
    """The HTTP status of a GET of ``url``; the one network call of this script, made only under ``--pypi``."""
    req = urllib.request.Request(url, headers={"User-Agent": "caos-check-notebooks"})
    try:
        with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT_SECONDS) as response:
            return int(response.status)
    except urllib.error.HTTPError as e:
        return int(e.code)


def pypi_findings(root: Path) -> list[str]:
    """The pin of each method package must exist on PyPI: anything but HTTP 200 is a finding naming the URL and the status."""
    out: list[str] = []
    for dist in method_packages(root):
        version = method_pin(root, dist)
        if version is None:
            continue  # the missing pin is already a finding of the static check
        url = PYPI_URL.format(name=dist, version=version)
        try:
            status: object = http_status(url)
        except OSError as e:
            status = f"unreachable ({e})"
        if status != 200:
            out.append(f"{url}: pypi: the pin {dist}=={version} of notebooks/requirements.txt is not published (answer: {status}); "
                       "a Setup cell would tell a reader to install a version that does not exist")
    return out


def method_copy_findings(rel: str, cells: list, methods: dict[str, str]) -> list[str]:
    """A code cell that defines a name a method package defines: the notebook imports it and never copies it."""
    out: list[str] = []
    for i, c in enumerate(cells, 1):
        if isinstance(c, dict) and c.get("cell_type") == "code":
            for copied in sorted(defined_names(text_of(c.get("source", ""))) & set(methods)):
                out.append(f"{rel}: engine: code cell {i} defines {copied!r}, which the method package {methods[copied]!r} already defines; "
                           "import it instead of re-implementing it")
    return out


DOI = re.compile(r"10\.\d{4,9}/[^\s)>\]|`]+")
LINK = re.compile(r"https?://[^\s)>\]|`]+")


def canonical(source: str) -> str:
    """A source as the SDD can hold it: its DOI when it names one (lower case), else the link without a closing slash or dot."""
    m = DOI.search(source)
    return ("doi:" + m[0].rstrip(".,;/").lower()) if m else source.strip().rstrip("/.,;").lower()


def sdd_sources(root: Path) -> set[str]:
    sdd = root / "docs" / "design" / "SDD.md"
    text = sdd.read_text(encoding="utf-8") if sdd.is_file() else ""
    return {canonical(m[0]) for m in DOI.finditer(text)} | {canonical(m[0]) for m in LINK.finditer(text)}


def requirement_lines(root: Path) -> list[str]:
    """The requirement lines of ``notebooks/requirements.txt``, without comments and blank lines."""
    path = root / "notebooks" / "requirements.txt"
    lines: list[str] = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split(" #")[0].strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def is_exact(line: str) -> bool:
    """An exact requirement line: ``name==version`` (PyPI) or ``name @ git+https://github.com/<owner>/<repo>.git@<tag>``."""
    return bool(PIN.match(line) or GIT_PIN.match(line))


def read_pins(root: Path) -> set[str]:
    """The exact requirement lines of ``notebooks/requirements.txt``: what a notebook's ``caos.packages`` may hold."""
    return {line for line in requirement_lines(root) if is_exact(line)}


def unpinned_lines(root: Path) -> list[str]:
    return [line for line in requirement_lines(root) if not is_exact(line)]


def install_spec(package: str) -> str:
    """What the Setup install line shows for a package: ``name==version``, or the ``git+https://...@<tag>`` part."""
    m = GIT_PIN.match(package)
    return f"{m[2]}@{m[3]}" if m else package


def sections_of(cells: list[dict]) -> dict[str, str]:
    """The markdown text of each second-level section (keyed by its heading), code fences respected."""
    out: dict[str, list[str]] = {}
    current: str | None = None
    fenced = False
    for c in cells:
        if c["cell_type"] != "markdown":
            continue
        for line in text_of(c["source"]).splitlines():
            if FENCE.match(line):
                fenced = not fenced
            elif not fenced and (m := HEADING2.match(line)):
                current = m[1].strip()
                out.setdefault(current, [])
                continue
            if current is not None:
                out[current].append(line)
        fenced = False
    return {k: "\n".join(v) for k, v in out.items()}


def install_lines(text: str) -> list[str]:
    """The ``pip install`` commands of a text, a trailing backslash joining the next line to its command."""
    lines = text.splitlines()
    out: list[str] = []
    n = 0
    while n < len(lines):
        command = lines[n]
        while command.rstrip().endswith("\\") and n + 1 < len(lines):
            n += 1
            command = command.rstrip()[:-1] + " " + lines[n].strip()
        if re.search(r"\bpip\s+install\b", command):
            out.append(command)
        n += 1
    return out


def without_comments(code: str) -> str:
    """A code cell without its comment tokens (a ``#`` inside a string stays); an unparsable cell loses its ``#`` lines."""
    try:
        keep = [t for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type != tokenize.COMMENT]
        return tokenize.untokenize(keep)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return "\n".join(ln for ln in code.splitlines() if not ln.strip().startswith("#"))


def sdd_claims(root: Path) -> tuple[set[str] | None, str | None]:
    """The ``BS-`` identifiers of the SDD section, ``set()`` for 'None claimed.', and the problem reading it, if any."""
    sdd = root / "docs" / "design" / "SDD.md"
    if not sdd.is_file():
        return None, "docs/design/SDD.md is missing"
    lines = sdd.read_text(encoding="utf-8").splitlines()
    body: list[str] | None = None
    fenced = False
    for line in lines:
        if FENCE.match(line):
            fenced = not fenced
        if not fenced and (m := re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)) and not line.startswith("###"):
            if body is not None:
                break
            if m[1].strip().lower() == BEYOND_SECTION.lower():
                body = []
            continue
        if body is not None:
            body.append(line)
    if body is None:
        return None, f"the SDD has no section '## {BEYOND_SECTION}' (list the BS- claims, or say 'None claimed.')"
    text = "\n".join(body)
    ids = set(BS_ID.findall(text))
    none = "None claimed." in text
    if ids and none:
        return None, "the section says 'None claimed.' and lists BS- claims"
    if not ids and not none:
        return None, "the section lists no BS- claim and does not say 'None claimed.'"
    return ids, None


class Tree:
    """One language tree: its topics, notebooks and the parsed documents."""

    def __init__(self, root: Path, lang: str) -> None:
        self.lang = lang
        self.base = root / "notebooks" / lang
        self.topics = sorted(p.name for p in self.base.iterdir() if p.is_dir()) if self.base.is_dir() else []

    def files(self) -> set[str]:
        if not self.base.is_dir():
            return set()
        return {p.relative_to(self.base).as_posix() for p in self.base.rglob("*")}


def load(path: Path, rel: str, findings: list[str]) -> dict | None:
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        findings.append(f"{rel}: layout: not readable as JSON ({e})")
        return None
    if not isinstance(nb, dict) or nb.get("nbformat") != 4 or not isinstance(nb.get("cells"), list) \
            or not isinstance(nb.get("metadata"), dict):
        findings.append(f"{rel}: layout: not a notebook of format 4 (needs nbformat 4, cells and metadata)")
        return None
    for i, c in enumerate(nb["cells"], 1):
        if not isinstance(c, dict) or c.get("cell_type") not in {"markdown", "code"} or "source" not in c:
            findings.append(f"{rel}: layout: cell {i} is not a markdown or code cell with a source")
            return None
    return nb


def check_numbering(names: list[str], pattern: re.Pattern[str], rel: str, kind: str, findings: list[str]) -> None:
    nums: list[int] = []
    for n in names:
        m = pattern.match(n)
        if not m:
            findings.append(f"{rel}: numbering: {kind} {n!r} is not NN-slug (two digits, lower case English slug)")
        else:
            nums.append(int(m[1]))
    if nums and nums != list(range(1, len(nums) + 1)):
        findings.append(f"{rel}: numbering: the {kind}s are numbered {nums}, not 01 up to {len(nums):02d} with no gap or repeat")


def check_notebook(root: Path, lang: str, topic: str, name: str, nb: dict, pins: set[str], claims: set[str],
                   engine: set[str], listed: set[str], findings: list[str]) -> None:
    rel = f"notebooks/{lang}/{topic}/{name}"
    path = root / rel
    size = path.stat().st_size
    if size > MAX_NOTEBOOK_BYTES:
        findings.append(f"{rel}: size: {size} bytes is above the {MAX_NOTEBOOK_BYTES} byte limit of a notebook")
    meta = nb["metadata"]
    cells = nb["cells"]
    # ---- metadata
    extra = sorted(set(meta) - NOTEBOOK_KEYS)
    if extra:
        findings.append(f"{rel}: metadata: notebook metadata beyond kernelspec, language_info and caos: {extra}")
    for key in ("kernelspec", "language_info"):
        if not isinstance(meta.get(key), dict):
            findings.append(f"{rel}: metadata: {key} is missing")
    caos = meta.get("caos")
    level = 0
    if not isinstance(caos, dict):
        findings.append(f"{rel}: metadata: the caos block is missing")
    else:
        level = caos.get("level") if isinstance(caos.get("level"), int) and not isinstance(caos.get("level"), bool) else 0
        for key in CAOS_KEYS:
            if key not in caos:
                findings.append(f"{rel}: metadata: caos.{key} is missing")
        for key in sorted(set(caos) - set(CAOS_KEYS)):
            findings.append(f"{rel}: metadata: caos.{key} is not a field of the block")
        if caos.get("language") != lang:
            findings.append(f"{rel}: metadata: caos.language is {caos.get('language')!r}, the tree is {lang!r}")
        if caos.get("topic") != topic:
            findings.append(f"{rel}: metadata: caos.topic is {caos.get('topic')!r}, the folder is {topic!r}")
        if "level" in caos and level not in {1, 2, 3, 4}:
            findings.append(f"{rel}: metadata: caos.level is {caos.get('level')!r}, not 1, 2, 3 or 4")
        if "title" in caos and not (isinstance(caos["title"], str) and caos["title"].strip()):
            findings.append(f"{rel}: metadata: caos.title is empty")
        markdown_all = "\n".join(text_of(c["source"]) for c in cells if c["cell_type"] == "markdown")
        packages = caos.get("packages")
        if "packages" in caos and not (isinstance(packages, list) and all(isinstance(p, str) for p in packages)):
            findings.append(f"{rel}: metadata: caos.packages is not a list of exact requirement lines of notebooks/requirements.txt")
        else:
            sections = sections_of(cells)
            if packages and not any(c["cell_type"] == "code" and "importlib.metadata" in text_of(c["source"]) for c in cells):
                findings.append(f"{rel}: anatomy: no code cell prints the versions of the packages (importlib.metadata.version), "
                                "as the Setup section's last step")
            setup = sections.get("Setup" if lang == "en" else "Preparación", "")
            commands = install_lines(setup)
            for p in packages or []:
                if not is_exact(p):
                    findings.append(f"{rel}: metadata: package {p!r} is not an exact requirement line "
                                    "(name==version, or name @ git+https://github.com/<owner>/<repo>.git@<tag>)")
                elif p not in pins:
                    findings.append(f"{rel}: metadata: package {p!r} is not a pin of notebooks/requirements.txt (an exact line of it)")
                else:
                    spec = install_spec(p)
                    if spec not in markdown_all:
                        findings.append(f"{rel}: metadata: package {p!r} is not written in the notebook's text (the Setup `pip install` line)")
                    elif not any(spec in c for c in commands):
                        findings.append(f"{rel}: anatomy: the Setup section shows no `pip install` line with {spec!r} "
                                        "(the familiar install command, in a markdown code block)")
                    if GIT_PIN.match(p) and TAG_SENTENCE[lang] not in setup:
                        findings.append(f"{rel}: anatomy: {p!r} is installed from its release tag, so the Setup section says "
                                        f"\"{TAG_SENTENCE[lang]}\"")
        data = caos.get("data")
        if "data" in caos and not (isinstance(data, list) and all(isinstance(d, str) for d in data)):
            findings.append(f"{rel}: metadata: caos.data is not a list of repository paths")
        else:
            for d in data or []:
                if d.startswith("/") or MACHINE_PATH.search(d) or ".." in Path(d).parts or not (root / d).is_file():
                    findings.append(f"{rel}: metadata: data path {d!r} is not a file of the repository (a path from the repository root)")
        sources = caos.get("sources")
        if "sources" in caos and not (isinstance(sources, list) and sources and all(isinstance(s, str) and s.startswith("http") for s in sources)):
            findings.append(f"{rel}: metadata: caos.sources is not a non-empty list of https links")
        else:
            references = sections_of(cells).get("References" if lang == "en" else "Referencias", "").lower()
            for src in sources or []:
                if canonical(src) not in listed:
                    findings.append(f"{rel}: sources: {src!r} is not a source the SDD lists (add it to the SDD's research basis, or cite another)")
                key = canonical(src)
                if (key[4:] if key.startswith("doi:") else key) not in references:
                    findings.append(f"{rel}: sources: the References section does not list {src!r} (it lists every source cited)")
        beyond = caos.get("beyond")
        if "beyond" in caos and not (isinstance(beyond, list) and all(isinstance(b, str) for b in beyond)):
            findings.append(f"{rel}: metadata: caos.beyond is not a list of BS- identifiers")
        elif isinstance(beyond, list):
            if beyond and level != 4:
                findings.append(f"{rel}: metadata: caos.beyond lists claims but the level is {level}, not 4")
            if level == 4 and not beyond:
                findings.append(f"{rel}: metadata: a level 4 notebook lists the BS- claims it demonstrates in caos.beyond")
            for b in beyond:
                if b not in claims:
                    findings.append(f"{rel}: metadata: {b!r} is not a claim of the SDD's '## {BEYOND_SECTION}' section")
    # ---- anatomy
    if not cells or cells[0]["cell_type"] != "markdown":
        findings.append(f"{rel}: anatomy: the first cell is not a markdown cell (title, level, prerequisites, reading time)")
    seen: list[str] = []
    for c in cells:
        if c["cell_type"] == "markdown":
            seen.extend(headings(text_of(c["source"])))
    want = [(en if lang == "en" else es) for en, es, low in SECTIONS if level >= low and level in {1, 2, 3, 4}]
    if level in {1, 2, 3, 4}:
        every = {en if lang == "en" else es for en, es, _ in SECTIONS}
        for w in want:
            if w not in seen:
                findings.append(f"{rel}: anatomy: the section '## {w}' is missing (level {level}, language {lang})")
        for s in seen:
            if s not in want:
                why = "a section of a higher level" if s in every else "not a section of the anatomy"
                findings.append(f"{rel}: anatomy: the section '## {s}' is {why} for level {level}")
        got = [s for s in seen if s in want]
        if len(got) != len(set(got)):
            findings.append(f"{rel}: anatomy: a section appears twice")
        elif got != [w for w in want if w in got]:
            findings.append(f"{rel}: anatomy: sections out of order: {got}, expected {[w for w in want if w in got]}")
    previous = None
    for i, c in enumerate(cells, 1):
        if c["cell_type"] == "code":
            code = text_of(c["source"])
            if previous != "markdown":
                findings.append(f"{rel}: anatomy: code cell {i} is not preceded by a markdown cell that says what it does and why")
            if not has_comment(code):
                findings.append(f"{rel}: anatomy: code cell {i} carries no comment line")
            if RUNS_PIP.search(without_comments(code)):
                findings.append(f"{rel}: anatomy: code cell {i} runs pip or conda: a notebook never runs pip itself (convention section 4); "
                                "the Setup text shows the install command")
            for copied in sorted(defined_names(code) & engine):
                findings.append(f"{rel}: engine: code cell {i} defines {copied!r}, which the pipeline's engine or oracle modules already define; "
                                "import it instead of re-implementing it")
        previous = c["cell_type"]
    # ---- cell metadata and clean
    expected = 1
    for i, c in enumerate(cells, 1):
        cm = c.get("metadata", {})
        if not isinstance(cm, dict) or set(cm) - {"tags"}:
            findings.append(f"{rel}: metadata: cell {i} metadata beyond tags: {sorted(set(cm) - {'tags'}) if isinstance(cm, dict) else cm!r}")
        texts = [text_of(c["source"])]
        if c["cell_type"] == "code":
            count = c.get("execution_count")
            if count != expected:
                findings.append(f"{rel}: execution: code cell {i} has execution_count {count!r}, expected {expected} "
                                "(run scripts/run_notebooks.py: only the runner writes outputs)")
            expected += 1
            for o in c.get("outputs", []) or []:
                if o.get("output_type") == "error":
                    findings.append(f"{rel}: output: code cell {i} holds an error output ({o.get('ename')})")
                if o.get("output_type") == "stream" and o.get("name") == "stderr":
                    findings.append(f"{rel}: output: code cell {i} holds a stderr stream")
                if o.get("output_type") != "error" and TRACEBACK in text_of(o.get("text", "")):
                    findings.append(f"{rel}: output: code cell {i} prints a traceback ({TRACEBACK!r}) to its output")
            texts += output_texts(c)
            for mime, n in image_sizes(c):
                if n > MAX_IMAGE_BYTES:
                    findings.append(f"{rel}: size: an image ({mime}) of code cell {i} is {n} bytes, above the {MAX_IMAGE_BYTES} byte limit")
        for t in texts:
            if m := MACHINE_PATH.search(t):
                findings.append(f"{rel}: path: cell {i} holds a machine path ({m[0]!r}): use a path relative to the repository root")
            for pat in TOKENS:
                if pat.search(t):
                    findings.append(f"{rel}: secret: cell {i} holds a token pattern")
                    break


def counterpart_findings(root: Path, en_docs: dict[str, dict], es_docs: dict[str, dict], findings: list[str]) -> None:
    for key in sorted(set(en_docs) & set(es_docs)):
        a, b = en_docs[key], es_docs[key]
        ca, cb = a["metadata"].get("caos"), b["metadata"].get("caos")
        rel = f"notebooks/es/{key}"
        if isinstance(ca, dict) and isinstance(cb, dict):
            for field in ("level", "packages", "data", "beyond"):
                if ca.get(field) != cb.get(field):
                    findings.append(f"{rel}: mirror: caos.{field} differs from its English counterpart")
        kinds_a = [c["cell_type"] for c in a["cells"]]
        kinds_b = [c["cell_type"] for c in b["cells"]]
        if kinds_a != kinds_b:
            findings.append(f"{rel}: mirror: {len(kinds_b)} cells in a different order of kinds than the English counterpart's "
                            f"{len(kinds_a)}: it is not a full counterpart")


def index_findings(root: Path, lang: str, tree: Tree, levels: dict[str, dict[str, int]], findings: list[str]) -> None:
    path = root / "notebooks" / lang / "README.md"
    if not path.is_file():
        return
    rel = f"notebooks/{lang}/README.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for topic in tree.topics:
        row = [ln for ln in lines if topic in ln]
        if not row:
            findings.append(f"{rel}: index: the topic {topic} has no row")
            continue
        have = set(levels.get(topic, {}).values())
        if have and 3 not in have:
            line = next((ln for ln in row if NO_LEVEL_3[lang] in ln), None)
            reason = line.split(NO_LEVEL_3[lang], 1)[1].strip(" |*_") if line else ""
            if len(reason.split()) < MIN_REASON_WORDS:
                findings.append(f"{rel}: levels: the topic {topic} has no level 3 notebook and its row gives no reason "
                                f"('{NO_LEVEL_3[lang]} <why, {MIN_REASON_WORDS} words or more>')")
        for name in levels.get(topic, {}):
            if name not in text:
                findings.append(f"{rel}: index: the notebook {topic}/{name} is not listed")


def ci_findings(root: Path, findings: list[str]) -> None:
    ci = root / CI / "ci.yml"
    if not ci.is_file():
        findings.append(f"{CI}/ci.yml: ci: the workflow is missing")
    else:
        text = ci.read_text(encoding="utf-8")
        for script in ("check_notebooks.py", "check_readme_areas.py"):
            if f"python scripts/{script}" not in text:
                findings.append(f"{CI}/ci.yml: ci: no step runs `python scripts/{script}` (a static check, in CI and locally)")
    for wf in sorted((root / CI).glob("*.y*ml")) if (root / CI).is_dir() else []:
        if "run_notebooks" in wf.read_text(encoding="utf-8"):
            findings.append(f"{CI}/{wf.name}: ci: runs the notebooks; the execution is a local release gate, never CI (ADR-0074)")


def findings_of(root: Path, infos: list[str] | None = None) -> list[str]:
    findings: list[str] = []
    nb = root / "notebooks"
    for rel in ("README.md", "requirements.txt", "en/README.md", "es/README.md"):
        if not (nb / rel).is_file() or not (nb / rel).read_text(encoding="utf-8").strip():
            findings.append(f"notebooks/{rel}: layout: missing or empty")
    for line in unpinned_lines(root):
        findings.append(f"notebooks/requirements.txt: pins: {line!r} is not an exact pin "
                        "(name==version, or name @ git+https://github.com/<owner>/<repo>.git@<tag>)")
    for found_at in sorted(nb.rglob("*.ipynb")) if nb.is_dir() else []:
        rel = found_at.relative_to(nb).parts
        if not (len(rel) == 3 and rel[0] in LANGS):
            findings.append(f"notebooks/{'/'.join(rel)}: layout: a notebook lives at {NOTEBOOK_PATH} "
                            "(a notebook elsewhere is neither checked nor run)")
    claims, problem = sdd_claims(root)
    if problem:
        findings.append(f"docs/design/SDD.md: beyond: {problem}")
    pins = read_pins(root)
    engine = engine_names(root)
    methods, method_findings = method_state(root, infos)
    findings.extend(method_findings)
    listed = sdd_sources(root)
    trees = {lang: Tree(root, lang) for lang in LANGS}
    for lang in LANGS:
        if not trees[lang].base.is_dir():
            findings.append(f"notebooks/{lang}: layout: the {lang} tree is missing")
    a, b = trees["en"].files(), trees["es"].files()
    for lang, mine, other in (("es", b, a), ("en", a, b)):
        for rel in sorted(other - mine):
            findings.append(f"notebooks/{lang}/{rel}: mirror: absent from the {lang} tree (present in {'en' if lang == 'es' else 'es'})")
    docs: dict[str, dict[str, dict]] = {lang: {} for lang in LANGS}
    levels: dict[str, dict[str, dict[str, int]]] = {lang: {} for lang in LANGS}
    covered: dict[str, set[str]] = {lang: set() for lang in LANGS}
    for lang, tree in trees.items():
        check_numbering(tree.topics, SLUG, f"notebooks/{lang}", "topic", findings)
        for topic in tree.topics:
            folder = tree.base / topic
            for stray in sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix != ".ipynb"):
                findings.append(f"notebooks/{lang}/{topic}/{stray.name}: layout: only notebooks live in a topic folder")
            names = sorted(p.name for p in folder.iterdir() if p.suffix == ".ipynb")
            check_numbering(names, NOTEBOOK, f"notebooks/{lang}/{topic}", "notebook", findings)
            order: list[int] = []
            for name in names:
                doc = load(folder / name, f"notebooks/{lang}/{topic}/{name}", findings)
                if doc is None:
                    continue
                docs[lang][f"{topic}/{name}"] = doc
                check_notebook(root, lang, topic, name, doc, pins, claims or set(), engine, listed, findings)
                findings.extend(method_copy_findings(f"notebooks/{lang}/{topic}/{name}", doc["cells"], methods))
                caos = doc["metadata"].get("caos")
                lv = caos.get("level") if isinstance(caos, dict) else None
                if isinstance(lv, int) and not isinstance(lv, bool):
                    levels[lang].setdefault(topic, {})[name] = lv
                    order.append(lv)
                    if lv == 4 and isinstance(caos.get("beyond"), list):
                        covered[lang].update(x for x in caos["beyond"] if isinstance(x, str))
            if order != sorted(order):
                findings.append(f"notebooks/{lang}/{topic}: levels: the level decreases inside the topic ({order}); the reading order never goes down")
            have = set(order)
            for need in (1, 2):
                if names and need not in have:
                    findings.append(f"notebooks/{lang}/{topic}: levels: the topic has no level {need} notebook")
        index_findings(root, lang, tree, levels[lang], findings)
    for lang in LANGS:
        for claim in sorted((claims or set()) - covered[lang]):
            findings.append(f"notebooks/{lang}: beyond: the SDD claim {claim} is covered by no level 4 notebook (caos.beyond)")
    counterpart_findings(root, docs["en"], docs["es"], findings)
    ci_findings(root, findings)
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(prog="check_notebooks", description=__doc__.split(chr(10))[0])
    ap.add_argument("root", nargs="?", help="the repository root (default: this script's repository)")
    ap.add_argument("--pypi", action="store_true",
                    help="also read PyPI for the pin of each method package (opt-in, needs the network, never CI)")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parents[1]
    infos: list[str] = []
    findings = findings_of(root, infos)
    if a.pypi:
        findings.extend(pypi_findings(root))
    for line in infos:
        print(line)
    if findings:
        print("NOTEBOOKS CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    count = sum(1 for _ in (root / "notebooks").rglob("*.ipynb"))
    print(f"check_notebooks: OK, {count} notebooks in two trees, mirrored, ordered, annotated and clean"
          + (", method-package pins published on PyPI" if a.pypi and method_packages(root) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
