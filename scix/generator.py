"""Generation helpers for Codex and Claude workspace files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from .constants import (
    GENERATED_REPO_POLICY_PATH,
    REPO_CATALOG_PATH,
    REQUIRED_ROOT_PATHS,
    ROOT_MARKER,
)
from .exceptions import CheckFailedError, ScixError

AUTO_GEN_HEADER = "<!-- AUTO-GENERATED FILE. EDIT repos.yaml OR ai/* INSTEAD. -->"
GENERATED_REPO_POLICY_HEADER = "# AUTO-GENERATED FILE. EDIT /repos.yaml INSTEAD.\n"


def find_workspace_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ROOT_MARKER).exists():
            return candidate
    raise ScixError(f"Could not find {ROOT_MARKER} from {current}")


def ensure_workspace_shape(root: Path) -> None:
    missing = [path for path in REQUIRED_ROOT_PATHS if not (root / path).exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise ScixError(f"Workspace is missing required files: {joined}")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ScixError(f"Expected a mapping in {path}")
    return data


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def sync_workspace(root: Path | None = None, check: bool = False) -> list[Path]:
    root = find_workspace_root(root)
    ensure_workspace_shape(root)

    changed: list[Path] = []

    repo_map = _normalized_repo_map(load_yaml(root / REPO_CATALOG_PATH))
    roles = load_yaml(root / "ai/agents/roles.yaml").get("roles", {})
    workspace_md = read_text(root / "ai/policy/workspace.md")
    rules_md = read_text(root / "ai/policy/rules.md")
    commands_md = read_text(root / "ai/policy/commands.md")
    skills_dir = root / "ai/skills"
    skills = sorted(path.name for path in skills_dir.iterdir() if path.is_dir())

    _write_or_check(
        root / GENERATED_REPO_POLICY_PATH,
        render_repo_policy(repo_map),
        changed,
        check,
    )
    _write_or_check(
        root / "AGENTS.md",
        render_workspace_doc(
            tool_name="Codex",
            title="AGENTS.md",
            workspace_md=workspace_md,
            rules_md=rules_md,
            commands_md=commands_md,
            repo_map=repo_map,
            skills=skills,
        ),
        changed,
        check,
    )
    _write_or_check(
        root / "CLAUDE.md",
        render_workspace_doc(
            tool_name="Claude",
            title="CLAUDE.md",
            workspace_md=workspace_md,
            rules_md=rules_md,
            commands_md=commands_md,
            repo_map=repo_map,
            skills=skills,
        ),
        changed,
        check,
    )
    _write_or_check(root / ".codex/config.toml", render_codex_config(), changed, check)
    _write_or_check(root / ".claude/settings.json", render_claude_settings(), changed, check)

    _sync_text_tree(skills_dir, root / ".agents/skills", changed, check)
    _sync_text_tree(skills_dir, root / ".claude/skills", changed, check)
    _sync_role_files(root / ".codex/agents", roles, render_codex_agent, ".toml", changed, check)
    _sync_role_files(root / ".claude/agents", roles, render_claude_agent, ".md", changed, check)
    _sync_repo_overlays(root, repo_map, changed, check)
    return changed


def render_repo_policy(repo_map: dict) -> str:
    return GENERATED_REPO_POLICY_HEADER + yaml.safe_dump(
        repo_map,
        sort_keys=False,
        default_flow_style=False,
    )


def render_workspace_doc(
    *,
    tool_name: str,
    title: str,
    workspace_md: str,
    rules_md: str,
    commands_md: str,
    repo_map: dict,
    skills: list[str],
) -> str:
    repos = repo_map.get("repos") or {}
    lines = [
        AUTO_GEN_HEADER,
        f"# {title}",
        "",
        f"This file is generated for {tool_name}.",
        "",
        "## Workspace Purpose",
        workspace_md,
        "",
        "## Hard Rules",
        rules_md,
        "",
        "## Repo Routing",
    ]
    if repos:
        for repo_name, spec in sorted(repos.items()):
            owns = ", ".join(spec.get("owns") or [])
            path = spec.get("path", f"repos/{repo_name}")
            lines.append(f"- `{repo_name}` at `{path}` owns: {owns}")
            for hint in spec.get("consult_when") or []:
                lines.append(f"  consult when: {hint}")
    else:
        lines.append(
            "- No repos are configured yet. Edit `repos.yaml` and rerun `python -m scix sync`."
        )
    lines.extend(
        [
            "",
            "## Common Commands",
            commands_md,
            "",
            "## Shared Skills",
        ]
    )
    for skill in skills:
        lines.append(f"- `{skill}`")
    return "\n".join(lines).strip() + "\n"


def render_repo_overlay(repo_name: str, spec: dict, *, tool_name: str) -> str:
    owns = spec.get("owns") or []
    consult = spec.get("consult_when") or []
    notes = spec.get("notes") or []
    lines = [
        AUTO_GEN_HEADER,
        f"# Repo Policy: {repo_name}",
        "",
        f"This file is generated for {tool_name}.",
        "",
        "## This Repo Owns",
    ]
    for item in owns:
        lines.append(f"- {item}")
    lines.extend(["", "## Inspect This Repo First When"])
    for item in consult:
        lines.append(f"- {item}")
    if notes:
        lines.extend(["", "## Notes"])
        for item in notes:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Guardrails",
            "- Modify this repo only when it is the primary repo for the task.",
            "- Read neighboring tests and examples before making changes.",
            (
                "- For behavior changes, add or update tests when feasible, run "
                "the relevant validation command, and explain if no automated "
                "test was possible."
            ),
            "- Summaries must include the exact validation command and result.",
            "- Report cross-repo compatibility risks in your summary.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_codex_config() -> str:
    return (
        'model = "gpt-5.4"\n'
        'approval_policy = "on-request"\n'
        'sandbox_mode = "workspace-write"\n'
        'project_root_markers = [".ai-root", ".git"]\n'
        "project_doc_max_bytes = 65536\n"
    )


def render_claude_settings() -> str:
    payload = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "./ai/hooks/pre_tool_guard.sh"}],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [{"type": "command", "command": "./ai/hooks/post_edit_format.sh"}],
                }
            ],
            "Stop": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": "./ai/hooks/session_context.sh"}],
                }
            ],
        }
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_codex_agent(role_name: str, spec: dict) -> str:
    description = spec.get("purpose", "")
    tools = spec.get("tools") or []
    sandbox = spec.get("sandbox", "workspace-write")
    model_hint = spec.get("model_hint", "default")
    prompt = spec.get("prompt", "")
    tools_list = ", ".join(f'"{item}"' for item in tools)
    return (
        f'description = "{description}"\n'
        f'sandbox_mode = "{sandbox}"\n'
        f'model_hint = "{model_hint}"\n'
        f"tools = [{tools_list}]\n"
        'prompt = """\n'
        f"{prompt}\n"
        '"""\n'
    )


