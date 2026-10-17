# 04 — Unlinkable Payments

## The question

How can you pay for something without the person you pay learning who you are — and what is the
catch?

## First principle

**A payment creates a link between your money and your purchase. Payment privacy is the art of
breaking that link, and you break it by hiding in a crowd.**

Keep lesson 01 in mind throughout: the security parameter is the **size of the set you hide in**, not
the elegance of the cryptography. A perfect proof with twelve possible payers hides you among twelve.

## Why payments leak identity in the first place

Think about what an ordinary API purchase records:

| Record | Who holds it | What it links |
| --- | --- | --- |
| Card number → account | Bank, processor | You, by legal identity |
| Account → API key | Provider | Every request to one billing entity |
| Prompt content | Provider | Your health, finances, relationships |
| *Requests to each other* | Provider | Years of usage into a single profile |

Every prompt you send joins the record attached to the account. The provider does not need to know
"who you are" in a legal sense — it needs only to know that *these ten thousand requests came from
one entity*, and it can then read all of them as one narrative.

So payment privacy is not a side concern. It is what stops the provider from assembling the narrative.

There are two ways the link can be broken: **don't use an identity-linked payment instrument at all**
(cash-like systems), or **prove you can pay without saying which money is yours** (zero-knowledge
credits). This project uses the second.

## How a zero-knowledge payment actually works

The mechanism feels like sleight of hand the first time. It rests on three cryptographic primitives,
each of which is simple in isolation.

### 1. A commitment: a sealed envelope

A **commitment** is a value that binds you to a secret without revealing it. Conceptually: you write a
number on a card, seal it in an envelope, and put the envelope in public. You can later prove what is
in the envelope, and you cannot change it now that it is sealed.

In practice (zkAPI uses Poseidon hashes): `commitment = H(secret)`. Publishing the commitment reveals
nothing about the secret. It is the ledger's record of "an amount of money exists that someone can
prove they control".

### 2. A Merkle tree: proving you are on a list without saying where

A **Merkle tree** is a way of summarising a whole list of commitments into one short value, such that
you can prove "my envelope is in this list" without revealing *which* entry is yours. zkAPI's tree is
32 levels deep — enough for billions of entries.

This is what makes the crowd possible: the proof demonstrates membership in a large set, and
deliberately discards the information about which member.

### 3. A nullifier: a serial number that prevents double-spending

If you can spend without revealing which envelope, what stops you spending twice? A **nullifier** —
a one-way serial number derived from the note's secret, published at spend time.

- It cannot be reversed to find out which note it came from.
- It is deterministic: the same note always produces the same nullifier.
- So a *second* spend of the same note produces a duplicate nullifier, which is detectable.

This is the elegant part. The system learns "this note has been spent" without learning **which note**,
and cheating is self-revealing.

### Putting it together: the zkAPI flow

```mermaid
sequenceDiagram
    participant U as You
    participant V as Vault contract (public)
    participant S as zkAPI server
    participant P as AI provider

    U->>V: deposit ETH → becomes a private note (public: amount, time)
    Note over U: note = commitment in a Merkle tree
    U->>S: proof: "a funded, unspent note covers this spend" (no identity, no prompt)
    S->>S: verify proof, mint short-lived API key, capped in dollars
    S-->>U: key (exists only in your memory)
    U->>P: prompts go DIRECT to the provider, with that key
    Note over P: provider sees content; never sees your funding identity
    P-->>U: response
    Note over S: at expiry: signed usage receipt settles the capped amount
```

Note the two design choices that matter most, and are easy to miss:

- **Your prompts never pass through the payment service** ("runtime-key mode"). The payment server
  learns that *a* valid payment exists and the dollars per session; it never sees content. There is a
  simpler "proxy mode" where the server relays your traffic — rejected here precisely because it
  reintroduces a party that sees both.
- **One authorization covers a whole session**, so you are not proving payment per request. This
  reduces latency and, importantly, reduces the number of visible proof events an observer could count.

