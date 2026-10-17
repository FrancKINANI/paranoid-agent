# 08 — Decision Worksheet

## The question this answers

You now have the concepts. This document turns them into the six decisions that shape the project —
**and the decisions are yours, not the tooling's.** Nothing here is being decided for you, and no code
should be written until you have made them consciously (see `AGENTS.md`).

A reassurance first: **the plan has been built so that every option below is reachable without a
rewrite.** Payment is an interface with three adapters (D5). Isolation has per-platform tiers (D3).
Rewriting is fail-closed with an explicit downgrade path (D8). Transport has a Tier 3 slot for a mixnet
(D9). So your answers change configuration and scope — not architecture.

## The method

Ask four questions of every option. They are not equally weighted.

**1. Which adversary does this address?** If you cannot name one from
[../THREAT-MODEL.md](../THREAT-MODEL.md) (`AD1`–`AD9`), the option is cost without benefit. If you
cannot name one, that is a finding, not a failure.

**2. What does it cost, and in which currency?** Latency, bandwidth, money, or utility — from
lesson 07. Naming the currency usually reveals who is paying. Bandwidth paid by a third party you do
not control is the one to be most suspicious of.

**3. Is it reversible?** This is the question people skip, and in this project it is the decisive one.
Latency and bandwidth are reversible. **A funded note is not**: the deposit is a permanent public
record, and the funds are exposed to pause/expiry risk. **An identity-linked on-ramp is not.** Prefer
spends you can undo.

**4. If I am wrong, what is the cost of changing my mind?** Cheap-to-reverse decisions can be made
faster and with less evidence. Expensive ones deserve evidence you gather yourself.

---

## U1 — Fund a real payment note, or ship mock-first?

**What it controls:** whether payment unlinkability is real or simulated in v1, and whether acceptance
testing needs money and mainnet access.

| Posture | Addresses which adversary | Cost | Reversible? |
| --- | --- | --- | --- |
| **Mock-first** | None directly — it proves the *interface*, not the privacy | Engineering time only | **Fully** |
| **Fund a small note (<$50)** | `AD4` (payment operator) — proves the real path end-to-end | Gas; funds exposed to pause/expiry; a permanent public deposit; and the crowd you join is currently **very small** | **No** |
| **Wait for multi-party setup + deployed production keys** | `AD4`, plus the trusted-setup concern | Nothing now; payment unlinkability stays unavailable and BYOK's identity link stays in place | Yes (you can fund later) |

**What lesson 04 established that bears on this:** the cryptography is not the weak point. The weak
points are the **crowd size** (anonymity set, on the order of tens), the **single-party trusted setup**,
the **operator's ability to pause withdrawals**, and the **on-ramp** where you obtain the ETH. Funding a
note buys you a genuine unlinkability property *among a small set*, subject to those caveats.

**Choose mock-first if:** you want the whole pipeline built, tested, and understood before any money is
exposed. This is also the only option that spends a *reversible* currency.

**Choose to fund a note if:** you specifically want to validate the operational reality — deposit,
authorization, settlement, withdrawal — with your own hands, and you accept the exposure. Keep the
balance small: the amount is the mitigation (open question U7).

**Choose to wait if:** the single-party setup or the pause capability is disqualifying for you, and you
would rather have no payment privacy than a version you cannot fully stand behind.

---

## U2 — Which providers must work?

**What it controls:** whether the zkAPI/OpenRouter path is the primary one, and whether unlinkable
payment is reachable at all for the models you actually want.

| Path | Unlinkable payment? | Constraint |
| --- | --- | --- |
| **OpenRouter via zkAPI** | **Yes** — the only path where it exists | zkAPI mints the key; OpenRouter and the model host still read your prompts and can link requests under one key |
| **Bring your own key** (OpenAI, Anthropic, Google, …) | **No** — the key *is* the identity | Providers differ sharply in whether they tolerate Tor-routed traffic; some require KYC'd paid accounts |
| **A local model** | Not applicable — nothing leaves | Requires hardware; gives up frontier capability |

**The trap to avoid:** designing for a provider that turns out to refuse Tor-routed requests. Privacy
that cannot reach a provider is not privacy, it is a failed request. This is risk R3, and it is why the
architecture has **no automatic direct-connection fallback** — a refusal must be visible, not silently
routed around the protections.

