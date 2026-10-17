# Layer Options — Best Available Choice, Per Layer

> Researched 2026-10-17. Every verdict names the evidence it rests on and what would change it.
> Vendor performance claims are marked **unverified** when we have not tested them ourselves.

This is the "look for the best options" document. The stack is not monolithic — it is nine
independent choices, and each is made separately:

| # | Layer | Verdict (one line) |
| --- | --- | --- |
| 1 | Network transport | **Tor SOCKS**, with a mixnet benchmarked for the request path only |
| 2 | Host isolation | **Kernel network namespace (oniux)**, not `torsocks` |
| 3 | Circuit isolation | **Per-conversation SOCKS auth token**, never `NEWNYM` |
| 4 | Prompt rewriting | **Local task-necessity rewriting, fail-closed, measured** |
| 5 | Cover traffic | **Bounded Poisson, opt-in, own targets** — labelled as unproven |
| 6 | Payment | **zkAPI**, behind a swappable interface, mock-first |
| 7 | Local runtime | **Ollama** |
| 8 | Gateway surface | **OpenAI-compatible local endpoint** |
| 9 | Last hop | **Acknowledged unsolved** for clearnet providers |

---

## 1. Network transport

| Option | Strength | Cost | Notes |
| --- | --- | --- | --- |
| **Tor SOCKS5** | Mature (15+ yrs), 3-hop circuits, per-stream isolation, large user base to hide in, free | Exit observes clearnet destination; vulnerable to timing correlation by a global or colluding observer; some providers block exits | The default. Circuit reuse and isolation semantics are specified and testable |
| Onion service (`*.onion`) for the provider | No exit node, no clearnet exit observation, strong against a colluding exit | Requires the provider to run an onion service — **no major AI provider does** | Not available. Relevant only if we ever front our own gateway |
| **Nym mixnet** | 5 hops, Poisson mixing, cover traffic by design — targets the exact weakness Vitalik named; NymVPN added "mixnet tuning" (2026) to trade latency vs anonymity | High latency and bandwidth overhead; packetized; smaller network; active adversarial research (2026 PoPETs paper on Nym's reputation system); streaming model output is a poor fit | **Benchmark in T3**, request path only. Vendor latency claims **unverified** |
| Katzenpost | Research-grade mixnet, constant-rate cover traffic, resistance to global adversaries is the design goal | Constant-rate means structural bandwidth cost (their own literature notes most cover traffic is dropped); not aimed at interactive chat | Watch; do not adopt in v1 |
| VPN → Tor | Hides Tor use from the local network | Adds a central point that sees everything; the VPN is a new trusted party; widely considered worse for strong anonymity | Rejected unless the user's ISP is the specific threat, and then it is their tradeoff to make |
| Tor bridge / pluggable transport (Snowflake, obfs4) | Needed where Tor is blocked | Not a privacy improvement over direct Tor | **Support, do not require** — a reachability option, not an anonymity option |

**Verdict:** Tor SOCKS5. It is the only transport that is simultaneously mature, free, isolation-capable,
and usable for streaming responses. Mixnet transport is a **Tier-3 experiment**, not a dependency.

**What would change it:** a mixnet that (a) sustains streaming throughput for multi-MB responses at
(b) latency acceptable for interactive use. Measured, not claimed.

### The last-hop problem (be fair about this)

Even with perfect source anonymity, the request eventually leaves Tor at an **exit node** to reach a
clearnet provider. That exit — and the provider — see the destination and the traffic shape. Tor
does not fix this and neither does zkAPI. A mixnet does not fix it either unless the provider is
reachable *inside* the anonymity network. Anyone claiming otherwise is selling something. This is
precisely the guard-collusion attack Vitalik described, and it is why T3 exists as an *experiment*.

---

## 2. Host isolation

| Option | Mechanism | Catches static binaries? | Trust level | Verdict |
| --- | --- | --- | --- | --- |
| None (correct config only) | Application sets `HTTPS_PROXY` | No | Discipline | Rejected |
| `torsocks` | libc symbol interposition via `LD_PRELOAD` | **No** — static binaries leak; app still sees host interfaces | Advisory | Rejected as a boundary (still handy as a debugging tool) |
| `bubblewrap` (`bwrap`) | Mount/PID/user namespaces; can `--unshare-net` | Yes, if net namespace is unshared | Kernel | Good, but netns wiring is manual |
| **`oniux`** | Dedicated **network namespace**, only an `onion0` interface, Tor-aware resolver, Arti + onionmasq | **Yes** | Kernel | **Chosen.** No root required (user namespace). **Linux only, experimental** |
| Network namespace by hand (`unshare -n` + Tor) | Same kernel primitives, hand-rolled plumbing | Yes | Kernel | Fallback if oniux proves unusable; more code to get wrong |
| Separate VM (Whonix-style gateway) | Full OS-level split, app cannot see host network | Yes | Kernel + hypervisor | Strongest; heavyweight. Offer as advanced deployment, not default |
| `firejail` | seccomp + namespaces, profiles | Yes | Kernel | Reasonable alternative; more surface than oniux for this purpose |

**Verdict:** `oniux` where available, with a documented `unshare -n` fallback, and **no
application-level SOCKS-only tier presented as equivalent**. The distinct failure mode of
application-level routing is that one unproxied syscall wins the attacker everything, and we refuse
to make "we set the proxy correctly" the security boundary.

**What would change it:** oniux remaining experimental and unreliable in practice across distros, or
Arti/onionmasq regressions. Then: hand-rolled netns + Tor, still kernel-enforced.

---

## 3. Circuit isolation mechanism

| Option | What it actually does | Per-conversation capable? | Verdict |
| --- | --- | --- | --- |
| `NEWNYM` (via Stem/control port) | Makes new requests avoid old circuits; clears the DNS cache; **rate-limited** (~10 s cooldown, ≈6 rotations/min) and global to the client | No — cannot express which streams belong together | **Rejected as the isolation primitive** |
| **SOCKS5 username/password with `IsolateSOCKSAuth`** | The credentials become an **application-provided isolation token**; Tor gives incompatible profiles different circuits. The spec calls application tokens the only *strong* property | **Yes** | **Chosen** |
| One Tor instance per session | Total separation of state | Yes, but heavy (one process, one guard set, one bootstrap per session) | Reserved for T3 / high-assurance |
| Do nothing | Streams share circuits | No | Rejected — leaks "these requests are the same user" to a hostile exit and to the destination |

**Verdict:** a deterministic per-conversation isolation token in the SOCKS credentials. Stem's
control port is used to **observe** (`GETINFO circuit-status`) so we can *prove* isolation, and as a
last-resort recovery tool — not as the mechanism.

**Important honest caveat, taken from Tor's own guidance and upstream's docs:** even correct
isolation cannot *prove* that two sockets used different circuits or different exits; SOCKS gives no
such guarantee, and Tor may reuse a circuit when profiles are compatible. Verification therefore
means reading circuit-status and reporting what actually happened — including collisions.

**What would change it:** Tor changing isolation semantics (proposal 368 territory), or evidence
that per-conversation tokens cluster too many conversations onto one guard.

---

## 4. Prompt rewriting

| Option | Idea | Privacy | Utility | Verdict |
| --- | --- | --- | --- | --- |
| Raw passthrough | Send as-is | None | Perfect | Rejected (that is the problem being solved) |
| PII regex / entity scrubbing | Strip by category | Weak — misses untyped sensitive context, and strips answer-bearing spans (over-removal) | Poor on task-critical details | Rejected alone; may be a cheap pre-filter |
| Naive local LLM "paraphrase this" | Ask a model to reword | Moderate; instruction-dependent, unpredictable, can drop constraints | Unreliable | Rejected as the final design; acceptable as a fallback tier |
| **Task-necessity (contextual-integrity) rewriting, fail-closed** | Reconstruct the request keeping only spans the remote model needs: task, necessary context, constraints | Best available | Measured, tunable | **Chosen** |
| Trained/RL-tuned rewriter | e.g. the GRPO-trained rewriter in arXiv 2606.04067, "+10.1 utility over on-device baselines" **on their benchmark** | Best reported | Best reported | Adopt the *method and metrics*; using their specific checkpoint is unverified for our prompts |
| Remote "privacy" rewriter service | Offload rewriting | **Catastrophic** — the original prompt leaves the machine, and upstream's rewriter connects **outside Tor** by design | — | Rejected outright |
| TEE / confidential-compute provider model | Provider processes in an enclave | Shifts trust to a hardware vendor + attestation | Good | Future option; orthogonal to our layers |
| Differential privacy / perturbation | Add noise to the prompt | Formal guarantees exist mostly for narrow settings (in-context learning demos), not free-form requests | Poor for real tasks | Rejected for v1 |

**Chosen design, concretely:** a local model receives the **new user turn only**, with a fixed
instruction: extract the task, the necessary context, and the constraints, then rebuild the request
in concise task-first prose; preserve code, quotes, identifiers, paths, URLs, numbers, and exact
output constraints; do not answer, do not add facts, do not resolve missing context; **fail closed**
on malformed output. This mirrors upstream's documented approach, so results are comparable — and we
add what upstream lacks: an **evaluation harness** measuring over-disclosure and over-removal with
**both** numbers reported, because reporting only one is how rewriting quality gets faked.

The two failure modes are named explicitly because they trade against each other (F8):
over-disclosure (leaking a non-essential sensitive span) and over-removal (stripping a span the
model needed, which silently degrades the answer).

**What would change it:** a model that hits both thresholds with better latency, or evidence that
our own instruction underperforms upstream's — in which case we adopt theirs and keep the harness.

---

## 5. Cover traffic

| Option | Design | Honest assessment |
| --- | --- | --- |
| None | — | Leaves timing/volume fingerprinting wide open; a chat-shaped burst is recognizable |
| Random dummy requests (the v0 idea) | Background thread hitting random public sites | Loads third parties, no schedule, provably weak; upstream's old helper "hammered" public APIs. Rejected |
| **Bounded Poisson cover (upstream's design)** | Random exponential interarrival, independent of prompts; fixed worker pool that **drops** under saturation (no queue, no catch-up burst); ≤20 s/request; 64 KiB cap; bodies discarded; separate SOCKS identities; opt-in; per-minute aggregate counters only | **Chosen.** The engineering discipline matters more than the volume, and upstream's documented behaviour avoids the classic failure of cover traffic *becoming* the signature |
| Constant-rate cover (mixnet-native) | Always transmit at a fixed rate, real or dummy | Theoretically the strong answer — but it costs the bandwidth of a continuous stream and is not achievable over plain Tor without a mixnet. Deferred to T3 |
| Padding inference streams to fixed sizes | Shape the *response* channel | Would help against shape fingerprinting; upstream explicitly does **not** do it and says so. A genuine improvement opportunity for us (see D7) |

**Verdict:** adopt bounded Poisson cover, **off by default**, aimed only at endpoints we own or are
permitted to poll, with a hard bandwidth budget and a documented refusal to claim protection it does
not provide. The upstream docs' own words — *"this is background noise, not proven traffic-analysis
protection"* — are quoted in our user-facing material rather than paraphrased into something
stronger.

**Load ethics as a design constraint:** the 5/s default can produce >1 GiB/hour of responses. We
default far lower, surface the cost, and require an explicit target list. Polling strangers' servers
to protect ourselves is not acceptable, and the obsolete upstream default that did so is an example
of what not to build.

**What would change it:** a measured demonstration (on our own harness) that our cover actually
degrades a specific timing classifier against our own gateway. Until then it is a mitigation, not a
guarantee.

---

## 6. Payment

| Option | Unlinks payer from usage? | Status (2026-10) | Verdict |
| --- | --- | --- | --- |
| **zkAPI, runtime-key mode** (v2-note-bound, live on mainnet) | Yes — proof of a funded note mints a short-lived capped key; server proves payment without receiving the conversation | **Live.** Single-party trusted setup; operator sees request time + budget tier; daemon reveals note id to the indexer; ~93 deposits total, ≈$2.29K TVL | **Chosen backend**, behind an interface |
| zkAPI, proxy mode | Yes, but the relay sees message traffic | Live | Rejected for our use — it reintroduces a party that sees content |
| zkAPI, "concession" protocol | Same goal, stronger exit story (withdraw without operator cooperation) | **Not deployable**: no network manifests, no production proving keys; published `clientd-v0.1.6` lacks the privacy features | Track; adopt when deployable |
| Monero (XMR) | Strong payment-graph privacy | Requires a *provider* that accepts XMR; essentially no major AI provider does, so it needs a human in the loop | Not viable for metered API in v1 |
| Lightning | Fast, low value, can be routed privately; some no-KYC services accept it | Needs a provider that accepts it; channel management adds operational weight | Not viable for metered API in v1 |
| Aztec / Railgun / other zk-rollups | Strong on-chain privacy for transfers | Not a metered-API credits system; and the v0 doc's invocation of these was a category error | Rejected |
| Tornado.cash | — | **OFAC-sanctioned and deprecated** | Rejected outright. Its presence in the v0 draft is why this doc exists |
| Bring-your-own API key | No | Works everywhere today, but the key *is* the identity | **T0/T1 fallback**, and honest about it |
| Prepaid card / gift card / VCC | Breaks the link with the card issuer | KYC at purchase, and providers ban them | Rejected as the primary path |
| Mock provider (no funds) | N/A — simulates the interface | Ours to write | **Default for development**, so the whole pipeline is testable without money or an undeployed protocol |

**Verdict:** define a `PaymentProvider` interface with three adapters — `mock` (default in dev),
`zkapi` (real, gated), `byok` (bring-your-own-key, T0/T1) — so the choice is configuration, not
architecture. Never hand-roll the proofs; never present zkAPI's guarantees without its caveats.

**The caveat that must ship in the product:** the operator can see per-request timing and budget
tier, the client discloses the note id to the indexer, the provider can link requests made under one
key, and the anonymity set is currently tiny. Payment unlinkability is real but *qualified*.

**What would change it:** a deployable concession protocol with production keys and a multi-party
ceremony; or a provider accepting Monero/Lightning directly, which would remove the ETH dependency.

---

## 7. Local runtime

| Option | Notes | Verdict |
| --- | --- | --- |
| **Ollama** | `POST /api/chat`, OpenAI-compatible surface, `keep_alive`, `/api/show` for thinking modes; trivial to run | **Chosen** — lowest friction, and the interface we need |
| llama.cpp directly | Maximum control over quantisation and KV cache | Fallback for constrained hardware; more integration work |
| vLLM / TGI | High-throughput serving, GPU-oriented | Overkill for one user; useful if batching rewrites |
| MLX / Core ML | Apple Silicon efficiency | Relevant only if U4 requires macOS support |

**Verdict:** Ollama, with a thin client so the backend is replaceable. The Open WebUI
(OpenAI-compatible) ecosystem means the same endpoint serves both our gateway and the user's
frontend — one integration, two consumers.

**Model choice:** decided by measurement (SC5 and SC7), not by reputation. Rewriting is a
constrained text-transformation task, so a small model may beat a large one on latency at equal
utility — this is exactly what the harness is for. Vitalik's ~20–30 tok/s experience is the
reference point for what "usable" felt like to the person who popularized this design.

---

## 8. Gateway surface

| Option | Verdict |
| --- | --- |
| **OpenAI-compatible HTTP on loopback** (`POST /v1/chat/completions`, `/v1/models`, SSE streaming) | **Chosen.** Agent harnesses, Open WebUI, and editors already speak it; upstream's clientd exposes the same shape, so components are interchangeable |
| Custom protocol / SDK | Rejected — forces users to adopt us and breaks composability |
| Patching the agent's HTTP client (MITM proxy) | Rejected — brittle, breaks TLS expectations, and turns certificate trust into a vulnerability |
| Browser extension | Rejected for v1 — dramatically larger attack surface for no privacy gain over a local endpoint |

**Design rule:** the gateway terminates HTTP on loopback only, never binds a routable interface, and
treats every inbound header as untrusted. Session identity comes from our own session cookie/header,
not from anything the caller can assert freely.

---

## 9. Summary of what "best" means here

"Best available" is not "most exotic." It means, in order of precedence:

1. **Mature over novel** where the difference is not measurable (Tor over mixnet for bulk data).
2. **Kernel-enforced over convention** (netns over `LD_PRELOAD`).
3. **Specified mechanism over folklore** (isolation tokens over `NEWNYM`).
4. **Measured over claimed** (our own span metrics over a paper's headline number).
5. **Delegated over hand-rolled** where the component is cryptographic (zkAPI over homebrew).
6. **Disclosed over implied** (every residual risk named, in the product).

---

*Next: [ARCHITECTURE.md](ARCHITECTURE.md) — how the chosen pieces fit together.*
