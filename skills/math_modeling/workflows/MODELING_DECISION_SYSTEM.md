# Modeling Decision System

## Purpose

The modeling decision system sits between problem intake and executable model specification. Its job is to prevent the workflow from jumping directly from a problem statement to one favored model.

The system produces a machine-checkable `*.model-decision.yaml` record containing:

- a problem and data profile;
- multiple materially different modeling routes;
- applicability conditions, assumptions, strengths, risks and computational cost;
- explicit hard, soft and diagnostic comparison criteria;
- a complete comparison matrix;
- a recommendation, fallback and unresolved risks;
- the human checkpoint that owns the final choice;
- a case stop and reopen rule.

## Workflow position

```text
W1 intake and decomposition
  -> W2A modeling decision record
  -> human route decision
  -> W2B executable model specification
  -> W3 execution
  -> W4 validation and sensitivity
  -> W5 frozen evidence package
```

A model specification must not silently replace the route selected in the frozen decision record.

## Machine responsibilities

The validator checks:

- at least two candidate routes when a route decision is being made;
- unique candidate and criterion IDs;
- one complete comparison row per candidate;
- one assessment per criterion in every row;
- resolvable recommendation and fallback IDs;
- rejection reasons and blockers;
- no recommendation that fails a declared hard criterion;
- pre-implementation declaration;
- human approval before a record is frozen;
- repository provenance and evidence paths.

## Human responsibilities

The validator does not choose:

- the primary objective;
- which candidate families deserve inclusion;
- criterion weights;
- accepted assumptions or residual risk;
- the final route;
- the strength of the resulting claim.

The machine may recommend a route while the record is `draft`. Only explicit human approval changes the record to `frozen` and the route status to `selected`.

## Innovation rule

Novelty is not a default scoring bonus. Every candidate states whether novelty is required and which concrete deficiency it addresses. Added complexity without a named deficiency remains optional and must not displace a simpler validated baseline.

## Stop rule

A decision record includes case-specific stopping and reopening conditions. Case work stops when the reusable objective of the demonstration has been met and remaining work only improves the score. Reopening requires a named reusable gap, a Skill-owned artifact and generic test, and explicit human authorization.

## Commands

Validate the generic example:

```bash
python skills/math_modeling/validation/modeling_decision_validator.py \
  --decision skills/math_modeling/specs/modeling_decision.example.yaml
```

Validate a repository case record and its evidence paths:

```bash
python skills/math_modeling/validation/modeling_decision_validator.py \
  --decision tests/case001/artifacts/modeling/problem3.model-decision.yaml \
  --repo-root . \
  --check-paths
```
