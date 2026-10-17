# 01 — What "Private" Actually Means

## The question

When someone says a system is "private", what claim is being made — and how would you check it?

## First principle

**Privacy is not a property of a system. It is a relationship between a system and an adversary.**

There is no such thing as a private computer. There is only a computer that tells a specific observer
less than a specific alternative would. Change the observer, and every conclusion changes. Increase
the observer's power, and protections that looked solid become decorative.

This one idea dissolves most bad reasoning in this field. "Is Tor private?" is unanswerable. "Does
Tor hide my source IP from a passive network observer? Yes. From a global adversary watching all
network links? No." is answerable, and it is useful.

So the first question in any privacy analysis is never "how strong is the encryption?" It is:

> **Who are you hiding from, and what can they see?**

## Observation versus linkage

These are different problems, and they need different fixes. Novices often solve the first and
imagine they have solved the second.

| | Question | Example | Fixed by |
| --- | --- | --- | --- |
| **Observation** | Can the adversary read/intercept this information? | An ISP reading your prompt | Encryption, tunnelling |
| **Linkage** | Can the adversary connect two facts that should be separate? | Learning that *this* purchase and *this* search came from one person | Anonymity mechanisms, unlinkability |

Linkage is the harder and more interesting half. Consider: your bank knows how much you spent. Your
doctor knows your diagnosis. Neither observation is alarming alone. **The linkage of the two is the
privacy harm.** Almost every real privacy failure is a linkage failure, and almost every naive
privacy fix (encrypt the message!) leaves linkage completely untouched.

Hold onto that word. **Linkability** is the enemy. Tor, mixnets, and zero-knowledge payment
protocols are all, in different ways, machines for *refusing to create links*.

## Content versus metadata

| | What it is | Example |
| --- | --- | --- |
| **Content** | What you actually said | "I have a heart condition — what should I eat?" |
| **Metadata** | Facts about the communication | That you talked to a medical AI at 02:14, for 40 minutes, 3 MB each way, every Tuesday for a year |

Metadata is often more revealing than content, and it is much harder to hide, because it is needed
to deliver the message at all. A famous framing from the NSA's own history: they kill people based on
metadata. You do not need to read a message to know a lot about the person who sent it.

This is why "we encrypt your data" is a weak privacy claim: encryption protects content, while the
timing, volume, and destination pattern remain in plain view. Our project's cover-traffic layer
exists entirely because of this gap.

## The anonymity set: hiding in a crowd

Here is the second load-bearing idea, and it is simple:

> **You are not anonymous. You are anonymous *among some set of people*.**

If you are the only person using a service in your city, "no one knows who used it" is false — the
set has size one, and any observer who knows the city knows you.

The **size of that set** is the real security parameter, far more than the strength of the
cryptography. This has a consequence that surprises people:

- Cryptography can prove you are a member of a set without revealing which member.
- **No cryptography can make the set bigger than it is.**

That distinction explains nearly every disappointing real-world privacy deployment. A flawless
zero-knowledge design with twelve users hides you among twelve. This exact issue is why
[../THREAT-MODEL.md](../THREAT-MODEL.md) flags the payment layer as `Partial/Exposed` despite the
proofs being sound: zkAPI's anonymity set was on the order of **93 deposits, total, all time** when
we researched it.

## A worked example: one request, seven observers

The most useful practical tool in this field is a **"who learns what" table**. Let us trace one
request through a paranoid-mode stack and fill it in. This is the same request we will follow in
later lessons.

> **Request:** "I have a heart condition and my doctor wants me on a low-sodium diet. Suggest a
> week of dinners. My address is 12 Elm Street."

Assume the full stack: Tor with a per-conversation circuit, local prompt rewriting, cover traffic,
and a zkAPI-style payment whose unlinkability is qualified exactly as lesson 04 describes — the proofs
are sound, and the crowd is small.

| Observer | Learns | Does not learn | How we know |
| --- | --- | --- | --- |
| **Your ISP** | That you are using Tor; how much data; roughly when | The provider, the prompt, the destination | Tor's TLS; traffic volume always leaks |
| **Your Tor guard relay** | Your IP address; that you are talking to *someone*; timing and volume | The destination or the content | Layered encryption, one layer per hop |
| **Middle relay** | Its two neighbours in the path | Your IP, the destination, the content | Same |
| **Exit relay** | The destination and the traffic shape — **for clearnet destinations** | Your IP | It must forward the connection, so it sees where it goes |
| **The model provider** | The rewritten prompt and the response; request timing; that you may be on Tor | Your real name, your payment identity, your IP | It must read the prompt to answer |
| **Payment operator** | That a valid payment exists; request times; spending tier | Which deposit paid, what you asked | Zero-knowledge proofs |
| **Ethereum (public)** | A deposit happened; later, a withdrawal | What the money bought | Public ledger by design |
| **Your own machine** | Everything | — | This is why the endpoint is inside the trust boundary |

