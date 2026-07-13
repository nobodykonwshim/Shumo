# Paper blueprint contract

## Purpose

The paper blueprint is the executable W6 handoff from validated modeling artifacts to writing. It prevents W7 from silently redefining models, recomputing results, changing labels or introducing unsupported claims.

A blueprint does not write the paper. It fixes the architecture that writing must follow.

## Required decisions

Before a blueprint can be frozen, it must record:

- every source model specification used by the paper;
- ordered sections and the purpose of each section;
- exactly one definition owner for every included model and formula;
- locked labels and numbering policy;
- where each validated output will appear, including precision policy;
- allowed, forbidden and qualified claims inherited from model specifications;
- content assigned to the body, appendix, reference-only treatment or omission;
- human approval checkpoints and unresolved limitations.

## Machine checks

The schema and validator detect:

- duplicate section orders, IDs and paper labels;
- missing or conflicting model and formula owners;
- unplaced formulas, models or outputs from required source specifications;
- references to unknown source specifications, sections or semantic IDs;
- claims that exceed the source model's allowed claim boundary;
- frozen blueprints that depend on draft or blocked model specifications;
- pending human checkpoints in frozen or validated blueprints;
- writing policies that would permit recomputation, renumbering, duplicate definition or new unverified modeling content;
- missing repository evidence and source-spec paths.

## Human judgment boundary

The validator cannot choose the best chapter structure, decide how much detail belongs in the body, determine the desired page allocation or approve final labels. Those are architecture decisions for the user or modeling team.

The validator ensures that once those decisions are made, they are internally consistent and traceable to the modeling package.

## Files

- Schema: `skills/math_modeling/specs/paper_blueprint.schema.json`
- Validator: `skills/math_modeling/validation/paper_blueprint_validator.py`
- Example: `skills/math_modeling/specs/paper_blueprint.example.yaml`
- Regression tests: `tests/specs/test_paper_blueprint_validator.py`

Committed blueprints should use the suffix `*.paper-blueprint.yaml` so the Skill CI can discover them.
