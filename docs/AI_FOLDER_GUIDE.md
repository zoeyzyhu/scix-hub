# Maintaining `/ai`

This document is for people who change the shared agent behavior inside the `scix-hub` repo.

## Canonical Inputs

Editable sources live in these places:

- `repos.yaml`
- `ai/agents/roles.yaml`
- `ai/policy/*.md`
- `ai/skills/*/SKILL.md`
- `ai/hooks/*.sh`

Generated outputs live in these places:

- `ai/policy/repos.yaml`
- `AGENTS.md`
- `CLAUDE.md`
- `.codex/*`
- `.claude/*`
- `.agents/skills/*`
- `ai/generated/repos/*`

Do not hand-edit generated files unless you are debugging the generator.

## What `repos.yaml` Controls

`repos.yaml` is the human-facing source of truth for the repo catalog. It tells agents and bootstrap commands:

- which repos should be cloned
- where they should live under `repos/`
- which repo owns which concept
- when a repo should be consulted first
- any extra notes that should appear in generated overlays

`make sync` turns `repos.yaml` into the generated `ai/policy/repos.yaml` file and updates all other derived outputs.

## Safe Workflow

1. Edit the canonical file you actually mean to change.
2. Run:

   ```bash
   make sync
   ```

3. Inspect the generated diff.
4. Run:

   ```bash
   make ci
   ```

## Important Cautions

- Skills must keep valid YAML frontmatter.
- Hooks are executable code. Keep them small, explicit, and portable.
- Repo routing changes can point agents at the wrong repo. Keep `owns` and
  `consult_when` precise.
- Never put secrets into prompts, hooks, or examples.