Read the table again and notice what is *not* in the "does not learn" columns:

- The provider learns **the content** — even rewritten, "heart condition, low-sodium dinners" is
  personal. Rewriting removes the *address*; it cannot remove the *task*.
- The exit relay learns **the destination**. Tor cannot hide where you are going from the last hop,
  unless the destination itself lives inside the network.
- Nobody learns your name — and yet a provider with a year of these requests would know you
  intimately.

This table is the deliverable of a threat model. Not a diagram, not a list of ciphers. A table of
who learns what.

## Trust versus verification

You will always trust *something*. The useful question is what, and how much.

| You can verify | You must trust |
| --- | --- |
| That a proof is valid, given the mathematics | That the setup ceremony destroyed its secret |
| That your traffic left through Tor (with a probe) | That the guard relay is not hostile |
| That the client code you built does what it appears to do | That the hardware, OS, and compiler are honest |
| That a service *claims* not to log | That it does not |

Cryptography's contribution is not "trust nobody" — it is **converting trust into verification where
possible**. zkAPI is a good example: instead of trusting a payment processor's promise not to link
your deposit to your usage, you can *check* a proof that it cannot. But note the row above: the
proof system's own setup requires trusting a ceremony. Lesson 04 covers why that matters.

When you evaluate any privacy tool, ask of each guarantee: **can I verify this, or am I trusting
someone's word?** Then ask what happens if the trusted party is wrong or malicious.

## Where it breaks

**1. Threat models that defend the wrong adversary.** This is the most common failure, and this
project nearly made it. The original draft defended against an ISP (via Tor) and a payment processor
(via zkAPI) — while the observer that actually reads your most intimate thoughts, the model
provider, was barely addressed. Write the "who learns what" table *first*; it exposes this instantly.

**2. Adversaries get stronger; data does not expire.** Traffic an adversary cannot correlate today
may be decryptable or correlatable in five years. Timing data recorded now is a permanent liability,
because it can be attacked with techniques that did not exist when it was captured. This is an
argument for not generating the data.

**3. Adding layers can add risk.** Every component is a party that could be compromised, a log that
could be kept, and a bug that could leak. A stack of five privacy tools is not automatically safer
than three. This project delegates payment rather than reimplementing it partly for this reason.

**4. "Nothing to hide" is a category error.** It confuses "I have done nothing wrong" with "I am
content for every observer to build a complete model of my life". Those are different claims, and the
second is the one privacy engineering addresses.

## What this means here

This lesson is why the repository is structured the way it is:

- [../THREAT-MODEL.md](../THREAT-MODEL.md) names nine adversaries (`AD1`–`AD9`) with capabilities, and
  rates every protection `Protected` / `Partial` / `Exposed` **for each one**. There is no global
  "private: yes".
- The four layers exist because they answer different observers: network (IP), payment (billing
  identity), content (the words), environment (the endpoint).
- Claims that cannot name an adversary are forbidden. See `AGENTS.md` rule for documentation, and
  the release checklist in [../EVALUATION.md](../EVALUATION.md) §9.

## Self-check

1. A VPN provider advertises "military-grade AES-256 encryption, no-logs policy". Name three things
   an observer could still learn about you, and say which of them the encryption does not touch.
2. Your service has 10,000 users. A flaw lets an attacker prove that you are one of 100 users who
   meet some condition. Has your anonymity gone down, and what is your anonymity set now?
3. Which observer in the worked-example table could most easily re-identify you after a year of
   requests, and what would be the cheapest way to reduce that?

<details>
<summary>Answers</summary>

1. (a) That you are using a VPN, and to which provider — the connection to the VPN server is
   visible; (b) the timing and volume of your traffic — metadata, untouched by encryption; (c) the
   destination, from the VPN operator's perspective, who now sits in the position your ISP used to
   occupy. Encryption protects content in transit, not who you talk to or when. "No-logs" is a
   *claim you must trust*, not a verifiable property.

2. Yes, it has gone down. Your anonymity set is now **100**, not 10,000. The cryptography did not
   fail; the set shrank. This is the single most common way privacy systems disappoint in practice.

3. The **model provider**, because content — including writing style, reused details, and the
   subjects you ask about — accumulates into a profile no network-layer protection can touch.
   Cheapest mitigations: rewrite more aggressively, and avoid reusing distinctive personal details
   and documents across sessions. Note that "cheapest" and "fully effective" are not the same
   thing — see lesson 05 on why rewriting reduces rather than eliminates this.

</details>

---

*Next: [02 — Anonymity networks: how Tor works](02-anonymity-networks.md)*
