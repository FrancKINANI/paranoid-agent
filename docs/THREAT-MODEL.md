# Threat Model

> **This document is normative.** If the code, the README, or a commit message claims more than
> this document allows, the claim is a bug.

The threat model is deliberately adversary-by-adversary, because "private" is not a property —
it is a relationship between a system and an attacker with specific capabilities.

---

## 1. Assets

| Asset | Why it matters | Where it lives |
| --- | --- | --- |
| **Raw prompt text** | Contains health, finances, identity, work product — the substance of the request | User's machine, memory only |
| **Conversation linkability** | Whether two requests came from one person | Network metadata, provider records, payment records |
| **Source identity** | Who the user is | IP address, payment trail, writing style |
| **Usage pattern** | When, how often, how much — a behavioural profile | Traffic timing/volume, provider logs |
| **Payment identity** | The funding trail | Blockchain (public), operator records |
| **Local key material** | Wallet note secret, provider keys | User's machine, `config.json` (owner-only) |
| **Session isolation** | Circuit separation between conversations | Tor client state |

---

## 2. Adversaries

Each adversary is rated for what they learn **under the recommended Tier 2 configuration**. Ratings
are honest, not aspirational: `Protected` / `Partial` / `Exposed`.

### AD1 — Passive local network observer (ISP, cafe Wi-Fi, employer)

*Capability:* sees all traffic from the user's machine to the first hop.

| Aspect | Rating | Why |
| --- | --- | --- |
| Destination host | Protected | Tor's TLS hides the provider |
| Content | Protected | TLS + Tor |
| **Fact that Tor is being used** | **Exposed** | Tor traffic is fingerprintable; bridges/pluggable transports mitigate but do not eliminate this |
| Volume and timing | Partial | Cover traffic obscures; it is not constant-rate, and total bytes correlate with usage |

*Verdict:* learns that you use Tor, how much, and roughly when. Not what you asked.

### AD2 — Tor relay adversaries (entry/guard, middle, exit)

*Capability:* one or more relays under adversary control; the guard is long-lived by design.

| Aspect | Rating | Why |
| --- | --- | --- |
| Source IP | Protected, unless the adversary controls both guard and exit **and** correlates timing | Standard Tor assumptions |
| Destination | Protected against everyone except the **exit** (for clearnet destinations) |
| Which conversations belong to one user | Partial | Mitigated by per-conversation isolation; a hostile exit still sees a single circuit's streams together |
| **Traffic correlation with a colluding destination** | **Exposed** | See AD5 — this is the attack Vitalik named |

### AD3 — The model provider (OpenRouter, or the underlying model host)

*Capability:* reads every prompt and response it serves; can correlate requests made under one key;
controls response timing.

| Aspect | Rating | Why |
| --- | --- | --- |
| Prompt content | **Exposed by design** | The provider must read the prompt to answer. Rewriting removes non-essential sensitive spans — it does not hide the task |
| Which requests are the same user | Partial | Runtime-key mode rotates keys per unrelated conversation; the provider can still correlate by content, style, and documents |
| The user's real identity | Partial | Only if content or style is identifying, or if payment identity leaks (it should not) |
| Request timing | **Exposed** | The provider sees exactly when requests arrive — the input to the AD5 attack |
| Whether the user is on Tor | Likely Exposed | Exit ranges are public; providers can and do flag them |

*Verdict:* the provider learns what you asked (minus rewritten spans) and can profile your style.
This is the largest practical exposure and it is **not** a bug we can fix — only reduce.

### AD4 — The payment operator (zkAPI server operator, e.g. Open Anonymity)

*Capability:* verifies spend proofs, mints keys, sees request arrival times and budget tiers, holds
the signing keys pinned in the vault, can pause the vault.

| Aspect | Rating | Why |
| --- | --- | --- |
| Which deposit paid | Protected | That is the point of the proofs — unless the anonymity set is tiny (see below) |
| Which requests belong to one session | **Exposed** | The operator sees each request's time and budget tier (L2BEAT, privileged insider) |
| Link from request to deposit | **Partial/Exposed** | Few active notes cover high budget tiers, so candidates narrow quickly; the client also reveals the note id to the operator's indexer before each request |
| Prompt content | Protected in runtime-key mode | The payment path carries no conversation |

