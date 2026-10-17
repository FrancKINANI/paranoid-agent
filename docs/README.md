# Paranoid-Agent — Documentation Index

This repository is **documentation-first**. No implementation code exists yet, by design: the
problem is defined, options are researched, and the plan is written down before anything is built.

The documentation is organized around George Pólya's four-step method (*How to Solve It*, 1945)
because the hard part of this project is not writing code — it is deciding what to build, and being
honest about what it does not protect against.

| Step | Pólya's question | Document |
| --- | --- | --- |
| 1 | *Understand the problem.* What do we know, assume, and still not know? | [PROBLEM.md](PROBLEM.md) |
| 2 | *Devise a plan.* Similar problems, alternative approaches, simpler subproblems. | [PLAN.md](PLAN.md) |
| 3 | *Carry out the plan.* Work each step, check the reasoning. | [ARCHITECTURE.md](ARCHITECTURE.md) · [IMPLEMENTATION.md](IMPLEMENTATION.md) |
| 4 | *Look back.* Did it work? Could it be simpler? What carries forward? | [EVALUATION.md](EVALUATION.md) |

Supporting documents that cut across all four steps:

| Document | Purpose |
| --- | --- |
| [LAYER-OPTIONS.md](LAYER-OPTIONS.md) | Best-available option for each layer, with evidence and verdicts |
| [THREAT-MODEL.md](THREAT-MODEL.md) | Adversaries, what is protected, what is not, residual risk ranking |
| [DECISIONS.md](DECISIONS.md) | Decision log (ADRs) and open questions needing an owner |
| [SOURCES.md](SOURCES.md) | Annotated citations with dates and caveats |

## Reading order

- **First time here?** [PROBLEM.md](PROBLEM.md) → [PLAN.md](PLAN.md) → [ARCHITECTURE.md](ARCHITECTURE.md).
- **Evaluating whether to trust this?** [THREAT-MODEL.md](THREAT-MODEL.md) → [EVALUATION.md](EVALUATION.md).
- **About to build or review a PR?** [IMPLEMENTATION.md](IMPLEMENTATION.md) → [DECISIONS.md](DECISIONS.md).
- **Disagreeing with a choice?** [LAYER-OPTIONS.md](LAYER-OPTIONS.md) → [SOURCES.md](SOURCES.md), then file an ADR.

## Status

| Item | State |
| --- | --- |
| Problem definition | Complete ([PROBLEM.md](PROBLEM.md)) |
| Option research | Complete as of 2026-10-17 ([LAYER-OPTIONS.md](LAYER-OPTIONS.md)) |
| Architecture | Draft, pending open questions U1–U10 in [DECISIONS.md](DECISIONS.md) §B |
| Implementation | Not started ([IMPLEMENTATION.md](IMPLEMENTATION.md) is the plan) |
| Verification | No checks have been run — nothing is built yet |

## What this project is

A privacy-preserving local gateway between you and a remote AI model, in the spirit of the
"paranoid mode" Vitalik Buterin described on 2026-10-16: each conversation gets its own Tor
circuit, prompts are rewritten by a local model before leaving the machine, requests are padded
with cover traffic, and payment is unlinked from identity using zkAPI.

## What this project is not

A guarantee of anonymity. Every claim in these documents is scoped to a named adversary in
[THREAT-MODEL.md](THREAT-MODEL.md). Where we cannot protect you, the documentation says so
explicitly rather than implying safety by omission.

---

*Documentation researched and written 2026-10-17. Technology in this area moves quickly and some
components carry explicit "not production-ready" warnings from their own authors — see the
verification dates and caveats in [SOURCES.md](SOURCES.md) before relying on any specific claim.*
