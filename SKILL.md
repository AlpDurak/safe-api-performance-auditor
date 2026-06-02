---
name: safe-api-performance-auditor
description: Use when auditing local or explicitly approved staging backend APIs for performance, endpoint latency, load testing, bottlenecks, N+1 queries, slow SQL or ORM calls, runtime resource use, or safe optimization recommendations.
---

# Safe API Performance Auditor

Use this skill to benchmark backend APIs safely, identify likely bottlenecks, and produce a concise report. Prioritize safety, reproducibility, and measured evidence over aggressive load.

## Non-Negotiable Safety Rules

- Never benchmark production unless the user explicitly confirms the exact target is safe to test.
- Prefer `localhost`, `127.0.0.1`, Docker Compose services, local dev servers, and confirmed staging URLs.
- Skip destructive or externally visible endpoints by default: payments, deletes, password resets, email/SMS, webhooks, account spam, irreversible jobs, and third-party writes.
- For `POST`, `PUT`, `PATCH`, and `DELETE`, test only when a safe test database, fixture, seed flow, or explicit user approval exists.
- Start with conservative load and stop when error rate exceeds 5%, CPU stays above 90%, memory grows continuously, or the service becomes unhealthy.
- Do not install global tools, change schemas, edit `.env`, or modify application code without approval.
- Do not fabricate results. If startup, route discovery, auth, or benchmarking fails, report the failure plainly.

## Workflow

1. Discover the backend stack and startup command from existing project files.
2. Discover API routes and classify each endpoint before testing.
3. Pick the best installed benchmark and monitoring tools.
4. Run a warmup, then low-concurrency benchmark phases.
5. Cross-reference slow endpoints with source code and runtime/database signals.
6. Write `performance_skill/[run_id].md`.
7. Ask before applying any code optimization.

## Discovery

Read local documentation and config first:

- `README*`, `package.json`, `Makefile`, `docker-compose*.yml`, `.env.example`
- OpenAPI/Swagger files, Postman/Insomnia collections, route files, controller files
- Test fixtures, seed scripts, test credentials, and local-only compose services

Classify routes as:

| Class | Meaning |
|---|---|
| `SAFE_GET` | Read-only endpoint suitable for conservative benchmarking |
| `AUTH` | Login, token, session, guard, or protected-route behavior |
| `MUTATION_SAFE` | Mutation endpoint proven safe in a test environment |
| `MUTATION_UNSAFE` | Destructive or externally visible endpoint to skip |
| `UNKNOWN` | Endpoint needing user confirmation |

## Tool Priority

Use installed tools only. Prefer structured output when available.

Load testing:

1. `k6`
2. `oha`
3. `autocannon`
4. `bombardier`
5. `wrk`
6. `hey`
7. `vegeta`
8. `ab`
9. `siege`
10. bundled fallback: `scripts/benchmark.py`

Runtime and system monitoring:

- Containers: `docker stats --no-stream`, `docker compose ps`, `docker compose logs`
- Processes: `ps`, `pidstat`, `/usr/bin/time -v`, `top`, `htop`
- Ports/connections: `ss`, `netstat`, `lsof`
- Linux host signals when available: `vmstat`, `iostat`, `sar`, `perf stat`

Profiling, only on local or approved staging:

- Node.js: `node --prof`, `clinic`, `0x`, `--inspect`
- Python: `py-spy`, `scalene`, `cProfile`, `pyinstrument`
- Go: `pprof`, `go tool trace`
- Java/Kotlin: Java Flight Recorder, `jcmd`, async-profiler

Database inspection, read-only unless explicitly approved:

- PostgreSQL: `EXPLAIN`, `EXPLAIN ANALYZE` only when safe, `pg_stat_statements`, index listings
- MySQL/MariaDB: `EXPLAIN`, `EXPLAIN ANALYZE` when safe, slow query log hints, index listings
- MongoDB: `.explain("executionStats")`, index listings, profiler status
- Redis/cache: `INFO`, hit rate, memory, keyspace, slow log if available

