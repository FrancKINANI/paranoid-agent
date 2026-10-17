# Step 1 — Understand the Problem

> *"It is foolish to answer a question that you do not understand."* — Pólya, *How to Solve It*

This document separates what we **know**, what we **assume**, what we are **constrained by**, and
what we **still do not know**. Nothing here is a design; that is [PLAN.md](PLAN.md).

---

## 1. The problem in one sentence

> Build a local drop-in gateway in front of a remote AI model such that no single party can link
> a request to the person who made it — not the network observer, not the model provider, and not
> the payment system — while keeping the latency and answer quality good enough that a person
> actually uses it.

"Paranoid mode" is the informal name for this. The realistic goal is **raising the cost of
correlation**, not eliminating it.

### Why this is worth doing

An API key is an identity. Every prompt sent to a hosted model today joins a billing-linked
history: the account points to a payment method, and the prompts profile the person. zkAPI's
launch note states the problem plainly — "every prompt you send joins the record attached to
both" — which is why the reference design funds the network, payment, and content layers
separately.

### Why it is hard

The three leaks live in different layers and are fixed by different means:

| Layer | Leak | Fixed by | Not fixed by |
| --- | --- | --- | --- |
| Network | Source IP, timing, volume | Tor / isolation | Payment privacy |
| Payment | Billing identity tied to usage | zkAPI-style unlinkable-by-design credits — **qualified**, see F3 | Tor |
| Content | Prompt text identifies you | Local rewriting | Tor, zkAPI |
| Environment | Agent process reaches the network directly | Kernel-level isolation | Application discipline |

A solution that addresses only one layer is easy and nearly useless. Most "private AI" tools
address only the content layer, or only the network layer, and then market the result as private.

---

## 2. What we know (facts)

Each fact is dated and sourced in [SOURCES.md](SOURCES.md). Facts decay; re-verify before relying
on them.

### F1 — The reference design exists and was published 2026-10-16

Vitalik Buterin described a "paranoid mode" wrapper for his `pi` agent harness combining zkAPI,
Tor, cover traffic, and local LLM prompt rewriting behind an **OpenAI-compatible daemon**. Stated
properties:

- a separate Tor circuit per conversation;
- requests masked with random cover traffic;
- zkAPI for unlinkable payment (his framing; the qualifiers are F2 and F3);
- local model rewriting prompts before they leave the machine (his setup used
  `qwen3.8-flash-next`);
- the agent harness itself wrapped in a `bubblewrap` sandbox and run under `torsocks`;
- experimental MicroVM isolation was mentioned but not part of the working setup.

He also stated the two weaknesses himself, which we treat as design inputs rather than
objections:

1. **Latency.** "It's getting quite usable!" but it adds "quite a bit" of latency, worst at the
   start of a new conversation. Earlier local-model tests in this line of work ran at ~20–30
   tokens/second, with 100+ tokens/second described as preferable.
2. **Traffic analysis.** Tor was called "far from optimal here for privacy." The specific
   residual attack: an AI provider **colluding with the user's Tor guard relay** can manipulate
   request/response timing to defeat random cover traffic. His proposed direction was a
   specialized mixnet with constant-rate cover built into the network.

### F2 — zkAPI is real, live, and narrower than it sounds

The Ethereum Foundation and the Open Anonymity Project announced zkAPI on **2026-10-01**, running
on Ethereum mainnet. Mechanism:

- deposit ETH/USDC into a vault contract once; the balance becomes a **private note**;
- spend it by producing a **Groth16 proof over BN254** that a funded, unspent note covers the
  spend; commitments and nullifiers use Poseidon, in a 32-level Merkle tree;
- the server verifies the proof off-chain and mints a **short-lived, dollar-capped API key** in
  memory;
- payment verifies spending rights without receiving the conversation; the provider serves the
  prompt without learning the funding identity.

Two operating modes matter to us:

- **Runtime-key mode** — the key is issued, then your prompts go **directly** to the provider.
  No payment intermediary sees message traffic. This is the mode that matters for us.
- **Proxy mode** — the zkAPI server relays requests. Easier to run, but the relay sees traffic.

The project's own documentation lists two limitations, and both are load-bearing for this design:

