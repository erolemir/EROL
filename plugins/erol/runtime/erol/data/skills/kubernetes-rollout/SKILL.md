---
name: kubernetes-rollout
description: "Plan recoverable Kubernetes deployments using readiness, capacity, versioned artifacts and rollback checks."
metadata:
  version: "1.0.0"
---
# Kubernetes Rollout

Plan recoverable Kubernetes deployments using readiness, capacity, versioned artifacts and rollback checks.

## Workflow

1. Identify cluster context, namespace, workload kind and artifact revision; inspect existing rollout settings and live capacity before mutation.
2. Make readiness represent ability to serve; distinguish startup, readiness and liveness so dependency failures do not create restart loops.
3. Align surge/unavailability, resource requests and shutdown drain with observed capacity and request duration.
4. Rehearse a versioned rollback and account for data/schema compatibility; rollout completion alone does not establish application correctness.

## Verification

Validate manifests and authorized staging rollout, request continuity, unhealthy new pods and rollback. Preserve exact artifact/context evidence.

## Deliverable

Rollout plan, versioned manifests and availability/rollback checks.

## Current reference

Verify platform-specific details against [official documentation](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) for the deployed version.
