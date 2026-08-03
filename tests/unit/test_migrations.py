from __future__ import annotations

import ast
from pathlib import Path


def test_migration_revision_ids_fit_alembic_version_column() -> None:
    migration_dir = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "kernel-storage"
        / "src"
        / "kernel_storage"
        / "migrations"
        / "versions"
    )

    for migration_file in migration_dir.glob("*.py"):
        tree = ast.parse(migration_file.read_text())
        revision = _find_string_assignment(tree, "revision")

        assert revision is not None, f"{migration_file.name} is missing revision"
        assert len(revision) <= 32, (
            f"{migration_file.name} revision id {revision!r} exceeds Alembic's "
            "default version_num VARCHAR(32) column"
        )


def _find_string_assignment(tree: ast.Module, name: str) -> str | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None
