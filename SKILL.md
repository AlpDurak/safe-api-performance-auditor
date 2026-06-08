---
name: safe-api-performance-auditor
description: Use when auditing local or explicitly approved staging backend APIs for performance, endpoint latency, load testing, bottlenecks, N+1 queries, slow SQL or ORM calls, runtime resource use, or safe optimization recommendations. Supports MADMAX mode for parallel deep-scan of large codebases.
---

# Safe API Performance Auditor

Use this skill to benchmark backend APIs safely, identify bottlenecks with measured evidence, and produce a concise report. Prioritize safety, reproducibility, and statistical rigor over aggressive load.

## Non-Negotiable Safety Rules

- Never benchmark production unless the user explicitly confirms the exact target is safe to test.
- Prefer `localhost`, `127.0.0.1`, Docker Compose services, local dev servers, and confirmed staging URLs.
- Skip destructive or externally visible endpoints by default: payments, deletes, password resets, email/SMS, webhooks, account spam, irreversible jobs, and third-party writes.
- For `POST`, `PUT`, `PATCH`, and `DELETE`, test only when a safe test database, fixture, seed flow, or explicit user approval exists.
- Start with conservative load and stop when error rate exceeds 5%, CPU stays above 90%, memory grows continuously, or the service becomes unhealthy.
- Do not install global tools, change schemas, edit `.env`, or modify application code without approval.
- Do not fabricate results. If startup, route discovery, auth, or benchmarking fails, report the failure plainly.

---

## Mode Selection

This skill operates in two modes:

| Mode | When to use | What happens |
|---|---|---|
| **Standard** | Small/medium projects, quick audits, single-agent workflows | One agent runs discovery → benchmark → report sequentially |
| **MADMAX** | Large codebases, deep audits, when the user says "MADMAX", or when the agent detects the project is too big for a single pass | Multiple parallel agents split the codebase and merge findings |

### Triggering MADMAX

MADMAX activates when:
1. The user explicitly requests it (e.g., "use MADMAX", "go MADMAX", "madmax mode")
2. The agent detects the project exceeds the size threshold and **asks** the user

### Auto-detection threshold

After discovery, measure the project:

```
source_files = count of .js/.ts/.py/.go/.java/.kt/.rs/.rb/.cs files (exclude node_modules, vendor, dist, build, .git)
source_lines = total lines across source_files
route_count  = number of discovered API routes
```

If **any** of these conditions are met, recommend MADMAX to the user:

| Metric | Threshold |
|---:|---|
| `source_files` | > 150 |
| `source_lines` | > 30,000 |
| `route_count` | > 40 |

Present the recommendation like this:

```text
This project has [source_files] source files ([source_lines] lines) with [route_count] routes.
A single-pass audit may miss deep bottlenecks in a codebase this size.

I recommend MADMAX mode:
  • Agents to launch: [N] parallel agents
  • Estimated extra tokens: ~[T]k tokens
  • Each agent covers a focused zone of the codebase

Would you like to activate MADMAX? (y/n)
```

Do **not** activate MADMAX without user confirmation.

---

## MADMAX Mode

### Agent Calculation

The main agent calculates how many parallel agents to spawn based on the project's shape:

```
base_agents = ceil(source_files / 80)          # ~1 agent per 80 source files
route_agents = ceil(route_count / 15)          # ~1 agent per 15 routes
agent_count = max(base_agents, route_agents)
agent_count = clamp(agent_count, 2, 8)         # minimum 2, maximum 8
```

Token estimation for user approval:

```
tokens_per_agent ≈ 25,000                      # average for deep code scan + analysis
total_extra_tokens ≈ agent_count × 25,000
```

### Zone Assignment

The main agent partitions the work **before** spawning. Each agent gets a **zone** — a non-overlapping slice of responsibility:

| Zone type | What the agent does |
|---|---|
| **Route Zone** | Benchmarks assigned endpoints + traces code paths from handler → DB |
| **Code Zone** | Deep static analysis on assigned source directories for anti-patterns |
| **Database Zone** | Schema analysis, query plan review, index audit, N+1 detection |
| **Infra Zone** | Runtime monitoring, container metrics, connection pool analysis, memory profiling |

Zone assignment strategy:

