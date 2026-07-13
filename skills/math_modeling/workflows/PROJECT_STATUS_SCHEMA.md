# Project Status Schema

A project status record answers:

- Where is the modeling process now?
- What blocks progression?
- Which human decisions are pending?
- What evidence supports completion?
- What is the next valid action?

The structural contract is `skills/math_modeling/specs/project_status.schema.json`. A real project instance links its problem bundles, supporting sensitivity evidence, lifecycle stop record, external dependencies and state-specific next actions.

## Status ownership

The system may calculate status from evidence and contracts. It may recommend next actions. It may not approve assumptions, final models, risk acceptance or paper claims.

`expected_status` is a regression assertion. It cannot force the calculator to report a preferred state. When the calculated and expected values differ, validation fails with `project_status_drift`.

## State precedence

The calculator applies this order:

1. `blocked` when any structural, cross-artifact, evidence or blocking-dependency error exists;
2. `demonstration_complete` when a valid project-owned stop record freezes the bounded cycle;
3. `needs_model_candidates` when a required bundle lacks a complete candidate decision;
4. `waiting_for_human_decision` when an authorized human choice remains pending;
5. `ready_for_implementation` when a route is approved but its executable model is absent or draft;
6. `ready_for_validation` when implementation exists but required validation or sensitivity execution remains;
7. `ready_for_paper` when the linked modeling package is solved, validated and traceable.

## Meaning of the states

### `needs_model_candidates`

The problem has no usable candidate-route set or the recommendation cannot resolve to a declared candidate.

### `waiting_for_human_decision`

The machine has assembled alternatives, but a checkpoint involving the objective, route, assumption, risk or claim strength remains unresolved.

### `ready_for_implementation`

The modeling route is frozen and approved, but an executable model specification or implementation is incomplete.

### `ready_for_validation`

A model artifact exists, but required validation checks or predeclared sensitivity rules are not complete.

### `ready_for_paper`

The modeling package is solved and validated. This permits paper preparation; it does not mean the paper has already been written or approved.

### `blocked`

At least one inconsistency must be repaired before downstream work. The report identifies the blockers and returns only next actions declared for `blocked`.

### `demonstration_complete`

The declared development-cycle objective has been achieved and a valid stop record closes the cycle. Unfinished case work may remain when it is outside the bounded demonstration goal.

## Next-action priority

Within a non-stopped cycle, priority is:

1. repair cross-artifact blockers;
2. resolve blocking human decisions;
3. obtain or compare missing model candidates;
4. implement the approved model;
5. complete missing validation and sensitivity execution;
6. freeze evidence and enable paper preparation.

External dependencies may remain in `waiting` without blocking a completed cycle when `blocks_current_cycle: false` is declared explicitly.
