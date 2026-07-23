from __future__ import annotations

import csv
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


EXCLUDED_DIRECTORY_REASONS = {
    ".git": "Git object database and repository internals; represented by source-control status instead of file contents.",
    ".venv": "Installed Python runtime and third-party packages; represented by requirement manifests and audited installed versions.",
    "node_modules": "Installed JavaScript third-party packages; represented by package manifests and lockfiles.",
    ".next": "Generated Next.js build cache and compiled output; represented by the production-build result.",
    "__pycache__": "Generated Python bytecode cache; not project source.",
    ".pytest_cache": "Generated pytest cache; not project source.",
    ".playwright-cli": "Volatile browser-automation traces; summarized as QA evidence.",
    ".playwright-mcp": "Volatile browser-automation state; summarized as QA evidence.",
    ".vercel": "Local deployment-tool metadata; deployment configuration is documented from source files.",
    "session_storage": "Runtime user/session data; excluded to protect private uploaded data and avoid treating mutable state as source.",
    "tmp": "Temporary render, conversion, and verification files; not deliverable project source.",
    "certificates": "Local HTTPS certificate/key material; presence is documented but file details and contents are withheld.",
}

SENSITIVE_NAMES = {".env", ".env.local", ".env.production", ".env.development"}
TEXT_SUFFIXES = {
    ".css",
    ".csv",
    ".example",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sql",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

CATEGORY_ORDER = {
    "Project governance and root configuration": 1,
    "Frontend application": 2,
    "Backend API and application": 3,
    "Backend automated tests": 4,
    "Data, trained models, and ML evidence": 5,
    "Supabase database and storage": 6,
    "Development, QA, and document automation": 7,
    "Project documentation and academic material": 8,
    "Generated reports, figures, logs, and screenshots": 9,
    "Repository automation metadata": 10,
    "Other project file": 11,
}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _tracked_files(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def _measure_tree(path: Path) -> tuple[int, int]:
    count = 0
    size = 0
    for base, _, files in os.walk(path):
        for name in files:
            candidate = Path(base) / name
            count += 1
            try:
                size += candidate.stat().st_size
            except OSError:
                pass
    return count, size


def _line_count(path: Path) -> int | str:
    if path.name in SENSITIVE_NAMES:
        return "withheld"
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
        "Dockerfile",
        "LICENSE",
        ".gitignore",
    }:
        return ""
    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            return "large"
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return "unreadable"


def _markdown_title(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for _ in range(40):
                line = handle.readline()
                if not line:
                    break
                stripped = line.strip()
                if stripped.startswith("# "):
                    return stripped[2:].strip()
    except OSError:
        return None
    return None


def _category(relative: str) -> str:
    parts = relative.split("/")
    name = parts[-1]
    suffix = Path(name).suffix.lower()

    if relative.startswith("frontend/"):
        return "Frontend application"
    if relative.startswith("dataverse_backend/tests/"):
        return "Backend automated tests"
    if relative.startswith("dataverse_backend/app/") or relative.startswith("dataverse_backend/"):
        if name.startswith("sample_") or suffix == ".csv":
            return "Data, trained models, and ML evidence"
        if suffix == ".sql":
            return "Supabase database and storage"
        return "Backend API and application"
    if relative.startswith("data/") or relative.startswith("models/"):
        return "Data, trained models, and ML evidence"
    if relative.startswith("supabase/"):
        return "Supabase database and storage"
    if relative.startswith("scripts/") or name in {"_build_deck.py", "_build_corrections.py"}:
        if name == "train_retail_mart.py":
            return "Data, trained models, and ML evidence"
        return "Development, QA, and document automation"
    if relative.startswith("docs/"):
        return "Project documentation and academic material"
    if parts[0] in {"output", "outputs", "report", "logs"} or suffix in {".png", ".pdf", ".pptx", ".docx"}:
        return "Generated reports, figures, logs, and screenshots"
    if parts[0] in {".github", ".claude", ".agents"}:
        return "Repository automation metadata"
    if len(parts) == 1:
        return "Project governance and root configuration"
    return "Other project file"


def _role(path: Path, relative: str, category: str) -> str:
    name = path.name
    stem_words = path.stem.replace("_", " ").replace("-", " ")
    suffix = path.suffix.lower()

    if name in SENSITIVE_NAMES:
        return "Local secret-bearing environment configuration; presence only, contents withheld."
    if name.endswith(".env.example") or name == ".env.example":
        return "Environment-variable template without credential values."
    if name == "AGENTS.md":
        return "Repository operating, quality, security, testing, and delivery instructions."
    if name == "CLAUDE.md":
        return "Additional repository development guidance."
    if name == "README.md" and "/" not in relative:
        return "Top-level project overview, setup, architecture, and usage guide."
    if name == "LICENSE":
        return "Software license terms."
    if name == ".gitignore":
        return "Source-control exclusion rules."
    if name == "docker-compose.yml":
        return "Local multi-container frontend/backend orchestration."
    if name == "Dockerfile":
        return f"Container build definition for {path.parent.name}."
    if name in {"package.json", "package-lock.json"}:
        scope = "workspace" if len(relative.split("/")) == 1 else path.parent.name
        return f"{scope.capitalize()} JavaScript scripts/dependency manifest or exact lockfile."
    if relative.startswith("frontend/app/") and name == "page.tsx":
        route_parts = relative.split("/")[2:-1]
        route = "/" + "/".join(route_parts) if route_parts else "/"
        return f"Next.js App Router page for {route}."
    if relative == "frontend/app/layout.tsx":
        return "Global Next.js application layout and metadata."
    if relative == "frontend/app/globals.css":
        return "Global frontend design tokens, layout, and component styling."
    if relative.startswith("frontend/components/dashboard/"):
        return f"Dashboard user-interface component: {stem_words}."
    if relative.startswith("frontend/components/site/"):
        return f"Public/authentication site component: {stem_words}."
    if relative.startswith("frontend/lib/"):
        return f"Frontend client utility or contract: {stem_words}."
    if relative.startswith("frontend/hooks/"):
        return f"Reusable React hook: {stem_words}."
    if relative.startswith("frontend/scripts/"):
        return f"Frontend development or contract-test script: {stem_words}."
    if relative.startswith("dataverse_backend/app/api/"):
        return f"FastAPI request, route, schema, or upload module: {stem_words}."
    if relative.startswith("dataverse_backend/app/agents/"):
        return f"Agent orchestration or analysis module: {stem_words}."
    if relative.startswith("dataverse_backend/app/services/"):
        return f"Backend service module: {stem_words}."
    if relative.startswith("dataverse_backend/app/core/"):
        return f"Backend infrastructure/core module: {stem_words}."
    if relative.startswith("dataverse_backend/tests/"):
        return f"Automated backend test coverage: {stem_words.removeprefix('test ')}."
    if name.startswith("requirements") and suffix == ".txt":
        return "Python dependency manifest for the indicated runtime profile."
    if suffix == ".csv":
        return "Structured dataset or API test fixture; row/column details are documented in the data section."
    if suffix == ".pkl":
        return "Serialized scikit-learn pipeline artifact; metadata and limitations are documented in the model section."
    if relative == "models/model_metadata.json":
        return "Training metrics, features, estimator, and evaluation metadata for saved models."
    if suffix == ".sql":
        return "PostgreSQL/Supabase schema or ordered migration."
    if category == "Development, QA, and document automation":
        return f"Automation utility: {stem_words}."
    if category == "Project documentation and academic material":
        if suffix == ".md":
            return _markdown_title(path) or f"Project documentation: {stem_words}."
        return f"Academic specification or supporting document: {stem_words}."
    if category == "Generated reports, figures, logs, and screenshots":
        labels = {
            ".png": "Generated figure, architecture asset, or UI verification screenshot.",
            ".pdf": "Generated or revised PDF deliverable.",
            ".docx": "Generated or revised Word deliverable.",
            ".pptx": "Generated or revised presentation deliverable.",
            ".log": "Development/runtime log artifact; content is not treated as source code.",
            ".md": "Generated narrative, evidence log, or report chapter output.",
            ".json": "Generated machine-readable verification or report metadata.",
        }
        return labels.get(suffix, f"Generated project artifact: {stem_words}.")
    if category == "Repository automation metadata":
        return f"Repository automation or agent configuration: {stem_words}."
    return f"Project file ({suffix.lstrip('.') or 'no extension'}): {stem_words}."


def build_inventory(root: Path, output_dir: Path) -> dict[str, Any]:
    root = root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tracked = _tracked_files(root)
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for base, directories, files in os.walk(root):
        base_path = Path(base)
        retained_directories: list[str] = []
        for directory in directories:
            child = base_path / directory
            if directory in EXCLUDED_DIRECTORY_REASONS:
                file_count, byte_count = _measure_tree(child)
                excluded.append(
                    {
                        "path": _relative(child, root),
                        "files": file_count,
                        "bytes": byte_count,
                        "reason": EXCLUDED_DIRECTORY_REASONS[directory],
                    }
                )
            else:
                retained_directories.append(directory)
        directories[:] = retained_directories

        for filename in files:
            path = base_path / filename
            relative = _relative(path, root)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            category = _category(relative)
            rows.append(
                {
                    "path": relative,
                    "category": category,
                    "type": path.suffix.lower().lstrip(".") or "no extension",
                    "bytes": size,
                    "lines": _line_count(path),
                    "source_control": "Tracked" if relative in tracked else "Local/generated/untracked",
                    "role": _role(path, relative, category),
                }
            )

    rows.sort(key=lambda row: (CATEGORY_ORDER.get(row["category"], 99), row["path"].lower()))
    excluded.sort(key=lambda row: row["path"].lower())
    category_counts = Counter(row["category"] for row in rows)
    extension_counts = Counter(row["type"] for row in rows)
    total_lines = sum(row["lines"] for row in rows if isinstance(row["lines"], int))
    summary = {
        "audited_files": len(rows),
        "audited_bytes": sum(row["bytes"] for row in rows),
        "audited_text_lines": total_lines,
        "tracked_files": sum(row["source_control"] == "Tracked" for row in rows),
        "local_generated_untracked_files": sum(row["source_control"] != "Tracked" for row in rows),
        "excluded_files": sum(row["files"] for row in excluded),
        "excluded_bytes": sum(row["bytes"] for row in excluded),
        "physical_files_accounted_for": len(rows) + sum(row["files"] for row in excluded),
        "categories": dict(category_counts),
        "extensions": dict(extension_counts),
    }

    csv_path = output_dir / "DataVerse_AI_Current_Folder_File_Inventory.csv"
    json_path = output_dir / "DataVerse_AI_Current_Folder_Audit.json"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "category", "type", "bytes", "lines", "source_control", "role"])
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps({"summary": summary, "excluded_directories": excluded, "files": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "excluded_directories": excluded,
        "files": rows,
        "csv_path": csv_path,
        "json_path": json_path,
    }


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[1]
    result = build_inventory(repository_root, repository_root / "output" / "technical_report")
    print(json.dumps(result["summary"], indent=2))
    print(result["csv_path"])
    print(result["json_path"])
