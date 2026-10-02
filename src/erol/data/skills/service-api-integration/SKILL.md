---
name: service-api-integration
description: "Implement external service adapters from verified provider contracts, including credentials, timeouts and uncertain outcomes."
metadata:
  version: "1.0.0"
---
# Service Api Integration

Implement external service adapters from verified provider contracts, including credentials, timeouts and uncertain outcomes.

## Workflow

1. Read the current provider contract and existing adapter conventions; map each request, response, authentication method and environment separately.
2. Represent money and provider references without lossy floats or numeric coercion. Separate provider IDs from internal IDs and merchant scope.
3. Set bounded connect/read timeouts. Distinguish confirmed rejection from an unknown outcome; retry writes only with a provider-supported deduplication or reconciliation path.
4. Keep credentials out of logs. Validate provider envelopes and isolate malformed responses behind the application's established error contract.

## Verification

Test valid/expired requests, cross-merchant access, timeout after acceptance, malformed provider data and replay. Label mocked contract tests separately from an authenticated sandbox trial.

## Deliverable

Adapter, field/error mapping, focused contract fixtures and documented sandbox gaps.