**Choose OpenRouter only if:** you want the single coherent story (one provider, unlinkable payment,
runtime-key mode where prompts go direct and no intermediary sees them).

**Choose OpenRouter + one BYOK provider if:** you want a hedge against Tor being refused, and you accept
that the BYOK path has **no payment unlinkability** and must be labelled as such.

**Choose any OpenAI-compatible endpoint if:** flexibility matters more than payment privacy — including
pointing the gateway at a local model, where content privacy is solved outright and the network and
payment layers become moot.

---

## U3 — What added latency is acceptable?

**What it controls:** the rewriter model class, the cover-traffic rate, whether Tier 2 is interactive at
all, and whether Tier 3 is even a candidate.

**Procedure (from lesson 07):**

1. **Measure the floor first.** Tor-only, no rewriting, no cover. You cannot choose a budget for a
   delta until you know the base. This is Milestone M0's job, and it needs Tor installed.
2. **Set a provisional ceiling now** so work is not paralysed, and upgrade or downgrade it with real
   numbers in hand.

| Ceiling | Implies | Rules out |
| --- | --- | --- |
| **≤3s added** | Small rewriter model (~1–4B) kept resident; low cover rate; reuse payment leases | Mixnet transport; large rewriters |
| **≤8s added** | A stronger rewriter; more aggressive cover | Mixnet; anything with mixing delay |
| **>15s** | Optimise purely for privacy; larger models, higher cover, constant-rate experiments | Interactive chat — this is closer to batch usage |
| **Decide after measuring** | Provisional 5s, revisit at M2 with published p50/p95 | Nothing — but you are deferring a decision, so write down that you deferred it |

**Why this decision is load-bearing:** per lesson 07, a protection the user disables is worth zero.
Your latency ceiling is therefore *how much privacy you will actually have*, not a performance
preference. If you pick 3s and the only model that fits your hardware cannot preserve constraints
reliably, the honest option is a lower tier with the reason stated — not a hidden downgrade.

> **A note on this one:** the "decide by measurement" option is not a dodge. It is defensible, and it
> is arguably the most rigorous, *provided* the measurement is scheduled and the provisional ceiling is
> written down. What would be a dodge is proceeding without any ceiling and declaring the result
> acceptable after the fact.

---

## U4 — Is Linux-only acceptable for strict isolation?

**What it controls:** the isolation floor, and therefore the truthfulness of the tier labels.

| Choice | Tier ceiling | What you give up |
| --- | --- | --- |
| **Linux only** | T2 as designed — kernel-enforced, leaks impossible rather than unlikely | Convenience; user must be on Linux |
| **Cross-platform, documented gaps** | T1 elsewhere, with the gap stated in the product | On macOS/Windows, isolation is advisory — one missed path leaks |
| **Cross-platform, pretend parity** | Not offered | This would be a documentation lie, which `AGENTS.md` prohibits |

**Choose Linux-only if:** you are the primary user and you are on Linux (you are — the development
machine is Linux 7.2.5). This is the simplest honest option.

**Choose cross-platform if:** other people will use it. Then the work is in *reporting* the ceiling per
platform through `paranoid doctor`, so nobody believes they have T2 when they have T1.

---

## U5 — Is token streaming required?

**What it controls:** whether the response channel can be shaped, and whether Tier 3's constant-rate
idea is viable at all.

- **Streaming (default for chat):** better usability, and it is what OpenAI-compatible clients expect.
  Costs: the response is a long, unmistakable stream; you cannot pad it to a fixed size without
  delaying output, and constant-rate cover over a shared Tor path is not achievable.
- **Whole responses:** you could pad and batch responses, at the cost of a much worse experience for
  anything but short answers — and the request part remains streamed anyway.
- **Both, per request:** implement streaming first (it is what clients speak) and treat response
  shaping as a Tier 3 research question.

**Choose streaming if:** this is for interactive use, which is the stated purpose. Then record
explicitly that **the response path is not padded or constant-rate**, which is why lesson 03's
conclusion stands: cover traffic here is a local mitigation only.

---

## U6 — Is provider-plus-guard collusion acceptable as out of scope for v1?

**What it controls:** whether Tier 3 (mixnet) work starts now, or stays a documented experiment.

