# MVP scope decisions

Date: 2026-06-29

## Admin flow

Use seed scripts for the first backend version. A production admin API is deferred
until the core auth, catalog, validation, and profile flows are stable.

## Telegram bot worker

Do not include a Telegram bot worker in the first version. The backend should run
as a standalone HTTP API, and bot-specific dependencies can be added later if a
separate worker becomes necessary.