- **No network anonymity.** The gateway can correlate request patterns under a stable IP. The
  stated mitigation is Tor with a fresh circuit per session — i.e. exactly what we are building.
- **Prompt content leaks.** Sessions can be re-linked by the provider through reused personal
  details, writing style, reused history, or project documents. Described as a privacy–utility
  tradeoff, with local or TEE models generating requests as one mitigation.

### F3 — An independent review of zkAPI rates the privileged insider **Exposed**

The L2BEAT privacy review of zkAPI (published Oct 2026; figures captured mid-October 2026) is
the most useful counterweight to the launch announcement:

| Finding | Detail |
| --- | --- |
| Trusted setup | **Single-party Groth16 setup.** No multi-party ceremony. Retained secrets allow forged withdrawal proofs. |
| Request metadata | The operator sees each request's **time and budget tier** — though not its note. |
| Note linkage | `zkapi-clientd` **reveals the note id to the operator's indexer before each request**. |
| Provider linkage | OpenRouter and the model provider can read prompts and **link requests under one key**. |
| Anonymity set | Tiny. TVL **≈$2.29K** across **93 deposits, total, all time**. Few active notes cover a top-tier budget, so an insider can narrow candidates heavily. |
| Custody risk | The owner EOA can **pause withdrawals**; expired notes can be swept to the treasury. Escape exists (1 day) but cannot be started during a pause. |
| Verifier | Runs in an Azure confidential container (AMD SEV-SNP) with attestation; both clients pin only the verifier address, so the check only holds if the user verifies it. |

**Consequence for us:** zkAPI removes a real class of linkage (which deposit paid), but it is not
a magic anonymity layer, and its current anonymity set is small enough that "unlinkable" must
always be qualified. Any claim we make must be scoped to an adversary, not stated absolutely.

### F4 — Upstream `zkapi-clientd` already implements much of the privacy stack

The `ethereum/zkapi` repository contains a **privacy-enabled client development branch** whose
README describes native Tor conversation isolation, canonical prompt rewriting, a separate
target-side transcript, bounded cover traffic, and saved vault-protocol selection. Documented
behavior, quoted from its own docs:

**Tor isolation** — configure Tor's SOCKS port with `IsolateSOCKSAuth`, then point the client at it
with `config --relay-url tor://127.0.0.1:9050`. The daemon then "retains a Tor isolation identity
for prefix-continuing message histories and rotates both identity and provider key for unrelated
histories." No global NEWNYM is used. Its own caveat: *"SOCKS cannot prove circuit construction or
reuse or exit rotation."*

**Cover traffic** — opt-in, disabled by default:
`config --cover-urls URL... --cover-rate 5 --cover-concurrency 4`. Properties its documentation
commits to: Poisson (random exponential) interarrival times independent of prompts; random first
arrival with no startup burst; fixed worker pool with unbuffered dispatch that **drops** arrivals
under saturation rather than queuing or bursting; ≤20 s per request; 64 KiB response cap;
per-worker random SOCKS identity that never derives from inference or payment context;
authenticated `tor://` only, remote DNS, no direct fallback; bodies discarded and not logged;
aggregate counters printed once a minute, never per-request logs.

Its stated costs and limits, which we adopt wholesale rather than re-deriving:

- at the default 5/s with every response at the 64 KiB cap, response payload alone can exceed
  **1 GiB/hour**, excluding TLS and Tor overhead;
- *"More noise is not necessarily stronger anonymity"*;
- *"This is background noise, **not proven traffic-analysis protection**"* — it is not constant-rate
  traffic, does not pad inference, does not conceal startup/shutdown, and **does not address the
  rewriter's direct connection**;
- an exit observer may distinguish small GETs from streamed inference; selected hosts, User-Agent,
  TLS fingerprint, response sizes and schedule may themselves be recognizable;
- cover consumes bandwidth and third-party resources, **not** zkAPI credit.

**Prompt rewriting** — opt-in, disabled by default:
`config --rewriter-url http://localhost:8012 --rewriter-model qwen3.8-flash-next`. Properties:
target-side history kept separately from client history; every user text part in a target request
must have passed through the rewriter; cached rewrites are replayed verbatim rather than replaced
by raw text; only each new user turn's text is sent to the rewriter; the cache holds
original-message **hashes** and normalized text only, is memory-only, ≤4096 messages and ≤8 MiB,
and **fails closed** on overflow; on restart, edited/truncated history, or unknown turns, all
unknown user turns are normalized before inference rather than passed raw.

