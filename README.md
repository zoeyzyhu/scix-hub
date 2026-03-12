# scix-hub

`scix-hub` is a fork-first workspace template for multi-repo projects that want
shared AI policy, generated agent files, and a simple local bootstrap flow.

The repo itself is the workspace. Users are expected to fork or clone it,
customize the repo catalog in `repos.yaml`, review `requirements.txt`, and run
the checked-in CLI with `python -m scix`.

Forking is recommended because it gives you a central GitHub repo for syncing
learned skills and workflow updates across machines. Users should expect to need
a GitHub account.

## Quick Start

```bash
git clone <your-fork-or-template-url> scix-hub
cd scix-hub
python3 -m venv xenv
source xenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Edit these two files first:

- `repos.yaml`: which repositories should be cloned, where they live, and what
  they own.
- `requirements.txt`: which Python dependencies you want in the shared local
  environment.

Then bootstrap the repo:

```bash
python -m scix up
```

`python -m scix up` will:

1. regenerate root AI files from `repos.yaml` and `ai/`
2. clone any missing repos declared in `repos.yaml`
3. write repo-local overlays into cloned repos when present
4. try to install missing Codex and Claude CLIs if needed

## Key Commands

| Command | Use it when |
| --- | --- |
| `python -m scix up` | You want to bootstrap or refresh this checkout. |
| `python -m scix sync` | You changed `repos.yaml` or editable files under `ai/`. |
| `python -m scix sync --check` | You want CI-safe validation for generated files. |
| `python -m scix install-repos` | One or more configured repos are still missing. |
| `python -m scix doctor` | You want a quick health check for this checkout. |
| `python -m scix cheat` | You want a compact command reference. |

## Editable vs Generated

The main editable inputs are:

- `repos.yaml`
- `requirements.txt`
- `ai/agents/roles.yaml`
- `ai/policy/*.md`
- `ai/skills/*/SKILL.md`
- `ai/hooks/*.sh`

Generated outputs include:

- `ai/policy/repos.yaml`
- `AGENTS.md`
- `CLAUDE.md`
- `.codex/*`
- `.claude/*`
- `.agents/skills/*`
- `ai/generated/repos/*`

Run `python -m scix sync` after changing editable files.

## Layout

- `repos/`: cloned reference repositories declared in `repos.yaml`
- `workspace/`: your notebooks, drafts, scripts, and rough work
- `ai/`: editable AI canon
- `scix/`: repo-local runtime used by `python -m scix`
- `docs/`: maintenance notes for this template repo

## Maintenance

Before pushing changes to the template itself, run:

```bash
pre-commit run --all-files
pytest -q
python -m scix sync --check
```

The detailed maintenance notes for `ai/` live in
[`docs/AI_FOLDER_GUIDE.md`](docs/AI_FOLDER_GUIDE.md).
