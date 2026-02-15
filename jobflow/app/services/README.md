# Services Layer

Service layer for external integrations and orchestration.

Responsible for:
- External API clients
- Third-party integrations
- Service orchestration
- Cross-service communication

---

## Planners

Planners use LLMs to analyze directives and generate execution plans.

**Important:** Planners are **advisory only**. They:
- Read directive documents and generate suggested plans
- Provide structured output (pipeline_name, steps, risks, assumptions)
- Do NOT execute code, modify files, or interact with databases
- Do NOT have access to orchestrator, pipelines, execution modules, or models
- Serve as a planning aid for the orchestration layer

The orchestrator decides whether to use planner suggestions or follow deterministic logic.
