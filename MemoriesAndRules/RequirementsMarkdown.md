# Requirements Authoring Best Practices (for Prompts/)

This guide defines how to write implementation-agnostic, defensible, and testable requirement specs for files under `Prompts/`. It consolidates patterns from existing project prompts and adds recommendations for LLM-driven development workflows.

## Goals
- Be implementation-agnostic (portable across desktop/web/mobile; Python/Rust/Web).
- State behaviors unambiguously and without contradiction.
- Support defensive design: validate inputs, fail fast, surface precise errors.
- Provide strong examples for testing: happy paths, edge cases, error scenarios.
- Include helpful diagrams (ER/UML/sequence/state) that clarify relationships and flows.
- Be concise but complete: enough detail to implement and test without prescribing exact code.

## Required Structure for New Requirement Specs
- __[Executive Summary & Global Criteria]__
  - Key objectives, non-negotiable criteria (determinism, idempotency, normalization, timing policy), and brief system rationale.
- __[Acceptance Criteria Overview]__
  - Few bullets summarizing what must be verifiable end-to-end.
- __[Document Map]__
  - A quick map of sections to orient the reader.
- __[Conformance Checklist]__
  - Short list of must-haves used to self-audit an implementation.
- __[Terminology and Invariants]__
  - Canonical terms and “always true” properties; define separators/boundaries if applicable.
- __[Title and Scope]__
  - What the component/system does and what it does not do.
- __[Definitions and Invariants]__
  - Glossary of terms and constraints that must always hold.
- __[Functional Requirements]__
  - Behavior expressed as must/shall statements, not code.
- __[Non-Functional Requirements]__
  - Performance, reliability, portability, observability.
- __[Configuration]__
  - Keys, defaults, ranges, validation rules; how config is applied (not how retrieved).
- __[Defensive Design & Error Handling]__
  - Validate-before-use, error taxonomy, error payloads.
- __[Examples for Testing]__
  - Happy paths, edge cases, error scenarios; not coupled to a specific implementation.
- __[Diagrams]__
  - ER/UML/sequence diagrams that clarify contracts and flows.
- __[Acceptance Criteria]__
  - Verifiable statements that confirm requirements are met.
- __[Traceability Crosswalk]__
  - Matrix mapping requirements to examples/tests and acceptance criteria.
- __[Change Log / Versioning]__
  - Semantic versioning for the spec; note breaking vs. additive changes.

## Writing Style Guidelines
- __Non-prescriptive__: Describe behavior, not specific classes, functions, or APIs. Prefer "shall" and "must" over suggestive language.
- __Unambiguous__: Avoid vague terms ("fast", "soon"). Use measurable statements ("< 100 ms", "NFC-normalized equality").
- __Consistent Terms__: Define terms once in Definitions; reuse consistently.
- __Portable__: Avoid platform-specific APIs; if needed, require an abstraction (e.g., clock provider).
- __Deterministic__: State when behavior must be deterministic vs. when nondeterminism is acceptable.
- __Idempotent__: Specify idempotency for operations re-run with identical inputs.
- __Security & Privacy__: Call out sensitive data handling, logging redaction, and permissions.

## Defensive Design Checklist
- __Validate Inputs__: type/shape/ranges/nullability before processing.
- __Fail Fast__: Abort disqualified operations early, with precise error codes.
- __Partial Tolerance__: Handle a bad record without corrupting the batch.
- __Structured Errors__: Include error code, message, and context fields.
- __Logging Policy__: INFO (normal), WARN (validation drops), ERROR (systemic failures).
- __Resource Guards__: Timeouts, memory limits, and bounded retries where applicable.

## Error Taxonomy Template
- `ERR_INVALID_ARGUMENT`: Invalid parameter (name, expected type/range, observed).
- `ERR_PRECONDITION_FAILED`: Required state not met.
- `ERR_NOT_FOUND`: Required entity absent.
- `ERR_CONFLICT`: Duplicate/uniqueness violation.
- `ERR_INTEGRITY`: Data corruption or referential violation.
- `ERR_TIMEOUT`: Operation exceeded time budget.
- `ERR_DEPENDENCY_FAILURE`: Downstream service or store failed.
- `ERR_UNSUPPORTED`: Unsupported mode/feature/character.

Each error includes: `code`, `message`, `context` (ids, indices, values), optional `remediation`.

