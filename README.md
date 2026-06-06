# 🤖 manin-jarvis

A personal AI majordomo engine for **Claude Code** — the orchestration layer, doctrine
system, routines, and guardrails that turn a coding assistant into a persistent personal
assistant with memory, autonomy rules, and self-validation.

> **This is a sanitized template.** It's the *engine and doctrine structure* of a real,
> daily-driven personal assistant — with all personal content stripped and replaced by
> fill-in-the-blank templates. Copy it, make it yours.

---

## The idea

Most "personal AI" setups are a system prompt and a prayer. This one treats the assistant
as a **butler with a soul, a memory, and house rules** that survive across sessions:

- **A SOUL** — a stable persona: tone, how much autonomy it has, what it does on its own vs.
  what needs your confirmation, how it validates its own work before reporting back.
- **A tiered memory** — facts live in files, loaded *only when relevant* (HOT every session,
  WARM on context match, COLD on demand). The assistant knows a fact exists before reading it.
- **A decision log** — dated, dense, append-only. The source of truth when a new idea
  contradicts a past choice.
- **Routines** — opt-in scheduled jobs (morning brief, weekly review, prod watchtower,
  self-evaluation) with a manual dispatcher so nothing runs the LLM behind your back.
- **Guardrails** — hooks that enforce the rules mechanically (sequential git ops, memory-size
  caps, large-file watch, anti-recursion).

The companion **cockpit** that drives several of these majordomos in parallel lives in a
separate repo: [`thousand-sunny`](https://github.com/ibhugeloo/thousand-sunny).

---

## Architecture

```
memory/      ← the doctrine (persona, profile, decisions, dreams, workflows, tools)
                loaded into the assistant's context — HOT files every session
share/       ← prompts for each routine (brief, weekly, eval, watchtower…) + missions
bin/         ← the engine: dispatcher, search, routines, hooks, guards, dashboard server
docs/        ← how each subsystem works (one doc per subsystem)
config/      ← per-project config (watchtower, finance, deploys…) — *.example.yaml here
LaunchAgents/← macOS launchd templates for the scheduled routines
claude-config/← Claude Code hooks + slash commands + the CLAUDE.md @import list
mos/         ← Mission OS: bounded tasks with state (FastAPI + SQLite)
tests/       ← doctrine scenarios — the persona's rules are *tested*, not just written
plugins/     ← skeleton for extending the assistant
```

### The memory model

| Tier | When loaded | What goes there |
|------|-------------|-----------------|
| 🔥 HOT | every session (`@import` in `CLAUDE.md`) | persona, profile, decisions, core workflows |
| 🌤️ WARM | on context match (cwd / keywords) | one file per project or domain |
| 🧊 COLD | only on explicit request | archives, history, raw logs |

Rule of admission to HOT: only what's relevant in ≥ 50% of sessions, or high blast-radius
(a prod guardrail). Everything else stays WARM. *"The garage must not become the house."*

### Multiple majordomos

The pattern supports more than one assistant identity — e.g. a **contrarian second opinion**
running a different model, and a **scoped sysadmin** for infra. Each has its own persona file;
the cockpit gives each a colored session. See `docs/majordomes.md`.

---

## Getting started

> Requires [Claude Code](https://claude.com/claude-code). Built and daily-driven on macOS.

```bash
git clone https://github.com/ibhugeloo/manin-jarvis.git
cd manin-jarvis

# 1. Turn the templates into your real doctrine
for f in memory/*.example.md;  do cp "$f" "${f%.example.md}.md"; done
for f in config/*.example.yaml; do cp "$f" "${f%.example.yaml}.yaml"; done

# 2. Fill them in — start with memory/jarvis_soul.md (tone + autonomy) and memory/profil.md
# 3. Wire the @imports and hooks, then install
./bootstrap.sh
```

`bootstrap.sh` symlinks the `bin/` scripts into `~/.local/bin`, wires the Claude Code hooks,
and (optionally) installs the launchd routines. Read it before running — it touches your shell
environment.

**Start minimal.** Fill in the SOUL and profile, skip every automatic routine at first, run
things by hand for a couple of weeks. Automate a routine only once you notice you run it daily.

---

## Philosophy

- **Confirm before irreversible or outward-facing actions.** Drafts, local commits, and reads
  are free; sends, pushes, and deletes need a yes.
- **State operations are sequential.** One mutating git/deploy command at a time, verified,
  before the next. Batching them hides errors.
- **No bluffing.** If the assistant can't find something, it says so — it doesn't invent.
- **Self-validate before reporting.** "Tests pass" is not "ready for production."

---

## License

MIT — see [`LICENSE`](./LICENSE). This repo is a **sanitized reference**; the real personal
memory (profile, decisions, sessions) is never committed. Adapt the doctrine to your own life,
and keep your filled-in `*.md` / `*.yaml` out of any public repo.
