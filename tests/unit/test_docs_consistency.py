from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
LOCAL_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ENV_ASSIGNMENT_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]+)=")


def _local_markdown_links(path: Path) -> list[str]:
    links: list[str] = []
    for match in LOCAL_LINK_PATTERN.finditer(path.read_text(encoding="utf-8")):
        link = match.group(1).strip()
        if not link or link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        links.append(link)
    return links


def _resolve_markdown_link(source: Path, link: str) -> Path:
    target = link.split("#", 1)[0]
    return (source.parent / target).resolve()


def test_docs_index_links_point_to_existing_files() -> None:
    checked_indexes = [
        DOCS_ROOT / "README.md",
        DOCS_ROOT / "daily" / "README.md",
    ]

    missing_links: list[str] = []
    for index_path in checked_indexes:
        for link in _local_markdown_links(index_path):
            target = _resolve_markdown_link(index_path, link)
            if not target.exists():
                missing_links.append(f"{index_path.relative_to(REPO_ROOT)} -> {link}")

    assert missing_links == []


def test_env_example_variables_are_documented() -> None:
    env_example = REPO_ROOT / ".env.example"
    configuration = DOCS_ROOT / "configuration.md"

    env_vars = {
        match.group(1)
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if (match := ENV_ASSIGNMENT_PATTERN.match(line.strip()))
    }
    documented = configuration.read_text(encoding="utf-8")

    missing_vars = sorted(env_var for env_var in env_vars if f"`{env_var}`" not in documented)

    assert missing_vars == []
