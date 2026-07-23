from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "node_modules", ".next", ".pytest_cache", "tmp", "session_storage", "__pycache__"}
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
REFERENCE_LINK = re.compile(r"(?m)^\s*\[[^\]]+\]:\s*(?P<target><[^>]+>|\S+)")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
    )


def local_target(document: Path, value: str) -> Path | None:
    target = value[1:-1] if value.startswith("<") and value.endswith(">") else value
    if not target or target.startswith(("#", "/", "http://", "https://", "mailto:", "tel:", "data:")):
        return None
    path_part = unquote(target.partition("#")[0])
    if not path_part:
        return None
    return (document.parent / path_part).resolve()


def main() -> None:
    failures: list[tuple[str, str, str]] = []
    checked = 0
    files = markdown_files()
    for document in files:
        text = document.read_text(encoding="utf-8", errors="replace")
        targets = [match.group("target") for match in INLINE_LINK.finditer(text)]
        targets.extend(match.group("target") for match in REFERENCE_LINK.finditer(text))
        for value in targets:
            target = local_target(document, value)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                failures.append((document.relative_to(ROOT).as_posix(), value, str(target)))

    print(f"markdown_files={len(files)}")
    print(f"local_links_checked={checked}")
    print(f"broken_links={len(failures)}")
    for document, value, target in failures:
        print(f"BROKEN {document}: {value} -> {target}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
