# Shumo Mathematical Modeling Skill

## Mission

The purpose of this directory is to build a reusable mathematical-modeling capability system. It is not to solve one competition problem as completely as possible.

The skill must help a user move from an unfamiliar problem statement to an auditable modeling package through deterministic workflows, bounded agents, independent validation and explicit human decisions.

A case study is evidence for the skill. It is never the product boundary.

## Primary product

The primary product is a reusable workflow and capability set that can be applied to new mathematical-modeling problems:

1. source and attachment intake;
2. problem decomposition and deliverable contracts;
3. route and method exploration under an admission gate;
4. executable model specification;
5. deterministic implementation;
6. independent validation and sensitivity analysis;
7. human decision records;
8. evidence packaging;
9. paper architecture and delivery checks.

## Non-goals

The skill does not attempt to:

- prove that one case-study solution is globally optimal;
- spend unlimited iterations repairing one candidate route;
- encode case-specific constants as reusable policy;
- treat green CI as equivalent to mathematical correctness;
- allow an agent to make an unreviewed final modeling decision;
- write a final paper before the modeling package is frozen.

## Reusable-first architecture

```text
Problem case
  -> exposes a capability gap
  -> creates the smallest reproducible fixture
  -> implements or improves a generic capability under skills/math_modeling/
  -> validates the capability with generic tests and at least one case fixture
  -> records evidence in the capability registry
  -> stops case-specific expansion unless a new reusable gap is identified
```

The repository therefore has two distinct loops.

### Skill loop

The skill loop owns reusable contracts, workflows, tools, evaluators, geometry primitives, registries and quality gates. Its outputs belong under `skills/math_modeling/` and generic tests under `tests/evaluators/` or `tests/orchestration/`.

### Case loop

The case loop owns source manifests, assumptions, candidate plans, run evidence and case-specific decisions. Its outputs belong under `tests/caseXXX/`.

Case code may orchestrate reusable capabilities, but it must not silently define the reusable contract.

## Promotion rule

A case-specific artifact is promoted into the skill only when all of the following hold:

- the capability can be described without case identifiers;
- inputs and outputs have an explicit schema or contract;
- failure states are detectable;
- at least one analytic or synthetic test exists;
- at least one real case demonstrates value;
- case-specific policy remains outside the reusable implementation.

The detailed policy is in `support/CASE_TO_SKILL_PROMOTION.md`.

## Current reusable capabilities

The authoritative inventory is `CAPABILITY_REGISTRY.yaml`. Current implemented capabilities include:

- workflow-first orchestration;
- bounded Agent admission;
- reference isolation;
- XLSX depth-grid ingestion;
- independent spatial coverage evaluation;
- explicit route geometry and finite-curvature diagnostics;
- deterministic validation and GitHub Actions evidence generation.

## Case-study stop rule

A case study must stop consuming implementation effort when:

1. the intended reusable capability has been demonstrated;
2. remaining work only improves that case's score or numerical result;
3. no new reusable contract, validator, failure detector or workflow requirement is being learned.

At that point the case is labeled `partial`, `demonstration_complete` or `blocked`, and work returns to the skill backlog.

## Success criteria

A development cycle is successful when it produces a reusable capability with:

- a stable contract;
- deterministic tests;
- auditable evidence;
- documented limits;
- a clear human checkpoint;
- proof that the capability can be reused independently of the originating case.

A fully solved case is useful, but it is not required for the skill cycle to succeed.
