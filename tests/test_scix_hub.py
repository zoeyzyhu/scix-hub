from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import scix.bootstrap as bootstrap
from scix.bootstrap import doctor, install_missing_repos
from scix.generator import sync_workspace

REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _seed_checkout(tmp_path: Path) -> Path:
    seed_paths = [
        Path(".ai-root"),
        Path(".gitignore"),
        Path(".pre-commit-config.yaml"),
        Path("LICENSE"),
        Path("README.md"),
        Path("Makefile"),
        Path("requirements.txt"),
        Path("repos.yaml"),
        Path("docs"),
        Path("ai"),
        Path("repos"),
        Path("workspace"),
        Path("scix"),
    ]
    for relative_path in seed_paths:
        _copy_path(REPO_ROOT / relative_path, tmp_path / relative_path)
    generated_repo_policy = tmp_path / "ai/policy/repos.yaml"
    if generated_repo_policy.exists():
        generated_repo_policy.unlink()
    return tmp_path


def test_make_sync_runs_in_source_checkout(tmp_path: Path) -> None:
    checkout = _seed_checkout(tmp_path)

    result = subprocess.run(
        ["make", "sync"],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "python -m scix sync updated" in result.stdout
    assert (checkout / "AGENTS.md").exists()
    assert (checkout / "ai/policy/repos.yaml").exists()


def test_sync_workspace_uses_top_level_repo_catalog(tmp_path: Path) -> None:
    checkout = _seed_checkout(tmp_path)
    (checkout / "repos.yaml").write_text(
        "\n".join(
            [
                "workspace_name: scix-hub",
                'python_version: "3.11"',
                "repos:",
                "  sample:",
                "    path: repos/sample",
                "    clone_url: https://github.com/example/sample.git",
                "    pip_package: sample",
                "    owns:",
                "      - sample-domain",
                "    consult_when:",
                "      - tasks involving sample-domain",
                "",
            ]
        ),
        encoding="utf-8",
    )

    changed = sync_workspace(checkout)

    assert changed
    generated_policy = (checkout / "ai/policy/repos.yaml").read_text(encoding="utf-8")
    assert "sample-domain" in generated_policy
    assert (checkout / "ai/generated/repos/sample/AGENTS.md").exists()
    assert (checkout / "ai/generated/repos/sample/CLAUDE.md").exists()
    assert "sample-domain" in (checkout / "AGENTS.md").read_text(encoding="utf-8")


def test_default_template_is_repo_neutral(tmp_path: Path) -> None:
    checkout = _seed_checkout(tmp_path)

    sync_workspace(checkout)

    requirements = (checkout / "requirements.txt").read_text(encoding="utf-8")
    assert "paddle" not in requirements
    assert "scix\n" not in requirements
    assert not (checkout / "ai/skills/disort").exists()
    assert not (checkout / "ai/skills/thermodynamics").exists()
    assert not (checkout / "ai/skills/paddle-examples").exists()
    generated_repo_paths = sorted(
        path.relative_to(checkout / "ai/generated/repos")
        for path in (checkout / "ai/generated/repos").rglob("*")
        if path.is_file()
    )
    assert generated_repo_paths == [Path(".gitkeep")]


def test_doctor_reports_expected_issues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout = _seed_checkout(tmp_path)
    sync_workspace(checkout)

    (checkout / "ai/skills/repo-router/SKILL.md").write_text("# broken\n", encoding="utf-8")
    (checkout / "repos.yaml").write_text(
        "\n".join(
            [
                "workspace_name: scix-hub",
                'python_version: "3.11"',
                "repos:",
                "  missing-repo:",
                "    path: repos/missing-repo",
                "    clone_url: https://github.com/example/missing.git",
                "    pip_package: missing-repo",
                "    owns:",
                "      - missing-domain",
                "    consult_when:",
                "      - missing tasks",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bootstrap, "_has_any_agent_cli", lambda: False)

    issues = doctor(checkout)

    assert any("Invalid skill file" in issue for issue in issues)
    assert any("No agent CLI found" in issue for issue in issues)
    assert any("Missing repo clone" in issue for issue in issues)
    assert any("Generated files are stale" in issue for issue in issues)


def test_install_missing_repos_only_clones_declared_repos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = _seed_checkout(tmp_path)
    (checkout / "repos.yaml").write_text(
        "\n".join(
            [
                "workspace_name: scix-hub",
                'python_version: "3.11"',
                "repos:",
                "  existing:",
                "    path: repos/existing",
                "    clone_url: https://github.com/example/existing.git",
                "    pip_package: existing",
                "    owns:",
                "      - existing-domain",
                "    consult_when:",
                "      - existing tasks",
                "  missing:",
                "    path: repos/missing",
                "    clone_url: https://github.com/example/missing.git",
                "    pip_package: missing",
                "    owns:",
                "      - missing-domain",
                "    consult_when:",
                "      - missing tasks",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (checkout / "repos/existing").mkdir(parents=True)
    sync_workspace(checkout)

    commands: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, check: bool = False, **_: object) -> None:
        del cwd, check
        commands.append(cmd)

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    cloned = install_missing_repos(checkout)

    assert cloned == [checkout / "repos/missing"]
    assert commands == [
        ["git", "clone", "https://github.com/example/missing.git", str(checkout / "repos/missing")]
    ]
