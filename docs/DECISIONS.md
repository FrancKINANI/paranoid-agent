# Decisions and Open Questions

Two things live here: decisions already made (so they are not relitigated by accident, and so the
reasoning survives), and questions still open (so they are not silently answered by whoever writes
code first).

Format: `status` is one of **Accepted** / **Superseded** / **Open**. A decision with no
"revisit if" trigger is a decision that will rot.

---

## Part A — Decisions (ADRs)

### D1 — Do not reimplement payment cryptography; delegate the data plane

**Status:** Accepted (2026-10-17)

**Context.** Note-bound Groth16 proofs, Baby-JubJub commitments, Schnorr-signed balances, nullifier
chains, and settlement are all implemented upstream. The existing bar is already a **single-party
trusted setup** with no multi-party ceremony.

**Decision.** Payment proofs, the vault, and settlement are delegated to `ethereum/zkapi`. We write
only a thin adapter behind our own `PaymentProvider` interface.

**Alternatives rejected.** Hand-rolling the proof layer (catastrophic risk, no benefit); using a
zk-rollup or mixer as a metered-API rail (a category error, and one of them is sanctioned and
deprecated).

**Consequences.** We inherit upstream's security posture, including its caveats, and we must pin a
specific commit rather than a branch, because the privacy features are explicitly **not** in a
production release. Nothing in our threat model can be stronger than upstream's.

**Revisit if.** A multi-party ceremony ships and hardening improves; or upstream becomes unmaintained.

---

### D2 — Own the transport, rewriting, enforcement, and measurement

**Status:** Accepted (2026-10-17)

**Context.** Three approaches were compared in [PLAN.md](PLAN.md) §2. The value of this project is
not calling a model or moving bytes through Tor — both are solved. It is *policy*, *enforcement*, and
*evidence*.

**Decision.** We own: session lifecycle and isolation policy, kernel-level enforcement, the leak and
measurement harness, rewrite-quality evaluation, cover-traffic planning and target policy, the
gateway contract, and the honest-limitations documentation.

**Consequences.** More work than a wrapper; a smaller audit surface than a full reimplementation; and
an obligation to actually run the measurements we claim.

**Revisit if.** A wrapping approach demonstrates equal enforcement and measurement — unlikely, since
upstream's own docs state that SOCKS "cannot prove circuit construction/reuse or exit rotation" and
that the rewriter connects outside Tor.

---

### D3 — Linux is the primary platform for Tier 2; other platforms are explicitly weaker

**Status:** Accepted (2026-10-17)

**Context.** Kernel-enforced isolation (network namespaces) is Linux-only. `oniux` is Linux-only and
experimental; `torsocks` is cross-platform but leaks for static binaries and is not a boundary.

**Decision.** Linux gets kernel-enforced isolation (Tier 2). Other platforms get Tier 1, with the
gap **stated in the product**, never an implication of equivalence.

**Consequences.** A cross-platform story exists without a false one. Tier ceilings are per-platform
facts, reported by `paranoid doctor`.

**Revisit if.** A macOS/Windows sandbox provides kernel-enforced network isolation we can rely on.

---

### D4 — Isolation is a per-conversation SOCKS auth token; `NEWNYM` is never in the request path

**Status:** Accepted (2026-10-17)

**Context.** The v0 plan used `NEWNYM` per interaction. Tor's path spec rates application-provided
isolation tokens as the only *strong* isolation property; `NEWNYM` is a global, rate-limited circuit
flush that cannot express which streams belong together.

**Decision.** Session-scoped SOCKS5 credentials with `IsolateSOCKSAuth` enabled. The control port is
used to *observe* and verify. `NEWNYM` exists only as an operator-triggered recovery action.

**Consequences.** The gateway refuses to start in Tier 2 if `IsolateSOCKSAuth` is absent. Isolation
is verified by reading circuit state and reporting collisions honestly, because SOCKS cannot prove
circuit separation by itself.

**Revisit if.** Tor changes isolation semantics (see proposal 368 territory), or per-conversation
tokens prove to cluster conversations onto one guard in practice.

---

### D5 — Payment is an interface with mock, zkAPI, and BYOK adapters

**Status:** Accepted (2026-10-17)

**Context.** The newer "concession" protocol has no deployed manifests and no production proving
keys; published `clientd-v0.1.6` does not contain the privacy features. Meanwhile the whole pipeline
must be testable.