Its stated limits, again adopted as ours:

- **the rewriter sees original text**, over a **direct connection outside Tor**, ignoring
  environment proxies. This is why the rewriter must be local;
- attachments, images and audio are **retained and not anonymized**;
- text copied into system/developer/assistant/tool messages is **not** rewritten — only `user`
  message text is protected;
- *"no raw prompt" is not a guarantee that every character changes* — normalized wording may match
  the original, especially code and quotes;
- meaning preservation and reduced stylometric identifiability are **model instructions, not
  proven properties**.

### F5 — Tor's own specification says `NEWNYM` is the wrong tool for per-conversation isolation

The original v0 design said to "use Stem to request new circuit before each interaction." That is
the wrong mechanism, and the distinction matters:

- Tor's path-spec defines **stream isolation** via isolation properties. Two streams share a
  circuit only if their profiles are compatible. Of the standard properties, only
  **application-provided isolation tokens** are rated *strong*.
- For SOCKS, the isolation token is carried in the **SOCKS username/password** fields, gated by
  the `IsolateSOCKSAuth` flag.
- `NEWNYM` is a different operation: it makes new requests avoid old circuits and clears the DNS
  cache. Tor's control spec notes Tor **MAY rate-limit** it, and it is rate-limited in practice
  (on the order of a 10-second cooldown, roughly six rotations/minute). Spamming it degrades the
  whole client, and it does not express *which* streams belong together.
- With a strong isolation token present, Tor's guidance is to **reuse the circuit for a long time**
  (circuit rotation controlled by `MaxCircuitDirtiness`, default 10 minutes, and
  `KeepAliveSocksAuth`).

**Consequence:** isolation is expressed per conversation via a SOCKS auth token, not by global
circuit-flushing. Stem's control port is used for *observing and diagnosing* circuits, not as the
isolation primitive.

### F6 — `torsocks` is not a sufficient isolation mechanism, and a kernel-level alternative exists

`torsocks` works by overriding libc network functions. Its documented limitations:

- applications making syscalls outside a dynamically linked libc — including **purely static
  binaries** and Zig-built programs — **leak**;
- it is not true isolation: the app still has access to the host's real network interfaces, so a
  single missed path is a direct connection.

The Tor Project released **oniux** (2025) specifically to fix this: it drop-ships any Linux program
into its own **network namespace** with only an `onion0` interface, using Arti and onionmasq, and
mounts a Tor-aware resolver. Kernel-enforced, so a malicious or careless application cannot leak.
Stated caveats: **Linux only**, and **experimental** — newer Tor software (Arti, onionmasq) with
less battlefield history than 15-year-old torsocks. It was at v0.4.0 at announcement and now has a
dedicated site under arti.torproject.org.

### F7 — A mixnet is the theoretically better transport and the practically worse one, today

- **Nym** runs a 5-hop mixnet with Poisson mixing and cover traffic; NymVPN exposes "mixnet tuning"
  (2026) to trade latency against anonymity. Mixnets pay for metadata protection with **latency and
  bandwidth**, and Nym packetizes traffic.
- **Katzenpost** is the long-running research-grade mixnet with constant-rate cover traffic; its own
  literature notes that most cover traffic is dropped by design, meaning bandwidth cost is
  structural.
- Mixnet research is active and adversarial: a 2026 PoPETs paper analyzes attacks on Nym's
  reputation system.

**Consequence:** for a chat request a mixnet is defensible; for **streaming multi-megabyte model
responses** it is not, today. We treat mixnet transport as a **Tier-3 option for the request path
only**, to be benchmarked rather than assumed. Vendor performance claims here are unverified by us.

### F8 — Rewriting has a measurable, benchmarkable privacy/utility tradeoff

The most relevant recent work recasts the problem as **task necessity** rather than PII type: a
span should be forwarded only if the remote model needs it. The "Need to Know" paper (arXiv
2606.04067, June 2026) builds `DelegateCI-Bench` — 3,167 samples across 11 domains and 20 task
types — annotating each request with **task-essential spans** and **task-non-essential sensitive
spans**, which names the two failure modes precisely:

