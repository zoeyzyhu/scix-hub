# Maintaining `/ai`

This document is for contributors who change the shared agent behavior in the `scix-hub` repository.

## What `/ai` is

The repo-root `ai/` directory is the canonical source for shared agent behavior. It defines how Codex and Claude should reason about this workspace, route tasks across repos, load reusable skills, and apply shell hooks.

In practice, an "AI agent" in this repo is not just a model name. It is the combination of:

- prompt and policy text
- tool access and tool restrictions
- repo-routing rules
- reusable skills
- subagent or role definitions
- hook scripts that run before or after tool actions
- generated tool-specific wrapper files

Changing `ai/` changes behavior, not just documentation.

## The mechanisms in `scix-hub`

The main layers are:

- `repos.yaml`
  - The editable repo map.
  - This tells agents which repo owns which domain, when to inspect a repo, and which clone URL or package name goes with it.
- `ai/policy/*.md`
  - Shared workspace purpose, rules, and common command guidance.
  - These feed the generated root `AGENTS.md` and `CLAUDE.md`.
- `ai/policy/repos.yaml`
  - The generated repo map.
  - This is derived from `repos.yaml` and should not be hand-edited.
- `ai/agents/roles.yaml`
  - Canonical role definitions.
  - These generate `.codex/agents/*.toml` and `.claude/agents/*.md`.
  - This includes the `implementer`, `tester`, and `reviewer` collaboration flow for implementation work, plus `student` for lesson capture.
- `ai/skills/*/SKILL.md`
  - Reusable local instructions for focused workflows.
  - These are mirrored into `.agents/skills/` and `.claude/skills/`.
- `ai/hooks/*.sh`
  - Executable shell hooks.
  - These are called by tool integrations such as Claude settings.
- `ai/generated/repos/*`
  - Generated repo-local overlays.
  - These become `AGENTS.md` and `CLAUDE.md` inside cloned repos when present.

The generator lives in `scix/generator.py`. `make sync` is the command that turns the canonical sources into generated files.

## The repo-local model

The canonical checkout:

- repo-root `repos.yaml`
- repo-root `ai/`
- generated files at repo root, under `.codex/`, `.claude/`, `.agents/`, and `ai/generated/repos/*`

The workflow is simple:

- edit the canonical repo-root files
- run `make sync`
- inspect the generated diff


## Safe change workflow

When you want to change agent behavior:

1. Decide which layer you actually need to change.
   - Routing issue: edit `repos.yaml`.
   - Shared instruction issue: edit `ai/policy/*.md`.
   - Specialized workflow issue: edit `ai/skills/*/SKILL.md`.
   - Tool-role issue: edit `ai/agents/roles.yaml`.
   - Runtime shell behavior issue: edit `ai/hooks/*.sh`.
2. Edit the repo-root canonical files first.
3. Regenerate generated files:

```bash
make sync
```

4. Inspect the diff. In a normal checkout, you should usually see generated updates in one or more of:

- `AGENTS.md`
- `CLAUDE.md`
- `.codex/*`
- `.claude/*`
- `.agents/skills/*`
- `ai/policy/repos.yaml`
- `ai/generated/repos/*`

5. Run contributor checks:

```bash
make ci
make doctor
```

6. Sanity-check the actual agent behavior if the change is behavioral, not just structural.

Implementation changes should also preserve the expected agent handoff:

- `implementer` makes the change
- `tester` adds or updates tests when feasible and runs the relevant command
- `reviewer` checks correctness, regression risk, and whether testing evidence is present

For lesson capture, the expected flow is:

- the user starts a message with `203 /learn` in the main conversation
- the main agent routes that request to `student`
- `student` proposes the lesson title, skill folder, and summary first
- only after confirmation does `student` edit `ai/skills/*/SKILL.md` and run `make sync`

The literal prefix `203 /learn` only activates the workflow when it appears at the start of the message; quoted or explanatory mentions should not trigger it.

## What not to edit directly

Do not hand-edit generated files unless you are debugging the generator:

- `AGENTS.md`
- `CLAUDE.md`
- `.codex/config.toml`
- `.codex/agents/*`
- `.claude/settings.json`
- `.claude/agents/*`
- `.agents/skills/*`
- `.claude/skills/*`
- `ai/policy/repos.yaml`
- `ai/generated/repos/*`
- repo-local overlay files inside `repos/*`

If you change a generated file directly, `make sync` will overwrite it.

## Important cautions

### 1. Prompt changes have code-like blast radius

An instruction tweak can redirect edits, change tool usage, or make the agent too aggressive. Treat prompt and policy edits with the same care as code.

### 2. Skills must stay structurally valid

Codex expects `SKILL.md` files to begin with YAML frontmatter delimited by `---`. If that is missing or malformed, the skill may stop loading in practice except for runtime warnings.

### 3. Hooks are executable code

Anything under `ai/hooks/` can block commands or mutate behavior at runtime.
Keep hooks:

- portable across macOS and Linux
- small and easy to audit
- deterministic and idempotent
- explicit about failures

Avoid hidden network calls, interactive prompts, or machine-specific paths.

### 4. Repo routing errors can damage the wrong repo

Changes in `repos.yaml` affect which repo the agent treats as authoritative. Keep `owns` and `consult_when` precise. Ambiguous routing is one of the easiest ways to cause cross-repo mistakes.

### 5. Never put secrets into prompts, hooks, or examples

Do not hardcode tokens, credentials, internal endpoints, or private paths in any `ai/` content. Remember that this material gets copied into generated files and may end up in user workspaces.

### 6. Keep tool-specific behavior intentional

Codex and Claude do not read exactly the same files. `scix-hub` smooths over that with generated wrappers, but the tools still differ. If a change relies on a tool-specific behavior, document that assumption in the PR.

### 7. Prefer small, testable edits

Large prompt rewrites are hard to review. Prefer narrow changes with a clear expected behavior change and a short rationale.

## Review checklist for `/ai` changes

Before merging, check:

- Did I edit the right layer?
- Did I run `make sync` after editing `repos.yaml` or `ai/`?
- Did I inspect the generated diff instead of editing generated files by hand?
- Did I run `make ci` and `make doctor`?
- If behavior changed, did I manually verify the change with Codex or Claude?

## Additional contributor notes

- If `pre-commit` rewrites generated files and `make sync-check` then fails, the generator likely needs to be updated to emit the normalized output.
- If a change is intended only for local contributors and not for downstream users of the template, document that explicitly in the PR.
- When in doubt, prefer clearer and shorter instructions over broader and more "powerful" prompts. Over-specification often makes agents less reliable, not more.
