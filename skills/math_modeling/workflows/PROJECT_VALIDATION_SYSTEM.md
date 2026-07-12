# Project Validation System

## Purpose

Validate the consistency of a complete mathematical-modeling project rather than individual files only.

## Validation chain

A project is considered structurally consistent only when:

1. modeling decision records identify candidate routes and approved choices;
2. model specifications match the selected modeling route;
3. sensitivity policies cover declared important assumptions and parameters;
4. evidence artifacts support reported outputs;
5. paper blueprints only reference frozen and traceable modeling results.

## Blocking states

The validator must block progression when:

- a model is selected without a decision record;
- a paper blueprint references an unfrozen model;
- conclusions exceed validated evidence;
- required human decisions remain unresolved;
- evidence paths are missing.

## Project status states

Supported states:

- `needs_model_candidates`
- `waiting_for_human_decision`
- `ready_for_implementation`
- `ready_for_validation`
- `ready_for_paper`
- `blocked`
- `demonstration_complete`

The validator reports state and reason. It does not make human modeling decisions.
