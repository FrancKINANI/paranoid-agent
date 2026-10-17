# Step 2 — Devise a Plan

> *"If you can't solve a problem, then there is an easier problem you can solve: find it."* —
> Pólya, *How to Solve It*

---

## 1. Looking for an analogous problem

Pólya's advice is to find a related problem we already know how to solve. Four analogies shaped the
plan.

**Analogy A — Tor Browser solved "user doesn't configure proxying correctly."**
The hard part was never SOCKS; it was that a single misspelled proxy setting leaks everything. Tor
Browser's answer was to make the whole application live inside the anonymity boundary, with
per-domain circuit isolation built in rather than opt-in. *Transfer:* our gateway must be the
boundary, not a wrapper around a boundary. This is why application-level "we set the SOCKS proxy"
is rejected in favour of kernel-enforced isolation (see [LAYER-OPTIONS.md](LAYER-OPTIONS.md) §2).

**Analogy B — Whonix/Tails solved "the app must not be trusted."**
Both split the system so the untrusted application cannot see the real network. *Transfer:* assume
our own agent process is careless or hostile. Every leak defence must hold without cooperation from
the app.

**Analogy C — Signal's sealed sender solved "the server is honest-but-curious about metadata."**
The insight is to separate *what the server must know* from *what it must not*, and use cryptography
to enforce the gap. *Transfer:* zkAPI does exactly this for payment (server learns a valid payment
exists and the dollars per session; never who, what, or which deposit). We should copy the
*structure* — separate the layers so no party sees two of {identity, content, payment} — instead of
inventing crypto.

**Analogy D — a canary in the coal mine is a sensor, not a defence.**
Safety-critical systems do not assert they are safe; they *instrument* for failure. *Transfer:* the
deliverable includes a leak-detection and measurement harness. A privacy tool without a
self-test is a belief system.

**The "easier problem" move:** the easiest version of this problem is *"prove, with a script, that
traffic is really leaving through Tor and that prompts are really being rewritten."* That is
buildable in a day, it de-risks the core assumptions, and it is **Milestone M0** below. We resist
building the user-facing product first.

---

## 2. Three candidate approaches

### Approach A — Thin wrapper around upstream `clientd`

Configure and launch `zkapi-clientd` with its Tor, rewriter, and cover-traffic features; add a
shell/CLI around it and documentation.

- **Wins:** fastest to something working; delegates the cryptographic surface (note-binding,
  Groth16, settlement) to the people who wrote it; inherits real Tor isolation semantics.
- **Loses:** no control over two things we care most about — enforcement (upstream relies on
  application-level Tor routing, with **no network-namespace containment**) and *measurement* (no
  rewrite-quality evaluation, no leak self-test). Its own docs admit that SOCKS "cannot prove
  circuit construction/reuse or exit rotation," and that the rewriter connects **directly, outside
  Tor**. We would be shipping a black box we cannot verify.
- **Verdict:** necessary but insufficient. It is the right *data plane*, the wrong *product*.

### Approach B — Reimplement everything in Python

Own Tor controller, own rewriter pipeline, own cover-traffic worker, own payment client.

- **Wins:** maximum control, one language, no cross-toolchain build.
- **Loses:** we would be reimplementing (a) note-bound Groth16/Schnorr settlement — a
  catastrophic place to hand-roll, with a single-party trusted setup as the existing bar; and
  (b) cover-traffic and rewriting logic that upstream has already reasoned about in detail, with
  documented failure modes we would have to rediscover. It also multiplies audit surface in the one
  area where audit is hardest.
- **Verdict:** rejected. The interesting, defensible work is not the crypto.

### Approach C — Hybrid: own control plane and verification, upstream data plane **(chosen)**

We own: session lifecycle and isolation policy, kernel-level enforcement, the measurement and leak
harness, rewrite-quality evaluation, cover-traffic planning and target management, the user-facing
gateway contract, and the honest-limitations documentation. Upstream (or a hardened equivalent)
owns: payment proofs and settlement, and the Tor/rewriter/cover plumbing it already implements.

**The division of labour follows one rule: own what we can verify, delegate what we would only be
able to trust.**

### Comparison