**Decision.** `PaymentProvider` with `mock` (development default), `zkapi` (production intent, thin
adapter), and `byok` (T0/T1 fallback). `status()` is part of the interface so anonymity-set size and
operator visibility are disclosed at run time.

**Consequences.** U1 (fund a real note or not) stops being an architectural blocker. The mock path
must be honest: it must never be presented as payment privacy.

**Revisit if.** Concession deploys with production keys and a multi-party ceremony.

---

### D6 — Original prompts live in memory only; "discarded" is defined precisely

**Status:** Accepted (2026-10-17) — supersedes the v0 contradiction

**Context.** The v0 draft said both "original prompt discarded from memory" and "optionally de-rewrite
the response with a local model". The second requires the first to still exist.

**Decision.** Original text is kept in memory for the life of the request (and, where a local
response-integration step needs it, for the session), and is **never** transmitted or persisted.
"Discarded" means *not sent and not written*, never "zeroized from RAM instantly". The persistence
audit (SC6) tests the claim that is actually made.

**Consequences.** Precise, testable language. We do not claim protection against a live local
attacker (AD7).

**Revisit if.** A design emerges that genuinely needs no access to the original, making the stronger
claim available.

---

### D7 — Cover traffic: bounded, Poisson, opt-in, own targets only, and never oversold

**Status:** Accepted (2026-10-17)

**Context.** The v0 idea ("background thread sending random HTTP requests to public sites") loads
third parties and is provably weak. Upstream's design is disciplined but defaults to 5/s, which its
own docs note can exceed 1 GiB/hour of responses, and its older helper hammered public APIs by
default.

**Decision.** Adopt upstream's scheduling discipline (Poisson interarrival, no startup burst, fixed
worker pool that drops rather than queues, byte and time caps, bodies discarded, separate SOCKS
identities, aggregate counters only). Change three things: **off by default**, a much lower default
rate, and a required list of targets we own or are permitted to poll. Label it exactly as upstream
does — background noise, not proven traffic-analysis protection.

**Consequences.** Cover is a mitigation, not a guarantee. A constant-rate design (the theoretically
stronger answer) waits for a mixnet and Tier 3.

**Revisit if.** We can demonstrate on our own harness that cover measurably degrades a timing
classifier; or a mixnet becomes viable for streaming.

---

### D8 — Rewriting fails closed, and both quality metrics ship together

**Status:** Accepted (2026-10-17)

**Context.** Upstream's rewriter is fail-closed and its own docs are careful about what "no raw
prompt" means. Research (arXiv 2606.04067) shows the tradeoff is two-sided: over-disclosure and
over-removal are both failures.

**Decision.** Any rewrite failure refuses the request. Tiers below Tier 2 may send unrewritten text
**only** if the user pre-authorised that downgrade, and the downgrade is visible in status output.
Publishing only a disclosure rate or only a retention rate is forbidden — the pair is the finding.

**Consequences.** Availability suffers when the rewriter is down, by design. Metrics become part of
the product's honesty rather than a research afterthought.

**Revisit if.** Measurements show a class of requests where fail-closed is worse for users than an
explicit, consented downgrade.

---

### D9 — Provider + guard collusion (AD5) is out of scope for Tiers 0–2

**Status:** Accepted (2026-10-17)

**Context.** Vitalik named this attack as the weakness of Tor for this use case, and proposed a
mixnet with constant-rate cover traffic. Random cover traffic is substantially less effective
against an adversary that can actively manipulate response timing.

**Decision.** Declare it out of scope, in the threat model, the README, and any claim we make. Tier 3
may benchmark a mixnet for the request path; no Tier-0–2 material may imply protection against it.

**Consequences.** The most sophisticated attack against this design remains unsolved and is stated
openly. This is a feature of the documentation, not a gap in it.

**Revisit if.** A mixnet benchmark shows acceptable latency and throughput for the request path, or
providers begin offering in-network endpoints.

---

### D10 — Run-time disclosure, not documentation-only disclosure

**Status:** Accepted (2026-10-17)

**Context.** The most likely way this project causes harm is by leaving a user with a stronger belief
than the evidence supports (R15).

**Decision.** Payment posture (including anonymity-set size) and cover-traffic posture (including
that it is unproven) are printed at startup and visible in `/admin/status`. Documentation alone is
insufficient, because users do not read it and attackers benefit when they do not.

