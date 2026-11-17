---
name: review-playbook
description: Evidence-based review of finished work before it is handed back, or of someone else's work on request. Covers code changes, apps and UI, backends and databases, writing, and research or data analysis. Use when the user says review, check, verify, audit, double-check, "is this ready", or /review-playbook, and before reporting any non-trivial task as done. Not for brainstorming or for work that has not been attempted yet.
---

# Review Playbook

The mistakes that get through are the ones the author was blind to. Review deliberately, from the real diff and the real output, never from memory of what was intended.

## 1. Pick the mode

- **Self-review (default).** You did the work and are about to hand it back. Review it, fix what you find, then report.
- **Reviewing someone else's work.** The user asked you to review a pull request, diff, file, document or analysis they or someone else wrote. Read [references/reviewing-others.md](references/reviewing-others.md) first. Do not change their work unless asked; report findings.

## 2. Gather evidence first (when you can run commands)

If the work is in a git repository and you can run commands, run the bundled helper from inside the repository before reviewing:

```bash
python3 <this skill's folder>/scripts/review_context.py
```

Add `--base <ref>` to compare against a specific branch or commit, and `--json` for structured output. It only reads; it never changes files. It reports:

- every changed file, including uncommitted and untracked ones, with line counts
- a suggested risk level and why (auth, money, permissions, migrations, secrets, deployment config)
- which checklists in section 4 apply
- warnings in the added lines with file and line: possible secrets (masked), skipped tests, disabled lint or type checks, switched-off TLS or hooks, `eval` and unsafe HTML, destructive SQL, empty catch blocks, leftover TODOs and debug output
- the build, test and lint commands the project appears to use

Treat its output as leads, not verdicts: confirm each warning by reading the code, and remember that no warnings does not mean no bugs. Exit code 1 means a possible secret was found; resolve that before anything else. If Python or git is unavailable, skip this step and review the files directly.

## 3. Size the review to the risk

| Risk | When | What to do |
| --- | --- | --- |
| **Low** | One-line fix, copy change, comment, config value with no runtime effect | Core rules, a quick pass of the relevant checklist's first two parts, verification, report |
| **Standard** | Most features and fixes, most documents and analyses | Core rules, every relevant checklist, full verification, final gate, report |
| **High** | Anything touching auth, permissions, money, personal data, deletion, migrations, concurrency, production config, or anything hard to undo | Everything in Standard, every item in every relevant checklist, and at least one deliberate failure test |

When unsure, go one level higher. If the helper in section 2 suggested a level, use it unless you can say why it is wrong.

## 4. Load only the checklists that match the work

| The work includes | Read |
| --- | --- |
| Any code change | [references/code.md](references/code.md) |
| A UI, web page or mobile app | [references/ui.md](references/ui.md) |
| A backend, API, database, auth or Supabase | [references/backend.md](references/backend.md) |
| Writing, documents or messages | [references/writing.md](references/writing.md) |
| Research or data analysis | [references/research.md](references/research.md) |

Work the checklists silently. Do not print them or tick items off in the reply; report only findings, evidence and gaps.

## 5. Core rules (always)

1. **Evidence, not belief.** Say something works only if it was run in this session and the output was seen. "Should work" means unverified; say "not verified".
2. **Answer what was asked.** Re-read the original request at the end. Correct work on a different question is a failure.
3. **Fix causes, not symptoms.** Never get a green result by editing the test, special-casing the input, hard-coding the expected value, or catching and ignoring the error.
4. **Stay in scope.** No drive-by refactors, renames, reformatting, new dependencies or unrequested features.
5. **Read before you write.** Open the real file, signature, schema or docs. Never guess an API, path, column or config key.
6. **Never weaken a safeguard to make progress:** no disabled lint rules, skipped hooks, `any` types, removed assertions or switched-off auth, unless that was the task.
7. **Ask before anything irreversible:** deleting data, force push, history rewrite, migrations on real data, production config, spending money, sending messages.
8. **Disclose gaps.** Skipped steps, failures, assumptions and unverified claims go in the report, early and plainly.

## 6. Understand the task first (even after the fact)

