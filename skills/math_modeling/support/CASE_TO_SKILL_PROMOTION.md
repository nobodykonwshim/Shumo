# Case-to-Skill Promotion Policy

## Purpose

This policy prevents Shumo from becoming a collection of one-off competition solutions. Every case study must either improve a reusable mathematical-modeling capability or stop.

## Separation of responsibilities

### Case-owned artifacts

Case-owned artifacts contain problem-specific data, constants, assumptions, candidates, decisions and evidence. They stay under `tests/caseXXX/`.

Examples:

- source manifests;
- question-specific model specifications;
- candidate routes;
- competition-specific overlap definitions;
- human selection records;
- numerical outputs and figures.

### Skill-owned artifacts

Skill-owned artifacts describe reusable behavior independent of a particular problem. They stay under `skills/math_modeling/` with generic tests.

Examples:

- workflow stages and gates;
- schemas and contracts;
- data adapters with declared input shape;
- independent evaluators;
- geometry primitives;
- validation and sensitivity mechanisms;
- registries and evidence-packaging rules.

## Promotion checklist

Promote a case implementation only when all answers below are yes.

1. Can the capability be named without referring to the originating question?
2. Are inputs, outputs and units explicit?
3. Can invalid inputs and failed outputs be detected?
4. Is case policy injected as data rather than hard-coded?
5. Is there at least one analytic or synthetic test?
6. Is there at least one real-case demonstration?
7. Are limitations documented?
8. Does the capability avoid selecting a final human-value decision automatically?

If any answer is no, keep the implementation case-local or refine the contract before promotion.

## Required promotion record

Each promotion decision must record:

```yaml
capability_id: string
originating_case: string
case_gap: string
reusable_contract: string
owner_path: string
generic_tests: []
case_evidence: []
known_limits: []
decision: promote | refine | keep_case_local | stop
human_decision_required: true
```

The capability must also be added to `skills/math_modeling/CAPABILITY_REGISTRY.yaml`.

## Case stop conditions

Stop case-specific development when any of the following becomes true:

- the reusable capability has passed generic tests and a real-case demonstration;
- remaining improvements only optimize the current case score;
- additional work requires a missing domain or operational constraint that the case does not provide;
- repeated iterations produce no new reusable contract or failure detector;
- the case has become a benchmark for a capability already marked reusable;
- a human modeling decision is required before further work.

Stopping does not mean the case solution is correct or final. It means further work belongs to a separate case-solution objective, not to the current skill-development objective.

## Iteration budget

A capability gap may consume at most:

- one minimal failing fixture;
- one reusable implementation pass;
- one generic test pass;
- one real-case demonstration pass;
- one corrective pass after review.

Further iterations require a written statement of the new reusable knowledge expected. “Improve the case result” alone is insufficient.

## Evidence hierarchy

The preferred evidence order is:

1. analytic or synthetic unit test;
2. deterministic integration test;
3. real-case demonstration;
4. human review of scope and limits.

A real case without generic tests is not sufficient for promotion. Green CI without a declared mathematical contract is also not sufficient.

## Decision authority

Agents may propose promotion candidates and generate evidence. They may not decide that a capability is reusable, nor may they silently expand the skill boundary. Final promotion and case-stop decisions are human checkpoints.