**Consequences.** Some users will be told their privacy is weaker than they hoped. That is the
correct outcome.

**Revisit if.** Never, in the direction of less disclosure.

---

### D11 — We operate no infrastructure on the user's behalf

**Status:** Accepted (2026-10-17)

**Context.** A relay or gateway we operated would see traffic timing for every user, becoming exactly
the correlation point the design exists to remove.

**Decision.** The project is local software only. No hosted service, no relay, no telemetry, no
analytics. Cover-traffic targets are the user's own or permitted resources.

**Consequences.** No operational cost and no central point of failure or compromise. Requires user
setup, which the `doctor` command exists to soften.

**Revisit if.** Never — this is a load-bearing privacy property.

---

### D12 — HTTP is not re-implemented; the gateway speaks OpenAI's API

**Status:** Accepted (2026-10-17)

**Context.** The reference design and upstream both expose an OpenAI-compatible endpoint; agent
harnesses, Open WebUI, and editors already speak it.

**Decision.** Interoperate with the existing contract instead of inventing one. Loopback only, no
routable bind, no protocol extensions that break generic clients; extras ride in headers and admin
endpoints.

**Consequences.** Immediate compatibility; a stable contract to test; some awkwardness where
OpenAI's API has no room for our concepts (tier, session), handled via headers that degrade
gracefully.

**Revisit if.** The OpenAI-compatible surface changes in a breaking way, or a needed capability has
no representable form.

---

---

### D13 — An egress guard checks the final payload (proposed 2026-10-18)

**Status:** Proposed — needs the owner's sign-off, because it adds a component and a failure mode.

**Context.** Two independent reviews of this repository converged on the same weakness: the rewriter
is a local LLM processing untrusted text, and "fail closed" only rejects *malformed* output. A
rewrite that is well-formed, on-topic, and still contains the sensitive span is a silent leak we
cannot detect by inspecting the rewriter. We currently have no check on what actually leaves.

**Decision (proposed).** Before any request leaves, compare the final serialized payload against a
session-scoped blocklist of **protected literals** — strings the user marks as must-not-leave (an
email, a wallet address, a client name, a path). Match on normalised forms, not just exact bytes.
On a match: refuse the request by default, with an explicit override that is logged as metadata.

The same component supplies the two things the threat model currently lacks: a **dry-run mode**
that prints the exact outbound payload to the terminal without persisting it (R17), and fixed-size
**request padding**, which is the cheap half of cover traffic and costs no tokens.

**Consequences.** A testable guarantee replaces an unprovable one ("the rewriter is careful"). False
positives become a real failure mode — over-removal or refusal on legitimate content — so the guard
must be measured on both leak and utility, like the rewriter (R8). It does not stop a leak the user
never listed; it stops the ones they care about, which is what they asked for.

**Revisit if.** False-positive refusals make the guard get disabled (then it is security theatre), or
the rewriter becomes deterministic enough that the guard is redundant.

---

### D14 — Deterministic minimization is the floor; the LLM rewriter is an optional layer (proposed 2026-10-18)

**Status:** Proposed — this would change the recommended T1/T2 configuration and is the owner's call.

