"""Shared constants for the repo-local scix runtime."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "scix"
ROOT_MARKER = ".ai-root"
REPO_CATALOG_PATH = Path("repos.yaml")
GENERATED_REPO_POLICY_PATH = Path("ai/policy/repos.yaml")
REQUIRED_ROOT_PATHS = [
    REPO_CATALOG_PATH,
    Path("requirements.txt"),
    Path("ai/policy/workspace.md"),
    Path("ai/policy/rules.md"),
    Path("ai/policy/commands.md"),
    Path("ai/agents/roles.yaml"),
    Path("repos/README.md"),
    Path("workspace/README.md"),
    Path("scix/cli.py"),
]