1. **2 agents**: Zone A = routes + benchmark, Zone B = code + database scan
2. **3 agents**: Zone A = routes + benchmark, Zone B = code anti-patterns, Zone C = database + infra
3. **4 agents**: Zone A = GET routes benchmark, Zone B = mutation routes benchmark, Zone C = code anti-patterns + static search, Zone D = database + infra + memory
4. **5–8 agents**: Split routes across multiple Route Zone agents (max 15 routes each), assign remaining agents to Code Zones (split by directory), keep 1 Database Zone and 1 Infra Zone

### Agent Prompt Template

Each spawned agent receives this structured prompt:

```text
You are a MADMAX performance analysis agent.
Zone: [ZONE_TYPE]
Assignment: [specific files, directories, or routes]

Your job:
1. [Zone-specific instructions]
2. Collect evidence with file:line references
3. Classify each finding as "confirmed" or "suspected"
4. Return your findings as a structured JSON block:

{
  "zone": "[zone_type]",
  "files_scanned": [count],
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "category": "[algorithmic|concurrency|memory|io|database|config]",
      "location": "file:line",
      "description": "...",
      "evidence": "confirmed|suspected",
      "fix": "..."
    }
  ],
  "metrics": { ... }
}
```

### Main Agent Merge

After all agents return:

1. Collect all findings into a single list.
2. Deduplicate findings that reference the same file:line.
3. Sort by severity: critical → high → medium → low.
4. Cross-reference: if a Code Zone agent flagged an N+1 and a Route Zone agent measured high p99 on the same handler, promote to `confirmed` and link them.
5. Write the unified `performance_skill/[run_id].md` report.
6. Include a MADMAX summary section showing which agents ran and what they found.

---

## Tool Acquisition

By default, use only tools already installed on the system. However, if no adequate load testing tool is available:

### When to ask

Ask the user to install a tool **only** when ALL of these are true:
- No load testing tool from the Tool Priority list is installed
- The bundled `scripts/benchmark.py` fallback is insufficient for the task (e.g., user wants open-workload testing, rate limiting, or advanced reporting)
- The tool can be installed via a simple package manager command

### How to ask

Present the recommendation clearly:

```text
No load testing tools are currently installed. The bundled Python fallback works
but doesn't support open-workload testing (constant arrival rate), which means
tail latency measurements may be inaccurate due to coordinated omission.

Recommended install (pick one):
  1. [oha]     → cargo install oha        (Rust, single binary, open-workload)
  2. [k6]      → choco install k6         (Go, scriptable, open-workload)
  3. [vegeta]  → go install github.com/tsenart/vegeta@latest  (Go, rate-limited)
  4. [hey]     → go install github.com/rakyll/hey@latest      (Go, simple)

Or I can proceed with the bundled Python fallback (closed-workload, basic metrics).

Install one of these? (reply with number, or "skip" to use fallback)
```

Rules:
- Never install anything silently.
- Never use `sudo` or admin install without explicit approval.
- If the user says "skip" or declines, proceed with the bundled fallback and note the limitation in the report.
- Only suggest tools that match the user's platform (check OS first).

---

## Workflow (Standard Mode)

1. Discover the backend stack and startup command from existing project files.
2. Check project size — if above threshold, recommend MADMAX (see Mode Selection).
3. Discover API routes and classify each endpoint before testing.
4. Check installed tools — if none adequate, ask about tool acquisition (see Tool Acquisition).
5. Check for coordinated omission risk and pick the best installed tool (see Tool Priority).
6. Run a warmup, then progressive load phases using an open workload model.
7. Collect USE + RED + Four Golden Signals telemetry alongside benchmark output.
8. Cross-reference slow endpoints with source code, runtime signals, and database signals.
9. Apply USL analysis if multiple concurrency levels were tested.
10. Write `performance_skill/[run_id].md`.
11. Ask before applying any code optimization.

## Workflow (MADMAX Mode)

1. Discover the backend stack, project size, and startup command.
2. Calculate agent count and zone assignments (see MADMAX Agent Calculation).
3. Present MADMAX plan to user with agent count + token estimate. Wait for approval.
4. Check installed tools — if none adequate, ask about tool acquisition.
5. Launch parallel agents with zone-specific prompts.
6. Main agent runs Infra Zone monitoring while Route Zone agents benchmark.
7. Collect all agent results.
8. Merge, deduplicate, cross-reference findings.
9. Apply USL analysis on aggregated benchmark data.
10. Write unified `performance_skill/[run_id].md` with MADMAX summary section.
11. Ask before applying any code optimization.

