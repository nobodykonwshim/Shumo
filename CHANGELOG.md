# Changelog

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

- `skills/math_modeling/SKILL.md` is now a router instead of a monolithic modeling-and-writing prompt.
- Formula reuse is assigned across the three layers: semantic IDs in modeling, ownership and labels in architecture, references in writing.
- Computational constraints are classified before writing instead of being copied directly into paper prose.
- Innovation must be selected and validated during modeling rather than invented during paper writing.
- The README now documents the three-layer workflow and compatibility strategy.

### Preserved

- Existing project directories such as `2024A/`.
- Project parameter, formula, and model-contract registries.
- `check_formula_reuse.py` command-line interface.
- Existing LaTeX sections and result assets.

### Migration note

Existing projects can adopt the new workflow incrementally. New problems should generate modeling packets first; existing chapters may be reverse-extracted into packets without changing verified numerical results.