- **over-disclosure** — forwarding a non-essential sensitive span;
- **over-removal** — stripping a span the remote model needed to answer.

The distinction is genuinely non-obvious: "I'm allergic to peanuts" must be preserved when asking
for hiking snacks and removed when asking for a file-renaming script. Its reported learned rewriter
improves utility by up to +10.1 over on-device baselines.

**Consequence:** rewriting quality is not a vibe; it can be measured, and we should measure it
rather than assert it. Neither upstream's instruction nor ours has a published utility guarantee.

### F9 — The local half of the stack is commoditized

- **Ollama** serves `POST /api/chat` and an OpenAI-compatible surface; `keep_alive` controls model
  residency; `/api/show` reports supported thinking modes. VRAM, not API shape, is the real
  constraint.
- Local serving is a solved problem; the interesting engineering is in policy, isolation, and
  measurement, not in calling a local model.

### F10 — Practical, non-cryptographic blockers exist

Not security facts, but they decide whether the project is usable:

- **Providers block or throttle Tor exits.** Some require paid, KYC'd accounts or reject Tor
  ranges outright. A privacy design that assumes any provider accepts a Tor-routed runtime key can
  fail on contact.
- **Payments are gated in the current upstream state.** The newer "concession" protocol has
  **no deployed network manifests and no production proving keys**; the live mainnet vault is the
  older `v2-note-bound` circuit line, reachable via the `release/v2-note-bound` branch. Published
  client release `clientd-v0.1.6` **does not contain** the privacy branch's features.
- **Gas and latency costs are real**, and the local runtime needs a capable machine.

---

## 3. Assumptions (each one is a risk if false)

| # | Assumption | If it is false |
| --- | --- | --- |
| A1 | The user's own machine is not already compromised; the endpoint is trusted | Everything downstream is defeated; no design here helps against local malware or a keylogger |
| A2 | A local model good enough to rewrite prompts runs acceptably on the user's hardware | Rewriting either degrades answers badly (over-removal) or adds untenable latency; must fall back to a weaker tier and say so |
| A3 | The Tor network is not wholly adversary-controlled, and guard/exit diversity is meaningful | Timing correlation attacks get cheaper; the design degrades to "hides from casual observers" |
| A4 | The user has a legitimate reason to route AI traffic this way, and Tor use is acceptable in their jurisdiction and compatible with the provider's terms | The project may be unusable or unlawful for that user; this is a decision for the user, not for us to assume away |
| A5 | At least one provider accepts zkAPI-issued keys, and the anonymity set for notes stays above a handful | Payment unlinkability becomes nominal; the privileged-insider exposure in F3 dominates |
| A6 | The rewriter is local and reachable over loopback | Upstream's rewriter path is a **direct connection outside Tor**; pointing it at a remote service re-identifies the user (see F4) |
| A7 | Tor's circuit reuse behavior is acceptable — circuits are reused while healthy, rotated on dirtiness | Overtesting for "new circuit per request" leads to wasted effort; per-conversation isolation is the requirement, not per-request rotation |
| A8 | Upstream's budget figures are representative (64 KiB/response, ≤20 s/request) for our cover targets | Bandwidth and load on third parties scale differently; must be measured, not assumed |

---

## 4. Constraints

**Technical**

- Linux for any *strict* isolation story (netns/oniux). Non-Linux support is best-effort with
  documented gaps — see [DECISIONS.md](DECISIONS.md) D3.
- Local toolchain present on this machine (verified 2026-10-17): Python **3.14.7**, uv **0.12.7**,
  cargo **1.98.0**, node **26.7.0**, curl 8.22.0, Linux 7.2.5. **Tor is not installed** and
  **ruff is not installed** — both are prerequisites, see [IMPLEMENTATION.md](IMPLEMENTATION.md).
- Building upstream `clientd` requires the Rust and Node toolchains; both are present.
- The concession protocol is not deployable today (F10), which constrains what "working payment"
  can mean in v1.

**Economic**

- Cover traffic consumes real bandwidth and third-party resources. At upstream defaults it can
  exceed **1 GiB/hour** in responses alone. It must be opt-in, bounded, and aimed at resources we
  control or are permitted to poll.
