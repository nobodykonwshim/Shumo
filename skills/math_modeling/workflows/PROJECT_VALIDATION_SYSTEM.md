# Project Validation System

## Purpose

Validate the consistency of a complete mathematical-modeling project rather than individual files only.

The project validator is the control layer above the modeling-decision, model-specification, sensitivity-policy and paper-blueprint validators. A collection of individually valid files is not a valid project when their identifiers, selected route, evidence, claims or lifecycle state disagree.

## Executable command

```bash
python shumo.py validate-project tests/case001/project_status.yaml \
  --repo-root . \
  --check-paths \
  --expect-status demonstration_complete
```

The command prints a machine-readable report containing:

- the calculated project status;
- reasons for that status;
- completed lifecycle items;
- pending human decisions;
- blockers and warnings;
- the next actions valid for the calculated state;
- loaded-artifact counts and external dependencies.

The expected status is an assertion, not an instruction. The calculator never rewrites its result to match the expected value. Status drift fails validation.

## Validation chain

A project is structurally consistent only when:

1. modeling decision records identify candidate routes and approved choices;
2. model specifications belong to the same problem and trace the selected route into named model components;
3. solved specifications have passed every required validation check and closed their human checkpoints;
4. executed sensitivity policies contain results for every required acceptance rule and preserve their evidence;
5. paper blueprints reference the linked solved model by both path and specification ID;
6. paper claims remain inside the source model's allowed and forbidden claim boundaries;
7. evidence and lifecycle records exist inside the repository when path checking is enabled.

## Blocking states

The validator blocks progression when, among other conditions:

- a model specification exists without a modeling-decision record;
- the selected candidate does not match the project traceability record;
- a traceability record names a model component that does not exist;
- a frozen decision lacks human approval;
- a solved model retains an unsatisfied required check or pending checkpoint;
- a required sensitivity rule lacks a passing execution result;
- a paper blueprint references an unsolved model or unsupported claim;
- a stop status lacks a matching stop record;
- evidence paths are missing or escape the repository;
- a waiting external dependency is declared to block the current cycle.

## Lifecycle stop rule

`demonstration_complete` has precedence over ordinary downstream readiness only when all of the following hold:

- no cross-artifact blocking error exists;
- the project status record declares a stop record;
- the stop record belongs to the same project;
- the stop record itself records `demonstration_complete`.

This state closes a bounded development cycle. It does not imply that every competition subproblem is solved or that a final paper is complete.

## Supported project states

- `needs_model_candidates`
- `waiting_for_human_decision`
- `ready_for_implementation`
- `ready_for_validation`
- `ready_for_paper`
- `blocked`
- `demonstration_complete`

The validator calculates state and recommends valid next actions. It does not approve objectives, assumptions, model families, accepted risks or paper claims on behalf of a human authority.
