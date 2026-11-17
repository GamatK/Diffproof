# diffproof

**A pre-merge verification protocol for AI coding agents:** risk-tiered review, diff forensics and evidence-based sign-off.

[![tests](https://github.com/GamatK/diffproof/actions/workflows/tests.yml/badge.svg)](https://github.com/GamatK/diffproof/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An [Agent Skill](https://agentskills.io) that makes an AI coding assistant review its own work properly before telling you it's done, and review other people's work when you ask.

Most AI mistakes reach you because the assistant reports "done" from memory of what it meant to do, not from what it actually ran. diffproof turns review into a fixed routine:

1. **Gather evidence** with a bundled script that inspects the real git diff.
2. **Size the review to the risk**: low, standard or high.
3. **Check the work** against only the checklists that apply: code, UI, backend, writing, data.
4. **Prove it** by running the build, tests and the real thing after the last edit.
5. **Report honestly**: outcome first, real numbers, what was *not* verified, and findings rated Blocker / Major / Minor, each with the concrete case that triggers it.

## The evidence helper

`skills/diffproof/scripts/review_context.py` is a small, dependency-free Python script the assistant runs before reviewing. It reads the changes on your branch (committed, uncommitted and untracked) and prints:

- **A suggested risk level, with reasons.** Changes to authentication, permissions, payments, migrations, secrets or deployment config are marked high risk.
- **Which checklists apply**, based on the kinds of files that changed.
- **Warnings in the added lines, with file and line number:**
  - possible secrets: API keys, private keys, tokens, hard-coded passwords, masked in the output
  - skipped or focused tests, disabled lint or type checks
  - switched-off TLS verification or git hooks
  - `eval`, unsafe HTML injection, unsafe deserialization, `shell=True`
  - destructive SQL, Row Level Security switched off, service role keys
  - empty catch blocks that swallow errors
  - leftover TODOs and debug output
- **Gaps:** code changed without any test changes, dependency files changed.
- **The project's own build, test and lint commands**, detected from `package.json`, `pyproject.toml`, `Package.swift`, Xcode projects, `go.mod`, `Cargo.toml` or a `Makefile`.

Example output:

```text
Changes vs 3f2a91c: 4 files, +86 / -12 lines

Suggested risk: HIGH
  - touches authentication

Checklists to load: references/code.md, references/backend.md

Warnings in added lines (2):
  [blocker] src/auth/client.py:14  possible API secret key (sk-...)
      API_KEY = "sk-p…9x"
  [major] tests/test_login.py:30  test skipped or focused (.only)
      @pytest.mark.skip(reason="flaky")

Commands to run after the last edit:
  test      python -m pytest
  lint      ruff check .

Notes:
  - Dependencies changed (requirements.txt). Verify each new package name and pin versions.
```

It only reads files and never modifies anything, makes no network requests, and sends nothing anywhere. It exits with code 1 when a possible secret is found, so it can also run in CI or a pre-commit hook. The pattern checks give the assistant leads to confirm, not verdicts; no warnings does not mean no bugs.

You can run it yourself from inside any git repository:

```bash
python3 path/to/skills/diffproof/scripts/review_context.py              # vs. your main branch
python3 path/to/skills/diffproof/scripts/review_context.py --base HEAD~3
python3 path/to/skills/diffproof/scripts/review_context.py --json
```

Requires Python 3.10 or newer and git.

## What the checklists cover

| Area | Examples |
| --- | --- |
| **Code** | Requirements met, edge cases (empty, huge, unicode, timezones, concurrency), error paths, security, data integrity, tests that actually test something |
| **Apps and UI** | Every state (loading, empty, error), accessibility, narrow screens, SwiftUI ownership and threading |
| **Backends** | Server-side authorization per record, safe migrations, idempotent webhooks, Supabase Row Level Security |
| **Writing** | Facts traceable to sources, arithmetic, unfilled placeholders, tone for the reader |
| **Research and data** | Fresh sources, row counts through joins, honest charts, stated limits |
| **Other people's work** | Pull requests and documents: a merge verdict, findings with failing cases, no rewriting unless asked |

## Install

### Claude Code

```text
/plugin marketplace add GamatK/diffproof
/plugin install diffproof@gamatk-skills
```

Or copy the `skills/diffproof/` folder into `~/.claude/skills/` (all projects) or `.claude/skills/` in one project.

### Claude apps (web and desktop)

Download this repository as a ZIP, zip the `skills/diffproof` folder on its own, and upload it in the app's skills settings. The evidence helper runs only where the assistant can execute code; elsewhere the checklists still apply.

### Other assistants

`SKILL.md` follows the open Agent Skills format: Markdown with a short header. Assistants that support that format can load the folder directly; others can use `SKILL.md` as project instructions.

## Use

It triggers on its own when you ask the assistant to review, check, verify or audit something, and before it reports a non-trivial task as done. You can also call it directly:

```text
/diffproof
Review this pull request against its description.
Check this report before I send it to my manager.
```

## Repository layout

```text
.claude-plugin/              plugin and marketplace metadata for Claude Code
skills/diffproof/
  SKILL.md                   the core routine: modes, evidence, risk, rules, verification, report
  references/                checklists, loaded only when relevant
  scripts/review_context.py  the evidence helper
tests/                       unit tests for the helper (python3 -m unittest discover -s tests)
```

## Limitations

- The helper uses pattern matching. It will miss problems that need understanding of the code, and it can flag safe code. Every warning should be confirmed by reading it.
- It is not a security scanner or a replacement for dedicated tools such as secret scanners, SAST tools or human review of high-stakes changes.
- The checklists are general. Add your own team's rules in your project instructions.

## Contributing

Issues and pull requests are welcome, especially new checks with an example of the real bug they catch. Please add a test in `tests/` for any change to the helper.

## License and disclaimer

[MIT](LICENSE). Provided as is, without warranty of any kind; you are responsible for reviewing what your assistant produces.

This is an independent project. It is not affiliated with, endorsed by or sponsored by Anthropic. Claude and Claude Code are trademarks of Anthropic, PBC, and are used here only to describe compatibility.
