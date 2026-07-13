# Shumo Mathematical Modeling Skill

## Mission

The purpose of this directory is to build a reusable mathematical-modeling capability system. It is not to solve one competition problem as completely as possible.

The Skill must help a user move from an unfamiliar problem statement to an auditable modeling package through explicit model-route decisions, deterministic workflows, bounded agents, independent validation and human authority.

A case study is evidence for the Skill. It is never the product boundary.

The governing rules are defined in `support/SKILL_CONSTITUTION.md`.

## Two-system product

Shumo contains two systems separated by a frozen handoff:

1. **Modeling and solving** produces a validated, frozen modeling evidence package.
2. **Paper writing** converts that package into a paper without silently changing models, results or claim strength.

## Primary workflow

The reusable workflow is:

1. source and attachment intake;
2. problem decomposition and deliverable contracts;
3. problem classification and candidate modeling-route generation;
4. route comparison and explicit human selection;
5. executable model specification;
6. deterministic or controlled-randomness implementation;
7. independent validation and predeclared sensitivity analysis;
8. human decision and claim-boundary records;
9. frozen evidence packaging;
10. paper architecture and delivery checks.

The modeling-decision contract is documented in `workflows/MODELING_DECISION_SYSTEM.md`.

## Non-goals

The Skill does not attempt to:

- prove that one case-study solution is globally optimal;
- spend unlimited iterations repairing one candidate route;
- encode case-specific constants as reusable policy;
- treat green CI as equivalent to mathematical correctness;
- allow an agent to make an unreviewed final modeling decision;
- claim innovation without a named deficiency that requires it;
- write a final paper before the modeling package is frozen.

## Reusable-first architecture

```text
Problem case
  -> exposes a capability gap
  -> classifies the gap as reusable, case-specific or score-only
  -> creates the smallest reproducible fixture
  -> implements or improves a generic capability under skills/math_modeling/
  -> validates the capability with generic tests and at least one case fixture
  -> records evidence in the capability registry
  -> stops case-specific expansion unless a new reusable gap is identified
```

The repository therefore has two distinct loops.

### Skill loop

The Skill loop owns reusable contracts, workflows, tools, evaluators, geometry primitives, registries and quality gates. Its outputs belong under `skills/math_modeling/` and generic tests under `tests/evaluators/`, `tests/orchestration/` or `tests/specs/`.

### Case loop

The case loop owns source manifests, assumptions, candidate routes, run evidence and case-specific decisions. Its outputs belong under `tests/caseXXX/`.

Case code may orchestrate reusable capabilities, but it must not silently define the reusable contract.

## Promotion rule

A case-specific artifact is promoted into the Skill only when all of the following hold:

- the capability can be described without case identifiers;
- inputs and outputs have an explicit schema or contract;
- failure states are detectable;
- at least one analytic or synthetic test exists;
- at least one real case demonstrates value;
- case-specific policy remains outside the reusable implementation;
- limitations are explicit.

The detailed policy is in `support/CASE_TO_SKILL_PROMOTION.md`.

## Capability inventory

The authoritative inventory is `CAPABILITY_REGISTRY.yaml`. Implemented capabilities include:

- workflow-first orchestration;
- pre-implementation modeling-route decision records;
- generic executable model specifications;
- bounded Agent admission;
- reference isolation;
- structured grid ingestion;
- independent spatial coverage evaluation;
- explicit route geometry and finite-curvature diagnostics;
- pre-result sensitivity governance;
- paper-blueprint validation;
- deterministic CI evidence generation.

## Human decision boundary

The machine may recommend but must not silently decide the primary objective, final model family, major assumptions, accepted risk, sensitivity thresholds, claim strength or capability promotion.

A frozen modeling decision requires an explicit human record.

## Case-study stop rule

A case study must stop consuming implementation effort when:

1. the intended reusable capability has been demonstrated;
2. remaining work only improves that case's score or numerical result;
3. no new reusable contract, validator, failure detector or workflow requirement is being learned;
4. the current result, uncertainty and limitations are recorded.

At that point the case is labeled `partial`, `demonstration_complete` or `blocked`, and work returns to the Skill backlog.

## Success criteria

A development cycle is successful when it produces a capability with:

- a stable contract;
- deterministic tests;
- auditable evidence;
- documented limits;
- a clear human checkpoint;
- proof that the capability can be reused independently of the originating case.

A fully solved case is useful, but it is not required for a Skill-development cycle to succeed.