## The crowd is the security parameter

Here is where the design's promise meets reality, and it is the single most important thing to
understand before deciding whether to fund a note.

| What cryptography gives you | What cryptography cannot give you |
| --- | --- |
| Proof that your note is funded and unspent | A large set of *other people* doing the same thing |
| No disclosure of which note paid | Protection when only a handful of notes exist |
| Detection of double-spends | Anything at all if the operator can narrow candidates |

At the time this was researched, zkAPI's public figures were **around 93 deposits ever, and roughly
$2.3K** of value locked. Even setting aside dormant and expired notes, that is a *small* crowd. Now
combine it with the operational facts an independent review reported:

| What the operator observes | Consequence |
| --- | --- |
| The **time and budget tier** of each request | Requests can be clustered by session and by how expensive the model chosen was |
| The client **reveals the note id to the operator's indexer** before each request | A direct linkage path that does not need cryptography to be broken |
| Few active notes cover a high budget tier | Candidate sets for expensive models become *very* small |
| The provider can **link requests made under one key** | Within a session, all turns are correlated (by design) |

So the honest description of payment privacy in this architecture is: **the link between your deposit
and your usage is broken against a non-colluding operator, and only as strongly as the size of the
current anonymity set allows.** That is genuinely valuable and far better than an API key — and it is
not "anonymous".

## The trust assumptions you cannot cryptographically remove

Two categories of trust sit outside the mathematics, and both matter for your decision (U1).

**1. The trusted setup.** The proof system used (Groth16) requires a one-time setup that generates
secret randomness. If the party that ran the setup kept that randomness, they can forge proofs — not
learn who you are, but create money/withdrawals that should not exist. zkAPI's deployment at the time
of research used a **single-party setup**: one party, no ceremony. Public artifacts can show that the
deployed keys match the published ones; they **cannot** show that the secrets were destroyed. A
multi-party ceremony, where only one honest participant is needed, is the standard fix, and it was
still pending.

**2. The operator's operational power.** Independent review noted the vault owner can **pause
withdrawals**, and that expired notes can be swept to the treasury. A 1-day escape path exists, but it
cannot be *started* during a pause. Reviews of the newer protocol revision describe an improved exit
(a "concession" path that needs no operator cooperation), but that revision had **no deployed network
manifests and no production proving keys** — it was not usable.

These are not cryptography failures. They are custody and governance facts, and they have a privacy
consequence people underestimate: **if your funds are at risk, you will not use the system freely**,
and systems people do not use freely stay small — which shrinks the crowd again. Usability and
anonymity are connected.

## The linkage nobody warns you about: the on-ramp

Suppose every proof is perfect. You still had to acquire ETH somehow. If you bought it on an exchange
with your ID and card, then:

```
your identity → exchange → ETH → address → deposit → ??? → usage
```

The first four links are fully public or knowable by the exchange. The proofs hide the last two. **The
unlinkability you bought is bounded by how your money entered the system**, and the fiat on-ramp is
usually the weakest link — not the protocol.

There is also a **temporal** linkage: deposit at 12:00 and spend at 12:01, and an observer can link
by time alone, without breaking any cryptography. The community manners that matter here — wait,
deposit larger amounts less often, and don't be the only active note — are not implementation
details. They are part of the privacy property.

## Alternatives, and why none is a drop-in replacement