Static search:

- Prefer `rg`; fall back to `grep`.
- Search for N+1 queries, unbounded ORM calls, missing pagination, sync I/O, large serialization, repeated external calls, inefficient loops, and missing cache/index opportunities.

Useful search terms:

```text
findMany(
.find(
.populate(
include:
select *
JSON.stringify
fs.readFileSync
fs.writeFileSync
await .* map
forEach(async
for .* await
limit:
skip:
take:
EXPLAIN
ORDER BY
GROUP BY
```

## Benchmark Plan

Default conservative profile:

| Phase | Duration | Concurrency |
|---|---:|---:|
| Warmup | 10s | 2 |
| Baseline | 30s | 5 |
| Moderate | 30s | 10 |
| Higher | 30s | 25 |

Only run the next phase if the previous phase stayed healthy. For fragile apps, reduce duration or concurrency and record the change.

If no load tool is installed, run the bundled fallback from the skill directory:

```bash
python scripts/benchmark.py --url http://127.0.0.1:3000/api/health --duration 30 --concurrency 10
```

Use headers only when they are safe test credentials:

```bash
python scripts/benchmark.py --url http://127.0.0.1:3000/api/items --header "Authorization: Bearer TEST_TOKEN"
```

## Bottleneck Review

For each slow or error-prone endpoint, connect measurements to likely causes:

- missing indexes, full scans, expensive joins, slow aggregations
- N+1 queries, unbounded `find`/`findMany`, broad `include`/`populate`
- missing pagination, large response payloads, excessive JSON serialization
- blocking file/network calls, synchronous CPU-heavy work, password hashing hot paths
- repeated auth/session/database lookups, middleware overhead
- memory growth, GC pressure, process restarts, queue backlogs, cache misses

Use `confirmed` only when measurement or source evidence supports the cause. Otherwise write `suspected`.

## Report Format

Create `performance_skill/` and write `performance_skill/[run_id].md`.

```markdown
# Run: [run_id]

Target: [local/staging URL or startup command]
Mode: [tool and concurrency profile]
Stack: [detected stack]
Date: [ISO timestamp]

## Summary

- Tested: [n] endpoints
- Skipped: [n] endpoints
- Worst p99: [METHOD] [route] - [latency]ms
- Highest error rate: [METHOD] [route] - [error_rate]%
- Main risk: [one-line summary]

## Bottlenecks

| Endpoint | RPS | p95 | p99 | Err | Cause |
|---|---:|---:|---:|---:|---|
| `[METHOD] /route` | [rps] | [ms] | [ms] | [%] | [file:line + confirmed/suspected cause] |

## Proposed Fixes

1. `[file:line]` - [brief fix]
2. `[file:line]` - [brief fix]
3. `[file:line]` - [brief fix]

## Skipped

- `[METHOD] /route` - [reason]

## Commands

```bash
[exact benchmark and monitoring commands]
```

## Approval Required

No code changes were applied. Ask the user before implementing fixes.
```

Keep the report short. Prefer tables over paragraphs.

## Response To User

After writing the report, answer briefly:

```text
Benchmark complete. Report saved to performance_skill/[run_id].md.

Top bottlenecks:
1. [METHOD route] - p99 [x]ms - [cause]
2. [METHOD route] - p99 [x]ms - [cause]
3. [METHOD route] - p99 [x]ms - [cause]

Recommended fixes:
1. [brief]
2. [brief]
3. [brief]

No code changes were made. Do you want me to implement these fixes?
```

If benchmarking could not be completed, still write a report with the failure reason, assumptions, skipped work, and next step needed from the user.

## After Approval

When the user approves code changes:

1. Apply the smallest low-risk fix first.
2. Run relevant tests.
3. Re-run the same benchmark command.
4. Write `performance_skill/[run_id]-after.md`.
5. Compare before and after. Do not claim improvement unless measured.
