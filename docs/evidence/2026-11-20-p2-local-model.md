# Local model planner evidence

Recorded 2026-11-20 on a MacBook Air (Apple silicon) with Docker Desktop, Docker Model Runner
(`llama.cpp b9879-metal`), Docker Agent v1.163.0 installed with Homebrew, and `ai/qwen3:4b`.
The transcripts contain model reasoning, so this file keeps only metadata: event types, tool
names, token counts, timings, and the host's decisions.

## Runs

| Run | Configuration | Tool calls, in order | Host decision | Duration |
| --- | --- | --- | --- | --- |
| 1 | stdio server per session, structured output in tool mode | `__structured_output__` with `[10, 11]` | Verifier accepted. The evidence gate, added after this run, rejects it: no `forecast_day` call | about 6.5 min |
| 2 | Same | `__structured_output__` with `[12, 13, 14]` | Gate rejected: no `forecast_day` call | not recorded |
| 3 | HTTP server in a running container, tool mode | `forecast_day` | Docker Agent failed: `HTTP 400: Cannot have 2 or more assistant messages at the end of the list` | not recorded |
| 4 | Same, `thinking_budget: none` | `forecast_day` | Same HTTP 400. The current gate rejects the transcript's text answer with `Extra data` | 12 min 21 s |
| 5 | HTTP server, plain JSON answer | `forecast_day` | Gate passed, verifier accepted `[10, 11]` with 600 Wh | 6 min 11 s |
| 6 | Same, engine context 4,096 tokens | `forecast_day` | Gate passed, verifier accepted `[10, 11]` with 600 Wh | 4 min 31 s |

Runs 5 and 6 produced 1,665 and 1,807 reasoning events and 1,322 and 1,314 output tokens in the
final model turn. The task used about 2,200 tokens of context.

## Why the first runs had no tool

```console
$ docker agent debug toolsets lab/agent/solar-planner.yaml
No tools for root
```

The debug log of that command, with the stdio server started by `docker run`:

```text
14:58:24.781 Starting MCP toolset server=docker
14:58:55.026 Toolset start still running; skipping for this turn cause="context deadline exceeded"
14:59:09.027 Started MCP toolset successfully server=docker
```

| Check | Time to a ready MCP session |
| --- | --- |
| Docker Agent, server started with `docker run` over stdio | about 44 s, past the 30 s turn budget |
| Python MCP client, the same `docker run` command over stdio | 1.96 s |
| Docker Agent, the same server run with the host Python over stdio | 0.75 s |
| Python MCP client, the server already running in a container over HTTP (Linux test host) | 1.4 s to ready, then immediate |