| Dimension | A. Thin wrapper | B. Reimplement | **C. Hybrid (chosen)** |
| --- | --- | --- | --- |
| Cryptographic risk | Low (delegated) | **Very high** (hand-rolled) | Low (delegated) |
| Time to first working demo | Days | Weeks–months | ~1 week for M0, weeks for full |
| Control over isolation | None (advisory) | Full | Full (kernel-enforced) |
| Control over rewrite quality | None | Full | Full (own eval + own module if needed) |
| Verifiability of claims | Low (trust upstream docs) | Medium | **High** (own leak + quality harness) |
| Dependency risk | High (one project) | Low | Medium (payment delegated, rest owned) |
| Payment compliance/legal | Delegated | **Ours to carry** | Delegated |
| Latency control | None | Full | Full (tiers) |
| Effort to audit before trusting | Small surface, unknown internals | Large | Medium, well-bounded |

---

## 3. Breaking the challenge into smaller pieces

Decomposition, each piece independently verifiable:

| # | Subproblem | Independently verifiable by |
| --- | --- | --- |
| P1 | Prove traffic is Tor-only, kernel-enforced | `P0` harness, §5 |
| P2 | Express per-conversation isolation | Circuit-status assertions |
| P3 | Rewrite prompts locally, fail closed | Adversarial corpus with 0 raw transmissions |
| P4 | Pad with cover traffic without harming anyone | Target-load budget + scheduler tests |
| P5 | Unlink payment | zkAPI runtime-key path, or mock with identical interface |
| P6 | Never persist raw prompts | Post-run filesystem/memory audit |
| P7 | Measure quality and latency honestly | Published numbers, CI gates |
| P8 | Survive failure without leaking | Failure-mode tests (Tor down, rewriter down, provider reject) |

The ordering matters: **P1 and P2 before P3–P5**, because a beautiful rewriter behind a leaking
transport is theatre. This is the single most important sequencing decision in the plan.

---

## 4. The chosen plan

### 4.1 Privacy tiers (the latency/strength dial)

Different users have different tolerances, and the honest answer to "how private is it?" is "it
depends which tier you turned on." Tiers are documented, not hidden:

| Tier | Network | Isolation | Rewriting | Cover | Payment | Added latency (expected) |
| --- | --- | --- | --- | --- | --- | --- |
| **T0 Baseline** | Tor SOCKS | App-level | Off | Off | BYO key | Low |
| **T1 Practical** | Tor SOCKS | App-level, per-session token | Local model | Off | BYO key | +0.5–3 s/turn |
| **T2 Paranoid** (default goal) | Tor SOCKS | **Kernel netns (oniux)** | Local model, fail-closed | Bounded Poisson | zkAPI / mock | +1–5 s/turn |
| **T3 Maximum** *(experimental)* | Mixnet for request path (benchmark first) | netns | Local model | Constant-rate (deferred) | zkAPI | Seconds to tens of seconds |

Tier selection is explicit configuration, and the docs must state the residual risks **per tier**.
T1 is genuinely weaker than T2, and saying so is the product.

### 4.2 Component ownership

