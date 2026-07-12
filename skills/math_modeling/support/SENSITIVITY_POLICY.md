# Sensitivity policy

## Governance decision

Shumo does not provide a universal numerical sensitivity threshold.

Different model families, units, risks and competition objectives make a single percentage rule misleading. The Skill therefore standardizes the declaration and audit process, while every case must choose and justify its own perturbations, metrics and acceptance rules before seeing the final result.

## Required lifecycle

1. Identify the model or evaluation artifact covered by the policy.
2. Declare perturbation targets, methods and values before the final result.
3. Declare the metrics that will expose numerical, structural or feasibility changes.
4. Freeze acceptance rules and record their source.
5. Execute every required perturbation without suppressing adverse cases.
6. Record pass or fail for every required rule and preserve the evidence.
7. Keep post-result amendments separate from the original frozen rule and verdict.

## What the Skill enforces

The schema and validator require:

- `declared_before_final_result: true`;
- `thresholds_are_case_specific: true`;
- `default_thresholds_used: false`;
- at least one perturbation, metric and acceptance rule;
- explicit threshold provenance or a declared non-numeric rule;
- freeze records for frozen, executed, failed or waived policies;
- complete results and evidence for executed policies;
- preservation of the original rule when an amendment is made after results are known;
- optional repository-path and model-ID checks.

## What remains a human decision

The user, team, problem statement or domain authority must decide:

- which uncertainty or numerical settings matter;
- the perturbation magnitudes and scenario set;
- which outputs and constraints are decision-relevant;
- the acceptable change, failure rate or qualitative stability rule;
- whether a failed sensitivity result requires model revision, a narrower claim or rejection.

The validator detects missing or inconsistent decisions. It does not invent them.

## Files

- Schema: `skills/math_modeling/specs/sensitivity_policy.schema.json`
- Validator: `skills/math_modeling/validation/sensitivity_policy_validator.py`
- Example: `skills/math_modeling/specs/sensitivity_policy.example.yaml`
- Regression tests: `tests/specs/test_sensitivity_policy_validator.py`

Policies committed under `tests/` should use the suffix `*.sensitivity.yaml` so CI can discover them.
