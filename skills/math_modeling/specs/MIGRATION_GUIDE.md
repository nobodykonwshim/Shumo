# Migrating legacy model artifacts

Legacy `problemX.model.yaml` files may remain as historical evidence. New or revised specifications should use schema version `1.0` and a versioned filename such as `problemX.model.v2.yaml` until the migration is accepted.

## Mapping

| Legacy concept | Model-spec v1 location |
|---|---|
| free-text objective | `objective.description` plus one or more `objective.metrics` |
| scalar input mapping | `inputs` and `symbols.parameters` |
| route decision | `model_components`, `human_checkpoints` and `claims` |
| formula candidates | `formulas` with stable IDs and declared symbols |
| informal feasibility notes | `constraints` with detectable `failure_signal` |
| method name | `algorithm.method`, ordered `steps` and `termination` |
| result values | `outputs`; numerical evidence stays in a separate result artifact |
| validation list | `validation.checks` with acceptance, status and evidence |
| reference notes | `provenance.reference_exposure_status` and source artifacts |
| paper notes | `claims.allowed`, `claims.forbidden` and `limitations` |

## Migration policy

1. Do not overwrite historical evidence during the first migration.
2. Translate the model contract, not the prose layout.
3. Keep numerical result files separate and link them through evidence paths.
4. Validate semantic IDs and references before marking the migrated specification solved.
5. Run repository path checks for every committed evidence path.
6. Compare the legacy and migrated claims; the migration must not silently strengthen an optimality or correctness claim.
7. Replace the legacy artifact only after human review confirms semantic equivalence.

`tests/case001/artifacts/modeling/problem3.model.v2.yaml` is the first real-case migration demonstration. It intentionally retains the original `problem3.model.yaml` beside it.

## Human judgment boundary

Schema conformance is an engineering check. A human still decides whether the objective, route family, assumptions, accepted risks and claim boundaries are appropriate for the modeling problem. The validator must block missing or inconsistent decisions, but it must not invent them.