def render_claude_agent(role_name: str, spec: dict) -> str:
    tools = ", ".join(spec.get("tools") or [])
    description = spec.get("purpose", "")
    prompt = (spec.get("prompt") or "").strip()
    return f"---\nname: {role_name}\ndescription: {description}\ntools: {tools}\n---\n\n{prompt}\n"


def _normalized_repo_map(repo_map: dict) -> dict:
    return {
        "workspace_name": repo_map.get("workspace_name", "scix-hub"),
        "python_version": str(repo_map.get("python_version", "3.11")),
        "repos": repo_map.get("repos") or {},
    }


def _sync_text_tree(source_dir: Path, target_dir: Path, changed: list[Path], check: bool) -> None:
    source_files = sorted(path for path in source_dir.rglob("*") if path.is_file())
    target_files = {
        path.relative_to(target_dir): path for path in target_dir.rglob("*") if path.is_file()
    }

    for source_path in source_files:
        relative_path = source_path.relative_to(source_dir)
        _write_or_check(
            target_dir / relative_path,
            source_path.read_text(encoding="utf-8"),
            changed,
            check,
        )
        target_files.pop(relative_path, None)

    for extra_path in sorted(target_files.values()):
        _remove_or_check(extra_path, changed, check)
    _prune_empty_dirs(target_dir)


def _sync_role_files(
    target_dir: Path,
    roles: dict,
    renderer,
    suffix: str,
    changed: list[Path],
    check: bool,
) -> None:
    expected: dict[Path, str] = {}
    for role_name, spec in sorted(roles.items()):
        expected[Path(f"{role_name}{suffix}")] = renderer(role_name, spec)

    existing = {
        path.relative_to(target_dir): path
        for path in target_dir.rglob(f"*{suffix}")
        if path.is_file()
    }
    for relative_path, content in expected.items():
        _write_or_check(target_dir / relative_path, content, changed, check)
        existing.pop(relative_path, None)
    for extra_path in sorted(existing.values()):
        _remove_or_check(extra_path, changed, check)
    _prune_empty_dirs(target_dir)


def _sync_repo_overlays(root: Path, repo_map: dict, changed: list[Path], check: bool) -> None:
    overlay_root = root / "ai/generated/repos"
    expected = {Path(".gitkeep"): ""}
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        overlay_dir = Path(repo_name)
        agents_text = render_repo_overlay(repo_name, spec, tool_name="Codex")
        claude_text = render_repo_overlay(repo_name, spec, tool_name="Claude")
        expected[overlay_dir / "AGENTS.md"] = agents_text
        expected[overlay_dir / "CLAUDE.md"] = claude_text

        repo_root = root / (spec.get("path") or f"repos/{repo_name}")
        if repo_root.exists() and repo_root.is_dir():
            _write_or_check(repo_root / "AGENTS.md", agents_text, changed, check)
            _write_or_check(repo_root / "CLAUDE.md", claude_text, changed, check)

    existing = {
        path.relative_to(overlay_root): path for path in overlay_root.rglob("*") if path.is_file()
    }
    for relative_path, content in expected.items():
        _write_or_check(overlay_root / relative_path, content, changed, check)
        existing.pop(relative_path, None)
    for extra_path in sorted(existing.values()):
        _remove_or_check(extra_path, changed, check)
    _prune_empty_dirs(overlay_root)


def _prune_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    directories = sorted(
        (candidate for candidate in root.rglob("*") if candidate.is_dir()),
        reverse=True,
    )
    for path in directories:
        if not any(path.iterdir()):
            path.rmdir()


def _remove_or_check(path: Path, changed: list[Path], check: bool) -> None:
    if check:
        raise CheckFailedError(f"Generated file is stale or missing: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    changed.append(path)


def _write_or_check(path: Path, content: str, changed: list[Path], check: bool) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return
    if check:
        raise CheckFailedError(f"Generated file is stale or missing: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if path.suffix == ".sh":
        path.chmod(0o755)
    changed.append(path)
