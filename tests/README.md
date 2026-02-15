# Tests

Automated tests (unit + integration).

**Testing is mandatory.**

## Structure
Mirrors the structure of `/execution` and `/jobflow` folders.

## Test Types

### Unit Tests
- All non-trivial execution logic must have unit tests
- Pure logic tested without I/O
- External dependencies mocked
- Must be fast, deterministic, and run locally

### Integration Tests
- May touch dev sandboxes, test sheets, mock APIs
- Never touch production
- Require explicit opt-in (env flag or CI label)

### Coverage Requirements
- Unit tests for all execution scripts
- Integration tests for critical workflows
- Worker/pipeline routing logic verified