**Context.** Today's design makes a local LLM rewriter mandatory and fail-closed. That has three
costs: it needs a machine that can run one (the owner's own stated constraint — many people cannot),
it is non-deterministic and therefore hard to test, and it is the component most vulnerable to
prompt injection (R16). Meanwhile the cheapest, most reliable minimization is deterministic and needs
no GPU at all.

**Decision (proposed).** Define a **floor** of deterministic transforms — typed detectors (patterns
for emails, phone numbers, addresses, keys, paths), and reversible pseudonyms — that run always and
are unit-testable. The LLM abstraction becomes a **layer above the floor**, enabled only when a local
model is available, and its output is never the sole protection.

If pseudonyms are introduced, the design inherits a **substitution table** and a **restoration**
step: placeholders must be mapped back in responses *and* in tool calls, and streaming must be
buffered so a placeholder split across chunks is not emitted half-restored. That is a component in
its own right, not a detail — which is precisely why the current design has none (it rewrites rather
than substitutes) and why adding one is a decision, not a patch.

**Consequences.** The gateway can run on a laptop with no GPU and still reduce leakage. Two code
paths must be measured separately, or the floor's real value gets hidden inside the LLM's score.

**Revisit if.** A small local model proves deterministic enough under constrained decoding, or
detector quality on real traffic is too poor to be worth the false positives.

---

## Part B — Open questions

These block or shape work and need an owner. Referenced from [PLAN.md](PLAN.md) §6 and
[PROBLEM.md](PROBLEM.md) §5.

**U1–U6 are the owner's own decisions, and they are intentionally still open.** The concepts they rest
on are built from scratch in [learn/](learn/00-how-to-use.md), and
[learn/08-decision-worksheet.md](learn/08-decision-worksheet.md) lays each one out with its costs,
its reversibility, and a template for recording the answer here as a new ADR.

| # | Question | Blocks | Impact if unanswered | Owner |
| --- | --- | --- | --- | --- |
| **U1** | Fund a real mainnet zkAPI note in v1, or ship mock-first? | M3 scope; acceptance testing | Payment layer stays simulated; "unlinkable payment" remains unproven in practice | User |
| **U2** | Which providers must work, and do they accept Tor? | Provider strategy; tier reachability | Requests may be refused by the provider; the design is unusable regardless of its own correctness | User |
| **U3** | What added latency per turn is acceptable? | Rewriter model class; cover rate; whether Tier 2 is interactive at all | We may build something correct and unusable; protections get switched off (R13) | User |
| **U4** | Is Linux-only acceptable for strict isolation? | Isolation layer; threat-model verdicts per platform | Non-Linux users get T1 while believing they have T2 | User |
| **U5** | Is token streaming required? | Response-path padding; Tier 3 feasibility | Rules out constant-rate cover on the response path | User |
| **U6** | Is AD5 (provider + guard collusion) acceptable as out of scope for v1? | Whether Tier 3 mixnet work starts now or later | If unacceptable, v1 scope grows into mixnet benchmarking with unproven payoff | User |
| **U7** | How much may be deposited in a note, given pause/expiry risk (R6)? | Payment UX; `budget_per_session_usd` defaults | Funds can be frozen; the mitigation is simply not leaving much in the vault | User |
| **U8** | Which cover-traffic endpoints do we own or have permission to poll? | M4; cover cannot ship enabled without them | Cover stays disabled, leaving timing exposure in place | User |
| **U9** | Do we pin upstream `clientd` at a commit now, or wait for a reviewed release? | M3 build reproducibility | Pinning an unreleased branch is a maintenance and trust decision | Maintainer |
| **U10** | Public repo hygiene: license, security policy, and how to report findings? | Publishing, accepting contributions | Privacy-critical code without a disclosure process invites unmanaged risk | Maintainer |
| **U11** | Which wire formats must your agents speak — OpenAI only (D12), Anthropic Messages, or both? | Gateway facades in M1 | An agent that speaks Anthropic Messages cannot use the gateway at all, however private it is | User |
| **U12** | Is per-task routing in scope — send what a local model can handle to the local model, escalate only the reduced context? | Scope; whether a router exists or the gateway is one hop | Without it, every request leaks a task description to the frontier provider; with it, the product answers a different question than "hide my identity" | User |

---

## Part C — How to change a decision

1. Open a new ADR; do not edit an accepted one except to mark it **Superseded** with a pointer.
2. State which threat-model row or evaluation gate changes.
3. Update [THREAT-MODEL.md](THREAT-MODEL.md) §3/§4 and the affected gates in
   [EVALUATION.md](EVALUATION.md) in the same change.
4. If the decision weakens a guarantee, the README must change too — the same commit, not later.

A decision that changes guarantees without changing documentation is a defect, and is treated as
one in review.

---

---

## Part D — Response to external review (2026-10-18)

Two independent reviews were run against this repository, both of them restricted to the README. Each
objection is adjudicated below, including the ones where the reviewer was wrong. **A review is an
input, not a verdict** — the last word is the threat model.

| # | Objection | Verdict | Disposition |
| --- | --- | --- | --- |
| 1 | "A per-conversation Tor circuit is meaningless while the API key identifies you (T0/T1)." | **Correct, and it was an overclaim.** The threat model already said key rotation only happens in runtime-key mode; the README did not. | README network bullet and tier table qualified; new guarantee row in [THREAT-MODEL.md](THREAT-MODEL.md) §3; AD3 carries an explicit *the key is the identity* paragraph |
| 2 | "In an agent loop, tool results and history are most of the traffic, and they are not rewritten." | **Correct on substance.** It was disclosed as R11 at Medium; the severity was wrong, and the README never drew the conclusion. | R11 raised to **High** with the agent-loop consequence spelled out; README scopes the product as chat-shaped today |
| 3 | "The rewriter can be prompt-injected, and fail-closed does not catch a valid leak." | **Correct and unmitigated.** The only prompt-injection note was a non-goal about model *output*; this is injection into our own component. | D13 (egress guard, proposed); R16 |
| 4 | "Rewriting has a utility/privacy tradeoff; you need numbers." | Already handled. | [EVALUATION.md](EVALUATION.md) measures both; R8; V2's fallback rule forbids silent substitution of the original |
| 5 | "Pseudonymisation needs a stable table and de-substitution in streaming and tool calls." | Correct as a *dependency*, not as a defect: this design rewrites rather than substitutes, so there is nothing to restore — and nothing to recover either. | Noted in D14 and [ARCHITECTURE.md](ARCHITECTURE.md) 3.4; the substitution table is scoped as a component if adopted, not a patch |
| 6 | "T2 'Paranoid' can run against a mock payment, so the name means nothing." | **Correct.** | T2 now requires zkAPI; `mock` is a development adapter and status reports payment unlinkability as absent |
| 7 | "zkAPI is young, its anonymity set is tiny, single-party setup, operator sees timing." | Already handled, and it is the strongest part of the documentation. | F3, R4, R5, AD4, SC8 |
| 8 | "Which providers accept zkAPI? If none, the universal gateway story collapses." | **Correct as an unknown**, and sharper than we had it: zkAPI mints **OpenRouter** keys, and no evidence exists that OpenAI or Anthropic accept zkAPI credentials. | README says so explicitly; U2 is the owner's question |
| 9 | "Providers block or challenge Tor exit traffic." | Already a first-class risk with no silent fallback. | R3, A4 |
| 10 | "oniux is experimental, so 'kernel-enforced' needs a maturity caveat." | Already documented. | F6, R14, D3, SOURCES |
| 11 | "Cover traffic on a token-priced API costs real money." | **Wrong as stated.** Cover traffic is explicitly forbidden from targeting paid APIs, so it does not consume provider tokens; its costs are bandwidth and third-party load (R7, R9). | No change beyond D13's padding, which is the cheap part and costs nothing |
| 12 | "Add fixed-size padding; keep constant-rate cover for later." | Accepted — padding was simply missing. | D13 |
| 13 | "Make deterministic minimization the base and the LLM optional; many users have no GPU." | **Accepted in principle** — and it is the reviewer's strongest structural point. | D14, pending the owner's decision |
| 14 | "Your real goal is minimising the profile providers build, not anonymity; add a local/frontier router." | Plausible, but it is an inference about the owner's goal, not a fact. It also answers a different question than the README asks. | Recorded as U12 rather than adopted |
| 15 | "Key on the credential (P1/P2/P3 postures) instead of T0–T3 tiers; the tiers mix five axes." | **Correct as a framing critique.** The tiers do bundle network, isolation, rewriting, cover, and payment. | Not adopted yet: reframing would rewrite every document, and the credential question is U1/U2. Tiers stay as presets, explicitly described as such |
| 16 | "Two API facades: OpenAI *and* Anthropic Messages." | Not a defect — D12 chose OpenAI deliberately. But the reviewer's underlying question is real and unasked until now. | U11 |
| 17 | "Enforce egress with a container whose only route is the gateway." | Already the design. | D3, [ARCHITECTURE.md](ARCHITECTURE.md) 3.7 |
| 18 | "Eleven documents and ten lessons for zero code is too much; build M0 now." | Half right. The volume is defensible *only if it is used*; the risk that it substitutes for measurement is real. But the gate is the owner's, not a reviewer's. | `AGENTS.md` gate left unchanged. M0 stays first, and EVALUATION already treats every doc claim as unverified until M0 reports |

**The one objection neither review could settle:** *which adversary comes first* — a network observer,
a profiling provider, or a colluding provider — determines the layer priorities more than U1–U6 do.
That is [PROBLEM.md](PROBLEM.md) §1's question, and it is the owner's to answer.

---

*Related: [PROBLEM.md](PROBLEM.md) §3 assumptions, §5 unknowns; [PLAN.md](PLAN.md) §6 risks;
[SOURCES.md](SOURCES.md) for the evidence behind each decision.*
