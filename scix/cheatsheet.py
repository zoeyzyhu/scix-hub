"""Curated workflow cheat-sheet content shared by the CLI and docs."""

from __future__ import annotations

import shutil
import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowSet:
    title: str
    note: str
    commands: tuple[str, ...]


WORKFLOW_SETS: tuple[WorkflowSet, ...] = (
    WorkflowSet(
        title="scix CLI help",
        note="Use this command to see available repo-local scix commands.",
        commands=("python -m scix --help",),
    ),
    WorkflowSet(
        title="Bootstrap this repo",
        note="Use this after forking or cloning scix-hub and editing repos.yaml.",
        commands=(
            "python3 -m venv xenv",
            "source xenv/bin/activate",
            "python -m pip install --upgrade pip",
            "python -m pip install -r requirements.txt",
            "make up",
        ),
    ),
    WorkflowSet(
        title="Refresh generated files",
        note="Use this after changing repos.yaml or editable files under ai/.",
        commands=("make sync", "make sync-check"),
    ),
    WorkflowSet(
        title="Clone configured repos",
        note="Use this when one or more repos declared in repos.yaml are still missing.",
        commands=("make install-repos",),
    ),
    WorkflowSet(
        title="Agent CLI fallback setup",
        note="Use this if scix could not finish installing nvm, Codex CLI, or Claude Code.",
        commands=(
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash",
            'export NVM_DIR="$HOME/.nvm"',
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
            "nvm install --lts",
            "nvm use --lts",
            "nvm alias default lts/*",
            "npm install -g @openai/codex",
            "npm install -g @anthropic-ai/claude-code",
        ),
    ),
    WorkflowSet(
        title="Authenticate Codex",
        note="Use ONE of these commands when Codex CLI is installed but not logged in yet.",
        commands=(
            "codex login",
            "codex login --device-auth",
            "printenv OPENAI_API_KEY | codex login --with-api-key",
        ),
    ),
    WorkflowSet(
        title="Authenticate Claude",
        note="Use ONE of these commands when Claude Code is installed but not authenticated yet.",
        commands=("claude auth login", "claude setup-token"),
    ),
    WorkflowSet(
        title="Maintenance workflow",
        note="Use these before pushing changes to keep the repo and generated files aligned.",
        commands=("make ci",),
    ),
)


def render_cheat_sheet_text() -> str:
    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10

    BOLD = "\033[1m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: tuple[str, ...]) -> list[str]:
        padded_cmds = [f"  {command}  " for command in cmds]
        box_w = min(max(len(command) for command in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{command.ljust(box_w)}{RESET}│" for command in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    lines = []
    for index, workflow in enumerate(WORKFLOW_SETS):
        lines.append(f"{BOLD}{workflow.title}{RESET}")
        lines.extend(wrap(workflow.note, indent=2))
        lines.append("")
        lines.extend(command_box(workflow.commands))
        if index != len(WORKFLOW_SETS) - 1:
            lines.append("")
            lines.append("")
    return "\n".join(lines) + "\n"
