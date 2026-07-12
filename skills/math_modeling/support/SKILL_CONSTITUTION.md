# Shumo Mathematical-Modeling Skill Constitution

## 1. Product boundary

Shumo contains two cooperating systems with a strict handoff boundary.

1. **Modeling and solving** turns problem sources into a frozen, auditable modeling package.
2. **Paper writing** turns that frozen package into a paper without silently changing the model, recomputing results or strengthening claims.

Real cases are validation fixtures for the Skill. They are not the product boundary.

## 2. Modeling lifecycle

Every case must move through the following stages unless explicitly blocked:

1. source and attachment intake;
2. problem decomposition;
3. objective, constraints and evaluation-metric confirmation;
4. candidate modeling-route generation;
5. route comparison and human selection;
6. executable model specification;
7. deterministic or controlled-randomness execution;
8. independent validation and predeclared sensitivity analysis;
9. human decision and claim-boundary confirmation;
10. frozen modeling evidence package.

A solver, evaluator or code module by itself is not a completed modeling capability.

## 3. Modeling-decision rule

The Skill must not jump directly from problem text to one favored model. Before implementation it must record:

- problem type and data profile;
- at least two materially different candidate routes when alternatives are plausible;
- applicability conditions, assumptions, strengths, risks and computational cost for each route;
- explicit hard and soft comparison criteria;
- the reason for selecting, rejecting or deferring every candidate;
- unresolved risks and the human checkpoint that owns the final choice;
- whether novelty is necessary and which real deficiency it addresses.

The machine may recommend. It may not make an unreviewed final choice about the primary objective, model family, major assumptions, risk acceptance or claim strength.

## 4. Real-case development loop

Development remains practice driven:

> real case -> capability gap -> gap classification -> generic contract -> generic tests -> case validation -> stop or next gap

Every discovered problem must be classified as one of:

- **reusable capability gap**: belongs under `skills/math_modeling/`;
- **case-specific requirement**: remains under `tests/caseXXX/`;
- **case-score refinement only**: stops by default.

## 5. Case stop rule

Case-specific work stops when all are true:

- the intended reusable capability has been demonstrated;
- remaining work only improves the numerical result or competition score;
- no new reusable contract, validator, failure detector or workflow requirement is being learned;
- the current result, uncertainty and limitations are recorded.

The case is then labeled `demonstration_complete`, `partial` or `blocked`. A partial case must never be presented as solved.

## 6. Human decision boundary

The following require explicit human authority:

- primary objective and objective hierarchy;
- final model route or route family;
- major assumptions;
- multi-objective weights;
- sensitivity perturbations and acceptance rules;
- accepted residual risk;
- final candidate selection;
- allowed paper claim strength;
- promotion from `validated` to `reusable`.

At each checkpoint the Skill must state the decision, options, trade-offs, recommendation and consequences.

## 7. Sensitivity governance

The Skill supplies no universal numerical sensitivity threshold.

Every case must declare perturbations, metrics and acceptance rules before final results are observed. Threshold provenance must be recorded. Post-result amendments preserve the original rule, result and verdict; they cannot erase an inconvenient failure.

## 8. Capability promotion

A case artifact may be promoted into the Skill only when:

- it can be described without case identifiers;
- inputs and outputs have an explicit contract;
- failure states are detectable;
- at least one analytic or synthetic generic test exists;
- at least one real case demonstrates value;
- case constants and case policy stay outside the reusable implementation;
- limitations are explicit.

## 9. Maturity states

- `prototype`: implementation exists but contract or tests are incomplete;
- `validated`: generic contract and tests exist, with one real-case demonstration;
- `reusable`: used successfully on at least two materially different real cases and promoted by human decision;
- `deprecated`: superseded or shown unreliable.

Green CI does not automatically promote a capability.

## 10. Paper-writing boundary

The writing system may organize, explain, format and check frozen modeling content. It must not:

- introduce a new unvalidated model;
- recompute or replace results;
- hide failed validation;
- renumber frozen formulas without an approved blueprint change;
- turn sampled evidence into proof;
- turn route-family optimality into global optimality;
- add unsupported claims.

Every major paper claim must trace to a frozen model specification or validation artifact.

## 11. Minimum viable Skill

The modeling MVP must demonstrate on at least two materially different cases that it can produce:

- problem classification;
- candidate model routes;
- comparison and selection reasoning;
- executable model specification;
- execution result;
- independent validation;
- sensitivity policy;
- human decision record;
- frozen evidence package.

The paper MVP must generate a complete draft from a frozen package without reopening modeling decisions.

## 12. Priority rule

Before every implementation task, ask:

> Does this build a reusable Skill capability, or only improve one case?

Case-only improvement stops unless a new reusable gap and explicit human authorization are both present.
