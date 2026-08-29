"""
Garde-fou de l'architecture.

La règle de dépendance ne vaut que si quelque chose la vérifie. Un `grep` ne
suffit pas : il remonte le mot « infrastructure » écrit dans un commentaire.
Ces tests lisent l'arbre syntaxique et ne regardent que les vrais imports.

Si l'un d'eux casse, ce n'est pas le test qu'il faut corriger — c'est que le
fichier est au mauvais endroit.
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


def _imported_modules(path: Path) -> set[str]:
    """Les modules réellement importés par un fichier, docstrings exclues."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _python_files(package: str) -> list[Path]:
    return [p for p in (SRC / package).rglob("*.py") if p.stat().st_size > 0]


def test_domain_imports_nothing_from_the_outer_layers():
    """
    Le domaine est le centre : tout pointe vers lui, il ne pointe vers rien.

    C'est ce qui permet de tester les règles métier sans réseau ni base, et de
    changer de source de données sans toucher aux entités.
    """
    forbidden = ("src.infrastructure", "src.interfaces", "src.application")

    offenders = {
        path.relative_to(SRC).as_posix(): sorted(
            m for m in _imported_modules(path) if m.startswith(forbidden)
        )
        for path in _python_files("domain")
    }
    offenders = {path: mods for path, mods in offenders.items() if mods}

    assert offenders == {}, f"le domaine importe des couches externes : {offenders}"


def test_domain_depends_on_no_technical_library():
    """
    Pydantic est la seule dépendance externe tolérée dans le domaine : les
    entités décrivent des données venues de l'extérieur, il faut bien les
    valider. httpx, boto3, sqlalchemy et lxml, eux, décrivent des mécanismes —
    leur place est dans `infrastructure/`.
    """
    forbidden = ("httpx", "boto3", "sqlalchemy", "lxml", "asyncpg", "fastapi", "loguru")

    offenders = {
        path.relative_to(SRC).as_posix(): sorted(
            m for m in _imported_modules(path) if m.split(".")[0] in forbidden
        )
        for path in _python_files("domain")
    }
    offenders = {path: mods for path, mods in offenders.items() if mods}

    assert offenders == {}, f"le domaine importe une brique technique : {offenders}"


def test_application_never_touches_infrastructure():
    """
    Un cas d'usage orchestre des ports, jamais des adaptateurs. C'est
    `composition.py` — et lui seul — qui choisit les implémentations concrètes.
    """
    offenders = {
        path.relative_to(SRC).as_posix(): sorted(
            m for m in _imported_modules(path) if m.startswith("src.infrastructure")
        )
        for path in _python_files("application")
    }
    offenders = {path: mods for path, mods in offenders.items() if mods}

    assert offenders == {}, f"un cas d'usage importe l'infrastructure : {offenders}"
