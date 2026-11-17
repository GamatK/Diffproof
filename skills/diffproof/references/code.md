# Code review checklist

Read the full diff line by line as if a stranger wrote it. For a low-risk change, parts 1 and 2 are enough; otherwise work through every part that applies.

## Contents

1. Does it do the job
2. Edge cases
3. Errors and failure
4. Security
5. Data and state
6. Concurrency and async
7. Performance
8. APIs and interfaces
9. Readability and fit
10. Tests
11. Version control and dependencies

## 1. Does it do the job

- Each requirement in the request is handled. Check them against the original wording one by one.
- The main path works when run with realistic input.
- Every caller of anything whose behavior, signature or return shape changed still works. Search for them; do not assume.
- The work reuses the project's existing patterns and helpers instead of inventing new ones.
- No leftovers in finished code: `TODO`, stubs, fake data, mock returns, "implement later".
- The change is the smallest one that fully solves the problem.

## 2. Edge cases

For each input and piece of state, what happens when it is:

- empty, null, missing or undefined
- zero, negative, huge, fractional or NaN
- one item, or very many
- duplicated, unordered or already processed
- the wrong type or shape, with extra or missing fields
- text with surrounding whitespace, unicode, emoji, right-to-left script, very long strings, quotes or special characters
- a date at midnight, month end, leap day, a timezone boundary or a daylight saving change
- arriving twice, concurrently, late, or never

Also: off-by-one errors in loops, ranges and slices; inclusive versus exclusive bounds; integer overflow and rounding; the first run with no data; the user cancelling halfway.

## 3. Errors and failure

- Every fallible operation (network, file, database, parsing, permissions) has a decided outcome. Nothing fails silently.
- No empty catch blocks, and no broad catch that hides unrelated bugs.
- Errors are handled at the level that can do something useful, and are not both logged and rethrown at every layer.
- User-facing messages say what happened and what to do, with no secrets, stack traces or internal paths.
- Resources are released on the failure path too: files, connections, locks, timers, listeners, subscriptions.
- Multi-step writes are atomic or safely retryable. A crash midway does not leave half-written data.
- Calls that can hang have timeouts. Retries are bounded, back off, and never repeat a non-repeatable action (a payment, an email, an insert without an idempotency key).
- Exit codes and return values signal failure correctly to whatever calls this code.

## 4. Security

- All outside input is untrusted: user input, URL parameters, headers, cookies, files, API responses, webhook bodies, and database rows others can write.
- Nothing is built by concatenating untrusted input: SQL, shell commands, file paths, HTML, templates, regular expressions, URLs. Use parameterized queries and proper escaping.
- Authentication is verified on the server for every protected action.
- Authorization checks the specific record: can this user touch this row, not merely are they logged in. Test by imagining user A requesting user B's id.
- No secrets in code, logs, error messages, client bundles, URLs or git history. Keys come from the environment or a secret store.
- Passwords are hashed with a proper password hash, never encrypted or stored plain. Tokens are random, expire, and can be revoked.
- Personal data is minimized, not logged, and sent only over TLS.
- Uploads and paths are validated for type, size and traversal (`../`). Fetching a user-supplied URL cannot reach internal addresses.
- Login, signup, password reset and anything expensive have rate limits or other abuse controls.
- CORS, cookies (`HttpOnly`, `Secure`, `SameSite`) and redirects are not left wide open.
- Permissions are the minimum needed. Nothing is public or world-writable for convenience.
- Deserialization, `eval` and dynamic code execution are never used on untrusted data.

## 5. Data and state

- Schema changes come with a migration that is safe on existing data, can run on a live system, and can be rolled back.
- Old data, old clients and old saved state still work with the new code.
- No race conditions: shared state is not read and then written from two places unprotected. Check every read-modify-write sequence.
- Caches are invalidated when the data changes, and cache keys include everything that affects the result, including the user.
- Money uses integers or decimals, never floats. Times are stored in UTC and converted only for display.
- Uniqueness and required fields are enforced by the database, not only by application code.
- Deletes handle related rows deliberately: cascade, restrict, or orphan on purpose.

## 6. Concurrency and async

- Every async call is awaited or deliberately detached. No forgotten promises or tasks.
- Errors inside async work are caught somewhere.
- Long-running work can be cancelled, and cancellation cleans up.
- A stale response cannot overwrite a newer one (the user typed again, navigated away, or refreshed).
- No deadlocks: locks are taken in a consistent order and never held across a slow call.

## 7. Performance (only what matters here)

- No query or network call inside a loop that could be batched.
- No whole table or file loaded when only part is needed.
- No accidental quadratic work on lists that can grow.
- No blocking work on the main or UI thread.
- Lists of unknown size are paginated or limited.
- Columns used to filter or sort have an index.
- Nothing is recomputed or refetched on every render or request when it could be reused.

## 8. APIs and interfaces

- Request and response shapes match what callers and docs expect, including field names, types, nullability and status codes.
- Input is validated at the boundary, with clear error responses.
- Changes to a public interface are backward compatible, or the break is called out.
- Endpoints that change state are safe to retry or are protected against double submission.

## 9. Readability and fit

- Matches the style, naming and structure of the surrounding files.
- Names say what things are. No `temp2`, `data2` or `newFunc`.
- No dead code, commented-out blocks, debug prints, unused imports or unused variables.
- No logic duplicated from elsewhere in the project.
- Comments explain why, not what, and never narrate the edit ("fixed bug", "new version").
- No magic numbers or strings where a named constant belongs.
- Complexity is justified. If a simpler version does the same job, use it.
- The README, docs, config examples and type definitions are updated if behavior changed.

## 10. Tests

- New behavior has a test. A bug fix has a test that fails without the fix.
- Tests assert real behavior and would fail if the code were wrong. A test that only checks that a mock was called proves little.
- At least one edge case and one failure case are covered, not only the happy path.
- Tests are independent of each other, of run order, of the clock and of the network.
- No existing test was deleted, skipped or loosened to pass. If a test was truly wrong, say so and explain why.

## 11. Version control and dependencies

- Only intended files changed. No secrets, build output, large binaries, editor files or lockfile churn by accident.
- The work is on the right branch. Nothing was force pushed or rewritten without being asked.
- Commit messages say what changed and why.
- New dependencies are real, maintained and needed, and the exact package name is verified (look-alike names are a known attack). Versions are pinned or locked.
