# 09 — Glossary

Every term used across this repository, defined once. Cross-references point to the lesson where the
concept is developed.

---

## Adversary and threat modelling

| Term | Definition |
| --- | --- |
| **Adversary** | A party with a capability and a goal. Privacy claims are meaningless without one. Lesson 01 |
| **Threat model** | The explicit statement of which adversaries a system resists, with what capabilities, and what it does not resist. This project's is normative: [../THREAT-MODEL.md](../THREAT-MODEL.md) |
| **Capability** | What an adversary can observe or do — passive/active, local/global, one relay or all links |
| **Passive adversary** | Observes without modifying traffic. Cheap; hard to detect |
| **Active adversary** | Can modify, delay, drop, or inject traffic — including manipulating response timing to defeat cover traffic. Lesson 03 |
| **Global passive adversary** | Observes every link in the network. Defeats Tor; the class mixnets are designed against. Lesson 03 |
| **Anonymity set** | The group you hide among. Its **size is the real security parameter** — no cryptography can enlarge it. Lesson 01 |
| **Linkability** | Whether two facts can be connected to one person. The core privacy harm. Lesson 01 |
| **Metadata** | Facts about a communication rather than its content: who, when, how much, how often. Lesson 03 |
| **Fingerprinting** | Identifying a system or person from distinctive characteristics — traffic shape, writing style, TLS parameters. Lessons 03, 05 |
| **Stylometry** | Identifying authorship from writing style alone. Survives fact removal; reduced by rewriting but **not proven** removed. Lesson 05 |

## Networks and anonymity

| Term | Definition |
| --- | --- |
| **Tor** | Anonymity network routing traffic through three relays, so no single relay knows both ends |
| **Circuit** | A path through Tor relays. Built once, reused while "clean" |
| **Guard (entry) relay** | First relay. Knows your IP and traffic timing; not the destination. Long-lived by design to prevent an adversary grinding its way into that position |
| **Middle relay** | Middle hop. Knows only its neighbours; exists so the guard and exit are not adjacent |
| **Exit relay** | Last relay. Knows the destination for clearnet traffic; not your IP. **The last-hop problem lives here** |
| **Onion service** (`.onion`) | A service reachable inside Tor with no exit node. Removes the last-hop problem — requires the provider to offer one |
| **Stream** | A single connection carried over a circuit; many streams can share one circuit |
| **Stream isolation** | Labelling streams so Tor gives incompatible ones different circuits. Prevents a hostile exit or destination from linking your conversations |
| **Isolation token** | The label used for isolation, carried in SOCKS username/password. The only isolation property Tor's spec rates **strong**. Lesson 02 |
| **`IsolateSOCKSAuth`** | The Tor `SocksPort` flag enabling username/password-based isolation. Must be on for our design |
| **`NEWNYM`** | Tor control signal: make new requests avoid old circuits; clears DNS cache. **Global and rate-limited**, so wrong for per-conversation isolation. Lesson 02 |
| **`MaxCircuitDirtiness`** | How long a circuit is reused before rotation. Default ~10 minutes |
| **Remote DNS** (`socks5h`) | Handing the hostname to the proxy so name resolution happens on the far side. **Essential** — local resolution leaks destinations. Lesson 06 |
| **Cover traffic** | Decoy traffic intended to obscure which requests are real. Helps against *local* observers; **cannot** defeat an end-to-end correlator. Lesson 03 |
| **Traffic analysis** | Inferring information from timing, volume, and direction rather than content |
| **End-to-end correlation** | Matching traffic at both ends by timing. The attack that defeats Tor against a colluding or global adversary. Lesson 03 |
| **Mixnet** | Network that breaks input-output correspondence via batching, randomised delay, and fixed-size packets. Strong against global passive adversaries; costs latency and bandwidth. Lesson 03 |
| **Constant-rate traffic** | Transmitting at a fixed rate regardless of activity, removing timing information. The strongest known answer; you pay for bandwidth while idle. Lesson 03 |
| **Poisson process** | Random, memoryless arrival pattern. Used for cover-traffic scheduling so it is independent of your real activity. Lesson 03 |
| **Oniux** | Tor Project tool putting an app in its own network namespace with only an `onion0` interface. Linux-only, experimental, no root required |
| **Arti** | Tor's Rust implementation; the engine behind oniux |
| **`torsocks`** | `LD_PRELOAD`-based Tor routing. **Not a security boundary** — static binaries and raw syscalls bypass it. Lesson 06 |
| **`LD_PRELOAD`** | Mechanism for interposing shared-library calls. Works only through a dynamically linked libc |
| **Network namespace** | Kernel feature giving a process its own network view. With no route out, leaks become impossible rather than unlikely. Lesson 06 |
| **Last-hop problem** | The exit relay must see the destination for clearnet traffic. Tor does not hide it; neither does encryption |

## Payments and cryptography

