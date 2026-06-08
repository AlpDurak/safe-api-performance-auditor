# Safe API Performance Auditor

A public agent skill for safely benchmarking local or approved staging backend APIs, finding likely bottlenecks, and proposing fixes without changing code first. Supports **MADMAX mode** for parallel deep-scan auditing of large codebases.

## GitHub description

Safe local/staging API performance audits for Claude Code and Codex, with bottleneck reports, MADMAX parallel agent mode, and approval-gated optimization suggestions.

## What it helps with

- Discover backend routes and classify safe vs unsafe endpoints
- Run conservative load tests with installed tools such as `k6`, `oha`, `autocannon`, `wrk`, `hey`, `vegeta`, or the bundled Python fallback
- Check CPU, memory, containers, database hints, and common source-code performance issues
- Detect N+1 queries, synchronous blocking, memory leaks, connection pool exhaustion, and payload bloat with precision regex patterns
- Write a short report to `performance_skill/[run_id].md`
- Ask for approval before applying any optimization

## Modes

### Standard Mode

One agent runs the full audit sequentially: discovery → benchmark → analysis → report. Best for small/medium projects.

### MADMAX Mode 🔥

For large codebases where a single-pass audit would miss deep bottlenecks. MADMAX launches **parallel agents** that split the codebase into focused zones and scan simultaneously.

**How it activates:**

1. **User request** — say "MADMAX", "go MADMAX", or "madmax mode" in your prompt
2. **Auto-detection** — the agent measures the project and recommends MADMAX when it exceeds:
   - 150+ source files, or
   - 30,000+ lines of code, or
   - 40+ API routes

**How many agents?**

The main agent calculates based on project size:

```
base_agents  = ceil(source_files / 80)
route_agents = ceil(route_count / 15)
agent_count  = clamp(max(base_agents, route_agents), 2, 8)
```

Each agent uses approximately **~25k tokens**. The agent shows you the total cost estimate before launching.

**What each agent does:**

| Zone          | Responsibility                                                         |
| ------------- | ---------------------------------------------------------------------- |
| Route Zone    | Benchmarks assigned endpoints, traces handler → DB code paths          |
| Code Zone     | Deep static analysis for anti-patterns (N+1, sync blocking, leaks)     |
| Database Zone | Schema audit, EXPLAIN plans, index coverage, query pattern review      |
| Infra Zone    | Container metrics, connection pools, memory profiling, runtime signals |

After all agents finish, the main agent merges findings, deduplicates, cross-references (e.g., N+1 detected in code + high p99 measured on same route = confirmed), and writes a single unified report.

**Example prompt:**

```text
Use $safe-api-performance-auditor in MADMAX mode to deep-audit my local API.
```

## Tool Acquisition

The agent uses whatever load testing tools are already installed. If none are available, it will **ask you** before installing anything — never silently.

It recommends lightweight single-binary tools like `oha`, `k6`, or `vegeta` that support open-workload testing (constant arrival rate), which produces more accurate tail latency measurements.

You can always decline and use the bundled Python fallback instead.

## Agent support

This skill is agent-neutral at its core:

- Claude Code reads `SKILL.md` and can run `scripts/benchmark.py`.
- Codex reads the same `SKILL.md`; `agents/openai.yaml` only adds optional Codex UI metadata.
- Claude does not need `agents/openai.yaml` and can safely ignore it.

## Install

The easiest way to install this skill into your project is using `npx skills add`:

```bash
npx skills add https://github.com/AlpDurak/safe-api-performance-auditor
```

For older local agent setups (like Codex) that don't support `npx skills add`, you can clone the repository manually:

```bash
git clone https://github.com/AlpDurak/safe-api-performance-auditor.git ~/.claude/skills/safe-api-performance-auditor
```

## Use

Open a backend project and ask your agent:

```text
Use $safe-api-performance-auditor to benchmark my local API and report bottlenecks.
```

You can also provide a target:

```text
Use $safe-api-performance-auditor on http://127.0.0.1:3000. Only test safe read endpoints.
```

For large projects, activate MADMAX:

```text
Use $safe-api-performance-auditor in MADMAX mode on my Go backend.
```

## Safety defaults

The skill does not benchmark production by default, skips destructive or externally visible endpoints, avoids global installs, and never edits application code unless you approve.

## Fallback benchmark tool

If no load-testing tool is installed, the skill can run:

```bash
python scripts/benchmark.py --url http://127.0.0.1:3000/api/health --duration 30 --concurrency 10
```

## Repository contents

- `SKILL.md` — the agent-facing workflow (Standard + MADMAX modes)
- `scripts/benchmark.py` — bundled fallback HTTP benchmark tool
- `agents/openai.yaml` — optional Codex UI metadata, ignored by Claude
- `docs/optimization-intel.md` — deep optimization knowledge base (algorithmic, memory, concurrency, I/O)
- `docs/performance-testing-intel.md` — testing methodology reference (USL, coordinated omission, statistical validation)

## License

MIT
