# Changelog

## 2026-07-11 — Workflow-first Agent architecture

### Added

- Agent admission gate based on ambiguity, task value, capability reliability, and error detectability.
- Agent runtime contract covering Environment, Tools, Prompt, budgets, verification, rollback, and stop conditions.
- Deterministic Workflow map from project initialization through final delivery checks.
- Bounded Solution Review Agent for hidden assumptions, counterexamples, validation gaps, and simplification opportunities.
- Dedicated Agent-versus-Workflow selection guide.
- Structured Agent admission and run records in modeling artifacts.

### Changed

- Shumo now defaults to `workflow_first` instead of treating the modeling layer as a continuously autonomous Agent.
- Agent use is limited to route exploration, unknown-failure diagnosis, and solution pressure testing.
- Innovation Explorer is optional and can run only after Agent admission.
- Route selection now requires a participant or team decision record before implementation.
- Standard implementation, validation, registry updates, paper architecture, and paper writing are deterministic workflows.
- Project configuration now controls Agent types, budgets, error detection, permissions, stop conditions, and rollback requirements.
- Agent autonomy is explicitly limited by the system's ability to detect errors.

### Preserved

- Three-layer separation between modeling, paper architecture, and paper writing.
- Existing project directories such as `2024A/`.
- Project parameter, formula, and model-contract registries.
- `check_formula_reuse.py` command-line interface.
- Existing LaTeX sections and result assets.

## 2026-07-11 — Three-layer architecture

### Added

- Independent modeling and numerical-solution layer.
- Independent paper-architecture and global-registry layer.
- Independent formal paper-writing layer.
- Innovation Explorer protocol for baseline comparison and verifiable, problem-specific improvements.
- Central project configuration template.
- Structured modeling packet and paper blueprint contracts.
- Architecture and migration documentation.
- Minimal-context loading rules to reduce unnecessary repository and conversation reads.

### Changed

- `skills/math_modeling/SKILL.md` became a router instead of a monolithic modeling-and-writing prompt.
- Formula reuse is assigned across the three layers: semantic IDs in modeling, ownership and labels in architecture, references in writing.
- Computational constraints are classified before writing instead of being copied directly into paper prose.
- Innovation must be selected and validated during modeling rather than invented during paper writing.

### Migration note

Existing projects can adopt the new workflow incrementally. New problems should generate modeling packets first; existing chapters may be reverse-extracted into packets without changing verified numerical results.
