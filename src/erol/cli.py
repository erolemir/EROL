"""Small JSON CLI for harness integration and inspectable lifecycle transitions."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from erol import __version__
from erol.adapters import capabilities
from erol.checktrust import CheckTrust
from erol.common import ErolError, canonical, digest
from erol.config import Config
from erol.execution import Runner
from erol.identity import detect_project
from erol.installer import Installer
from erol.learning import LearningEngine
from erol.orchestration import Orchestrator, agents, routing_eval
from erol.registry import Registry, evaluate_skill
from erol.runstore import RunStore
from erol.security import assert_secret_safe, scan_instructions
from erol.store import MEMORY_CLASSES, Store


def read_input(path: str) -> dict:
    target = Path(path)
    if target.stat().st_size > 131072:
        raise ErolError("Input file exceeds 128 KiB")
    value = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ErolError("Input must be a JSON object")
    assert_secret_safe(value)
    return value


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="erol", description="Local, evidence-gated project learning"
    )
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--project", default=".", help="Project directory")
    root.add_argument(
        "--home",
        default=os.environ.get("EROL_HOME", str(Path.home() / ".erol")),
        help="External state directory (default ~/.erol)",
    )
    commands = root.add_subparsers(dest="command")
    chat = commands.add_parser("chat", help="Open the EROL terminal or execute one prompt")
    chat.add_argument("--prompt", help="One task with machine-readable JSON result")
    chat.add_argument("--model", help="Explicit CONNECTION:MODEL; default automatic routing")
    chat.add_argument("--resume", help="Saved session id (use --prompt to continue its task)")
    chat.add_argument(
        "--mode",
        choices=("auto", "general", "research"),
        default="auto",
        help="Projectless chat/research or automatic project mode",
    )
    terminal_config = commands.add_parser(
        "terminal", help="Manage external terminal connections/settings"
    )
    terminal_config.add_argument(
        "--command", dest="terminal_command", default="/help", help="A terminal slash command"
    )
    logo = commands.add_parser("logo", help="Display the green mantis reference in the terminal")
    logo.add_argument("--width", type=int, help="Width in terminal columns (8..160; auto up to 80)")
    logo.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    commands.add_parser("status", help="Project identity and current local lifecycle counts")
    for name in ("install", "setup", "update", "uninstall"):
        command = commands.add_parser(name, help="Inspect safe harness installation changes")
        command.add_argument("--harness", choices=("codex", "claude"), required=True)
        command.add_argument(
            "--apply", action="store_true", help="Apply the changes; default is dry run"
        )
    for name in ("plan", "explain"):
        command = commands.add_parser(
            name, help="Route a task and construct bounded context; no execution"
        )
        command.add_argument("--task", required=True)
        command.add_argument(
            "--task-id", help="Persist an activation receipt for later real-use evidence"
        )
    execute = commands.add_parser("run", help="Execute a task in an isolated Git worktree")
    execute.add_argument("--task", required=True)
    execute.add_argument("--harness", choices=("codex", "claude"), required=True)
    execute.add_argument("--review-harness", choices=("codex", "claude"))
    execute.add_argument("--mode", choices=("development", "research"), default="development")
    execute.add_argument("--checks", required=True, help="Reviewed versioned acceptance-check JSON")
    checks = commands.add_parser("checks", help="Inspect and authorize reviewed host checks")
    check_actions = checks.add_subparsers(dest="action", required=True)
    for name in ("show", "trust", "revoke"):
        check_action = check_actions.add_parser(name)
        check_action.add_argument("--file", required=True)
        if name == "trust":
            check_action.add_argument("--env", action="append", default=[])
            check_action.add_argument(
                "--prefix",
                default="[]",
                help="Reviewed external executor argv prefix as JSON; no sandbox guarantee",
            )
    execute.add_argument("--task-id", help="Unique task identity; generated when omitted")
    execute.add_argument(
        "--reviewers", type=int, default=1, help="1..3 independent read-only reviewers"
    )
    executions = commands.add_parser("runs").add_subparsers(dest="action", required=True)
    executions.add_parser("list")
    for name in ("show", "resume", "cancel"):
        execution = executions.add_parser(name)
        execution.add_argument("--id", required=True)
    memory = commands.add_parser("memory").add_subparsers(dest="action", required=True)
    memory.add_parser("status")
    search = memory.add_parser("search")
    search.add_argument("query")
    search.add_argument("--max-chars", type=int, default=6000)
    search.add_argument("--mode", choices=("lexical", "hybrid"), default="hybrid")
    memory.add_parser("index")
    memory.add_parser("compact")
    memory.add_parser("export")
    add = memory.add_parser("add", help="Add sanitized evidence-backed memory")
    add.add_argument(
        "--kind",
        choices=("state", "decisions", "architecture", "learnings", "handoff"),
        required=True,
    )
    add.add_argument("--input", required=True)
    stale = memory.add_parser("stale")
    stale.add_argument(
        "--kind",
        choices=("state", "decisions", "architecture", "learnings", "handoff"),
        required=True,
    )
    stale.add_argument("--id", required=True)
    incident = commands.add_parser("incident").add_subparsers(dest="action", required=True)
    record = incident.add_parser(
        "record", help="Input: examples/incident.json; distinct reviewed task evidence required"
    )
    record.add_argument("--input", required=True)
    match = incident.add_parser("match")
    match.add_argument("--error", required=True)
    match.add_argument("--component", required=True)
    match.add_argument("--exception", default="")
    fail = incident.add_parser(
        "failure", help="Record a failed strategy attempt and detect retry loops"
    )
    fail.add_argument("--input", required=True)
    learning = commands.add_parser("learning").add_subparsers(dest="action", required=True)
    learning.add_parser("status")
    learning.add_parser("candidates")
    for name in ("candidate", "activate"):
        command = learning.add_parser(name)
        command.add_argument("--id", required=True)
    evaluate = learning.add_parser(
        "eval",
        help="Qualify positive/negative triggers and independently reviewed behavior evidence",
    )
    evaluate.add_argument("--id", required=True)
    evaluate.add_argument("--input", required=True)
    promotion = learning.add_parser("promotion")
    promotion.add_argument("--name", required=True)
    approve = learning.add_parser(
        "promote", help="Approve generalization candidate; never installs a project remedy globally"
    )
    approve.add_argument("--id", required=True)
    approve.add_argument("--approve", action="store_true")
    approve.add_argument("--input", required=True, help="Cross-project evidence report")
    skills = commands.add_parser("skills").add_subparsers(dest="action", required=True)
    skill_list = skills.add_parser("list")
    skill_list.add_argument("--category", help="Filter builtin domains or learned project skills")
    search_skill = skills.add_parser("search")
    search_skill.add_argument("query")
    disable = skills.add_parser("disable")
    disable.add_argument("--name", required=True)
    skill = commands.add_parser("skill").add_subparsers(dest="action", required=True)
    for name in ("show", "metrics", "export"):
        command = skill.add_parser(name)
        command.add_argument("--name", required=True)
    create = skill.add_parser(
        "create",
        help="Draft a revised project workflow; it must independently pass eval before activation",
    )
    create.add_argument("--name", required=True)
    create.add_argument("--input", required=True)
    rollback = skill.add_parser("rollback")
    rollback.add_argument("--name", required=True)
    rollback.add_argument("--version", required=True)
    usage = skill.add_parser(
        "usage", help="Complete a plan --task-id using reviewed real-use evidence"
    )
    usage.add_argument("--task-id", required=True)
    usage.add_argument(
        "--input", required=True, help="verification report with optional false_triggers"
    )
    usage.add_argument(
        "--failed", action="store_true", help="Input: reason and reference; disable failed revision"
    )
    commands.add_parser("agents", help="Canonical advisory roles; EROL does not spawn them")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("target", nargs="?", choices=("skills", "all"), default="all")
    lint = commands.add_parser("lint")
    lint.add_argument("target", choices=("context",))
    commands.add_parser("eval", help="Run deterministic routing and static pack quality evals")
    benchmark = commands.add_parser(
        "benchmark", help="Measure local routing CPU and rendered context proxies"
    )
    benchmark.add_argument("--iterations", type=int, default=20)
    benchmark.add_argument("--suite", help="Explicit controlled behavioral suite JSON")
    benchmark.add_argument("--harness", choices=("codex", "claude"))
    benchmark.add_argument("--report", help="Behavioral result JSON path")
    benchmark.add_argument("--repeat", type=int, default=1)
    scan = commands.add_parser(
        "scan", help="Discover bounded TODOs, imported issues and observed check failures"
    )
    scan.add_argument("--checks")
    scan.add_argument("--issues")
    queue = commands.add_parser("queue").add_subparsers(dest="action", required=True)
    queue.add_parser("list")
    policy = queue.add_parser(
        "policy", help="Write an explicit project-bound check-repair policy; no execution"
    )
    policy.add_argument("--harness", choices=("codex", "claude"), required=True)
    policy.add_argument("--checks", required=True)
    policy.add_argument("--output", required=True)
    policy.add_argument("--reviewers", type=int, default=1)
    policy.add_argument("--max-tasks", type=int, default=1)
    enqueue = queue.add_parser("enqueue")
    enqueue.add_argument("--policy", required=True)
    enqueue.add_argument("--candidate", action="append")
    work = queue.add_parser("work", help="Run matching queued jobs within explicit policy limits")
    work.add_argument("--policy", required=True)
    work.add_argument(
        "--scan", action="store_true", help="Discover TODOs and enqueue matching rules first"
    )
    for action in ("show", "cancel", "resume", "depend"):
        child = queue.add_parser(action)
        child.add_argument("--id", required=True)
        if action == "resume":
            child.add_argument("--policy", required=True)
        if action == "depend":
            child.add_argument("--on", action="append", required=True)
    panel = commands.add_parser("panel", help="Serve a read-only local evidence panel")
    panel.add_argument("--port", type=int, default=8765)
    panel.add_argument("--open", action="store_true")
    return root


def counts(store: Store) -> dict:
    return {kind: len(store.list(kind)) for kind in MEMORY_CLASSES}


def qualify_pack(registry: Registry) -> dict:
    reports = []
    for metadata in registry.list():
        skill = registry.get(metadata["name"])
        report = evaluate_skill(skill)
        security = scan_instructions(skill.body)
        reports.append(
            {
                "name": skill.name,
                "passed": report["passed"] and not security,
                "static": report,
                "security_findings": security,
            }
        )
    return {
        "passed": all(report["passed"] for report in reports),
        "skills": reports,
        "behavior_verified": False,
    }


def run(args: argparse.Namespace) -> dict:
    home = Path(args.home).expanduser()
    project = detect_project(Path(args.project))
    root = Path(project.root)
    # Installer dry runs must produce no memory/database side effects.
    if args.command in {"install", "setup", "update", "uninstall"}:
        installer = Installer(root, home)
        method = installer.uninstall if args.command == "uninstall" else installer.install
        return method(args.harness, dry_run=not args.apply)
    if args.command == "agents":
        return {"agents": agents(), "execution_supported": False}
    config = Config.load(home, root)
    with Store(home, project) as store:
        registry = Registry(project_store=store)
        engine = LearningEngine(store, config, registry)
        command = args.command
        if command == "panel":
            from .panel import make_server

            server = make_server(store.directory, store.project_id, args.port)
            url = server.access_url
            print(json.dumps({"panel": url, "read_only": True}), file=sys.stderr, flush=True)
            if args.open:
                import webbrowser

                webbrowser.open(url)
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return {"panel": f"http://127.0.0.1:{server.server_port}", "stopped": True}
        if command == "checks":
            from .execution import load_checks

            manifest = load_checks(Path(args.file).expanduser().resolve(strict=True))
            trust = CheckTrust(store.directory, root)
            if args.action == "show":
                return {
                    "manifest": manifest,
                    "manifest_digest": digest(manifest),
                    "trusted": any(
                        item["manifest_digest"] == digest(manifest) for item in trust.records()
                    ),
                    "execution": "host commands; review argv and invoked code before trusting",
                }
            if args.action == "revoke":
                trust.revoke(manifest)
                return {"manifest_digest": digest(manifest), "trusted": False}
            return {
                "approval": trust.approve(
                    manifest, environment=args.env, prefix=json.loads(args.prefix)
                ),
                "original_root": str(root),
                "sandbox_verified": False,
            }
        if command in {"scan", "queue"}:
            from .work import Queue, WorkStore, discover, load_policy

            with (
                WorkStore(store.directory, store.project_id) as work,
                RunStore(store.directory, store.project_id) as runs,
            ):
                queue = Queue(work, Runner(store, engine, runs))
                if command == "scan":
                    return discover(
                        root,
                        work,
                        checks_path=Path(args.checks) if args.checks else None,
                        issues_path=Path(args.issues) if args.issues else None,
                    )
                if args.action == "list":
                    return {"jobs": work.list("jobs")}
                if args.action == "policy":
                    from .common import atomic_write
                    from .execution import load_checks

                    checks = Path(args.checks).resolve(strict=True)
                    load_checks(checks)
                    if not 1 <= args.max_tasks <= 20 or not 1 <= args.reviewers <= 3:
                        raise ErolError("Policy permits 1..20 tasks and 1..3 reviewers")
                    data = {
                        "schema_version": 1,
                        "project_id": store.project_id,
                        "limits": {
                            "max_tasks": args.max_tasks,
                            "max_total_seconds": 3600,
                            "task_seconds": 3600,
                            "session_seconds": 900,
                            "check_seconds": 300,
                            "reviewers": args.reviewers,
                        },
                        "rules": [
                            {
                                "id": "repair-observed-check",
                                "kinds": ["check"],
                                "paths": ["*"],
                                "harness": args.harness,
                                "review_harness": args.harness,
                                "mode": "development",
                                "checks": str(checks),
                            }
                        ],
                    }
                    assert_secret_safe(data)
                    atomic_write(
                        Path(args.output), json.dumps(data, ensure_ascii=False, indent=2) + "\n"
                    )
                    return {
                        "policy": str(Path(args.output).resolve()),
                        "project_id": store.project_id,
                        "executes": False,
                    }
                if args.action == "show":
                    return work.get("jobs", args.id)
                if args.action == "cancel":
                    return queue.cancel(args.id)
                if args.action == "depend":
                    return queue.depend(args.id, args.on)
                policy = load_policy(Path(args.policy), store.project_id)
                if args.action == "enqueue":
                    return {"jobs": queue.enqueue(policy, args.candidate)}
                if args.action == "work" and args.scan:
                    discover(root, work)
                    queue.enqueue(policy)
                jobs = queue.execute(policy, resume_id=args.id if args.action == "resume" else None)
                return {"jobs": jobs, "passed": all(job["status"] == "completed" for job in jobs)}
        if command in {"run", "runs"}:
            with RunStore(store.directory, store.project_id) as executions:
                runner = Runner(store, engine, executions)
                if command == "run":
                    return runner.start(
                        args.task,
                        args.harness,
                        Path(args.checks),
                        task_id=args.task_id,
                        review_harness=args.review_harness,
                        mode=args.mode,
                        reviewers=args.reviewers,
                    )
                if args.action == "list":
                    return {
                        "runs": [
                            {
                                key: record.get(key)
                                for key in (
                                    "id",
                                    "task_id",
                                    "status",
                                    "phase",
                                    "harness",
                                    "created",
                                    "worktree",
                                )
                            }
                            for record in executions.list()
                        ]
                    }
                if args.action == "show":
                    return executions.get(args.id)
                if args.action == "resume":
                    return runner.resume(args.id)
                return runner.cancel(args.id)
        if command == "status":
            return {
                "version": __version__,
                "project": project.to_dict(),
                "home": str(store.home),
                "memory": counts(store),
                "memory_budgets": store.budget_report(),
                "config": config.to_dict(),
                "capabilities": capabilities(),
            }
        if command in {"plan", "explain"}:
            if args.task_id:
                return engine.begin_task(args.task_id, args.task)
            assert_secret_safe(args.task)
            return Orchestrator(registry).plan(
                args.task,
                memory=store.search(args.task, mode="hybrid"),
                token_budget=config.context_tokens,
                max_skills=config.max_active_skills,
            )
        if command == "memory":
            if args.action == "status":
                return {
                    "project": project.to_dict(),
                    "counts": counts(store),
                    "directory": str(store.directory),
                }
            if args.action == "search":
                return {
                    "matches": store.search(args.query, max_chars=args.max_chars, mode=args.mode)
                }
            if args.action == "index":
                from .retrieval import MemoryIndex

                index = MemoryIndex(store)
                try:
                    return index.sync()
                finally:
                    index.close()
            if args.action == "compact":
                return store.compact()
            if args.action == "export":
                return store.export_markdown()
            if args.action == "stale":
                store.mark_stale(args.kind, args.id)
                return {"id": args.id, "stale": True}
            if args.action == "add":
                data = read_input(args.input)
                if args.kind == "learnings":
                    return store.learn(data["id"], data["text"], data["evidence"])
                if not isinstance(data.get("evidence"), list) or not data["evidence"]:
                    raise ErolError("Durable memory requires evidence references")
                return store.put(args.kind, data)
        if command == "incident":
            if args.action == "record":
                return engine.record_incident(read_input(args.input))
            if args.action == "match":
                return {"matches": engine.matches(args.error, args.component, args.exception)}
            if args.action == "failure":
                data = read_input(args.input)
                return engine.record_failure(
                    data["task_id"],
                    data["attempt_id"],
                    data["error"],
                    data["component"],
                    data["strategy"],
                )
        if command == "learning":
            if args.action == "status":
                return {
                    "counts": counts(store),
                    "global_auto_promotion": False,
                    "global_registry_modified": False,
                    "learning_enabled": config.learning_enabled,
                }
            if args.action == "candidates":
                return {
                    "candidates": store.list("candidates"),
                    "promotions": store.list("promotions"),
                }
            if args.action == "candidate":
                return engine._require("candidates", args.id)
            if args.action == "eval":
                return engine.evaluate(args.id, read_input(args.input))
            if args.action == "activate":
                return engine.activate(args.id)
            if args.action == "promotion":
                return engine.promotion_candidate(args.name)
            if args.action == "promote":
                return engine.promote(
                    args.id, approve=args.approve, cross_project_report=read_input(args.input)
                )
        if command == "skills":
            if args.action == "list":
                entries = registry.list()

                def category(entry):
                    return entry.get(
                        "category", "project" if entry.get("scope") == "project" else "coding"
                    )

                categories = sorted({category(entry) for entry in entries})
                if args.category is not None:
                    if args.category not in categories:
                        raise ErolError("Unknown category; available: " + ", ".join(categories))
                    entries = [entry for entry in entries if category(entry) == args.category]
                return {"skills": entries, "categories": categories, "bodies_loaded": False}
            if args.action == "search":
                return {"matches": registry.explain(args.query, config.max_active_skills)}
            if args.action == "disable":
                return engine.disable(args.name)
        if command == "skill":
            if args.action == "show":
                return registry.get(args.name).to_dict()
            if args.action == "metrics":
                return engine.metrics(args.name)
            if args.action == "export":
                return engine.export_skill(args.name)
            if args.action == "create":
                data = read_input(args.input)
                if data.get("name") != args.name:
                    raise ErolError("Draft name must match --name")
                if store.get("skills", args.name):
                    return engine.revise(args.name, data)
                return engine.create_skill(data)
            if args.action == "rollback":
                return engine.rollback(args.name, args.version)
            if args.action == "usage":
                report = read_input(args.input)
                if args.failed:
                    return engine.failed_task(args.task_id, report)
                return engine.complete_task(
                    args.task_id, report.get("verification", report), report.get("false_triggers")
                )
        if command in {"doctor", "eval", "lint"}:
            pack = qualify_pack(registry)
            if command == "eval":
                routing = routing_eval(registry)
                return {
                    "passed": pack["passed"] and routing["passed"],
                    "pack": pack,
                    "routing": routing,
                    "behavior_verified": False,
                }
            if command == "doctor":
                return {
                    "passed": pack["passed"],
                    "skills": pack,
                    "harnesses_found": {
                        name: shutil.which(name) is not None for name in ("codex", "claude")
                    },
                    "capabilities": capabilities(),
                    "memory_schema": 1,
                }
            metadata_chars = len(canonical(registry.list()))
            from erol.adapters import managed_instruction_block

            instruction_chars = len(managed_instruction_block("codex", store.home))
            return {
                "passed": pack["passed"] and instruction_chars < 1500,
                "always_loaded_instruction_chars": instruction_chars,
                "registry_metadata_chars": metadata_chars,
                "max_active_skills": config.max_active_skills,
                "context_estimate_budget": config.context_tokens,
                "metadata_always_injected": False,
                "estimator": "characters/4; not actual tokenizer usage",
            }
        if command == "benchmark":
            if args.suite:
                from .benchmark import behavioral_benchmark

                if not args.harness or not args.report:
                    raise ErolError("Behavioral suite requires --harness and --report")
                result = behavioral_benchmark(
                    Path(args.suite),
                    args.harness,
                    Path(args.report),
                    repeat=args.repeat,
                    trust=CheckTrust(store.directory, root),
                )
                from .work import WorkStore

                with WorkStore(store.directory, store.project_id) as work:
                    work.put(
                        "benchmarks",
                        {
                            "id": result["id"],
                            "project_id": store.project_id,
                            "kind": result["kind"],
                            "created": result["created"],
                            "harness": args.harness,
                            "passed": result["passed"],
                            "pairs": len(result["pairs"]),
                            "report": str(Path(args.report).resolve()),
                        },
                    )
                return result
            if not 1 <= args.iterations <= 10000:
                raise ErolError("Iterations must be between 1 and 10000")
            task = "RabbitMQ duplicate consumer at least once delivery"
            started = time.perf_counter()
            for _ in range(args.iterations):
                packet = Orchestrator(registry).plan(task, memory=store.search(task))
            elapsed = time.perf_counter() - started
            all_body_chars = sum(len(registry.get(m["name"]).body) for m in registry.list())
            return {
                "kind": "local_routing_proxy",
                "iterations": args.iterations,
                "mean_route_ms": elapsed * 1000 / args.iterations,
                "rendered_packet_chars": len(packet["context"]["text"]),
                "catalog_body_chars": all_body_chars,
                "loaded_skills": len(packet["context"]["selected_skills"]),
                "limits": (
                    "No vanilla harness execution, task success comparison, "
                    "real LLM token savings or resolution-time measurement"
                ),
            }
    raise ErolError("Unsupported command")


def main(argv: list[str] | None = None) -> int:
    # JSON pipes have a stable Unicode encoding even on Windows legacy locales.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command is None:
            if sys.stdin.isatty() and sys.stdout.isatty():
                from .console import launch

                return launch(Path(args.project), Path(args.home))
            parser().print_help()
            return 2
        if args.command in {"chat", "terminal"}:
            from .chat import ChatEngine
            from .console import command, launch
            from .general import GeneralEngine

            if args.command == "chat" and args.prompt is None:
                return launch(
                    Path(args.project),
                    Path(args.home),
                    model=args.model,
                    resume=args.resume,
                    mode=args.mode,
                )
            root, home = (
                Path(args.project).expanduser().resolve(),
                Path(args.home).expanduser().resolve(),
            )
            general = (
                (args.command == "chat" and args.mode != "auto")
                or root == home
                or root in home.parents
            )
            engine = GeneralEngine(root, home) if general else ChatEngine(root, home)
            if isinstance(engine, GeneralEngine) and args.command == "chat":
                engine.mode = "research" if args.mode == "research" else "general"
            if args.command == "terminal":
                result = command(engine, args.terminal_command)
                if result.get("select_general"):
                    if not isinstance(engine, GeneralEngine):
                        engine = GeneralEngine(root, home)
                    engine.mode = result["mode"]
                    if "general_task" in result:
                        result = engine.execute(result["general_task"])
            else:
                engine.selected_model = args.model
                if args.resume:
                    engine.resume(args.resume)
                if not args.prompt:
                    result = {"session": engine.session_id, "status": engine.record.get("status")}
                else:
                    result = engine.execute(args.prompt, resume=bool(args.resume))
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return (
                1
                if result.get("status") in {"needs_attention", "cancelled", "waiting_budget"}
                else 0
            )
        if args.command == "logo":
            import shutil

            from .terminal import render_logo

            width = (
                args.width
                if args.width is not None
                else min(80, max(8, shutil.get_terminal_size().columns - 1))
            )
            if not 8 <= width <= 160:
                raise ErolError("Logo width must be between 8 and 160 columns")
            color = args.color == "always" or (
                args.color == "auto"
                and sys.stdout.isatty()
                and "NO_COLOR" not in os.environ
                and os.environ.get("TERM") != "dumb"
            )
            print(render_logo(width, color=color))
            return 0
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        if result.get("passed") is False or result.get("status") == "conflict":
            return 1
        if (
            args.command == "run" or (args.command == "runs" and args.action == "resume")
        ) and result.get("status") != "completed":
            return 1
        return 0
    except (ErolError, ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        # Never echo a parsed payload or arbitrary exception message which may contain credentials.
        message = (
            str(exc)
            if isinstance(exc, ErolError)
            else (
                "Invalid input, unavailable resource or integrity failure; "
                "inspect the command help and local files"
            )
        )
        print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
