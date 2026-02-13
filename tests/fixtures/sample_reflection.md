# Incident Postmortem: Database Connection Pool Exhaustion

## Timeline

Wednesday early morning alert: massive API 5xx errors. Investigation revealed the DB connection pool was fully occupied. Restarting the application restored service, but slow queries persisted.

## Root Cause

- A newly deployed reporting endpoint did not implement pagination, pulling the entire table in one request. Each request held a connection for too long.
- Connection pool size did not match instance count and per-request hold time; no load testing was performed before deployment.

## Improvements

- Reporting endpoint refactored to use pagination + async export.
- Connection pool parameters adjusted based on load test results; connection timeout and circuit breaker added.
- Established a "must pass load test before go-live" checklist.

## Lessons Learned

- Resource issues (connections, memory, threads) must be quantified at the design stage, not patched after production failures.
