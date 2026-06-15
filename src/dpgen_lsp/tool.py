"""Agent-facing CLI for Diagnostic Engine v1 operations.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import argparse
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .agent_operations import operation_path, with_capabilities
from .features.cross_artifact import get_cross_artifact_diagnostics
from .features.log_parser import parse_log_path
from .rich_diagnostics import agent_check_payload, agent_project_check_payload
from .schema.official_rules import pipeline_steps, source_provenance
from .schema.versioning import dpgen_version_support_payload
from . import templates as templates_lib

SOFTWARE = "dpgen"


def _load_capability_manifest() -> dict[str, Any]:
    root_manifest = Path(__file__).resolve().parents[2] / "lsp-capabilities.json"
    if root_manifest.exists():
        return json.loads(root_manifest.read_text(encoding="utf-8"))
    resource = files("dpgen_lsp").joinpath("lsp-capabilities.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _capabilities_payload() -> dict[str, Any]:
    payload = _load_capability_manifest()
    payload["pipeline"] = pipeline_steps()
    payload.setdefault("sourceProvenance", source_provenance())
    payload["dpgenVersionSupport"] = dpgen_version_support_payload()
    return payload


def _file_type(path: Path) -> str:
    from .features.output_logs import is_output_log_path

    if is_output_log_path(path):
        return "log"
    name = path.name.upper()
    if "PARAM" in name or "MACHINE" in name:
        return "json"
    if "." in path.name:
        return path.suffix.lstrip(".").lower()
    return name.lower()


def _collect_diagnostics(path: Path) -> list[Any]:
    from .features.diagnostic import DiagnosticProvider
    from .features.output_logs import LogDiagnosticProvider, is_output_log_path

    text = path.read_text(encoding="utf-8")
    if is_output_log_path(path):
        return LogDiagnosticProvider().get_diagnostics(text, path.resolve().as_uri())
    base_dir = path.parent.resolve()
    return DiagnosticProvider().get_diagnostics(text, path.resolve().as_uri(), base_dir=base_dir)


def _find_project_configs(project_dir: Path) -> tuple[Path | None, Path | None]:
    param_path = None
    machine_path = None
    for candidate in sorted(project_dir.iterdir()):
        if not candidate.is_file() or candidate.suffix.lower() != ".json":
            continue
        name = candidate.name.lower()
        if name == "param.json" or ("param" in name and param_path is None):
            param_path = candidate
        elif name == "machine.json" or ("machine" in name and machine_path is None):
            machine_path = candidate
    return param_path, machine_path


def check_path(path: Path) -> dict[str, Any]:
    if path.is_dir():
        return check_project(path)

    uri = path.resolve().as_uri()
    diagnostics = _collect_diagnostics(path)
    return agent_check_payload(
        software=SOFTWARE,
        uri=uri,
        operation="check",
        diagnostics=diagnostics,
        path=str(path),
        file_type=_file_type(path),
    )


def check_project(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    param_path, machine_path = _find_project_configs(project_dir)
    file_entries: list[dict[str, Any]] = []
    param_data: dict[str, Any] | None = None
    machine_data: dict[str, Any] | None = None

    for config_path in (param_path, machine_path):
        if config_path is None:
            continue
        diagnostics = _collect_diagnostics(config_path)
        file_entries.append(
            {
                "path": str(config_path),
                "uri": config_path.resolve().as_uri(),
                "file_type": _file_type(config_path),
                "diagnostics": diagnostics,
            }
        )
        try:
            parsed = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            parsed = None
        if config_path == param_path and isinstance(parsed, dict):
            param_data = parsed
        if config_path == machine_path and isinstance(parsed, dict):
            machine_data = parsed

    cross_diagnostics: list[Any] = []
    if param_data is not None and machine_data is not None:
        cross_diagnostics = get_cross_artifact_diagnostics(param_data, machine_data)

    return agent_project_check_payload(
        software=SOFTWARE,
        project_dir=project_dir,
        operation="check",
        files=file_entries,
        cross_artifact_diagnostics=cross_diagnostics,
    )


def parse_log_file(path: Path) -> dict[str, Any]:
    diagnostics = parse_log_path(path)
    return agent_check_payload(
        software=SOFTWARE,
        uri=path.resolve().as_uri(),
        operation="parse_log",
        diagnostics=diagnostics,
        path=str(path.resolve()),
        file_type="log",
    )


def _operation_payload(
    path: Path,
    operation: str,
    line: int = 0,
    character: int = 0,
) -> dict[str, Any]:
    return operation_path(
        path,
        operation,
        software=SOFTWARE,
        file_type_func=_file_type,
        collect_diagnostics=_collect_diagnostics,
        line=line,
        character=character,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dpgen-lsp-tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    capabilities = subparsers.add_parser("capabilities")
    capabilities.add_argument("--format", choices=["json"], default="json")

    init = subparsers.add_parser("init", help="Initialize dpgen input file from template")
    init.add_argument("path", type=Path, nargs="?", help="Output file path")
    init.add_argument("--template", type=str, help="Template key name or file path")
    init.add_argument("--kind", type=str, choices=["param", "machine"], help="Template kind filter")
    init.add_argument("--list", action="store_true", help="List available templates and exit")
    init.add_argument("--force", action="store_true", help="Overwrite existing file")
    init.add_argument("--stdout", action="store_true", help="Print template content to stdout")
    init.add_argument("--format", choices=["json"], default="json")

    for operation in ("check", "context", "complete", "hover", "symbols", "fix", "parse-log"):
        sub = subparsers.add_parser(operation)
        sub.add_argument("path", type=Path)
        sub.add_argument("--format", choices=["json"], default="json")
        sub.add_argument(
            "--line",
            type=int,
            default=0,
            help="0-based line for position-aware operations.",
        )
        sub.add_argument(
            "--character",
            type=int,
            default=0,
            help="0-based character for position-aware operations.",
        )
        if operation == "check":
            sub.add_argument("--fail-on-blocking", action="store_true")
    args = parser.parse_args(argv)

    if args.operation == "capabilities":
        print(json.dumps(_capabilities_payload(), indent=2, sort_keys=True))
        return 0

    if args.operation == "init":
        import sys as _sys

        if args.list:
            templates = templates_lib.list_templates(args.kind)
            print(json.dumps({"templates": templates}, indent=2, ensure_ascii=False))
            return 0

        if args.stdout:
            if not args.template:
                print("Error: --template is required when using --stdout", file=_sys.stderr)
                return 1
            content = templates_lib.read_template(args.template, args.kind)
            if content is None:
                print(f"Error: template '{args.template}' not found", file=_sys.stderr)
                return 1
            print(content)
            return 0

        if not args.path:
            print("Error: path is required (or use --list or --stdout)", file=_sys.stderr)
            return 1

        if not args.template:
            print("Error: --template is required when writing to file", file=_sys.stderr)
            return 1

        result = templates_lib.write_template(args.template, args.path, args.kind, args.force)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("success") else 1

    if args.operation == "check":
        payload = with_capabilities(check_path(args.path), "check")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    if args.operation == "parse-log":
        payload = with_capabilities(parse_log_file(args.path), "parse-log")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    payload = _operation_payload(args.path, args.operation, args.line, args.character)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
