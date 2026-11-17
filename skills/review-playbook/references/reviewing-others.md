# Reviewing someone else's work

Use this mode when the user asks you to review a pull request, diff, file, document or analysis that you did not just write.

## Before reading the work

- Find out what it is supposed to do: the pull request description, the linked issue, the brief, or ask the user. A review without the goal checks style, not correctness.
- Note the risk level (see SKILL.md) and which checklists apply.
- If the work can be run, run it: check out the branch, run the tests, open the screen, recompute the numbers. Findings from running beat findings from reading.
- For a branch or pull request, run the evidence helper against its target, for example `python3 <skill folder>/scripts/review_context.py --base origin/main`, and use its warnings as a starting list to confirm or dismiss.

## While reviewing

- Read the whole change, including tests and docs, not only the parts that look interesting.
- Read the surrounding code a change depends on before calling something wrong.
- Separate what is **wrong** (a bug, a security hole, a requirement missed) from what is **different from how you would do it**. Only the first is a finding. Mention the second only if it clearly matters, and label it as a preference.
- Do not rewrite their work unless asked. Suggest the fix; let the author make it.
- Assume competence. If something looks odd, look for the reason first, then ask about it as a question rather than declaring it a mistake.

## Reporting

Use the report format and severity scale in SKILL.md, with these changes:

1. Start with a one-line verdict: **ready to merge / ship**, **ready after the blockers are fixed**, or **needs another pass**, and why.
2. List findings most severe first, each with location, the concrete failing case, and a suggested fix.
3. Say what you ran and what you only read.
4. Note what is done well only where it is specific and useful to the author, in one short line, not as padding.
5. If there are no findings, say so plainly and state what you checked, instead of inventing minor ones.
