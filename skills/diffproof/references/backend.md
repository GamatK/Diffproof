# Backend, database and auth checklist

Use with the security and data sections of [code.md](code.md).

## All backends

- The client is never trusted for anything that matters: price, role, user id and ownership are decided by the server.
- Every endpoint or function exposed to clients validates its input and checks the caller's identity and permission for the specific record.
- Queries select only the columns needed, are paginated, and have indexes for their filters and sort order.
- Schema changes are written as migration files and reviewed, not made only by hand in a dashboard.
- Environments are separate: nothing points a development build at production data, or the reverse.
- Logs record enough to debug a failure without recording passwords, tokens or personal data.
- Background jobs and webhooks are idempotent: receiving the same event twice does no harm.
- Secrets are read from the environment or a secret store, differ per environment, and can be rotated.

## Supabase

- Row Level Security is enabled on every table with user data, with a policy for each of select, insert, update and delete. A table with RLS off is readable by anyone holding the public key.
- Policies check ownership of the specific row (`auth.uid()` against the owner column), not just that a user is signed in. Update policies have both a `using` and a `with check` clause.
- The service role key never appears in the app or any client code. Only the anon (publishable) key ships.
- Storage buckets have policies too; private files are not in a public bucket.
- Database functions called from clients check the caller; `security definer` functions are reviewed with extra care.
- Realtime subscriptions are removed when no longer needed.