**Name the adversary precisely:** `AD5` — a provider that cooperates with your guard relay, using
timing to correlate a request with your client. This is not a hypothetical attack; it is the one
Vitalik Buterin singled out as Tor's weakness for this use case.

| Option | Consequence |
| --- | --- |
| **Out of scope for T0–T2 (recommended)** | The project ships something usable, and states plainly that this attack is unsolved. This is what [../THREAT-MODEL.md](../THREAT-MODEL.md) currently says |
| **Benchmark a mixnet for the request path (Tier 3)** | Addresses `AD5` in principle. Costs: mixing latency (seconds, inherent), constant-rate bandwidth, and a poor fit for streamed responses. Requires a benchmark before any claim, and its latency may violate your U3 ceiling |
| **Treat it as disqualifying** | Then this project cannot protect you against your most likely sophisticated adversary, and the honest conclusion is that the content-minimisation layers plus a local model are the right answer for you, rather than a network-anonymity design |

**The question to ask yourself:** *who is my adversary, really?* If it is an ISP, a curious provider, or
a third party correlating casually, T2 is a good answer and mixnet work is wasted effort. If it is a
sophisticated actor who would actively collude with a relay, then Tor is the wrong foundation — and per
lesson 03, being honest about that is more valuable than adding a layer that looks protective.

---

## Recording your decisions

Write your answers into [../DECISIONS.md](../DECISIONS.md):

- Promote each answer from Part B (open questions) to Part A (a decision ADR), dated, with the reasoning
  and a "revisit if" trigger.
- If an answer changes a guarantee, update [../THREAT-MODEL.md](../THREAT-MODEL.md) §3–4 **in the same
  change**. Per `AGENTS.md`, a guarantee change without a documentation change is a defect.
- Then [../IMPLEMENTATION.md](../IMPLEMENTATION.md) §5 becomes actionable, starting with **M0** — which
  needs only Tor installed, answers none of the above, and de-risks the core transport assumption for
  everyone.

### Template

```markdown
### D13 — <decision title>

**Status:** Accepted (<date>)

**Context.** <what forced the decision; cite the lesson or adversary>

**Decision.** <what you chose>

**Alternatives rejected.** <what you did not choose, and why>

**Consequences.** <what this costs; which currency; what it forbids>

**Revisit if.** <the trigger that would reopen this>
```

## Self-check

1. Which of U1–U6 can be changed later at low cost, and which cannot? Order them by reversibility.
2. You have no intention of ever facing a state-level adversary, and you mostly want the provider not to
   build a profile of you. Which decisions become easy, and which become irrelevant?
3. Suppose you pick "Linux only" (U4), "≤3s" (U3), "mock-first" (U1), and "out of scope" (U6). Describe
   the thing you just specified in one sentence — and name the adversary you are *not* defended against.

<details>
<summary>Answers</summary>

1. Most reversible: **U5** (streaming — a request-shaping choice), **U2** (providers — configuration),
   **U3** (latency ceiling — retunable once measured), **U6** (scope — a research question you can
   revisit). Then **U4** (platform — affects who can use it, not what was built). Least reversible:
   **U1** if you fund a note — a public deposit and exposed funds cannot be undone. Hence the
   recommendation to build mock-first.

2. Easy: **U1** becomes clearly mock-first or BYOK-only — real unlinkable payment is a large cost for an
   adversary you are not prioritising. **U6** becomes trivially out of scope. **U3** can be generous,
   because the goal is comfort rather than defeating a correlator. Irrelevant: the mixnet question
   entirely, and much of the timing-analysis material. The remaining work is content minimisation
   (lesson 05) plus not leaking your IP — which is a much smaller and more achievable project.

3. *"A Linux-only, interactive gateway where prompts are rewritten locally with a small model, the
   network is Tor-isolated per conversation with bounded cover traffic that is explicitly labelled
   unproven, and payment is simulated behind a swappable interface."* Not defended against: **`AD5`**,
   a provider colluding with your guard relay via timing — plus, with payments mocked, there is **no
   payment unlinkability at all**, so `AD4` is unaddressed and your funding identity remains visible
   wherever a real key is used.

</details>

---

*Next: [09 — Glossary](09-glossary.md), then back to [../DECISIONS.md](../DECISIONS.md) to record your
answers.*
