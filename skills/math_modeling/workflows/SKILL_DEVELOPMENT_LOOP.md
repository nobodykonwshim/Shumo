# Skill Development Loop

## Why this loop exists

The standard W0-W8 workflow solves a modeling project. Skill development has a different objective: extract reusable capabilities from one or more projects without being trapped by a single case.

## Dual-loop model

```text
CASE LOOP                                  SKILL LOOP
C0 choose a representative case           S0 define the capability gap
C1 create a minimal failing fixture   ->   S1 write the reusable contract
C2 demonstrate the gap                    S2 implement under skills/math_modeling/
C3 run the reusable capability        <-   S3 add generic tests
C4 record case evidence                    S4 run one real-case demonstration
C5 stop or open a new gap             <-   S5 human promotion/stop decision
```

The case loop may not continue merely because the case result can still be improved. It continues only when a new reusable capability gap is declared.

## S0 Capability-gap record

Required fields:

```yaml
capability_gap_id: string
originating_case: string
observed_failure: string
why_existing_capabilities_are_insufficient: string
expected_reusable_output: string
case_only_improvement: false
human_owner: string
```

## S1 Reusable contract

Before implementation, define:

- generic capability name;
- input schema and units;
- output schema;
- invariants;
- failure signals;
- case policy injection points;
- prohibited automatic decisions;
- test plan.

## S2 Implementation boundary

Reusable implementation belongs under `skills/math_modeling/`. Case constants, candidate IDs, competition wording and human selection policy must not appear in the reusable core.

## S3 Generic tests

At least one analytic or synthetic test must fail before the capability is considered demonstrated. Tests must not require the originating case data unless they are explicitly integration tests.

## S4 Real-case demonstration

Run the capability on one real case and record:

- evidence paths;
- what the demonstration proves;
- what it does not prove;
- any case-specific adapters or policies;
- whether new reusable gaps were discovered.

## S5 Promotion and stop decision

The human decision is one of:

- `promote`: contract is reusable and enters the capability registry;
- `refine`: one corrective pass is authorized;
- `keep_case_local`: implementation is useful but not generic;
- `stop`: no additional reusable knowledge is expected.

## Anti-drift gate

Before every additional case iteration, answer:

1. What new reusable capability will this iteration create or improve?
2. What generic test will change?
3. Which skill-owned artifact will be updated?
4. Why is the work not merely improving the current case score?

If these questions do not have concrete answers, the iteration is blocked for the skill-development objective.

## Relationship to W0-W8

W0-W8 remains the workflow for solving a modeling project. S0-S5 governs development of the reusable modeling Skill itself. A single repository activity may produce both W-stage and S-stage records, but the objectives and stop conditions must remain separate.
