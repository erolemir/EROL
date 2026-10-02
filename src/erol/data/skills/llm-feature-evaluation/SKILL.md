---
name: llm-feature-evaluation
description: "Evaluate LLM features on representative fixtures, failure categories, cost and human-review requirements."
metadata:
  version: "1.0.0"
---
# Llm Feature Evaluation

Evaluate LLM features on representative fixtures, failure categories, cost and human-review requirements.

## Workflow

1. Define the user task, allowed data/tools and consequential failure modes; build a representative held-out set with independent expectations.
2. Separate deterministic contract checks from judgment-based quality; calibrate any model judge against human-reviewed examples.
3. Measure failure slices, tool errors, latency and actual cost on a fixed model/configuration; do not infer real token savings from character counts.
4. Version prompts, data and model settings, guard against leakage, and define release thresholds and human escalation for uncertain cases.

## Verification

Run held-out positive/adversarial fixtures and baseline comparisons through the authorized provider; report unexecuted model trials and judge disagreements honestly.

## Deliverable

Versioned eval set, score/failure report and release decision criteria.