*Verdict:* payment unlinkability holds against a **non-colluding** operator with a large anonymity
set. Today the set is on the order of tens of deposits, so treat this as *partial*, and the product
must say so at run time.

### AD5 — Provider colluding with the user's guard relay (**the hard case**)

*Capability:* the destination knows exactly when it received a request; the guard knows exactly when
the user's client sent one. Given cooperation, the pair can correlate even without the content.

| Aspect | Rating | Why |
| --- | --- | --- |
| Linking this conversation to this user | **Exposed** | This is the known weakness of Tor for interactive patterns, and it is exactly what random cover traffic fails against when the adversary can actively manipulate response timing |

**This is out of scope for T0–T2 by explicit decision (D9).** Our mitigation story is:
constant-rate cover traffic inside a mixnet (T3), which we have **not** built and will not claim.
Any documentation that implies our Poisson cover defends against this is wrong.

### AD6 — Global passive adversary (mass surveillance of the whole network)

*Capability:* observes all links.

| Aspect | Rating | Why |
| --- | --- | --- |
| Everything | **Exposed** | Tor provides no defence against a full-network passive observer without constant-rate traffic. Out of scope |

### AD7 — Local attacker (malware, keylogger, shoulder-surfer, forensic access to the host)

| Aspect | Rating | Why |
| --- | --- | --- |
| Everything | **Exposed** | The endpoint is in the trust boundary (assumption A1). The source prompt exists in memory and on screen |

*Note:* our no-persistence design (§4.5) reduces the forensic footprint — a disk image does not
contain the prompts — but a live, privileged attacker wins. Disk encryption and endpoint hygiene are
the user's responsibility and are documented as such.

### AD8 — Third parties we might harm

*Capability:* the operators of any host we direct cover traffic at.

| Aspect | Rating | Why |
| --- | --- | --- |
| Load, and the appearance of Tor-origin requests in their logs | **We are the attacker here** | Our *own* cover traffic is bounded, opt-in, and permitted to specific targets. Any solution that pollutes strangers' services by default is a harm we accept responsibility for not creating |

### AD9 — Legal / coercive adversary

*Capability:* subpoena to the provider, the operator, or the user; compelled disclosure; in extreme
cases compelled software modification.

| Aspect | Rating | Why |
| --- | --- | --- |
| Provider-side records | Exposed | If the user's content is identifying, records link it |
| Payment records | Partial | zkAPI hides which deposit paid; deposits and closes are public on-chain |
| Whether Tor was used | Exposed | Observable |

This document does not offer legal protection and does not advise on evading lawful obligations. It
describes technical properties. The user decides whether using Tor is lawful and appropriate for
them, and provider terms may prohibit it outright (assumption A4).

---

## 3. Guarantee matrix

What holds, per tier. T2 is the recommended configuration; anything stronger is aspirational.

| Property | T0 | T1 | **T2** | T3 (experimental) |
| --- | --- | --- | --- | --- |
| Source IP hidden from provider | yes | yes | **yes** | yes |
| Conversations isolated from each other | no | partial | **yes (verified)** | yes |
| Raw prompt leaves the machine | **yes** | no | **no** | no |
| Non-essential sensitive spans reduced | no | measured | **measured** | measured |
| Timing/volume obfuscated | no | no | **partial (not proven)** | constant-rate (unbuilt) |
| Payment unlinked from identity | no | no | **yes (qualified)** | yes (qualified) |
| Kernel-enforced egress | no | no | **yes** | yes |
| Survives AD2 guard+exit collusion | no | no | no | partially, if real |
| Survives AD5 provider+guard collusion | no | no | **no** | maybe |
| Survives AD6 global passive | no | no | **no** | no |

---

## 4. Residual risk register (ranked)

Ordered by expected harm, so effort goes where it matters. Each entry names the owner of the risk.

