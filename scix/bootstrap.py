"""Bootstrap and doctor helpers for the repo-local scix workflow."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from .constants import REPO_CATALOG_PATH, REQUIRED_ROOT_PATHS, ROOT_MARKER
from .exceptions import CheckFailedError, ScixError

NVM_VERSION = "v0.40.4"
NVM_INSTALL_URL = f"https://raw.githubusercontent.com/nvm-sh/nvm/{NVM_VERSION}/install.sh"


@dataclass(frozen=True)
class AgentToolState:
    nvm_script: Path
    nvm_default_bin: Path | None
    codex_path: str | None
    claude_path: str | None

    @property
    def node_ready(self) -> bool:
        if self.nvm_default_bin is None:
            return False
        return (self.nvm_default_bin / "node").exists() and (self.nvm_default_bin / "npm").exists()

    @property
    def install_needed(self) -> bool:
        return bool(self.missing_components())

    def missing_components(self) -> list[str]:
        missing: list[str] = []
        if not self.nvm_script.exists():
            missing.append("nvm")
        if not self.node_ready:
            missing.extend(["node", "npm"])
        if self.codex_path is None:
            missing.append("codex")
        if self.claude_path is None:
            missing.append("claude")
        return missing


@dataclass(frozen=True)
class AgentInstallResult:
    install_needed: bool
    attempted: bool


def perform_up(
    target_root: Path,
    *,
    skip_repos: bool = False,
    check: bool = False,
) -> list[str]:
    target_root = target_root.resolve()
    _ensure_repo_checkout(target_root)
    return _finalize_workspace(
        target_root,
        skip_repos=skip_repos,
        check=check,
    )


def install_missing_repos(root: Path | None = None) -> list[Path]:
    root = _find_workspace_root(root)
    repo_map = _load_yaml(root / REPO_CATALOG_PATH)
    cloned: list[Path] = []
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        target = root / (spec.get("path") or f"repos/{repo_name}")
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", spec["clone_url"], str(target)], cwd=root)
        cloned.append(target)
    return cloned


def doctor(
    root: Path | None = None,
    *,
    suppress_agent_cli_issues: bool = False,
) -> list[str]:
    root = _find_workspace_root(root)

    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10

    BOLD = "\033[1m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RED = "\033[31m"
    RESET = "\033[0m"

    rule = f"{DIM}{'─' * width}{RESET}"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: list[str]) -> list[str]:
        padded_cmds = [f"  {command}  " for command in cmds]
        box_w = min(max(len(command) for command in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{command.ljust(box_w)}{RESET}│" for command in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    def issue(title: str, text: str | None = None, cmds: list[str] | None = None) -> list[str]:
        lines = [f"{RED}✗{RESET} {BOLD}{title}{RESET}"]
        if text:
            lines += wrap(text, indent=3)
        if cmds:
            lines += command_box(cmds)
        return lines

    report: list[str] = [
        rule,
        f"{BOLD}Workspace Doctor Report{RESET}".center(width),
        rule,
        "",
    ]
    issue_lines: list[str] = []

    if not (root / ROOT_MARKER).exists():
        issue_lines += issue(
            "Missing workspace marker",
            f"{ROOT_MARKER} not found in {root}",
        )

    for relative_path in REQUIRED_ROOT_PATHS:
        if not (root / relative_path).exists():
            issue_lines += issue(
                "Missing required file",
                f"{relative_path} not found in {root}",
            )

    for skill_path in sorted((root / "ai/skills").glob("*/SKILL.md")):
        if not _has_yaml_frontmatter(skill_path):
            issue_lines += issue(
                "Invalid skill file",
                f"{skill_path} missing required YAML frontmatter (---).",
            )

    if not suppress_agent_cli_issues and not _has_any_agent_cli():
        issue_lines += issue(
            "No agent CLI found",
            _agent_cli_install_message(),
            _agent_install_commands(include_codex=True, include_claude=True),
        )

    repo_map = _load_yaml(root / REPO_CATALOG_PATH)
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        repo_path = root / (spec.get("path") or f"repos/{repo_name}")
        if not repo_path.exists():
            issue_lines += issue(
                "Missing repo clone",
                f"{repo_name} expected at {repo_path}",
                [f"git clone {spec.get('clone_url', '<repo-url>')} {repo_path}"],
            )

    try:
        _sync_workspace(root, check=True)
    except CheckFailedError as exc:
        issue_lines += issue(
            "Generated files are stale",
            str(exc),
            ["python -m scix sync"],
        )

    if not issue_lines:
        return []

    report.extend(issue_lines)
    report.append(rule)
    return report


def up_guidance(root: Path | None = None) -> list[str]:
    root = _find_workspace_root(root)

    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10

    BOLD = "\033[1m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    rule = f"{DIM}{'─' * width}{RESET}"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: list[str]) -> list[str]:
        padded_cmds = [f"  {command}  " for command in cmds]
        box_w = min(max(len(command) for command in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{command.ljust(box_w)}{RESET}│" for command in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    def step(title: str, text: str | None = None, cmds: list[str] | None = None) -> list[str]:
        lines = [f"{GREEN}✓{RESET} {BOLD}{title}{RESET}"]
        if text:
            lines += wrap(text, indent=3)
        if cmds:
            lines += command_box(cmds)
        return lines

    notes: list[str] = [
        rule,
        f"{BOLD}Workspace Setup Guidance{RESET}".center(width),
        rule,
        "",
    ]

    notes += step(
        "1. Review your editable inputs",
        "The main files to customize are repos.yaml and requirements.txt.",
        ["open repos.yaml", "open requirements.txt"],
    )
    notes += step(
        "2. Verify generated files stay aligned",
        None,
        ["python -m scix sync --check", "python -m scix doctor"],
    )
    notes += step(
        "3. Start an agent session",
        None,
        ["source xenv/bin/activate", "codex", "claude"],
    )

    notes.append(rule)

    if not _has_any_agent_cli():
        notes.append(f"{YELLOW}!{RESET} {BOLD}No agent CLI detected{RESET}")
        notes += wrap(_agent_cli_install_message(), indent=3)
    if _is_ssh_session():
        notes.append(f"{YELLOW}!{RESET} {BOLD}SSH session detected{RESET}")
        notes += wrap(
            "Enable device code authorization in ChatGPT Security Settings.",
            indent=3,
        )
        notes += command_box(["codex login --device-auth"])

    return notes


def _ensure_repo_checkout(target_root: Path) -> None:
    missing = [path for path in REQUIRED_ROOT_PATHS if not (target_root / path).exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise ScixError(
            f"python -m scix expects to run from the scix-hub repo root. Missing: {joined}"
        )


def _finalize_workspace(
    root: Path,
    *,
    skip_repos: bool,
    check: bool,
) -> list[str]:
    changed = [str(path) for path in _sync_workspace(root)]
    if not skip_repos:
        cloned = install_missing_repos(root)
        changed.extend(str(path) for path in cloned)
        changed.extend(str(path) for path in _sync_workspace(root))
    install_result = _ensure_agent_clis()
    if check:
        issues = doctor(root, suppress_agent_cli_issues=install_result.install_needed)
        if issues:
            raise ScixError("\n".join(issues))
    return changed


def _find_workspace_root(start: Path | None = None) -> Path:
    try:
        from .generator import find_workspace_root
    except ModuleNotFoundError as exc:
        raise _dependency_error(exc) from exc
    return find_workspace_root(start)


def _load_yaml(path: Path) -> dict:
    try:
        from .generator import load_yaml
    except ModuleNotFoundError as exc:
        raise _dependency_error(exc) from exc
    return load_yaml(path)


def _sync_workspace(root: Path, check: bool = False) -> list[Path]:
    try:
        from .generator import sync_workspace
    except ModuleNotFoundError as exc:
        raise _dependency_error(exc) from exc
    return sync_workspace(root, check=check)


def _dependency_error(exc: ModuleNotFoundError) -> ScixError:
    if exc.name == "yaml":
        return ScixError(
            "Missing dependency 'PyYAML'. Activate your virtual environment and run "
            "`python -m pip install -r requirements.txt`."
        )
    return ScixError(
        f"Missing dependency '{exc.name}'. Activate your virtual environment and install "
        "repo requirements."
    )


def _agent_cli_install_message() -> str:
    return (
        "Neither Codex nor Claude is on PATH. `python -m scix up` tries to install nvm, "
        "user-local Node.js/npm, Codex, and Claude automatically. If the commands are still "
        "missing afterwards, rerun the install commands below and then authenticate the CLIs."
    )


def _has_yaml_frontmatter(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    return any(line.strip() == "---" for line in lines[1:])


def _is_ssh_session() -> bool:
    return any(os.environ.get(name) for name in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"))


def _has_any_agent_cli() -> bool:
    return shutil.which("codex") is not None or shutil.which("claude") is not None


def _ensure_agent_clis() -> AgentInstallResult:
    state = _detect_agent_tool_state()
    if not state.install_needed:
        return AgentInstallResult(install_needed=False, attempted=False)

    bash_path = shutil.which("bash")
    curl_path = shutil.which("curl")
    missing_prereqs = [
        name for name, path in (("bash", bash_path), ("curl", curl_path)) if path is None
    ]
    if missing_prereqs:
        _print_agent_install_warning(
            f"Missing prerequisite command(s): {', '.join(sorted(missing_prereqs))}.",
        )
        return AgentInstallResult(install_needed=True, attempted=False)

    print("Installing nvm, user-local Node.js/npm, Codex CLI, and Claude Code CLI...")
    try:
        subprocess.run(
            [bash_path, "-lc", _agent_install_script(state)],
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        _prepend_nvm_default_bin_to_path()
        _print_agent_install_warning(
            f"Automatic install command failed with exit code {exc.returncode}.",
        )
        return AgentInstallResult(install_needed=True, attempted=True)

    _prepend_nvm_default_bin_to_path()
    remaining = _detect_agent_tool_state().missing_components()
    if remaining:
        _print_agent_install_warning(
            "Automatic install finished, but these commands are still missing: "
            f"{', '.join(remaining)}.",
        )
    return AgentInstallResult(install_needed=True, attempted=True)


def _detect_agent_tool_state() -> AgentToolState:
    nvm_script = _nvm_script_path()
    nvm_default_bin = _prepend_nvm_default_bin_to_path(nvm_script)
    if nvm_default_bin is None:
        nvm_default_bin = _resolve_nvm_default_bin_dir(nvm_script)
    return AgentToolState(
        nvm_script=nvm_script,
        nvm_default_bin=nvm_default_bin,
        codex_path=shutil.which("codex"),
        claude_path=shutil.which("claude"),
    )


def _agent_install_commands(
    *,
    include_codex: bool = False,
    include_claude: bool = False,
) -> list[str]:
    commands = [
        f"curl -o- {NVM_INSTALL_URL} | bash",
        'export NVM_DIR="$HOME/.nvm"',
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
        "nvm install --lts",
        "nvm use --lts",
        "nvm alias default lts/*",
    ]
    if include_codex:
        commands.append("npm install -g @openai/codex")
    if include_claude:
        commands.append("npm install -g @anthropic-ai/claude-code")
    return commands


def _agent_install_script(state: AgentToolState) -> str:
    lines: list[str] = []
    if not state.nvm_script.exists():
        lines.append(f"curl -o- {shlex.quote(NVM_INSTALL_URL)} | bash")
    lines.append(f"export NVM_DIR={shlex.quote(str(state.nvm_script.parent))}")
    lines.append('[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"')
    if not state.node_ready:
        lines.extend(
            [
                "nvm install --lts",
                "nvm use --lts",
                "nvm alias default lts/*",
            ]
        )
    if state.codex_path is None:
        lines.append("npm install -g @openai/codex")
    if state.claude_path is None:
        lines.append("npm install -g @anthropic-ai/claude-code")
    return "\n".join(lines)


def _print_agent_install_warning(reason: str) -> None:
    print("")
    print(
        "Warning: scix could not finish installing nvm, user-local Node.js/npm, Codex CLI, "
        "and Claude Code CLI automatically."
    )
    print(f"Reason: {reason}")
    print("Run these commands manually:")
    for command in _agent_install_commands(include_codex=True, include_claude=True):
        print(f"  {command}")
    print("If the commands are still missing afterwards, open a new shell or run:")
    print('  export NVM_DIR="$HOME/.nvm"')
    print('  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"')


def _nvm_script_path() -> Path:
    configured = os.environ.get("NVM_DIR")
    if configured:
        return Path(configured).expanduser() / "nvm.sh"
    return Path.home() / ".nvm" / "nvm.sh"


def _prepend_nvm_default_bin_to_path(nvm_script: Path | None = None) -> Path | None:
    bin_dir = _resolve_nvm_default_bin_dir(nvm_script)
    if bin_dir is None:
        return None
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    bin_str = str(bin_dir)
    if bin_str not in path_parts:
        os.environ["PATH"] = f"{bin_str}{os.pathsep}{current_path}" if current_path else bin_str
    return bin_dir


def _resolve_nvm_default_bin_dir(nvm_script: Path | None = None) -> Path | None:
    nvm_script = nvm_script or _nvm_script_path()
    bash_path = shutil.which("bash")
    if bash_path is None or not nvm_script.exists():
        return None
    command = "\n".join(
        [
            f"export NVM_DIR={shlex.quote(str(nvm_script.parent))}",
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
            "nvm which default",
        ]
    )
    result = subprocess.run(
        [bash_path, "-lc", command],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    node_path = result.stdout.strip()
    if not node_path or node_path == "N/A":
        return None
    resolved = Path(node_path).expanduser()
    if resolved.name != "node":
        return None
    return resolved.parent


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ScixError(f"Command failed: {' '.join(cmd)}") from exc