---

## Discovery

Read local documentation and config first:

- `README*`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Makefile`, `docker-compose*.yml`, `.env.example`
- OpenAPI/Swagger files, Postman/Insomnia collections, route files, controller files
- Test fixtures, seed scripts, test credentials, and local-only compose services
- ORM config: `prisma/schema.prisma`, `ormconfig.*`, `knexfile.*`, `alembic.ini`, `models/`, `migrations/`
- Middleware chains, auth guards, rate limiters, caching layers

Classify routes as:

| Class | Meaning |
|---|---|
| `SAFE_GET` | Read-only endpoint suitable for conservative benchmarking |
| `AUTH` | Login, token, session, guard, or protected-route behavior |
| `MUTATION_SAFE` | Mutation endpoint proven safe in a test environment |
| `MUTATION_UNSAFE` | Destructive or externally visible endpoint to skip |
| `UNKNOWN` | Endpoint needing user confirmation |

## Coordinated Omission Awareness

Standard closed-workload tools (wrk without rate limiting, autocannon defaults, ab) stall when the server pauses — they record one long outlier instead of the N requests that would have timed out in reality. This artificially compresses tail latency and produces false stability signals.

**Prefer open-workload tools** that fire requests at a constant arrival rate independent of response completion:

- `k6` (open workload via `constant-arrival-rate` executor) ← preferred
- `vegeta` (fixed rate mode) ← preferred
- `wrk2` / `oha` (rate-limited) ← good
- `autocannon` / `bombardier` / `ab` / `siege` ← closed-workload; acceptable for warmup only, note the limitation in the report

Always record **percentile distributions** (p50, p90, p95, p99, p99.9), never averages. The p99.9 is the primary early-warning indicator for GC pauses, lock contention, and I/O blocking.

## Tool Priority

Use installed tools only (unless user approves acquisition). Prefer structured JSON output when available.

Load testing (preferred open-workload tools first):

1. `k6` — use `constant-arrival-rate` executor for open workload
2. `vegeta` — fixed rate mode (`-rate`)
3. `oha` — rate-limited (`-q`)
4. `autocannon` — note closed-workload limitation
5. `bombardier`
6. `wrk` / `wrk2`
7. `hey`
8. `ab`
9. `siege`
10. bundled fallback: `scripts/benchmark.py`

Runtime and system monitoring (USE method — Utilization, Saturation, Errors per resource):

- Containers: `docker stats --no-stream`, `docker compose ps`, `docker compose logs`
- Processes: `ps`, `pidstat`, `/usr/bin/time -v`, `top`, `htop`
- Ports/connections: `ss`, `netstat`, `lsof`
- Linux host: `vmstat`, `iostat`, `sar`, `perf stat`
- If available: `eBPF` tools (`bpftrace`, `offcputime`, `profile`) for on-CPU and off-CPU profiling

Profiling, only on local or approved staging:

- Node.js: `node --prof`, `clinic`, `0x`, `--inspect`
- Python: `py-spy`, `scalene`, `cProfile`, `pyinstrument`
- Go: `pprof`, `go tool trace`
- Java/Kotlin: Java Flight Recorder, `jcmd`, async-profiler
- .NET: `dotnet-trace`, `dotnet-counters`, `dotnet-dump`
- Rust: `cargo flamegraph`, `perf`, `valgrind --tool=callgrind`

Database inspection, read-only unless explicitly approved:

- PostgreSQL: `EXPLAIN`, `EXPLAIN ANALYZE` only when safe, `pg_stat_statements`, `pg_stat_user_tables` (seq scan counts), index listings
- MySQL/MariaDB: `EXPLAIN`, `EXPLAIN ANALYZE` when safe, slow query log hints, `SHOW INDEX`, `SHOW TABLE STATUS`
- MongoDB: `.explain("executionStats")`, index listings, profiler status, `db.currentOp()`
- Redis/cache: `INFO`, hit rate, memory, keyspace, slow log, `MEMORY USAGE <key>`
- SQLite: `EXPLAIN QUERY PLAN`, pragma analysis

## Precision Anti-Pattern Detection

Beyond generic `grep`, use targeted multi-step detection:

### N+1 Query Detection (high-priority)

1. Search for ORM calls inside loops:
   ```
   for .* {[\s\S]*?\.(find|findOne|findMany|get|query|execute|load|fetch)
   \.forEach\(.*=>\s*{[\s\S]*?\.(find|save|update|delete|create)
   ```
2. Search for `include`/`populate`/`join` with nested relations (depth > 2)
3. Check if any route handler makes > 1 DB call without batching — count distinct query calls per handler function
4. In Prisma: search for `findMany` without `select` (fetches all columns)
5. In Sequelize/TypeORM: search for eager loading without `attributes`/`select`

### Synchronous Blocking Detection

1. Node.js event loop killers:
   ```
   fs.readFileSync|fs.writeFileSync|fs.appendFileSync
   execSync|spawnSync
   crypto.pbkdf2Sync|crypto.scryptSync
   child_process.execSync
   ```
2. Python async violations:
   ```
   time.sleep\(
   requests\.(get|post|put|delete)\(    # sync HTTP in async context
   open\(.*\)\.read\(\)                  # blocking file read in async handler
   ```
3. Go blocking patterns:
   ```
   sync\.Mutex.*Lock\(\)                 # mutex in hot path
   time\.Sleep\(                         # sleep in request handler
   ```

### Unbounded Data Patterns

```
SELECT \*
findMany\(\)                             # no where clause
\.find\(\{\}\)                           # empty MongoDB filter
\.find\(\)\.sort\(                       # sort without limit
OFFSET \d{4,}                            # large offset pagination
\.skip\(\d{4,}\)                         # large skip in MongoDB
```

### Memory Leak Indicators

```
global\s+\w+\s*=\s*\[\]                  # growing global arrays
module\.exports\.\w+\s*=\s*\[\]         # module-level mutable state
addEventListener.*without.*removeEventListener
setInterval\((?!.*clearInterval)         # intervals never cleared
new Map\(\)|new Set\(\)                  # at module scope without eviction
cache\[|cache\.set\(                     # unbounded cache without TTL/maxSize
```

### Missing Index Signals

1. Run `EXPLAIN` on queries hitting routes with p95 > 100ms
2. Look for `Seq Scan` (Postgres), `ALL` type (MySQL), `COLLSCAN` (MongoDB)
3. Check `pg_stat_user_tables.seq_scan` vs `idx_scan` ratio — high seq_scan on large tables = missing index
4. Look for WHERE clauses on columns without indexes in the ORM schema

### Connection Pool Exhaustion

```
pool.*max|maxConnections|connectionLimit    # check configured pool size
pool.*timeout|acquireTimeout               # check timeout config
getConnection|acquire\(\)                  # connection acquisition patterns
```

Cross-reference with:
- Error logs during benchmark showing "connection timeout" or "pool exhausted"
- Increasing p99 at moderate concurrency while CPU is low

### Response Payload Bloat

1. Measure response body size for each endpoint during benchmark
2. Flag any endpoint returning > 100KB per response
3. Check for missing field selection (`select`, `attributes`, `projection`)
4. Check for base64-encoded blobs in JSON responses
5. Look for `JSON.stringify` on large objects or circular reference guards

## Benchmark Plan

Default conservative profile (open workload where tool supports it):

| Phase | Duration | Target RPS / Concurrency |
|---|---:|---:|
| Warmup | 10s | 2 VUs / low rate |
| Baseline | 30s | 5 VUs / low rate |
| Moderate | 30s | 10 VUs / moderate rate |
| Higher | 30s | 25 VUs / higher rate |

Only run the next phase if the previous phase stayed healthy. For fragile apps, reduce duration or concurrency and record the change.

If no load tool is installed, run the bundled fallback from the skill directory:

```bash
python scripts/benchmark.py --url http://127.0.0.1:3000/api/health --duration 30 --concurrency 10
```

Use headers only when they are safe test credentials:

```bash
python scripts/benchmark.py --url http://127.0.0.1:3000/api/items --header "Authorization: Bearer TEST_TOKEN"
```

## Telemetry: USE + RED + Four Golden Signals

Collect three layers of signals simultaneously with benchmark runs:

**USE Method** (infrastructure per resource — CPU, memory, disk, network):
- **Utilization** — % of time resource is busy (e.g., CPU %, disk busy %)
- **Saturation** — queue depth or wait length (run queue, disk queue, connection pool wait). Saturation is the earliest warning of impending latency spikes.
- **Errors** — hardware/kernel error counts (dropped packets, disk errors)

**RED Method** (microservice / application layer):
- **Rate** — requests/sec flowing into each endpoint
- **Errors** — rate of failed requests (5xx, timeouts, connection refused)
- **Duration** — p50/p95/p99/p99.9 latency distributions

**Four Golden Signals** (Google SRE — unified view):
- **Latency** — p99 must stay below SLO during all phases
- **Traffic** — RPS throughput as concurrency grows (watch for non-linear drop = contention)
- **Errors** — roll back any applied optimization if error rate increases
- **Saturation** — most constrained resource's queue depth

Record all four in every benchmark phase. If latency rises while CPU utilization is low, suspect off-CPU wait (database locks, I/O blocking, network).

## Scalability Analysis (Universal Scalability Law)

When multiple concurrency levels have been tested, apply USL to predict true capacity limits without exhaustive testing:

```
X(N) = (γ·N) / (1 + α·(N-1) + β·N·(N-1))
```

- **γ** — linear scaling factor (ideal parallelism)
- **α** — contention penalty (lock queuing, connection pool waits) → limits throughput at 1/α asymptote
- **β** — coherency penalty (cache invalidation, distributed sync) → quadratic; causes retrograde scaling where adding concurrency *decreases* throughput
- **N_max** — predicted safe concurrency ceiling: `floor(sqrt((1-α)/β))`

Fit α and β using collected RPS-vs-concurrency data points. If α is high → investigate sequential bottlenecks and lock contention. If β is high → investigate state-sharing and inter-process communication.

Report USL coefficients and N_max when at least 3 concurrency levels were tested.

## Bottleneck Review

For each slow or error-prone endpoint, connect measurements to likely causes using the following hierarchy:

**Algorithmic / Structural (highest impact):**
- O(n²) or worse loops in hot paths — look for nested iterations over collections
- Missing indexes, full table scans, expensive joins, slow aggregations
- N+1 queries, unbounded `find`/`findMany`, broad `include`/`populate`
- Missing pagination, large response payloads, excessive JSON serialization (check `JSON.stringify` on large objects)

**Concurrency / Resource contention:**
- Mutex lock contention or global lock serializing parallel work (high α in USL)
- Database connection pool exhaustion under load
- Thread pool saturation — queued requests waiting for worker slots
- Synchronous CPU-heavy work blocking the event loop (Node.js) or main thread

**Memory / Cache issues:**
- Memory growth across requests → likely leak or object accumulation surviving GC
- Cache misses on hot data (check Redis hit rate via `INFO stats → keyspace_hits/misses`)
- Cache stampede (thundering herd) on high-traffic cache keys — consider Probabilistic Early Expiration
- GC pressure causing stop-the-world pauses → visible as p99.9 spikes with low CPU otherwise

**I/O / Network:**
- Blocking file I/O on async runtimes (`fs.readFileSync`, sync DB drivers)
- Repeated auth/session/database lookups per request that could be cached
- Missing HTTP keep-alive or connection pooling to downstream services
- Repeated external API calls without batching or caching

**Database-specific:**
- B-Tree index missing for read-heavy OLTP queries → full scans visible in EXPLAIN
- Unbounded queries without LIMIT
- Missing composite indexes for multi-column WHERE clauses
- Write amplification under heavy insert/update → consider batch writes

Use `confirmed` only when measurement or source evidence supports the cause. Otherwise write `suspected`.

## Statistical Regression Detection

When comparing before/after optimizations, do not rely on averages or simple thresholds:

- Use **Mann-Whitney U test** (non-parametric) to compare p99 latency distributions — it handles skewed, non-Gaussian data correctly
- Reject the null hypothesis at p-value ≤ 0.05 to confirm the optimization had a statistically significant effect
- Calculate effect size `r = 1 - (2U)/(n1·n2)` — values > 0.5 indicate a large shift
- If comparing more than two variants, use the **Kruskal-Wallis test**
- Do not claim improvement unless these tests confirm it with the before/after benchmark data

## Report Format

Create `performance_skill/` and write `performance_skill/[run_id].md`.

```markdown
# Run: [run_id]

Target: [local/staging URL or startup command]
Mode: [Standard | MADMAX (N agents)]
Tool: [tool used, workload model (open/closed)]
Stack: [detected stack]
Date: [ISO timestamp]

## Summary

- Tested: [n] endpoints
- Skipped: [n] endpoints
- Worst p99: [METHOD] [route] - [latency]ms
- Highest error rate: [METHOD] [route] - [error_rate]%
- Main risk: [one-line summary]
- USL N_max: [predicted safe concurrency ceiling, or "not computed"]
- Coordinated omission risk: [low/medium/high — based on tool used]

## Telemetry Snapshot

| Phase | RPS | p50 | p99 | p99.9 | Err% | CPU% | Mem | Queue |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Warmup | ... | ... | ... | ... | ... | ... | ... | ... |
| Baseline | ... | ... | ... | ... | ... | ... | ... | ... |
| Moderate | ... | ... | ... | ... | ... | ... | ... | ... |
| Higher | ... | ... | ... | ... | ... | ... | ... | ... |

## Bottlenecks

| # | Severity | Endpoint / Location | p99 | Evidence | Cause |
|---:|---|---|---:|---|---|
| 1 | critical | `[METHOD] /route` — `file:line` | [ms] | confirmed | [cause] |

## Proposed Fixes

1. **[severity]** `[file:line]` — [brief fix]
2. **[severity]** `[file:line]` — [brief fix]

## MADMAX Agent Summary (if MADMAX mode)

| Agent | Zone | Files Scanned | Findings | Critical |
|---:|---|---:|---:|---:|
| 1 | Route Zone (GET) | ... | ... | ... |
| 2 | Code Zone | ... | ... | ... |

## Skipped

- `[METHOD] /route` — [reason]

## Commands

```bash
[exact benchmark and monitoring commands used]
```

## Approval Required

No code changes were applied. Ask the user before implementing fixes.
```

Keep the report short. Prefer tables over paragraphs.

## Response To User

After writing the report, answer briefly:

```text
Benchmark complete. Report saved to performance_skill/[run_id].md.
Mode: [Standard | MADMAX (N agents)]

Top bottlenecks:
1. [severity] [METHOD route] - p99 [x]ms - [cause]
2. [severity] [METHOD route] - p99 [x]ms - [cause]
3. [severity] [METHOD route] - p99 [x]ms - [cause]

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
3. Re-run the exact same benchmark command at the same concurrency.
4. Write `performance_skill/[run_id]-after.md` with the same telemetry table format.
5. Run Mann-Whitney U test on p99 distributions from both runs. Do not claim improvement unless the p-value ≤ 0.05 and effect size r > 0.1.
6. Compare before and after in a summary table. Do not claim improvement unless measured.

## Quick Reference: Optimization Signals

| Signal | Likely Cause | Investigation Path |
|---|---|---|
| High p99, low CPU | Off-CPU wait (DB lock, I/O) | `offcputime` eBPF, `EXPLAIN ANALYZE`, connection pool stats |
| High CPU, low p99 | Algorithm O(n²), no caching | flame graph, static code search for nested loops |
| Memory grows continuously | Leak, GC pressure, no eviction | heap dump / `--inspect`, GC logs, cache policy review |
| Throughput drops as concurrency rises | Lock contention (high USL α) | mutex/lock profiling, pool size, serial bottleneck |
| Throughput retrograde at high concurrency | Coherency overhead (high USL β) | reduce state-sharing, batch operations, reduce cross-service sync |
| p99.9 spikes with stable p99 | GC stop-the-world, cache stampede | GC logs, probabilistic early expiration for hot cache keys |
| Errors spike under load | Connection pool exhaustion, timeout | pool size config, retry logic, circuit breaker |
| Response > 100KB | Missing field selection, payload bloat | add `select`/`projection`, remove base64 blobs from JSON |
| p99 > 100ms on single GET | N+1 queries, missing index | EXPLAIN output, count DB calls per request, check ORM eager loading |
| Latency rises linearly with data size | Missing pagination, unbounded query | add LIMIT, cursor pagination, check OFFSET values |