| Component | Owner | Rationale |
| --- | --- | --- |
| Session lifecycle, isolation tokens | **Us** | Core policy; determines P2 |
| Network enforcement / sandbox launch | **Us** | Determines P1; the thing upstream does not do |
| Leak + measurement harness | **Us** | The reason to trust any claim |
| Rewrite quality evaluation | **Us** | Turns F8 into numbers instead of adjectives |
| Cover-traffic planning, target policy, budget | **Us** | Third-party harm avoidance is ours to own |
| Rewriting execution | Us initially; upstream if it proves equal or better | Both are model-driven; we must be able to test either |
| Payment proofs, vault, settlement | **Upstream** | Never hand-roll (B's fatal flaw) |
| Payment interface abstraction | **Us** | Lets mock and real be interchangeable (U1) |
| Local model runtime | **Upstream (Ollama)** | Commodity (F9) |
| Gateway HTTP contract | **Us** | The product surface |

### 4.3 What we deliberately do *not* build

- A payment protocol, vault, or note scheme.
- A mixnet. (Benchmark, then decide — see U6/F7.)
- A new model. Reuse whatever local model wins on the P7 metrics.
- A browser extension or mobile app.
- Anything requiring a server we operate. **Not running infrastructure for other people's privacy is
  a deliberate choice:** it removes us as a correlation point and as a target.

---

## 5. Milestones preview

Full exit criteria in [IMPLEMENTATION.md](IMPLEMENTATION.md); this is the shape of the plan.

| Milestone | Goal | Exit gate |
| --- | --- | --- |
| **M0 PoC** | Prove transport truth: Tor-only egress + two sessions on different circuits | Scripted harness prints exit distribution and circuit mapping; zero direct egress |
| **M1 Gateway** | OpenAI-compatible local endpoint with session lifecycle | An unmodified client (Open WebUI/curl) chats through it; sessions isolated |
| **M2 Rewriting** | Fail-closed local rewriting + quality harness | SC4 = 0 raw transmissions; SC5 measured and published |
| **M3 Payment** | `PaymentProvider` interface; mock and zkAPI adapters | Mock path complete; zkAPI path documented, gated on U1 |
| **M4 Cover traffic** | Bounded Poisson scheduler against permitted targets | Bandwidth budget enforced; scheduler tests pass; no third-party abuse |
| **M5 Hardening** | Kernel-level isolation, leak suite, no-persistence audit | SC1, SC6, SC9 all green on Linux |
| **M6 Usability** | Tiers, config, honest docs, packaging | A new user reaches T2 without reading source |

**M0 is intentionally tiny** and comes first because it falsifies the cheapest assumptions.

---

## 6. Risks and how the plan absorbs them

| Risk | Likelihood | Impact | Mitigation in plan |
| --- | --- | --- | --- |
| Upstream privacy branch is unstable or renamed | Medium | High | Data plane behind our own interface; pin a commit; own the rewriter path if needed (D1) |
| zkAPI concession protocol never deploys | Medium | Medium | `PaymentProvider` interface with a mock; legacy vault path documented (U1, D5) |
| Providers reject Tor traffic | High | High | Document per-provider reality in [LAYER-OPTIONS.md](LAYER-OPTIONS.md) §5; never assume reachability |
| Rewriting over-removes and ruins answers | High | Medium | Measured, published, tunable; tier T1 fallback; never silently degrade (D8) |
| Latency unacceptable | Medium | High | Tiers; measure p95 from day one; model class chosen by measurement, not hype |
| Local model unavailable / too small | Medium | Medium | Fail closed *or* downgrade *explicitly* — never silent (A2, D8) |
| Cover traffic harms third parties | Medium | High (non-technical) | Own only permitted targets; hard budget; disabled by default (P4, D7) |
| We overclaim privacy | **High if unmanaged** | **Fatal to the project's purpose** | [THREAT-MODEL.md](THREAT-MODEL.md) is normative; SC8 requires run-time disclosure (D10) |
| Provider + guard collusion (F1's attack) | Low | High | Declared out of scope for T0–T2; T3 benchmarks a mixnet (U6) |

---

## 7. How we will know the plan was wrong

A plan that cannot fail is not a plan. These are the falsifiers, checked at every milestone
([EVALUATION.md](EVALUATION.md) makes this a ritual):

1. **If M0 shows we cannot reliably isolate circuits per conversation**, the architecture is wrong,
   not the test — move isolation to a stronger boundary (per-session Tor instance or netns-per-
   session) before building further.
2. **If SC5 cannot exceed "essential retention 90% AND non-essential disclosure 5%"** with a model
   that fits the user's hardware, then rewriting is not delivering its promised value and the honest
   move is to de-emphasize it and lead with payment + network privacy instead.
3. **If measured latency at T2 exceeds the user's tolerance (U3) even at the smallest useful
   rewriter**, then either rewriting is out of the interactive path or the product is not
   interactive — and we say which.
4. **If the payment anonymity set stays at tens of notes**, we must stop describing payment as
   unlinked and start describing it as "unlinked only against a non-colluding operator with a tiny
   set" — the L2BEAT privileged-insider verdict, in the product's own words.
5. **If kernel isolation is impossible on the target platform**, Tier 2 collapses to Tier 1 and the
   threat model must be rewritten, not quietly weakened.

---

*Next: [LAYER-OPTIONS.md](LAYER-OPTIONS.md) — for each layer, which concrete option wins and why.*
