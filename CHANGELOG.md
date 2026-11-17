# Changelog

## 1.1.0 (2026-11-17)

- Split the single file into a short core routine (`SKILL.md`) and checklists in `references/` that load only when relevant, so less of the assistant's context is used.
- Added a mode for reviewing other people's pull requests and documents, with a merge or ship verdict.
- Added explicit low, standard and high risk levels.
- Added web checks (console errors, narrow screens, keyboard use, image sizing) and general backend checks (idempotent webhooks, logging, secret rotation) alongside the Supabase checks.
- Added a worked example of the final report.
- Packaged as a Claude Code plugin with a marketplace file, a README and an MIT license.

## 1.0.0

- First version: core rules, checklists for code, UI and SwiftUI, Supabase, writing and research, a final gate and a report format.
