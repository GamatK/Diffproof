# Review Playbook

An [Agent Skill](https://agentskills.io) that makes an AI assistant review its own work properly before telling you it's done, and review other people's work when you ask.

Most AI mistakes reach you because the assistant reports "done" from memory of what it meant to do, not from what it actually ran. This skill turns review into a fixed routine: size the review to the risk, check the work against the right checklist, prove it by running it, and report only real results, including what was **not** verified.

## What it covers

| Area | Examples of what it checks |
| --- | --- |
| **Code** | Requirements met, edge cases, error paths, security, data integrity, concurrency, tests that actually test something |
| **Apps and UI** | Every state (loading, empty, error), accessibility, phone layouts, SwiftUI ownership and threading |
| **Backends** | Server-side authorization, migrations, idempotent webhooks, Supabase Row Level Security |
| **Writing** | Facts traceable to sources, arithmetic, placeholders, tone for the reader |
| **Research and data** | Fresh sources, row counts through joins, honest charts, stated limits |
| **Other people's work** | Pull requests and documents: a verdict, findings with concrete failing cases, no rewriting unless asked |

## How it works

1. **Mode:** self-review of work just done (default), or review of someone else's work.
2. **Risk:** low, standard or high. High covers anything touching auth, money, personal data, deletion or migrations, and gets every check.
3. **Checklists:** only the ones that match the work are loaded, so the assistant's context stays small.
4. **Verification:** build, tests and the real thing are run **after** the last edit, plus one deliberate failure test.
5. **Report:** outcome first, real numbers, what was not verified, findings rated Blocker / Major / Minor with the concrete case that triggers each.

## Install

### Claude Code

```text
/plugin marketplace add GamatK/review-playbook
/plugin install review-playbook@gamatk-skills
```

Or copy `skills/review-playbook/` into `~/.claude/skills/` (all projects) or `.claude/skills/` inside one project.

### Claude apps (claude.ai and desktop)

Download this repository as a ZIP, then upload the `skills/review-playbook` folder (zipped) under **Settings → Capabilities → Skills**. The exact menu names may change; see Claude's help pages on skills if they differ.

### Other assistants

`skills/review-playbook/SKILL.md` is plain Markdown with a short header, following the open Agent Skills format. Assistants that support that format can load it directly; others can use it as a system prompt or project instruction.

## Use

It runs on its own when you ask the assistant to review, check, verify or audit something, and before it reports a non-trivial task as done. You can also call it by name:

```text
/review-playbook
Review the open pull request against its description.
Check this report before I send it to my manager.
```

## Repository layout

```text
.claude-plugin/
  plugin.json          plugin metadata
  marketplace.json     lets Claude Code install it from this repo
skills/review-playbook/
  SKILL.md             core routine: modes, risk levels, rules, verification, report
  references/          checklists loaded only when relevant
    code.md
    ui.md
    backend.md
    writing.md
    research.md
    reviewing-others.md
```

## Limits

- It guides the assistant; it cannot run anything the assistant has no access to. When something can't be checked, the skill requires the assistant to say so and give you the command to run.
- Checklists are general. Add your team's own rules (style guides, deployment steps) in your project instructions.
- It is not a replacement for human review of high-stakes changes.

## Contributing

Issues and pull requests are welcome, especially new checklist items with a real example of the bug they catch.

## License

[MIT](LICENSE). Not affiliated with or endorsed by Anthropic. Claude and Claude Code are trademarks of Anthropic.