- zkAPI mainnet deposits require ETH and gas; withdrawals can pay fees from the payout via an
  ERC-4337 paymaster, so the payout address needs no ETH — but funding still costs real money.

**Legal / ethical**

- Route cover traffic only at endpoints we own or have written permission to poll. Upstream's docs
  are explicit: do not point it at sensitive URLs, signed paths, state-changing GET endpoints, paid
  APIs, or services without permission. The obsolete upstream helper did hammer third-party APIs by
  default; we will not.
- Payment unlinkability is a legitimate privacy property; it is not a licence to evade lawful
  obligations, and provider terms may prohibit Tor use outright.

**Scope**

- Single user, single machine. No multi-tenant anonymity, no mix-network operation, no
  cryptocurrency custody service.

---

## 5. Unknowns (nothing in the plan should silently depend on these)

These are tracked as open questions with owners in [DECISIONS.md](DECISIONS.md):

| # | Unknown | Why it blocks |
| --- | --- | --- |
| U1 | Does the user want to fund a real mainnet note in v1, or run against a mock payment provider first? | Determines whether the payment layer is real or simulated in M1–M3, and whether acceptance testing needs funds |
| U2 | Which model providers must work? | Determines whether the zkAPI/OpenRouter path suffices or we need a bring-your-own-key path; providers differ on Tor tolerance |
| U3 | What added latency is acceptable per turn? | Sets the rewriter model class, cover-traffic rate, and whether mixnet transport or streaming tradeoffs are even on the table |
| U4 | Is strict isolation required on macOS/Windows, or is Linux-only acceptable? | Changes the isolation layer from kernel-enforced to advisory, which changes the threat model's verdicts |
| U5 | Is token streaming required, or are whole responses acceptable? | Streaming rules out constant-rate cover for the response path and complicates padding |
| U6 | Does the user accept the residual guard-collusion attack as out of scope for v1? | If not, v1 scope grows into mixnet benchmarking |

---

## 6. Precise problem statement

Given a user `U` with an agent/application that speaks the OpenAI API, build a local gateway `G`
such that:

1. **No direct egress.** No process in `G`'s subtree establishes a TCP connection to any host other
   than the local Tor SOCKS listener, except the local rewriter and local admin socket.
2. **Per-conversation isolation.** Every conversation `c` maps to a distinct Tor isolation token
   for the lifetime of `c`, and unrelated conversations never share a circuit while both are live.
3. **No unrewritten user text on the wire.** Every `user`-role text part that reaches a remote
   provider has passed through the local rewriter; failure to rewrite **fails closed** — the request
   is refused, never sent raw.
4. **Content-residue minimization.** Rewriting removes task-non-essential sensitive spans while
   preserving task-essential ones, to a **measured** standard, not an asserted one.
5. **Payment unlinkability** at least as strong as zkAPI's runtime-key mode, with the residual
   exposure of F3 stated in the user-facing documentation rather than hidden.
6. **No persistence of raw prompts.** Original prompt text exists in memory only, for the duration
   of the request, and never reaches disk, logs, telemetry, or a crash dump.
7. **Observable health.** The user can see, at any moment: which session is live, its isolation
   token, its circuit, whether cover traffic is running, and whether the last leak self-test passed.

Subject to: the residual risks in [THREAT-MODEL.md](THREAT-MODEL.md), which are **not** solved by
this design and are listed as first-class limitations of the product.

---

## 7. Success criteria (measurable, per criterion)

Derived from §6. Methods and thresholds are refined in [EVALUATION.md](EVALUATION.md); the point of
listing them here is that every requirement has a *test*, not an opinion.

