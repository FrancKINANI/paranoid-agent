# paranoid-agent

A local, drop-in gateway that sits between your AI agent and a remote model provider, in the spirit
of the **"paranoid mode"** Vitalik Buterin described on 2026-10-16: a separate Tor circuit per
conversation, prompts rewritten by a local model before they leave the machine, requests masked with
cover traffic, and payment unlinked from identity using **zkAPI**.

Your agent keeps speaking the OpenAI API. It just stops being a profile of you.

> **Status: documentation-first. There is no implementation code yet — and that is deliberate.**
> The problem is defined, the options are researched, and the plan is written down before anything
> is built. See [docs/README.md](docs/README.md) for the roadmap of documents and
> [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) for the milestones.

---

## The honest summary

This project raises the cost of linking an AI request to a person. It does not make you anonymous,
and this README will not pretend otherwise.

**What it addresses**

- **Network layer** — Tor, with a *separate circuit per conversation* so unrelated conversations are
  not visibly the same user.
- **Content layer** — a local model rewrites each prompt, dropping the sensitive details the remote
  model does not need to answer.
- **Payment layer** — zkAPI proves you can pay without revealing which deposit is yours.
- **Environment layer** — the whole thing runs in a kernel-enforced network namespace, so a single
  misconfigured request cannot leak directly.

**What it does not address**

- The provider still **reads your prompt**. It must, in order to answer.
- A provider that **colludes with your Tor guard relay** can correlate timing. This is the weakness
  Vitalik named himself; our answer is an experimental tier, not a claim.
- Your **writing style and reused documents** can still re-link sessions. Rewriting reduces this; it
  does not prove it away.
- **Payment unlinkability is qualified**: zkAPI's operator sees request timing and budget tier, the
  client discloses the note id to the operator's indexer, and the current anonymity set is tiny
  (on the order of tens of deposits, per L2BEAT's review).
- A **compromised local machine** defeats all of it.
- **Attachments, images, and any text outside the `user` role** are not rewritten.

Every one of these is tracked adversary-by-adversary in [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md),
which is the normative document: if anything here claims more than it allows, that is a bug.

---

## Privacy tiers

Strength is a dial, not a marketing word. You pick a tier; the gateway refuses to start if your
environment cannot deliver it.

| Tier | Network | Isolation | Prompt rewriting | Cover | Payment |
| --- | --- | --- | --- | --- | --- |
| **T0 Baseline** | Tor | app-level | off | off | your own key |
| **T1 Practical** | Tor, per-conversation | app-level | local model | off | your own key |
| **T2 Paranoid** *(goal)* | Tor, per-conversation | **kernel netns** | local, **fail-closed** | bounded Poisson | zkAPI or mock |
| **T3 Maximum** *(experimental)* | mixnet request path | kernel netns | local, fail-closed | constant-rate | zkAPI |

Tier 2 is weaker on macOS/Windows, where kernel-enforced isolation is unavailable — the product says
so rather than implying parity ([docs/DECISIONS.md](docs/DECISIONS.md) D3).

---

## What we reuse, and what we build

This is not a reimplementation. Payment cryptography is **never** hand-rolled.

| Layer | Where it comes from | Why |
| --- | --- | --- |
| Payment proofs, vault, settlement | **[`ethereum/zkapi`](https://github.com/ethereum/zkapi)** | Reimplementing note-bound Groth16 proofs would be reckless; the existing bar is already a single-party trusted setup |
| Network transport | **Tor**, isolated via `IsolateSOCKSAuth` | Mature, free, isolation-capable, and usable for streaming |
| Kernel isolation | **oniux** (Arti + network namespaces) | `torsocks` is not a boundary — it leaks for static binaries and is not true isolation |
| Local model serving | **Ollama** | Commodity; the interesting work is policy and measurement |
| Session policy, enforcement, leak/quality measurement, cover planning, gateway contract | **This project** | The parts we can verify — and the reason to trust any claim here |

Full per-layer comparison, with evidence and the options we rejected, in
[docs/LAYER-OPTIONS.md](docs/LAYER-OPTIONS.md).

---

## Documentation

The docs follow George Pólya's four-step method (*How to Solve It*, 1945), because the hard part is
deciding what to build and being honest about what it protects.

| Document | Purpose |
| --- | --- |
| [docs/README.md](docs/README.md) | Index, reading order, and status |
| [docs/PROBLEM.md](docs/PROBLEM.md) | **Step 1** — facts, assumptions, constraints, unknowns, measurable success criteria |
| [docs/PLAN.md](docs/PLAN.md) | **Step 2** — three candidate architectures compared, one chosen, falsifiers |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | **Step 3** — components, interfaces, request lifecycle, failure modes |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | **Step 3** — environment, dependencies, module contracts, milestones |
| [docs/EVALUATION.md](docs/EVALUATION.md) | **Step 4** — acceptance gates, measurement protocols, look-back ritual |
| [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md) | Adversaries by name, guarantee matrix per tier, ranked residual risks |
| [docs/LAYER-OPTIONS.md](docs/LAYER-OPTIONS.md) | Best available option per layer, with verdicts |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decision log and the open questions that need answering |
| [docs/SOURCES.md](docs/SOURCES.md) | Annotated sources with dates and caveats |

---

## Where to start

**If you are evaluating this:** read [docs/PROBLEM.md](docs/PROBLEM.md) §2 (what is actually true as
of 2026-10-17), then [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md) §3–4 (what you would and would not
get). Those two answer "should I trust this?" faster than anything else here.

**If you are going to build it:** [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) §5. **Milestone M0
is the starting point** — a small probe that proves egress is Tor-only and that conversations really
do land on separate circuits. It is deliberately the first thing built, because a perfect rewriter
behind a leaking transport is theatre.

**If you disagree with a choice:** [docs/LAYER-OPTIONS.md](docs/LAYER-OPTIONS.md) names the evidence,
[docs/SOURCES.md](docs/SOURCES.md) links it, and [docs/DECISIONS.md](docs/DECISIONS.md) §C explains
how to supersede a decision properly.

---

## Prerequisites

Verified on the development machine on 2026-10-17: Python **3.14.7**, uv **0.12.7**, cargo
**1.98.0**, node **26.7.0**, Linux. **Tor and ruff are not installed yet** and are required —
installation steps are in [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) §1.2, and the Tor
configuration that makes isolation work is in §1.3 (without `IsolateSOCKSAuth`, the gateway refuses
to start rather than running unprotected).

Nothing has been built or tested yet, so today this section describes intent, not a verified
install.

---

## Contributing, in one rule

**Do not weaken a claim to make a test pass.** If a guarantee cannot hold, change the tier
documentation and the threat model in the same change — that is the correct fix, and it is a
documentation change, not a test change.

---

## License

Not yet chosen — see open question U10 in [docs/DECISIONS.md](docs/DECISIONS.md) §B.

---

*Documentation researched and written 2026-10-17, roughly a day after the reference design was
published and about two weeks after zkAPI launched. Given that pace, treat every fact as perishable:
[docs/SOURCES.md](docs/SOURCES.md) records where each came from and when.*
