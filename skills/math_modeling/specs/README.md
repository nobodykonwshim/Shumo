# Model specification contract

`model_spec.schema.json` is the reusable W2-to-W5 contract for a mathematical model. It separates the model itself from case-specific prose and from the final paper.

A conforming specification records:

- the primary objective and its metrics;
- typed inputs, variables, parameters and units;
- assumptions and their validation state;
- model components, formulas and hard or soft constraints;
- an executable algorithm with a termination rule;
- outputs and acceptance conditions;
- validation checks and sensitivity policy;
- provenance, evidence and reference-exposure state;
- human checkpoints, limitations and claim boundaries.

The core contract is deliberately model-family neutral. Optimization, statistical, simulation, prediction and feasibility models use the same top-level structure and may place domain-specific additions under `extensions`.

## Authoring formats

The validator accepts JSON directly and YAML when PyYAML is installed. The JSON Schema remains the authoritative structural contract regardless of authoring format.

## Validation

Install the small validation dependency set:

```bash
python -m pip install -r skills/math_modeling/validation/requirements.txt
```

Validate one specification:

```bash
python skills/math_modeling/validation/model_spec_validator.py \
  --spec skills/math_modeling/specs/model_spec.example.yaml
```

Validate repository evidence paths as well:

```bash
python skills/math_modeling/validation/model_spec_validator.py \
  --spec tests/case001/artifacts/modeling/problem3.model.v2.yaml \
  --repo-root . \
  --check-paths
```

The validator performs JSON-Schema checks plus semantic checks that JSON Schema alone cannot express reliably:

- globally unique semantic IDs;
- resolvable formula, symbol, component, output and validation references;
- at least one primary objective metric;
- an explicit randomness contract for non-deterministic algorithms;
- nonempty blockers for blocked specifications;
- passed required checks and closed human checkpoints before `status: solved`;
- finite, ordered parameter ranges;
- optional existence checks for repository evidence and implementation paths.

## Sensitivity declarations

The compact `validation.sensitivity_policy` field may summarize a model's sensitivity intent. A fully auditable plan should be stored as a separate `*.sensitivity.yaml` artifact validated against `sensitivity_policy.schema.json`.

The Skill provides no universal numerical threshold. Each case must freeze its perturbations, metrics and acceptance rules before the final result, record the source of those choices, and preserve the original verdict if later amendments are made. The governance policy is documented in `../support/SENSITIVITY_POLICY.md`.

## CI boundary

`Skill contract validation` is a reusable Skill gate. It runs the generic regression suites, validates the live capability registry, validates case-independent contract examples and validates committed model and sensitivity artifacts with repository-path checks.

Expensive case-study reconstruction workflows are not prerequisites for this gate. They are dispatched separately and cannot substitute for schema or semantic validation.

## Human judgment boundary

The validators can detect missing objectives, unresolved references, unverified required checks, post-result threshold replacement and pending decisions. They cannot decide whether a route family, objective weighting, assumption, perturbation magnitude or accepted risk is appropriate. Those decisions remain explicit human checkpoints.

## Lifecycle rule

A specification is written at W2, completed during W3, updated with evidence during W4 and frozen into the modeling package at W5. W7 paper writing may consume the frozen specification, but must not silently redefine it.

## Sequential problem review

Projects that require one-problem-at-a-time approval use `problem_review.schema.json` and
`../validation/problem_review_validator.py`. The review record binds the current model, blueprint, LaTeX and
results to SHA-256 hashes. A valid `pending` record is an intentional closed gate; only a valid `approved`
record opens the next configured problem. See `../support/PROBLEM_REVIEW_GATE.md`.
