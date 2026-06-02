# Safe API Performance Auditor

A public agent skill for safely benchmarking local or approved staging backend APIs, finding likely bottlenecks, and proposing fixes without changing code first.

## GitHub description

Safe local/staging API performance audits for Claude Code and Codex, with bottleneck reports and approval-gated optimization suggestions.

## What it helps with

- Discover backend routes and classify safe vs unsafe endpoints
- Run conservative load tests with installed tools such as `k6`, `oha`, `autocannon`, `wrk`, `hey`, `vegeta`, or the bundled Python fallback
- Check CPU, memory, containers, database hints, and common source-code performance issues
- Write a short report to `performance_skill/[run_id].md`
- Ask for approval before applying any optimization

## Agent support

This skill is agent-neutral at its core:

- Claude Code reads `SKILL.md` and can run `scripts/benchmark.py`.
- Codex reads the same `SKILL.md`; `agents/openai.yaml` only adds optional Codex UI metadata.
- Claude does not need `agents/openai.yaml` and can safely ignore it.

## Install

For Claude Code:

```bash
git clone https://github.com/AlpDurak/safe-api-performance-auditor.git ~/.claude/skills/safe-api-performance-auditor
```

PowerShell:

```powershell
git clone https://github.com/AlpDurak/safe-api-performance-auditor.git "$env:USERPROFILE\.claude\skills\safe-api-performance-auditor"
```

For Codex:

```bash
git clone https://github.com/AlpDurak/safe-api-performance-auditor.git ~/.agents/skills/safe-api-performance-auditor
```

Older Codex setups may use `~/.codex/skills`.

## Use

Open a backend project and ask your agent:

```text
Use $safe-api-performance-auditor to benchmark my local API and report bottlenecks.
```

You can also provide a target:

```text
Use $safe-api-performance-auditor on http://127.0.0.1:3000. Only test safe read endpoints.
```

## Safety defaults

The skill does not benchmark production by default, skips destructive or externally visible endpoints, avoids global installs, and never edits application code unless you approve.

## Fallback benchmark tool

If no load-testing tool is installed, the skill can run:

```bash
python scripts/benchmark.py --url http://127.0.0.1:3000/api/health --duration 30 --concurrency 10
```

## Repository contents

- `SKILL.md` - the agent-facing workflow
- `scripts/benchmark.py` - bundled fallback HTTP benchmark tool
- `agents/openai.yaml` - optional Codex UI metadata, ignored by Claude

## License

MIT
