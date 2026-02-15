# Execution Scripts

Deterministic tools and scripts (Layer 3).

## Purpose

Execution scripts **do the actual work**.

They are the operational layer that:
- Makes API calls
- Processes and transforms data
- Performs database operations
- Handles file I/O
- Executes scheduled tasks
- Implements business rules

## Core Principles

### Determinism
Every execution script must be **repeatable and predictable**:
- Same inputs → same outputs (for pure functions)
- No hidden state or global variables
- Explicit dependencies
- Idempotent where possible

### Single Responsibility
One script = one clear responsibility:
- `normalize_job_posting.py` - normalizes job data (pure function)
- `fetch_jobs.py` - fetches jobs from external sources
- `store_jobs.py` - saves jobs to database
- NOT `process_everything.py` ❌

### Testability
All logic must be importable and testable:
- Core logic in pure functions when possible
- External dependencies (DB, APIs) passed as parameters
- Side effects isolated and mockable
- Unit tests required for all non-trivial logic

## Requirements

**Every execution script must:**
- ✅ Be repeatable and deterministic
- ✅ Be testable (with unit tests in `/tests`)
- ✅ Be auditable (clear inputs/outputs)
- ✅ Have a single, clear responsibility
- ✅ Handle errors explicitly
- ✅ Be safe to rerun (idempotent when possible)

**Execution scripts must NOT:**
- ❌ Contain orchestration logic (that's for workers/pipelines)
- ❌ Include LLM prompts (those belong in `/directives` if needed)
- ❌ Make decisions about workflow (that's orchestration)
- ❌ Have global state or hidden dependencies

## Categories of Execution Scripts

### 1. Pure Functions
Functions with no side effects:
- Data transformation
- Validation
- Parsing and normalization
- Business rule calculations

**Example:** `normalize_job_posting.py`

### 2. I/O Operations
Functions that interact with external systems:
- API calls
- Database queries/writes
- File operations
- External service integration

**Best Practice:** Separate pure logic from I/O for easier testing.

### 3. Scheduled Jobs
Scripts designed to run on a schedule:
- Data sync operations
- Cleanup tasks
- Report generation
- Health checks

## Testing

Every execution script must have unit tests in `/tests/execution/`.

See `/tests/execution/test_normalize_job_posting.py` for example.

## Current Scripts

### `normalize_job_posting.py`
Pure function that normalizes raw job posting data into consistent format.
- Input: Raw job posting dict
- Output: Normalized job posting dict
- Type: Pure function (no I/O)
- Tests: `/tests/execution/test_normalize_job_posting.py`
