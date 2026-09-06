# CAPTAIN: Coding Agent Contract

This is a persistent coding-agent contract. It strictly instructs future coding agents.

## Mandatory Startup Procedure
Before modifying code, read these files in order:
1. `CLAUDE.md`
2. `README.md`
3. `docs/ARCHITECTURE.md`
4. `docs/RESEARCH_SPEC.md`
5. `project_state/CURRENT_STATE.md`
6. `project_state/COMPLETED_MODULES.md`
7. `project_state/NEXT_TASK.md`

Then inspect relevant source code and tests. **Never assume the repository matches an earlier prompt. The repository is the source of truth.**

## Scope Discipline
- Implement only the requested stage.
- Do not implement future modules prematurely.
- Do not redesign completed modules without reason.

## Interface Stability
- Existing public interfaces should remain stable unless explicitly required.
- If changing: document why, update tests, update architecture docs, record in `CHANGELOG.md`.

## Research Integrity  
- Never fabricate: research results, benchmark scores, citations, algorithm performance, statistical significance, novelty claims.
- Do not turn speculative ideas into established research claims.

## Dependency Discipline
- Do not add dependencies without necessity.
- When adding: explain why stdlib is insufficient, add through `pyproject.toml`, document significant architectural dependencies.

## Testing
- Every implemented behavior must have tests.
- Before completion: run tests, run full suite, run linting, run type checks.
- Never claim tests passed without executing them.

## Documentation
- After completing a stage, update: `CURRENT_STATE.md`, `COMPLETED_MODULES.md`, `NEXT_TASK.md`, `CHANGELOG.md`.

## No Hidden Failure
- If something can't be completed: state what remains, explain why, don't mark complete.

## Research-Code Separation
- Infrastructure separate from research algorithms.
- Research algorithms in identifiable modules with documented specs.

## Determinism
- Research functionality should be deterministic where possible, random behavior must support explicit seeds.

## External Systems
- External integrations through adapters.
- Core logic must not depend on vendor-specific response objects.
