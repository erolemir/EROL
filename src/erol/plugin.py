"""Generate native manifests and a portable runtime from canonical source files."""

from pathlib import Path

from erol import __version__
from erol.adapters import generated_files, skill_path
from erol.common import canonical, reject_links


def plugin_files(repository_root: Path | None = None) -> dict[str, str | bytes]:
    """Render all owned plugin assets; copies are derived, never hand-maintained."""
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "erol",
        "version": __version__,
        "description": (
            "Project memory, focused development and business workflows, "
            "and evidence-gated skill learning."
        ),
        "license": "AGPL-3.0-only",
        "author": {"name": "EROL contributors"},
        "extensions": {
            "com.openai": {
                "interface": {
                    "displayName": "EROL",
                    "shortDescription": "Project memory and focused workflows",
                    "longDescription": (
                        "Retrieve verified incidents, select focused skills "
                        "and develop project workflows with reviewed evidence."
                    ),
                    "developerName": "EROL contributors",
                    "category": "Productivity",
                    "defaultPrompt": [
                        "Use EROL to plan this task with relevant skills and evidence."
                    ],
                }
            }
        },
    }
    codex_marketplace = {
        "name": "erol",
        "interface": {"displayName": "EROL"},
        "plugins": [
            {
                "name": "erol",
                "source": {"source": "local", "path": "./plugins/erol"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }
    claude_marketplace = {
        "name": "erol",
        "owner": {"name": "EROL contributors"},
        "metadata": {"description": "EROL project memory and evidence-based learning."},
        "plugins": [
            {
                "name": "erol",
                "source": "./plugins/erol",
                "description": manifest["description"],
            }
        ],
    }
    claude_manifest = {
        key: value for key, value in manifest.items() if key not in {"$schema", "extensions"}
    }
    setup = (
        "Resolve <EROL_LAUNCHER> as ../../scripts/erol.mjs relative to the directory\n"
        "containing this loaded SKILL.md, never relative to the project's working directory.\n"
        "Use its absolute path as one safely quoted argument to node on every call.\n"
        "Resolve <PROJECT_ROOT> from the actual repository being worked on, not this plugin's\n"
        "installation/cache directory. Keep the caller's working directory in that project.\n"
        "Use the managed block's canonical home when present, otherwise ~/.erol.\n"
        "This plugin bundles its Python standard-library runtime and canonical skill data.\n"
        "Node and Python 3.11+ are required; no pip install or global erol command is required."
    )
    body = generated_files("codex")[skill_path("codex")].replace(
        "Read the EROL managed block in the root instructions for the canonical home.", setup
    )
    body = body.replace("`erol ", "`node <EROL_LAUNCHER> ").replace(
        "--project .", "--project <PROJECT_ROOT>"
    )
    body += (
        "\n## Direct Python fallback\n\n"
        "If the host denies Node child-process creation (EPERM/EACCES), or its Python\n"
        "probe fails despite an available Python 3.11+, keep the current permissions.\n"
        "Resolve <EROL_PYTHON_LAUNCHER> as ../../scripts/erol.py relative to this SKILL.md's\n"
        "directory. Resolve a Python 3.11+ executable using the host's normal tools.\n"
        "Replace the node prefix on every CLI call with the literal argv prefix\n"
        "`<PYTHON_EXECUTABLE> -I -S -X utf8 <EROL_PYTHON_LAUNCHER>`. Pass both absolute\n"
        "paths as individual safely quoted arguments, retaining the same --project,\n"
        "--home and command arguments. This runs the same bundled core directly; it\n"
        "does not install dependencies or relax sandbox policy. Do not retry a denied\n"
        "Node launcher repeatedly or claim Python is missing without checking it.\n"
    )
    ui = (
        'interface:\n  display_name: "EROL"\n'
        '  short_description: "Project memory and focused workflows"\n'
        '  default_prompt: "Use $erol to plan this task with relevant skills."\n'
    )
    result: dict[str, str | bytes] = {
        "plugins/erol/plugin.json": canonical(manifest) + "\n",
        "plugins/erol/.claude-plugin/plugin.json": canonical(claude_manifest) + "\n",
        "plugins/erol/skills/erol/SKILL.md": body,
        "plugins/erol/skills/erol/agents/openai.yaml": ui,
        ".agents/plugins/marketplace.json": canonical(codex_marketplace) + "\n",
        ".claude-plugin/marketplace.json": canonical(claude_marketplace) + "\n",
    }
    for notice in ("LICENSE", "COPYRIGHT"):
        source = root / notice
        reject_links(source)
        result[f"plugins/erol/{notice}"] = source.read_text(encoding="utf-8")
    launcher = root / "bin" / "erol.mjs"
    reject_links(launcher)
    result["plugins/erol/scripts/erol.mjs"] = launcher.read_text(encoding="utf-8")
    python_launcher = root / "bin" / "erol.py"
    reject_links(python_launcher)
    result["plugins/erol/scripts/erol.py"] = python_launcher.read_text(encoding="utf-8")
    canonical_root = root / "src" / "erol"
    reject_links(canonical_root)
    sources = list(canonical_root.glob("*.py"))
    sources.extend(
        path
        for path in (canonical_root / "data").rglob("*")
        if path.is_file() and path.suffix in {".json", ".md", ".png"}
    )
    if not sources or not (canonical_root / "__main__.py").is_file():
        raise ValueError("Canonical EROL source is unavailable for plugin generation")
    for source in sorted(sources):
        reject_links(source)
        if not source.resolve().is_relative_to(canonical_root):
            raise ValueError("Plugin source escapes canonical runtime")
        relative = source.relative_to(canonical_root).as_posix()
        result[f"plugins/erol/runtime/erol/{relative}"] = (
            source.read_bytes() if source.suffix == ".png" else source.read_text(encoding="utf-8")
        )
    return result
