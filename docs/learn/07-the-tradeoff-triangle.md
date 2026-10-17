# 07 — The Tradeoff Triangle

## The question

Why can you not have strong privacy, fast responses, and good answers all at once — and how do you
decide which to give up?

## First principle

**Privacy is bought with one of four currencies. You cannot spend none of them.**

| Currency | You pay it as | Example from the previous lessons |
| --- | --- | --- |
| **Latency** | Waiting | Tor circuit latency; mixnet mixing delay; local model inference on every prompt; key settlement windows |
| **Bandwidth** | Bytes, continuously | Cover traffic (upstream's cited figure: potentially >1 GiB/hour in response payloads alone at their default rate); constant-rate tunnels you pay for while idle |
| **Money** | Fees and hardware | Ethereum gas for deposits and withdrawals; a GPU or a bigger machine to run a capable rewriter |
| **Utility** | Worse answers | Over-removal in rewriting; smaller models; giving up conversation history to avoid content linkage |

The instinct, when someone says "add privacy", is to look for the version with no cost. It does not
exist. **Every privacy design is a decision about which currency to spend, made on someone's behalf.**
The useful question is therefore not "is this private?" but "what does this privacy cost, and who is
paying?"

## Why the costs compose

This is where intuition usually fails. Each layer's cost is individually acceptable, and they add:

```
total added latency  =  Tor circuit setup
                      + rewrite inference (local model)
                      + key acquisition / settlement (payment)
                      + transport round-trips (×2 for chat: send, stream back)
```

If each of four steps adds 1.5 seconds, the user experiences 6 seconds before the first token — and
they will conclude the tool is slow, which is a different and more damaging verdict than "the tool is
private". You cannot tune your way out of addition; you can only remove layers, shrink models, or
accept the delay.

There is also a **multiplicative** effect on top of the additive one: the cost of the slowest step is
paid *per turn*, and a conversation is many turns.

### Cold versus warm: measure both

The worst case is not the average case, and the two differ by everything that can be precomputed:

| | Cold (new conversation) | Warm (continuing) |
| --- | --- | --- |
| Local model | May need loading into memory: seconds | Resident: milliseconds |
| Tor circuit | New circuit to build | Reused |
| Rewriting | Nothing cached | Cached rewrites for prior turns |
| Payment | New key/lease | Existing lease still valid |

This is why the person who popularised this design reported that the *start of a new conversation* is
the slowest part, and why [../EVALUATION.md](../EVALUATION.md) §5 requires cold and warm to be
measured and reported separately. A single blended average would hide exactly the pain users notice.

## Usability is a security property

Here is the most important practical claim in this lesson:

> **A protection the user turns off is worth exactly zero.**

This is not a soft product concern. It is arithmetic. Consider a design that is twice as private on
paper but three seconds slower per turn: if the user disables it after a week, its realised privacy is
zero, while a weaker design the user keeps enabled has a realised privacy of whatever it provides. **The
stronger-looking option lost.**

This reframing has three consequences that shape this project:

1. **Tiers are a security feature, not a compromise.** Letting someone choose "Tor and local rewriting
   but no cover traffic, no payment" so that they actually use it beats a single maximum-strength mode
   they abandon. See [../PLAN.md](../PLAN.md) §4.1.
2. **Fail-closed needs an exception path that is explicit.** If the rewriter breaks and the gateway
   simply refuses to work, users will look for a way around it — and the way around it will be a
   version with no rewriting at all. Requiring an explicit, visible, pre-authorised downgrade (D8) is
   how fail-closed survives contact with an annoyed human.
3. **Latency must be measured from the beginning, not optimised at the end.** Instrumenting in
   Milestone M0 — before there is a product to be disappointed by — is what makes it possible to say
   later which layer costs what.

## The subtle one: memory versus privacy

Conversation history is a tradeoff in both directions, and it is easy to get backwards.

| Keeping history | Effect on utility | Effect on privacy |
| --- | --- | --- |
| Full conversation sent each turn | Best answers — context is what makes a model useful | Worst: reused history and details are the provider's best cross-session linking signal |
| Fresh sessions, no history | Worse answers — the model forgets | Better isolation between conversations |
| Rewritten history (reconstruct rather than resend raw) | Preserves context for the model | Reduces what is disclosed while keeping the benefit |

That third row is what a target-side transcript buys you, and it is a neat illustration of the theme:
the interesting engineering is in finding moves that do not simply trade one currency for another. It
does not eliminate the tradeoff — the model still sees a coherent conversation, which is still
linkable — it just spends less.

## How to budget: a procedure

When you face a latency-versus-privacy decision, do it in this order:

1. **Set the ceiling first.** Decide the maximum added delay you will accept before you start
   optimising (this is open question U3). A budget chosen afterwards will be chosen to fit whatever you
   built, which is the definition of motivated reasoning.
2. **Measure the floor.** Establish the cost of the minimum viable privacy: Tor alone, no rewriting, no
   cover. Everything else is a delta against that.
3. **Spend the remaining budget on the highest-value layer.** Usually rewriting, because content
   linkage (R1) is the highest-ranked residual risk in [../THREAT-MODEL.md](../THREAT-MODEL.md).
4. **Choose the smallest model that meets the quality bar** — where the quality bar is the measured
   span metrics from lesson 05, not a vibe. Rewriting is a constrained transformation, and a small
   model may well suffice.
5. **Decide in advance what happens when the budget is exceeded:** fail closed, or an explicit
   downgrade. Never a silent one.
6. **Re-measure at p95, not the mean,** because the tail is what users experience as "this is
   unusable".

## Prefer reversible spends

The four currencies are not equally recoverable:

| Spend | Reversible? |
| --- | --- |
| Latency | Yes — turn the layer off |
| Bandwidth | Yes — lower the cover rate |
| Hardware | Mostly — sell it |
| **Money in a private note** | **No** — funds can be at risk (pause/expiry), and a deposit creates a permanent public record |
| **Identity at the on-ramp** | **No** — buying ETH with your ID is a permanent link |

This asymmetry is a design principle, not just an observation: **early experiments should spend
reversible currencies.** Building and testing the whole pipeline against a mock payment provider spends
latency and effort, and risks nothing. Funding a real note spends a public, irreversible record — and
buys a crowd that is currently very small. That reasoning is the core of open question U1, and lesson 08
walks through it.

## Where it breaks

**1. Hardware reality.** The rewriter is only as good as the model you can run. A very small model on
a modest laptop may fail to preserve constraints reliably — which is over-removal, i.e. a *utility*
loss that looks like the AI being bad. If your hardware cannot run a model that meets the bar, the
honest options are: lower the tier and say so, or don't rewrite interactively.

**2. Tor's own latency and variability.** Tor round-trip times vary widely, and providers may
additionally throttle or block Tor exits. The floor is not yours to fix, and it is worth measuring on
your own network rather than trusting anyone's number, including this document's.

**3. Costs that are invisible until they are large.** Cover traffic at a "reasonable" 5 requests per
second is potentially more than a gigabyte per hour of responses — a real bandwidth bill and a real
load on whoever hosts the targets. Bandwidth is the currency people underestimate most, and the third
party paying it did not consent.

**4. Privacy theatre.** It is cheap to add a layer that looks protective and does not help — for
instance cover traffic that an observer can statistically subtract (lesson 03). Layers that do not
raise the cost for a *named adversary* are cost without benefit, and they make the documentation longer
without making the user safer.

## What this means here

- **Tiers (T0–T3)** are the mechanical answer to the triangle: the user chooses which currency to spend,
  and the documentation states the residual risk per tier.
- **`SC7`** in [../EVALUATION.md](../EVALUATION.md) requires per-layer latency instrumentation with
  published p50/p95 and cold/warm separation.
- **Risk R13** ("latency pushes users to disable protections") is tracked as a first-class project risk
  precisely because it is the most likely way this project fails in practice — not a breach, but
  abandonment.
- **Open question U3** is your latency ceiling. Everything downstream — model class, cover rate, whether
  Tier 2 is interactive at all — is derived from it.

## Self-check

1. A tool advertises "maximum privacy" as a single mode and no options. Give two reasons this can be
   *less* private in practice than a tool with a weaker but configurable mode.
2. Your full stack adds 5 seconds per turn. Where would you look first to recover 3 of them, and what
   would you need to have measured beforehand to know the answer?
3. Why is funding a real payment note a different kind of decision from enabling cover traffic?

<details>
<summary>Answers</summary>

1. (a) If the single mode is slow enough that users disable or abandon it, its realised privacy is zero
   — a protection not in use protects nobody. (b) With no tiers there is no way to make a *deliberate*,
   visible tradeoff, so users improvise one — typically by bypassing the tool entirely, losing even the
   protections that were cheap and working. Configurability is how a design survives its users.

2. First look for whatever is *not* strictly required for the privacy you need on that path: often the
   local rewrite model (shrink it, or keep it resident to remove load time), or repeated key
   acquisition (extend the reuse window). To know which, you need **per-layer timing instrumentation
   from the start** — measured cold and warm, p50 and p95. Without that you would be guessing, and you
   would probably optimise the layer that felt slow rather than the one that was.

3. Because the currencies differ in reversibility. Cover traffic spends bandwidth and can be turned off
   or turned down with no lasting trace. Funding a note spends **money and an irreversible public
   record**: the deposit is permanently on a public ledger, the funds are exposed to pause/expiry risk,
   and the on-ramp that provided the ETH is very likely identity-linked. Mistakes in the first are
   recoverable; mistakes in the second are not. Build the reversible things first.

</details>

---

*Next: [08 — Decision worksheet](08-decision-worksheet.md) — where these ideas become your answers to
U1–U6.*
