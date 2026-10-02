"""Conservative managed-file installation, with external ownership and backups."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from .adapters import (
    BEGIN_MARKER,
    END_MARKER,
    generated_files,
    instruction_path,
    managed_instruction_block,
    validate_harness,
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_links(path: Path) -> None:
    for node in (path, *path.parents):
        if node.is_symlink():
            raise ValueError(f"Refusing symbolic link: {node}")
        if node.exists():
            attrs = getattr(node.stat(follow_symlinks=False), "st_file_attributes", 0)
            if attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ValueError(f"Refusing reparse point: {node}")


def _atomic_write(path: Path, data: bytes) -> None:
    _reject_links(path)
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_links(path.parent)
    handle, temporary = tempfile.mkstemp(prefix=".erol-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if existing_mode is not None:
            os.chmod(temporary, existing_mode)
        _reject_links(path)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Installer:
    """Install one bridge and one bounded instruction block per harness.

    Dry runs are read-only. Edited owned content produces a conflict, while edits
    outside a managed instruction block survive reinstall and uninstall.
    """

    def __init__(self, root: Path, home: Path, launcher: Path | None = None):
        raw_root, raw_home = Path(root).expanduser().absolute(), Path(home).expanduser().absolute()
        _reject_links(raw_root)
        _reject_links(raw_home)
        self.root, self.home = raw_root.resolve(), raw_home.resolve()
        if not self.root.is_dir():
            raise ValueError("Project root must be an existing directory")
        if self.home.exists() and not self.home.is_dir():
            raise ValueError("EROL home must be a directory")
        if self.home.is_relative_to(self.root) or self.root.is_relative_to(self.home):
            raise ValueError("EROL home and project must be separate, non-overlapping directories")
        identity = _digest(os.path.normcase(str(self.root)).encode("utf-8"))[:24]
        self.state_dir = self.home / "installations" / identity
        selected_launcher = launcher or os.environ.get("EROL_LAUNCHER")
        self.launcher = (
            self._runtime_launcher(Path(selected_launcher)) if selected_launcher else None
        )

    @staticmethod
    def _runtime_launcher(launcher: Path) -> Path:
        """Only the launcher accompanying this installed module may be persisted."""
        _reject_links(launcher)
        runtime_root = Path(__file__).resolve().parents[2]
        allowed = {
            (runtime_root / "bin" / "erol.mjs").resolve(),
            (runtime_root / "scripts" / "erol.mjs").resolve(),
        }
        if (
            not launcher.is_absolute()
            or not launcher.is_file()
            or launcher.resolve() not in allowed
        ):
            raise ValueError("EROL_LAUNCHER does not match this installed EROL runtime")
        return launcher.resolve()

    def _target(self, relative: str) -> Path:
        target = self.root / relative
        if Path(relative).is_absolute() or not target.resolve().is_relative_to(self.root):
            raise ValueError("Managed target escapes project")
        _reject_links(target)
        if target.exists() and not target.is_file():
            raise ValueError(f"Managed target is not a regular file: {target}")
        return target

    def _manifest_path(self, harness: str) -> Path:
        target = self.state_dir / f"{validate_harness(harness)}.json"
        _reject_links(target)
        return target

    def _private_directory(self, path: Path) -> None:
        _reject_links(path)
        missing = []
        cursor = path
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        for directory in reversed(missing):
            directory.mkdir(mode=0o700)

    def _load_manifest(self, harness: str) -> dict[str, Any]:
        path = self._manifest_path(harness)
        if not path.exists():
            return {}
        document = json.loads(path.read_text(encoding="utf-8"))
        allowed = set(generated_files(harness)) | {instruction_path(harness)}
        if (
            not isinstance(document, dict)
            or document.get("version") != 1
            or document.get("root") != str(self.root)
            or document.get("harness") != harness
            or not isinstance(document.get("files"), dict)
            or set(document["files"]) != allowed
        ):
            raise ValueError("Invalid or mismatched installation ownership manifest")
        for relative, entry in document["files"].items():
            self._target(relative)
            expected_kind = "block" if relative == instruction_path(harness) else "file"
            if (
                not isinstance(entry, dict)
                or entry.get("kind") != expected_kind
                or not isinstance(entry.get("payload"), str)
                or not isinstance(entry.get("prefix"), str)
                or not isinstance(entry.get("created"), bool)
            ):
                raise ValueError("Invalid installation ownership entry")
            if entry.get("checksum") != _digest(entry["payload"].encode("utf-8")):
                raise ValueError("Installation ownership checksum mismatch")
        return document

    def _report(self, harness: str, operation: str, dry_run: bool) -> dict[str, Any]:
        return {
            "harness": harness,
            "operation": operation,
            "dry_run": dry_run,
            "status": "planned",
            "actions": [],
            "conflicts": [],
        }

    def _prepare_install(
        self, harness: str
    ) -> tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]:
        validate_harness(harness)
        report = self._report(harness, "install", True)
        manifest = self._load_manifest(harness)
        old_entries = manifest.get("files", {})
        rendered = generated_files(harness, self.launcher)
        rendered[instruction_path(harness)] = managed_instruction_block(
            harness, self.home, self.launcher
        )
        updates, entries = {}, {}
        for relative, text in rendered.items():
            path = self._target(relative)
            current = path.read_bytes() if path.exists() else b""
            desired = text.encode("utf-8")
            is_block = relative == instruction_path(harness)
            old = old_entries.get(relative)
            if old:
                payload = old["payload"].encode("utf-8")
                valid = (
                    (
                        current.count(payload) == 1
                        and current.count(BEGIN_MARKER.encode()) == 1
                        and current.count(END_MARKER.encode()) == 1
                    )
                    if is_block
                    else current == payload
                )
                if not valid:
                    report["conflicts"].append(
                        {"path": relative, "reason": "Owned content modified or removed"}
                    )
                    continue
                prefix = old.get("prefix", "") if is_block else ""
                payload_new = prefix.encode("utf-8") + desired
                updated = current.replace(payload, payload_new, 1) if is_block else desired
            elif is_block:
                if BEGIN_MARKER.encode() in current or END_MARKER.encode() in current:
                    report["conflicts"].append(
                        {"path": relative, "reason": "Unowned or malformed EROL markers"}
                    )
                    continue
                prefix = "\n\n" if current else ""
                payload_new = prefix.encode() + desired
                updated = current + payload_new
            else:
                if path.exists():
                    report["conflicts"].append(
                        {"path": relative, "reason": "Existing unowned file"}
                    )
                    continue
                prefix, payload_new, updated = "", desired, desired
            entries[relative] = {
                "kind": "block" if is_block else "file",
                "payload": payload_new.decode(),
                "checksum": _digest(payload_new),
                "prefix": prefix,
                "created": old.get("created", False) if old else not path.exists(),
            }
            report["actions"].append(
                {"path": relative, "action": "unchanged" if current == updated else "write"}
            )
            if current != updated:
                updates[relative] = updated
        if report["conflicts"]:
            report["status"] = "conflict"
        next_manifest = {"version": 1, "root": str(self.root), "harness": harness, "files": entries}
        return report, updates, next_manifest

    def plan_install(self, harness: str) -> dict[str, Any]:
        return self._prepare_install(harness)[0]

    def _apply(
        self, changes: Mapping[str, bytes | None], harness: str, manifest: dict[str, Any] | None
    ) -> None:
        """Back up every affected file; restore all originals on application failure."""
        originals = {
            relative: self._target(relative).read_bytes()
            if self._target(relative).exists()
            else None
            for relative in changes
        }
        state_path = self._manifest_path(harness)
        previous_state = state_path.read_bytes() if state_path.exists() else None
        backup_dir = self.state_dir / "backups" / uuid4().hex
        _reject_links(backup_dir)
        self._private_directory(self.state_dir)
        if originals:
            self._private_directory(backup_dir)
        for relative, data in originals.items():
            if data is not None:
                _atomic_write(backup_dir / f"{_digest(relative.encode())}.bak", data)
        try:
            for relative, data in changes.items():
                target = self._target(relative)
                if data is None:
                    target.unlink()
                else:
                    _atomic_write(target, data)
            if manifest is None:
                state_path.unlink()
            else:
                _atomic_write(state_path, (json.dumps(manifest, indent=2) + "\n").encode())
        except (OSError, ValueError):
            for relative, original in originals.items():
                target = self._target(relative)
                if original is None:
                    if target.exists():
                        target.unlink()
                else:
                    _atomic_write(target, original)
            if previous_state is not None:
                _atomic_write(state_path, previous_state)
            elif state_path.exists():
                state_path.unlink()
            raise

    def install(self, harness: str, dry_run: bool = True) -> dict[str, Any]:
        report, updates, manifest = self._prepare_install(harness)
        report["dry_run"] = dry_run
        if not dry_run and not report["conflicts"]:
            self._apply(updates, harness, manifest)
            report["status"] = "installed"
        return report

    def uninstall(self, harness: str, dry_run: bool = True) -> dict[str, Any]:
        report = self._report(validate_harness(harness), "uninstall", dry_run)
        manifest = self._load_manifest(harness)
        if not manifest:
            report["status"] = "not-installed"
            return report
        changes: dict[str, bytes | None] = {}
        for relative, entry in manifest["files"].items():
            path = self._target(relative)
            current = path.read_bytes() if path.exists() else b""
            payload = entry["payload"].encode()
            is_block = entry["kind"] == "block"
            valid = (
                (
                    current.count(payload) == 1
                    and current.count(BEGIN_MARKER.encode()) == 1
                    and current.count(END_MARKER.encode()) == 1
                )
                if is_block
                else current == payload
            )
            if not valid:
                report["conflicts"].append(
                    {"path": relative, "reason": "Owned content modified or removed"}
                )
                continue
            remaining = current.replace(payload, b"", 1) if is_block else b""
            data = remaining if is_block and (remaining or not entry["created"]) else None
            changes[relative] = data
            report["actions"].append(
                {"path": relative, "action": "write" if data is not None else "remove"}
            )
        if report["conflicts"]:
            report["status"] = "conflict"
        elif not dry_run:
            self._apply(changes, harness, None)
            report["status"] = "uninstalled"
        return report