- Can you restate the request in two sentences? If not, you do not understand it yet.
- What observable result means "done": a test passing, an output, a screen behaving a certain way?
- What is in scope? If the request names one bug or one file, that is the scope.
- What constraints are implied: language and framework versions, existing style, public interfaces others depend on?
- Was the starting state known (build, tests and lint run before the change, pre-existing failures noted)?
- If the request was ambiguous in a way that changes the result, was it asked? If only slightly, is the chosen reading stated in the report?

## 7. Verify: prove it

Do each that applies, **after the final edit**. A check run before the last change does not count.

1. Build or compile: no errors.
2. Type checker and linter: no new warnings from this change.
3. Tests: record real numbers (passed, failed, skipped).
4. Run the real thing: call the function, hit the endpoint, run the script, open the screen, render the document. Look at the actual output.
5. Feed one bad input on purpose and confirm it fails correctly.
6. Re-read the complete final diff or document top to bottom.
7. Confirm the list of changed files is exactly what was intended.

If something cannot be run (no environment, credentials or device), say exactly what was not run and give the command the user should run to confirm. Never imply it was checked.

**Debugging discipline:** read the whole error and stack trace; form one hypothesis; test it; then fix. If the same approach failed twice, change the approach instead of trying a third variation.

## 8. Final gate

Do not report done until each answer is yes, or the "no" is written into the report.

- The result matches the original request, re-read just now.
- The build, the tests and the real thing were run after the last edit, and the output was seen.
- The whole final diff or document was read.
- Edge cases and the failure path were checked, not only the happy path.
- Nothing outside the task's scope changed.
- No test, check or safety control was weakened to get here.
- No secrets, debug code, placeholders or temporary files remain.
- Nothing about to be claimed is a guess presented as fact.
- Everything unfinished, unverified or assumed is in the report.

### Warning signs in your own thinking

Each of these means stop and go back:

- "This should work." It has not been run.
- "The test is probably wrong." Prove it before touching the test.
- "I'll just make it pass for now." That is fixing the symptom.
- "While I'm here, I'll also clean up..." That is scope creep.
- "I think the function is called..." Go and read it.
- "It's probably fine on the error path." Check it.
- "I'll mention that later." Put it in the report now.
- "It's almost done, so I'll say done." Say what is left.

## 9. Report

Keep it short. The user wants the result, not a tour of the checklist.

1. **Outcome** in one or two sentences: what works now, or what does not.
2. **Verified**, with how and with real results ("test suite: 42 passed, 0 failed"). Never write "tests pass" without having run them.
3. **Not verified, failed or skipped**, early and without softening.
4. **Findings**, most severe first (see below). In self-review, say which were fixed.
5. **Assumptions and decisions** the user may want to reverse.
6. **Files changed.**
7. One line for a real next step or risk, if there is one.

No step-by-step narration, no praise for the work, and no "complete", "robust" or "production-ready" unless the evidence above supports it.

### Rating findings

- **Blocker:** wrong results, data loss, security hole, crash, or the request not met. Fix before hand-off.
- **Major:** unhandled realistic edge case, missing test for new behavior, broken failure path. Fix, or report clearly.
- **Minor:** naming, small duplication, style. Fix if cheap, otherwise mention.

For each finding give: the file and line (or section), what is wrong, a concrete input or situation that triggers it, and the fix. A finding with no concrete failing case is a suspicion: confirm it, or label it unconfirmed.

### Example

> **Outcome:** The CSV import now handles quoted commas; the upload screen is unchanged.
>
> **Verified:** `pytest`: 38 passed, 0 failed (2 new). Imported `sample_quoted.csv` (120 rows) and compared row counts before and after: 120 in, 120 stored. A file with a missing header now returns a 400 with "Missing column: email".
>
> **Not verified:** files over 50 MB; no large sample was available. Run `python import.py big.csv` to confirm.
>
> **Findings:**
> - Major (fixed): `parser.py:44` dropped the last row when the file had no trailing newline. Added a test.
> - Minor (not fixed): `utils.py:12` duplicates `clean_email()` from `validators.py`.
>
> **Files changed:** `parser.py`, `tests/test_parser.py`
