# Pipelines

Multi-step workflow definitions and orchestration patterns.

## Purpose

Pipelines define **high-level workflows** that coordinate multiple execution scripts.

They describe the "what and when" of complex operations:
- Which steps execute in what order
- Dependencies between steps
- Conditional branching logic
- Error handling and retry policies
- Data flow between steps

## Responsibility

Pipelines are responsible for:
- Defining multi-step workflow structures
- Declaring step dependencies and sequencing
- Specifying retry and failure handling policies
- Documenting data contracts between steps
- Providing workflow-level configuration

## What Pipelines Are NOT

**Pipelines are descriptive, not operational.**

### Pipelines vs Execution Scripts

| Aspect | Pipelines | Execution Scripts |
|--------|-----------|-------------------|
| Purpose | Define workflow structure | Do the actual work |
| Location | `/pipelines` | `/execution` |
| Contains | Step definitions, order, config | Deterministic logic, API calls |
| Runs | Via orchestrator/worker | Directly as Python functions |
| Imports | No execution imports | Can import libraries, models |

### What Does NOT Belong in Pipelines

- **No execution logic** - pipelines describe, execution scripts do
- **No API calls or I/O** - those belong in `/execution`
- **No database queries** - handled by execution scripts
- **No LLM calls** - execution layer responsibility
- **No side effects** - pipelines are pure definitions

## Architecture Pattern

```
Directive (SOP)
    ↓
Pipeline Definition (workflow structure)
    ↓
Orchestrator (worker/scheduler)
    ↓
Execution Scripts (actual work)
```

Pipelines sit between directives and execution, translating human intent into machine-executable workflows.

## When to Create a Pipeline

Create a pipeline when:
- A workflow has 3+ sequential steps
- Steps have dependencies or need specific ordering
- The same sequence will be reused/scheduled
- Error handling varies by step
- Different steps may run in parallel

Do NOT create a pipeline for:
- Single-step operations (just call execution script)
- One-off tasks (use directives + manual orchestration)
- Operations with no clear step boundaries

## Current Pipelines

### `job_discovery.py` (placeholder)
Skeleton for job discovery and parsing workflow.
Not yet operational.