| # | Risk | Severity | Our position |
| --- | --- | --- | --- |
| R1 | **Content-based re-identification by the provider.** Style, shared documents, reused personal details, and conversation history can re-link sessions regardless of network or payment hygiene | High | Reduced by rewriting, **not solved**. Disclosed in the product. Stylometric identifiability is a model instruction, not a proven property |
| R2 | **Timing correlation (AD5)** | High | Out of scope; would require a mixnet with constant-rate cover. Not claimed |
| R3 | **Provider refuses Tor / requires KYC.** A design that cannot reach the provider is not private, it is unusable | High | Documented as a first-class constraint; no automatic direct-connection fallback, so the failure is visible rather than silent |
| R4 | **Tiny payment anonymity set.** ~93 deposits total makes "unlinkable" weak against an insider | High | Reported at run time by `PaymentProvider.status()`; never described as strong |
| R5 | **Single-party trusted setup in zkAPI.** Retained setup secrets would allow forged withdrawal proofs | Medium-High | Delegated to upstream, disclosed to users, awaiting a multi-party ceremony |
| R6 | **Operator can pause exits / note expiry.** Funds can be frozen or swept after expiry | Medium | Escape path exists but is not startable during a pause; disclosed. Keep deposited balances small — the real mitigation is not leaving much in the vault |
| R7 | **Cover traffic is not proven protection** and may be *recognisable* through its own destination set, schedule, TLS fingerprint, and sizes | Medium | Labeled as unproven everywhere; rate deliberately low; target diversity is the user's choice |
| R8 | **Rewriter over-removal degrades answers**, silently reducing product value and tempting users to disable rewriting | Medium | Both metrics measured and published; never silently substitute the original |
| R9 | **Cover traffic harms third parties** if misconfigured | Medium (ethical) | Own/permitted targets only; hard budget; disabled by default |
| R10 | **Rewriter's direct connection** is outside Tor by upstream design and must be loopback | Medium | Config validation refuses non-loopback; leak suite asserts it |
| R11 | **Text outside the `user` role is unprotected** (system prompts, tool results, attachments) | Medium | Documented; refusal on unknown content types; clients are told not to place raw prompts there |
| R12 | **Non-Linux platforms cannot be kernel-enforced** | Medium | Tier ceiling lowered and stated, rather than papered over |
| R13 | **Latency pushes users to disable protections** — the most likely real-world failure | Medium | Tiers, measured p95, and T1 as an honest weaker option rather than a hidden one |
| R14 | **Tanstack of moving parts is experimental**: oniux is new, Arti/onionmasq are new, the upstream privacy branch is not a production release | Medium | Interfaces isolate each dependency; defaults avoid experimental features; failures are loud |
| R15 | **We might overclaim.** The biggest risk to the project's purpose | Medium-High | This document is normative; SC8 requires run-time disclosure; claims must cite a test |

---

## 5. Non-goals

Explicitly outside the threat model, so no one infers coverage from silence:

1. Defeating a global passive adversary (AD6).
2. Defeating provider + guard collusion (AD5) in T0–T2.
3. Protecting a compromised endpoint (AD7).
4. Hiding prompt content from the provider — impossible by construction; the provider must read it.
5. Anonymising attachments, images, audio, or non-`user`-role text.
6. Providing legal protection, or enabling illegal activity.
7. Multi-user anonymity, mix-network operation, or custody of anyone's funds.
8. Protecting against a provider that is itself the adversary's endpoint and serves malicious model
   output — prompt injection and output-side attacks are separate problems with their own literature.
9. Availability: we do not promise the provider will accept us, only that refusal is visible.

---

## 6. How to use this document

- **Before adding a feature:** identify which adversary it addresses and which row of §3 changes. If
  neither changes, it is probably not a privacy feature.
- **Before publishing a claim:** find the adversary and the tier. If you cannot, do not publish it.
- **Before shipping a tier downgrade:** update §3 and the residual register. A downgrade that does
  not update this file is a defect.
- **After every milestone:** re-read §4 and delete any risk that is genuinely closed. A risk register
  that never shrinks is not being used.

---

*Cross-references: [PROBLEM.md](PROBLEM.md) §2 for the facts these ratings rest on,
[LAYER-OPTIONS.md](LAYER-OPTIONS.md) for why each mitigation was chosen,
[EVALUATION.md](EVALUATION.md) for how each `yes` in §3 is tested.*
