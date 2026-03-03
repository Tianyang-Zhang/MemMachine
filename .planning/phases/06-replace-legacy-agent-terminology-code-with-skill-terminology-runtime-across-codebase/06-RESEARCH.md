# Phase 06 Research

## Current State Findings

- Retrieval runtime still uses `agent` naming in multiple core contracts:
  `AgentToolBase`, `AgentToolBaseParam`, `agent_name`, and metric fields such
  as `selected_tool`.
- `src/memmachine/retrieval_agent/agents/` remains the runtime strategy module
  namespace even after top-level migration to `RetrieveSkill`.
- Evaluation scripts and helper APIs still expose "agent" language
  (`agent_name`, "Agent used", `agent_mode` docs), which conflicts with the
  new skill-first design intent.
- Test suites assert legacy labels (`MemMachineAgent`, `SplitQueryAgent`,
  `ChainOfQueryAgent`, `ToolSelectAgent`) as canonical outputs.

## Migration Strategy

1. **Interface-first cutover**
   - Introduce canonical skill contract naming (`skill_name`, `SkillToolBase`)
     and keep minimal compatibility aliases temporarily.
2. **Runtime/contract normalization**
   - Convert retrieval runtime outputs, route decisions, and markdown tool
     contracts to skill terminology.
3. **Caller and test cleanup**
   - Update evaluation scripts, API docs, and tests to consume skill labels.
   - Remove compatibility aliases once all callers are migrated.

## Risks and Mitigations

- **Risk:** Broad renames can break imports across runtime/tests.
  - **Mitigation:** Execute in waves with targeted compatibility shims and
    per-wave test coverage.
- **Risk:** Metric consumers rely on legacy fields.
  - **Mitigation:** Add explicit migration in benchmarks and API response
    assertions before removing aliases.
- **Risk:** Hidden legacy references remain after refactor.
  - **Mitigation:** Add grep-based guard checks for retrieval runtime paths in
    final verification.
