"""One project-local destination for generated reports; durable memory stays external."""

import re
from pathlib import Path

from .common import ErolError, digest, identifier, reject_links


def relative_directory(project_name: str, task_id: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", project_name).strip(".-") or "project"
    if len(slug) > 80:
        slug = slug[:64] + "-" + digest(project_name)[:12]
    # Windows reserved device names cannot be used as folders.
    if re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", slug):
        slug = "project-" + slug
    return f"erol/{identifier(slug)}/{identifier(task_id)}"


def external_directory(home: Path, project_id: str, task_id: str) -> Path:
    target = home.expanduser().resolve() / "reports" / identifier(project_id) / identifier(task_id)
    reject_links(target)
    return target


def checked_directory(root: Path, relative: str, *, home: Path | None = None) -> Path:
    path = Path(relative)
    if ".." in path.parts:
        raise ErolError("Report directory traversal is forbidden")
    if path.is_absolute():
        if home is None:
            raise ErolError("External reports require the owning EROL home")
        base = home.expanduser().resolve() / "reports"
        if not path.is_relative_to(base) or len(path.relative_to(base).parts) != 2:
            raise ErolError("Reports must remain in the owning EROL reports directory")
        for part in path.relative_to(base).parts:
            identifier(part)
        target = path
    else:
        if ".." in path.parts or len(path.parts) != 3 or path.parts[0] != "erol":
            raise ErolError("Invalid legacy report directory")
        target = root / path
    reject_links(target)
    return target


def report_digest(directory: str | None) -> str | None:
    if directory is None:
        return None
    base = Path(directory)
    reject_links(base)
    files: dict[str, str] = {}
    if base.exists():
        for path in base.rglob("*"):
            reject_links(path)
            if path.is_file():
                if len(files) >= 100 or path.stat().st_size > 1024 * 1024:
                    raise ErolError("Generated reports exceed the evidence budget")
                files[path.relative_to(base).as_posix()] = digest(path.read_bytes().hex())
    return digest(files)


def instructions(relative: str) -> str:
    return (
        f"Generated inspection/research reports belong only under {relative}/. "
        "Do not scatter new report Markdown files in the project root or docs/. "
        "Update existing source documentation when the task requires it; an explicit "
        "user-requested document path takes precedence. Native AGENTS.md, CLAUDE.md "
        "and installed SKILL.md discovery locations remain unchanged. "
        "Do not copy credentials, conversations or EROL memory databases into reports."
    )
