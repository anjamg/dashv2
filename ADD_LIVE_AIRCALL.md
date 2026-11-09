# Live Aircall call ingestion — implementation tasks

## Goal and constraints

Replace repeated manual Aircall Excel imports with scheduled, incremental polling from the VITA backend to Aircall's public API. The VITA deployment is internal, so Aircall cannot reach it: **do not implement webhooks or expose an inbound endpoint**. The backend must have outbound HTTPS access to Aircall.

Use the existing `Monitoring-aircall` project as the reference for API pagination, retries, rate-limit handling, incremental collection, and scheduling. Adapt it to this project's synchronous FastAPI/SQLAlchemy and MariaDB stack; do not copy its PostgreSQL/async database code.

Initial scope is new/recent calls, not a historical backfill. Keep the Excel import available as a fallback.

## Jobs to do

### 1. Confirm deployment and Aircall API prerequisites

- [ ] Confirm the VITA server can make outbound HTTPS requests to the Aircall API.
- [ ] Obtain Aircall API credentials and confirm their permissions cover calls and the user/team/number information needed for reporting.
- [ ] Store credentials and sync configuration in the backend environment only; never expose them through the frontend or logs.
- [ ] Confirm the Aircall call-list endpoint's supported date filters, pagination, rate limits, and searchable-history limits against the account/API documentation.
- [ ] Choose the initial lower-bound timestamp and polling interval. Start with the reference project's 60-second default (configurable; it enforces a 15-second minimum), subject to measured API usage.

### 2. Map Aircall records to the existing VITA schema

- [ ] Implement and test a mapper from Aircall call payloads to the existing `data` table. Populate `call_id` with the Aircall call identifier, and map timestamps, direction, answered state, user, team, number, total/talk duration, and waiting/answer time to their corresponding columns where the API supplies them.
- [ ] Agree how incomplete or unavailable values are represented; do not invent agent/team assignments or treat missing values as valid measurements.
- [ ] Normalize agent names consistently with the existing `user_norm` reporting filters and map Aircall team names to the VITA `team_name` values used by reports.
- [ ] Verify which datetime and duration fields are used by the deployed views and reports. Respect generated columns in the database: do not try to write generated fields such as `date_only`, `hour`, `weekday`, or `out_of_hours`.
- [ ] Check the actual deployed definitions of `v_stats_all` and any other relevant views, and confirm they include records written to `data`.
- [x] Restore the legacy `data_stats` upsert after each data chunk: select affected `data.id` values by Aircall `call_id`, derive date/local hour/weekday from `datetime_tz_offset_incl`, and insert or update the matching stats rows.

### 3. Implement safe incremental polling

- [ ] Add backend configuration for API credentials, enabled/disabled state, poll interval, initial sync-from timestamp, and overlap duration.
- [ ] Add an outbound Aircall API client following the reference project's pagination, timeout, retry/backoff, and 429/server-error handling. Surface authentication/permission errors clearly.
- [ ] Fetch a bounded recent time range each run, using the last successful sync position and a configurable overlap so late-arriving or updated calls are revisited. Bound the upper end to the current run time if the endpoint supports it.
- [ ] Verify the API's actual date-filter semantics and the 10,000-results-per-search constraint. If a window approaches the result cap, split it into smaller time ranges rather than silently truncating data. Avoid broad historical requests.
- [ ] Persist progress only after records in that range are committed. A failed run must be retryable without advancing the checkpoint past unpersisted calls.
- [ ] Handle calls that are first returned before all final fields are available: revisit and update them during the overlap window. Do not assume the first API response is necessarily the final call state.

### 4. Make inserts and updates idempotent

- [ ] Use the database's existing unique index on `data.call_id` as the deduplication key. The attached schema already defines this unique index; do not add a redundant one.
- [x] Implement MariaDB-compatible insert-or-update behavior so replayed calls update the same row rather than creating duplicate call records.
- [x] Align the SQLAlchemy `Data` model with the deployed schema's unique `call_id` constraint so the model does not misrepresent the database.
- [ ] Check the existing database for rows with `call_id IS NULL` or duplicate/invalid identifiers before rollout. MySQL/MariaDB unique indexes allow multiple `NULL` values, so they do not deduplicate imports that lack a call ID.
- [x] Restore the legacy import behavior in the modern Excel route: map the Aircall call fields, derive `team_name` from `line`, normalize agent names, preserve `call_id`, and upsert on the existing unique key. Report inserted, updated, skipped, and ID-less row counts in the API/UI.
- [x] Keep support for workbooks without a `call_id` column, but report that those rows cannot be deduplicated against API calls.
- [ ] Verify whether existing production imports have IDs before deciding if any reconciliation is needed.

### 5. Run and observe the scheduled job

- [ ] Start and stop the scheduler with the FastAPI application lifecycle, with clean cancellation on shutdown.
- [ ] Ensure only one scheduler runs against the database. The reference scheduler is process-local; for a multi-instance deployment use a single worker or a database/shared lock.
- [ ] Record each run's start/end time, status, records inserted/updated, and a safe error summary. Expose status to operators without exposing credentials or sensitive call payloads.
- [ ] Log transient failures and rate limiting, retry as appropriate, and leave the last successful checkpoint intact on failure.
- [ ] Ensure the first deployment does not unexpectedly import all available history; require an explicit configured starting point or a deliberately bounded initial window.

### 6. Keep VITA reporting current

- [ ] Confirm the dashboard and calls pages read the same populated data/view and that their date, team, and agent filters work for API-sourced rows.
- [ ] Add a modest frontend refresh interval or an explicit refresh control for relevant call/dashboard queries so already-open pages display newly ingested data.
- [ ] Keep manual Excel import as a fallback and make its history distinguish manual imports from scheduled API syncs.

### 7. Test and roll out

- [ ] Unit-test field mapping, timezone handling, missing values, incomplete-to-final call updates, pagination, retry/rate-limit behavior, and timestamp-window boundaries.
- [ ] Test repeated and overlapping runs against MariaDB: the same Aircall call ID must produce one row, and a later payload must update it.
- [ ] Test API failure/restart recovery: no skipped checkpoint range, and a retry catches calls missed while the service was down.
- [ ] Test that the existing views, dashboard KPIs, team/agent reporting, calls page, and Excel fallback continue to work.
- [ ] Deploy with a short, controlled date range first; compare counts and representative calls against Aircall, then enable the normal schedule.

## Expected limitations

- This is near-real-time polling, not a push feed. Freshness depends on the interval, API response timing, network availability, and retries.
- Polling consumes API requests. Use incremental bounds and overlap, monitor rate-limit responses, and split time windows if needed to respect per-search result limits.
- Calls may be updated after their first appearance; overlap/re-fetch is needed to capture final values. Longer outages require catch-up over the missed period, still subject to Aircall's history and search limits.
- The database unique key protects calls with a populated `call_id` from duplication. The legacy Excel importer populated and upserted by this ID; the modern importer must regain that behavior. Rows imported without an ID cannot be reliably matched to API calls automatically.
- New database rows do not refresh an already-open browser by themselves; the frontend must re-fetch.
