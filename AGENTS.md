<!-- AUTO-GENERATED FILE. EDIT repos.yaml OR ai/* INSTEAD. -->
# AGENTS.md

This file is generated for Codex.

## Workspace Purpose
This workspace coordinates multiple repositories through one shared repo
catalog, one shared AI canon, and one local bootstrap workflow. For every task,
identify the primary repo to modify, the reference repos to read, and the
cross-repo compatibility risks before making changes.

## Hard Rules
- Modify only the primary repo unless the task explicitly requires coordinated edits.
- Read tests, examples, and neighboring code before implementation.
- Implementation work follows `implementer -> tester -> reviewer`.
- Add or update tests when a change affects behavior and automated coverage is feasible.
- Run the relevant test or validation command before finalizing.
- If tests fail, fix the issue and rerun before finalizing.
- If no automated test is feasible, say why and run the closest available validation step.
- Do not duplicate source-of-truth logic across repos.
- If a user message starts with `203 /learn`, hand off to `student`. Treat it
  as a prefix trigger, so extra instructions may follow after `203 /learn`.
- Summaries must mention which reference repos were consulted.
- Summaries for implementation work must include the exact validation command and result.

## Repo Routing
- No repos are configured yet. Edit `repos.yaml` and rerun `python -m scix sync`.

## Common Commands
- `pytest`: preferred default test entry point when a repo already uses pytest.
- `python -m pip install -r requirements.txt`: preferred setup command for this repo.
- `make sync`: regenerate generated files after editing `repos.yaml` or `ai/`.
- `make sync-check`: fail if generated files are stale.
- `make doctor`: validate this checkout, including CLI tools, skill frontmatter, repo clones, and generated drift.
- `pre-commit run --all-files`: preferred contributor-wide formatting and lint check.
- When a repo has its own documented commands, prefer that repo's README or test config.
- For implementation work, record the exact test or validation command that was run.

## Shared Skills
- `cross-repo-read`
- `repo-router`
- `tutorial-style`