| Term | Definition |
| --- | --- |
| **zkAPI** | Ethereum Foundation / Open Anonymity protocol for unlinkable metered API credits: deposit into a vault, authorize spending with proofs. Lessons 04, [../SOURCES.md](../SOURCES.md) |
| **Vault** | The on-chain contract holding deposits. Public: amounts, times, addresses |
| **Note** | The private representation of a deposit. Spendable by proving knowledge of its secret |
| **Commitment** | A binding-but-hiding value, e.g. `H(secret)`. "A sealed envelope in public" |
| **Nullifier** | One-way serial number published at spend time; prevents double-spending without revealing *which* note was spent |
| **Merkle tree** | Compact summary of a list that lets you prove membership without revealing which entry is yours |
| **Zero-knowledge proof** | A proof that a statement is true without revealing why. Here: "a funded, unspent note covers this spend" |
| **Groth16** | The zk-SNARK construction zkAPI uses. Efficient, and requires a per-circuit setup |
| **BN254 / Poseidon** | The curve and hash function used. Implementation detail; listed so the terms are not mysterious |
| **Trusted setup** | One-time generation of secret randomness for a proof system. If the party kept the secret, they can **forge proofs**. A multi-party ceremony reduces this to "at least one participant was honest". zkAPI's deployment used a **single-party** setup |
| **Runtime-key mode** | zkAPI mode where a short-lived, dollar-capped key is minted and your prompts then go **directly** to the provider — no payment intermediary sees content |
| **Proxy mode** | Simpler zkAPI mode where the payment server relays traffic. Rejected here: it reintroduces a party that sees content |
| **Settlement** | Reconciling actual usage against the authorized cap, using a signed receipt |
| **Lease** | This project's abstraction for a short-lived, capped credential obtained from a payment provider |
| **Anonymity set size** | For payments: how many other notes could have paid. Currently very small (tens), which is the dominant limitation. Lesson 04 |
| **On-ramp** | Where you acquire the currency. If it is identity-linked (an exchange purchase with a card), it bounds your payment privacy. Lesson 04 |
| **BYOK** | "Bring your own key". Works everywhere; provides **no** unlinkability, because the key *is* the identity |
| **Monero / Lightning** | Alternative privacy-preserving payment rails. Technically strong, but virtually no major AI provider accepts them for metered API access |
| **Confidential computing / TEE** | Hardware-isolated execution with attestation. Addresses content privacy *from the operator*; does not unlink payment; shifts trust to a vendor |
| **FHE** | Fully homomorphic encryption — computing on ciphertext. Not practical for LLMs at useful cost today |

## Content privacy

| Term | Definition |
| --- | --- |
| **Prompt rewriting** | Locally transforming a prompt before it is sent, removing what the model does not need. Lessons 05, and see the critique below |
| **Contextual integrity** | Privacy theory: whether information flow is appropriate depends on context and purpose, not on the information's type |
| **Task necessity** | The operative criterion: forward a span if and only if the remote model needs it for *this* task |
| **Over-disclosure** | Sending sensitive material the task did not require. Silently a privacy loss |
| **Over-removal** | Stripping material the model needed. Silently a utility loss — looks like model incompetence |
| **PII** | Personally identifiable information. Type-based PII filtering fails in both directions because it ignores the task. Lesson 05 |
| **Fail closed** | On any failure of a privacy layer, refuse the request rather than proceeding unprotected |
| **Target-side transcript** | A separately maintained, rewritten version of the conversation sent to the provider — so raw history is not resent. Upstream's approach; we adopt it |
| **Canary** | A unique string fed through a pipeline to test whether it leaks — e.g. into logs or onto disk |
| **Stylometric identifiability** | How recognisable your writing is. Reduced by rewriting is a **model instruction, not a proven property** |

## Project architecture

| Term | Definition |
| --- | --- |
| **Tier (T0–T3)** | The privacy/strength dial a user selects: T0 baseline, T1 practical, T2 paranoid, T3 maximum (experimental). [../PLAN.md](../PLAN.md) §4.1 |
| **Gateway** | The local OpenAI-compatible HTTP endpoint your agent talks to. Loopback only |
| **Session** | A conversation: one isolation token, one payment lease, one Tor identity |
| **Data plane** | The components doing the work (Tor routing, rewriting, cover, payment) — as opposed to the control plane that governs them |
| **Control plane** | Session policy, enforcement, and measurement — the part this project owns |
| **Enforcement** | Making a guarantee true by construction (namespace) rather than by configuration. Lesson 06 |
| **Fail closed / downgrade loudly** | Refuse, or degrade visibly. Never continue silently at lower protection |
| **Unverified state** | What status output reports when a guarantee cannot be *confirmed* (e.g. no control port). Never reported as `ok` |
| **Drift** | The running configuration no longer matching the declared tier. Detected and reported |
| **`paranoid doctor`** | Planned CLI command reporting the environment's real tier ceiling and any unmet prerequisites |

## Measurement

| Term | Definition |
| --- | --- |
| **p50 / p95** | Median and 95th-percentile latency. The tail is what users experience as "unusable"; means hide it |
| **Cold / warm start** | First turn of a conversation versus a continuation. Cold includes model loading, circuit building, and uncached rewriting — measure separately. Lesson 07 |
| **TTFT** | Time to first token. The number users actually feel |
| **Anonymity set disclosure** | Reporting how small the crowd is, at run time, rather than burying it. Decision D10 |
| **Acceptance gate** | A measurable condition a milestone must pass. [../EVALUATION.md](../EVALUATION.md) §2 |
| **Look-back** | The Pólya step 4 ritual: did it work, could it be simpler, is the reasoning sound, what carries forward. [../EVALUATION.md](../EVALUATION.md) §7 |

## Terms this project deliberately avoids

| Avoided | Because |
| --- | --- |
| "Anonymous" (unqualified) | Meaningless without a named adversary |
| "Untraceable" / "fully private" | Absolute claims no design here can support |
| "Military-grade encryption" | Says nothing about metadata, which is where the privacy problems are |
| "No-log" (as a privacy guarantee) | A claim to be trusted, not verified — note the difference from a *verified* property |
| "Decentralised" (as a synonym for private) | Distribution removes a single point of failure, not observability. A public ledger is decentralised **and** permanent |

---

*Back to the [learning index](00-how-to-use.md), or to [../DECISIONS.md](../DECISIONS.md) to record your
answers.*
