---
name: prune-mem-skill
description: "Use when you want pruning-first long-term memory for an assistant, including transcript extraction, recall, pruning, and evaluation."
---

# prune-mem-skill

## Role

This skill provides a Codex-native memory workflow.

When this skill is active, Codex must treat memory as part of the default turn lifecycle. Do not wait for the user to manually ask for memory commands.

This skill is an instruction-level hook. It does not rely on a platform lifecycle API. Codex itself must execute the workflow below every time the skill is relevant.

## Required Turn Protocol

### Rule 1: Pre-turn recall is default

Before writing a substantial answer, Codex should ask:

- does this request depend on user preference, long-running project context, working style, tooling habits, or durable constraints?

If the answer is yes or even maybe, Codex must recall memory first.

Run:

```bash
python scripts/prepare_context.py <optional-tag-1> <optional-tag-2>
```

Codex should then silently use the recalled memories as context for the answer.

### Rule 2: Post-turn writeback is default

Before finalizing the turn, Codex should ask:

- did the user reveal durable memory worth keeping?

If yes, Codex must write memory back in the same turn.

Run:

```bash
python scripts/remember_text.py "RAW_USER_MESSAGE" <optional-tag-1> <optional-tag-2>
```

### Rule 3: Memory should be silent by default

Do not narrate memory mechanics unless the user asks.

Good default behavior:

- use recalled memory silently
- update durable memory silently
- mention memory only when the user asks to inspect, explain, export, or debug it

### Rule 4: Maintenance should happen without user prompting

During long-running sessions, after multiple memory writes, or when the user is doing sustained work on a project, Codex should occasionally prune memory in the background.

Run:

```bash
python scripts/maintain_memory.py
```

### Rule 5: Avoid over-remembering

Only remember:

- stable preferences
- long-running projects
- persistent constraints
- working style
- recurring tooling/workflow facts

Do not remember:

- one-off tasks
- temporary mood
- speculative traits
- private data unrelated to future assistance

## Default Lifecycle Summary

For each relevant turn:

1. recall when relevance is plausible
2. answer using memory silently
3. remember durable new facts before the turn ends
4. prune occasionally during long sessions

## Layout

- Skill wrapper script: `scripts/run_prune_mem.py`
- Fast helpers:
  - `scripts/prepare_context.py`
  - `scripts/remember_text.py`
  - `scripts/remember_transcript.py`
  - `scripts/recall_memory.py`
  - `scripts/maintain_memory.py`
- Default local state root: `~/.codex/memories/prune-mem-skill`
- Default local memory workspace: `~/.codex/memories/prune-mem-skill/workspace`
- Optional override config: `~/.codex/memories/prune-mem-skill/config.local.toml`

## Commands

Inspect memory:

```bash
python scripts/run_prune_mem.py report --emit
python scripts/run_prune_mem.py explain --slot-key response_style --emit
```

## Model Config

If you want real model extraction without manually exporting environment variables each time, create `config.local.toml` under `~/.codex/memories/prune-mem-skill/`.

Example:

```toml
[openai_compatible]
model = "gpt-4.1"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
```

Or set the key directly:

```toml
[openai_compatible]
model = "gpt-4.1"
api_key = "YOUR_KEY"
```

## Notes

- The installed skill vendors the engine locally, so it still works after copying into the Codex skills directory.
- Prefer automatic workflow over exposing low-level commands to end users.
- Use low-level commands only when debugging or auditing behavior.
- The core default is: recall first, answer, then remember.