## Front-Matter Pattern (Executive Summary)
- __Purpose__: Surface the most important information first for faster comprehension and implementation.
- __Order__ (recommended):
  1) Executive Summary & Global Criteria
  2) Acceptance Criteria Overview
  3) Document Map
  4) Conformance Checklist (Must-Haves)
  5) Terminology and Invariants
- __Guidance__:
  - Keep bullets concise and testable.
  - Global criteria should include determinism, idempotency, normalization policies, and timing or ordering policies as relevant.
  - Conformance checklist should be auditable in minutes.

## Examples Section Guidance
- Use abstract data and timing; avoid library-specific types.
- Cover: 
  - __Happy paths__: canonical correct flows.
  - __Edge cases__: separators, normalization, boundaries, ordering, large inputs.
  - __Error scenarios__: invalid sizes, missing timestamps/fields, negative durations, duplicates.
- Include expected results and which rules justify them.

## Diagrams Guidance
- __ER Diagrams__: Entities, keys, relationships, uniqueness, and constraints.
- __UML Class Diagrams__: Public contracts and relationships; avoid language-specific features.
- __Sequence Diagrams__: Critical workflows showing interactions and error/timeout paths.
- __State Diagrams__: Lifecycle of core entities if stateful.
- Prefer Mermaid syntax for portability in markdown.

## Acceptance Criteria Template
- Determinism: "Given identical inputs, outputs (including timing fields) shall be identical."
- Idempotency: "Reprocessing shall not create duplicates; on conflict, return ERR_CONFLICT or ignore."
- Performance: "Process 10k events within X seconds and < Y MB peak memory."
- Validation: "Invalid inputs are rejected with specific error codes and do not affect valid items."
- Portability: "No dependency on language-specific APIs; all platform touch points use abstractions."

## LLM-Driven Development Recommendations
- __Single Source of Truth__: Keep requirements current and authoritative; code and tests derive from here.
- __Stable Interfaces__: Freeze contracts early; surface changes via spec versioning.
- __Traceability__: Tag every test case with the requirement(s) it verifies.
- __Prompt Hygiene__: 
  - Provide the spec, not code, to guide the model.
  - Ask for implementation that satisfies acceptance criteria and examples.
  - Instruct the model to add defensive checks and structured errors.
- __Review Loop__: After generation, run tests from examples; refine spec if gaps appear.

## Templates

### Front Matter Template
```
# <Feature/Subsystem Name>

### 0.1 Executive Summary & Global Criteria
- <Key objective 1>
- <Key objective 2>
- <Global constraints: determinism, idempotency, normalization, timing policy, etc.>

### 0.2 Acceptance Criteria Overview
- <High-level verifiable outcome 1>
- <High-level verifiable outcome 2>

### 0.3 Document Map
- Section 1: <Title>
- Section 2–N: <Highlights>

### 0.4 Conformance Checklist (Must-Haves)
- <Input validation and structured errors>
- <Policy enforcement specifics (e.g., normalization, bounds, separators)>
- <Determinism/idempotency guarantees>

### 0.5 Terminology and Invariants
- __<Term>__: <definition>
- __<Term>__: <definition>
- __Invariant__: <always-true property>
```

### Requirement Heading Template
```
# <Feature/Subsystem Name>

## 1. Scope
<What is in/out of scope>

## 2. Definitions and Invariants
<Canonical terms and always-true constraints>

## 3. Functional Requirements
- The system shall ...

## 4. Non-Functional Requirements
- Performance, reliability, etc.

## 5. Configuration
- Keys, defaults, ranges, validation

## 6. Defensive Design & Errors
- Error codes, messages, contexts

## 7. Examples for Testing
- Happy paths
- Edge cases
- Error scenarios

## 8. Diagrams
- ER/UML/Sequence/State

## 9. Acceptance Criteria
- Verifiable statements

## 10. Versioning
- Spec version, changes
```

### Examples Block Template
```
- Case: <name>
  Input: <abstract input>
  Expected: <outcome>
  Notes: <which rules apply>
```

## Patterns Observed in Existing Prompts
- Clear size bounds and separator rules for sequence processing.
- Time computation with explicit gross-up rules for start-of-sequence bias.
- Separate clean vs. error classifications with strict last-position error criteria.
- Consistent insistence on positive durations and idempotent persistence.

## Maintenance
- Keep requirements synchronized with UI/UX docs and database schemas.
- When adding features, extend Definitions and Error Taxonomy first; then add or modify requirements and examples accordingly.
- Update diagrams with each structural change; record spec version.

---

Following this guide will produce requirement specs that are portable, testable, and robust for LLM-assisted implementation across platforms and languages.
