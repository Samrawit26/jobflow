# JobFlow

## What it is

JobFlow is a **secure, approval-gated workflow execution system** that uses LLM-based planning with deterministic execution. It separates plan generation (probabilistic LLM) from plan execution (deterministic scripts), enforcing cryptographic approval artifacts before any action is taken. Think of it as "infrastructure as code" meets "plans as code with mandatory human/policy approval." Every execution requires explicit authorization, is fully auditable, and protects against plan tampering through SHA-256 hashing.

## Current status

- ✓ **Directive planning (read-only)**: LLM-based plan generation using OpenAI API
- ✓ **Plan review (fail-safe)**: Defaults to rejection; requires explicit approval
- ✓ **Policy auto-approval**: Allowlist-based, zero-risk, forbidden-keyword enforcement
- ✓ **Approval artifacts**: Cryptographic SHA-256 hashing binds approvals to exact plans
- ✓ **Execution gating**: Impossible to execute without valid approval artifact
- ✓ **CLI tools**: `review`, `approve`, `execute` commands for complete workflow
- ✓ **Comprehensive tests**: 178 passing tests (core + CLI)
- ✓ **Auditability**: Full metadata tracking (who approved, when, scope, plan details)

## Architecture

```
┌──────────────┐
│  Directive   │  (Human-readable SOP in /directives)
│ (job_disc.md)│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Planner    │  (LLM reads directive, generates structured plan)
│  (OpenAI)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Plan Review  │  (Fail-safe gate: policy checks or default rejection)
│  + Policy    │
└──────┬───────┘
       │
       ├─[rejected]─► Exit (no execution)
       │
       └─[approved]─► Create Approval Artifact (SHA-256 hash + metadata)
                      │
                      ▼
                   ┌──────────────┐
                   │  Executor    │  (Verify artifact, resolve pipeline, execute)
                   │ (orchestrator)│
                   └──────────────┘
```

## Quickstart

**Step 1: Review a directive (dry-run, never executes)**
```bash
python -m jobflow.scripts.review job_discovery --auto-approve
```

**Step 2: Issue approval artifact (never executes)**
```bash
python -m jobflow.scripts.approve job_discovery \
  --approved-by "policy" \
  --auto-approve \
  --out approval.json
```

**Step 3: Execute with approval artifact**
```bash
python -m jobflow.scripts.execute job_discovery \
  --approval approval.json \
  --payload data.json
```

**Note**: Requires `OPENAI_API_KEY` environment variable for LLM-based planning.

## Repo structure

- `/directives` — Human-readable SOPs and runbooks (plain language)
- `/jobflow/app/core` — Plan executor, orchestrator, approval gates, policies
- `/jobflow/app/services` — LLM planner (OpenAI integration)
- `/jobflow/scripts` — CLI tools (review, approve, execute)
- `/execution` — Deterministic scripts (one responsibility each)
- `/pipelines` — Pipeline definitions (orchestrated workflows)
- `/tests` — Unit and integration tests (mirrors execution structure)
- `/alembic` — Database migrations
- `CLAUDE.md` — Operating rules for AI coding agents

## Safety model

- **No execution without approval**: Every execution requires a valid approval artifact; no bypasses, no defaults
- **Cryptographic verification**: Approval artifacts use SHA-256 hashing to detect any plan tampering
- **Explainable decisions**: All approval/rejection decisions include detailed reasons (policy failures, risk counts, forbidden keywords)
- **Auditability**: Full metadata tracking (directive name, plan hash, approver, timestamp, scope) in every execution result
- **Separation of concerns**: Review (dry-run) → Approve (artifact issuance) → Execute (verified execution) are distinct, isolated steps