| # | Criterion | Method | Proposed pass condition |
| --- | --- | --- | --- |
| SC1 | No direct egress | Namespace-level packet check plus socket audit over a 10-minute mixed workload | Zero non-loopback sockets from the gateway subtree other than the Tor SOCKS listener |
| SC2 | Conversation isolation | 20 concurrent fresh sessions; read `GETINFO circuit-status` | Zero cases of two live unrelated sessions on one circuit; 100% carry distinct isolation tokens |
| SC3 | Exit diversity (informational) | Same 20 sessions; observe exit IPs | Report the distribution; **≥5 distinct exits** as a sanity floor, documented as statistical, not a guarantee |
| SC4 | Rewrite completeness, fail-closed | Adversarial corpus: retries, edited and truncated history, tool continuations, text smuggled into system/tool/assistant roles, attachments | 100% of `user` text rewritten; **0** raw-text transmissions; unknown content types refused |
| SC5 | Rewrite privacy/utility | Annotated span set in the style of `DelegateCI-Bench` (≥200 samples of our own) | Non-essential span disclosure ≤ 5%; task-essential spans retained ≥ 90%; report both, never one alone |
| SC6 | No raw prompt persistence | Post-session filesystem and log audit; forced-crash case | No original prompt text recoverable from disk, logs, or temp files |
| SC7 | Latency honesty | Instrument rewrite time, time-to-first-token, and total per turn; report p50/p95, not averages | Numbers published in the README; regressions gated in CI; budget set by D2 (U3) |
| SC8 | Payment posture is stated | Written per-adversary statement | Anonymity-set size and the F3 exposures disclosed in user-facing docs at run time |
| SC9 | Leak suite passes | DNS, IPv6, rewriter direct-connection, telemetry, and cover-traffic routing checks | All green on Linux; non-Linux gaps listed as failures, not skipped silently |

**Anti-criteria.** We explicitly do **not** claim, and will not test for:

- resistance to a global passive adversary;
- protection against a compromised local machine;
- hiding prompt content from the provider (impossible — it must read the prompt to answer);
- unlinkability stronger than the zkAPI note anonymity set of the moment;
- any protection for text the user voluntarily places outside the `user` role.

---

## 8. What the previous draft of this repository got wrong

Recorded because it justifies the rewrite, and because these errors are common in this space.

| Original claim | Problem | Corrected position |
| --- | --- | --- |
| "Use Stem to request new circuit before each interaction" | `NEWNYM` is a global, rate-limited circuit-flush; it cannot express which streams belong together | Per-conversation isolation via **SOCKS auth tokens** with `IsolateSOCKSAuth` (F5) |
| "Integrate zkAPI payment layer (Aztec, Tornado.cash)" | Tornado.cash is OFAC-sanctioned and deprecated; Aztec is a zk-rollup, not a metered-API payment rail | zkAPI is the actual rail for metered APIs, and it now exists (F2) |
| Treated payment privacy as sufficient on its own | Payment is one of four layers; content and network leaks survive it | All four layers are separate requirements with separate tests (F3, §6) |
| "After response, optionally de-rewrite with local model" **and** "original prompt discarded from memory" | Contradiction: re-integration needs the original | Keep the original **in memory only**, and define "discarded" as *not transmitted and not persisted*, never as "zeroized instantly" — see [DECISIONS.md](DECISIONS.md) D6 |
| "Generate cover traffic: background thread sending random HTTP requests to public sites" | Third-party load, no design, weaker than random noise; upstream's old helper hammered public APIs by default | Bounded, Poisson-scheduled, opt-in traffic against **endpoints we control**, with the honest admission that it is not proven protection (F4) |
| "Wrap into CLI/API interface" | Vague | An OpenAI-compatible gateway is the interface, because that is what agent harnesses already speak (F1, F4) |
| "Test for IP/DNS leaks using ipleak.net" | Manual, one-off, unrepeatable | Scripted leak suite with CI gates (SC9) |

---

## 9. Prior art we are not duplicating

| Project | What it does | Our relationship |
| --- | --- | --- |
| `ethereum/zkapi` / `zkapi-clientd` | zkAPI client, vault, proofs, Tor isolation, rewriting, cover traffic | **Reuse.** We do not reimplement note-bound Groth16 payments (F2, F4) |
| ToR / Arti / oniux | Network anonymity; kernel-level app isolation | **Reuse** as the transport and isolation primitive (F6) |
| Ollama / llama.cpp | Local model serving | **Reuse** as the rewriting engine (F9) |
| OA Chat / Open WebUI / `pi` | Chat frontends | **Interoperate.** We present an OpenAI-compatible endpoint (F1) |
| Nym / Katzenpost | Mixnet transport with cover traffic | **Benchmark later** for the Tier-3 request path (F7) |
| L2BEAT | Independent privacy review of zkAPI | **Consume and cite** — the source of our honest caveats (F3) |

---

*Next: [PLAN.md](PLAN.md) — devising the plan, and which of these options we actually choose.*
