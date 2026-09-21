"""Dependency rule, enforced on real imports (AST), not on grep."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


def _imported_modules(path: Path) -> set[str]:
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
    """Everything points at the domain; the domain points at nothing."""
    forbidden = ("src.infrastructure", "src.interfaces", "src.application")

    offenders = {
        path.relative_to(SRC).as_posix(): sorted(
            m for m in _imported_modules(path) if m.startswith(forbidden)
        )
        for path in _python_files("domain")
    }
    offenders = {path: mods for path, mods in offenders.items() if mods}

    assert offenders == {}, f"domain imports outer layers: {offenders}"


def test_domain_depends_on_no_technical_library():
    """Pydantic is the only external dependency allowed in the domain."""
    forbidden = ("httpx", "boto3", "sqlalchemy", "lxml", "asyncpg", "fastapi", "loguru")

    offenders = {
        path.relative_to(SRC).as_posix(): sorted(
            m for m in _imported_modules(path) if m.split(".")[0] in forbidden
        )
        for path in _python_files("domain")
    }
    offenders = {path: mods for path, mods in offenders.items() if mods}

    assert offenders == {}, f"domain imports a technical library: {offenders}"


def test_application_never_touches_infrastructure():
    """Use cases orchestrate ports; only composition.py picks adapters."""
    offenders = {
        path.relative_to(SRC).as_posix(): sorted(
            m for m in _imported_modules(path) if m.startswith("src.infrastructure")
        )
        for path in _python_files("application")
    }
    offenders = {path: mods for path, mods in offenders.items() if mods}

    assert offenders == {}, f"use case imports infrastructure: {offenders}"