| Option | Payment privacy | Why it is not usable here |
| --- | --- | --- |
| **zkAPI-style credits** | Payment unlinked from usage, qualified by set size | Live, but trusted setup, tiny set, custody caveats |
| **Monero (XMR)** | Strong: ring signatures and stealth addresses hide sender, receiver, amount | You need a *provider that accepts XMR*. Essentially no major AI provider does, so it requires a human in the middle — which destroys the automation and adds an observer |
| **Lightning / Bitcoin** | Fast, low-value, routeable with some privacy | Same acceptance problem, plus channel management overhead |
| **Card / gift card / virtual card** | Breaks the link at the processor | KYC at purchase; providers ban these; fragile |
| **Bring your own API key** | **None.** The key *is* the identity | Works everywhere today. Honest fallback, and must be *labelled* as unlinkable-by-nothing |
| **Confidential compute / TEEs** | Different axis: hides content from the provider's operator | Does not unlink payment; shifts trust to a hardware vendor and an attestation |
| Public mixer (Tornado-style) | Historically attempt at transfer privacy | **Sanctioned and deprecated.** Not an option, and the original draft's reference to it is why this repository was rewritten |

Notice the pattern: the constraint is rarely the cryptography. It is **whether the party you are paying
will accept the payment instrument**.

## Where it breaks

**1. Small crowds.** Covered above, and it is the dominant risk here.

**2. The on-ramp.** Covered above. Your anonymity is not stronger than your funding path.

**3. Timing linkage.** Deposit and spend are both public or observable events; correlating them by
time requires no cryptanalysis.

**4. Operationally enforced deanonymisation.** The client telling the operator's indexer your note id
is a design choice in the deployed client, and it is a direct link that no proof protects.

**5. Provider-side linkage.** Within a key's lifetime, all requests are linked by design. Rotating
keys more often shrinks that window and costs latency (settlement happens per key).

**6. Losing your note.** The flip side of private notes: lose the secret or the latest signed balance
and the funds are gone, unrecoverably. This is a real cost of self-custody, and it is a usability
pressure that pushes people toward custodial alternatives with worse privacy.

## What this means here

- **Decision D1:** we do not reimplement any of this. Note-bound proofs, nullifiers, and settlement
  are delegated, because hand-rolled cryptography here would be the most dangerous possible place to
  improvise.
- **Decision D5:** `PaymentProvider` is an interface with three adapters — `mock`, `zkapi`, and
  `byok` — so that the answer to U1 changes configuration, not architecture. `status()` is part of the
  interface specifically so the **anonymity set size is disclosed at run time** rather than buried in a
  README.
- **Open question U1** is the decision this lesson exists to inform: whether to fund a real note now,
  build against a mock, or wait for a deployable revision with production keys and a multi-party
  ceremony. Lesson 08 walks through the consequences, including that the mock path is the only
  *reversible* one.

## Self-check

1. You deposit and, one minute later, authorize a session. The proofs are flawless. What has an
   observer learned, and by what means?
2. A friend tells you "zkAPI is fully anonymous — it uses zero-knowledge proofs". Identify at least
   three separate things wrong with that sentence.
3. You lose the file containing your note secret. What happens, and which property of the design
   caused it?

<details>
<summary>Answers</summary>

1. That a deposit **and** a subsequent session are probably the same person, from **timing alone** —
   no cryptography broken. This is why depositing larger amounts less frequently and allowing delay
   before spending are privacy behaviours, not optional etiquette.

2. (a) "Fully anonymous" has no adversary attached — anonymous against your ISP? the operator? the
   provider? the exchange that sold you the ETH? Each answer differs. (b) Zero-knowledge proofs
   remove the need to reveal *which note* pays, but the operator still observes request timing and
   budget tier, and the deployed client reveals the note id to the indexer. (c) The anonymity set was
   on the order of tens of deposits, so even perfect proofs hide you among a very small crowd. (d) The
   trusted setup was single-party, so the setup party could forge proofs. Any one of these is enough
   to falsify "fully anonymous".

3. The funds are **permanently lost** — the note secret and the latest signed balance are what prove
   ownership, and there is no recovery authority to appeal to. It follows from self-custody, which is
   the same property that stops an operator from quietly confiscating your balance. Self-custody trades
   a custodial risk for a personal one; that is a real tradeoff to accept knowingly, not a bug.

</details>

---

*Next: [05 — Content privacy and rewriting](05-content-privacy.md)*
