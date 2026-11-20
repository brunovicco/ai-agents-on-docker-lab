# ADR-0001: Adopt Clean Architecture dependency boundaries

- Status: Accepted
- Date: 2026-11-20

## Context

The service requires business rules to remain independent from web frameworks, persistence, messaging, and external SDKs.

## Decision

Use the dependency direction documented in `docs/ARCHITECTURE.md` and enforce it through package structure, review, tests, and import-contract tooling when introduced.

## Consequences

- Domain code remains independently testable.
- Boundary translation is explicit.
- Small CRUD features should not receive unnecessary abstraction.
- More mapping code is accepted where it protects domain semantics.

## Update (2026-11-20)

The lab keeps only the domain and entrypoint layers. The scaffold's application and adapter
layers, with their unused OpenTelemetry and Langfuse adapters, were removed: nothing in the
dispatch flow called them. The dependency rule still applies when a planner needs a port.
