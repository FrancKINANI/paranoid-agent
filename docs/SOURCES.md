# Sources

Annotated evidence for every factual claim in this documentation set. Each entry says what it
establishes, what it does **not**, and how much weight it can carry.

**Research date:** 2026-10-17. Several of these facts are days old and this area is moving quickly —
re-verify before republishing any claim (see [EVALUATION.md](EVALUATION.md) §7).

**Method and limitations, stated plainly:**

- Sources were read over the public web. Where a page is JavaScript-rendered or gated, only the
  accessible portion was used and that is noted.
- **Vendor and blog performance numbers are unverified by us.** They are marked as such wherever
  they appear in these documents.
- Search-result snippets were treated as leads, not evidence; only positively fetched pages are
  cited as establishing a fact.
- No source in this list has been independently audited by this project, including the security
  reviews. They are evidence, not proof.

---

## 1. Primary: zkAPI and the reference design

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| *Introducing zkAPI: private usage credits for any API*, Ethereum Foundation blog — `blog.ethereum.org/2026/10/01/introducing-zkapi` | 2026-10-01 | The protocol's design and threat posture: deposit into a vault; balance becomes a private note; Groth16 on BN254, Poseidon commitments/nulls, 32-level Merkle tree; off-chain proof verification; runtime-key **and** proxy modes; the table of who learns what; and the two stated limitations (no network anonymity; prompt-content linkage) | Written by the protocol's authors. The "never learns" column is a **claim about their design**, not an independent audit. The anonymity-set and operator-visibility questions are addressed only as an advisory to route through Tor |
| `ethereum/zkapi` repository README — `github.com/ethereum/zkapi` | accessed 2026-10-17 | Existence and scope of the privacy-enabled client development branch: Tor conversation isolation, canonical prompt rewriting, separate target-side history, bounded cover traffic, vault-protocol selection. Also confirms the current circuit (`zkapi-v2-concession-v1`, vault revision 3), that it has a **single-party development setup**, that production keys are missing, and that concession network manifests are **undeployed**. Build/test toolchains (npm, cargo, forge) | Repository main branch. The privacy branch is explicitly **not a production release**. Branch names change; pin a commit |
| `zkapi-clientd` README — `raw.githubusercontent.com/ethereum/zkapi/main/zkapi-clientd/README.md` | accessed 2026-10-17 | Concrete interface facts used in [ARCHITECTURE.md](ARCHITECTURE.md): local OpenAI-compatible API on `127.0.0.1:8787/v1`; `config --relay-url tor://127.0.0.1:9050` for conversation-aware Tor routing with `IsolateSOCKSAuth`; default 60-second key-reuse window (`--key-reuse-window-seconds 0` for fresh keys per request); cover via `--cover-urls/--cover-rate`; rewriter via `--rewriter-url/--rewriter-model`; published `clientd-v0.1.6` does **not** contain the privacy features | Self-described behavior. The claim "rotates both identity and provider key for unrelated histories" is the vendor's; our M0 probe exists to verify the isolation half ourselves |
| `zkapi-clientd/docs/COVER_TRAFFIC.md` | accessed 2026-10-17 | The cover-traffic design in detail: Poisson interarrival, randomised first arrival with no startup burst, fixed worker pool with **unbuffered** dispatch that drops rather than queues, ≤20 s/request, 64 KiB cap, bodies discarded, per-worker SOCKS identity unrelated to inference, authenticated `tor://` only with remote DNS and no direct fallback, aggregate counters only. Also the cost figures (>1 GiB/hour at defaults) and the **explicit** admission: *"background noise, not proven traffic-analysis protection"* | Author-written documentation of their own implementation. The load characteristics are estimates from the authors, not measurements we made |
| `zkapi-clientd/docs/REWRITER.md` | accessed 2026-10-17 | The rewriter contract: target-side transcript, only the new user turn rewritten, digest-keyed memory-only cache (≤4096 messages / ≤8 MiB) that fails closed, replay of cached rewrites rather than raw text, and the limits — **the rewriter sees original text over a direct connection outside Tor**; attachments not anonymised; non-`user`-role text not protected; *"no raw prompt" is not a guarantee that every character changes*; meaning preservation and reduced stylometric identifiability are **model instructions, not proven properties** | The most useful single document for this project, because it states its own limits. Its evaluation section describes sample reconstructions, **not** a quantified fidelity benchmark |
| Open Anonymity blog — `openanonymity.ai/blog/oa-ethereum-foundation-collab/` | 2026-09-25 | The zkAPI collaboration and OA Chat's existence | Page is JavaScript-rendered; only metadata and the accessible summary could be read, so it is cited only for existence and framing, **not** for technical detail |
| zkAPI docs site — `zkapi.openanonymity.ai` | accessed 2026-10-17 | Product framing; note-bound Groth16, Baby-JubJub signatures, short-lived OpenRouter keys, native ETH settlement | Landing page only; the deeper docs were not fetched |

## 2. Independent scrutiny of zkAPI

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| **L2BEAT privacy review of zkAPI** — `l2beat.com/privacy/projects/zkapi` | published Oct 2026; figures captured mid-Oct 2026 | The counterweight to §1 — and the source of our honest caveats: **single-party Groth16 setup** with no MPC; operator sees each request's **time and budget tier**; the daemon **reveals the note id to the operator's indexer** before each request; the provider can link requests under one key; **TVL ≈$2.29K, 93 deposits total**; owner can pause withdrawals and expired notes can be swept to the treasury; escape exists (1 day) but cannot start during a pause; verifier attestation only helps if the user personally verifies. Rates the **privileged insider** posture as **Exposed** | A third-party review, not a penetration test. Figures are point-in-time and the TVL/anonymity-set numbers will have moved — re-check rather than quote. Its ratings assume the OA Chat frontend in some sections, which is not our client |

## 3. The reference design ("paranoid mode")

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| Vitalik Buterin, X post — `x.com/VitalikButerin/status/2111046730959433793` | 2026-10-16 | The design's existence and its four parts: separate Tor circuit per conversation, random cover traffic, zkAPI for payment, local LLM prompt rewriting, wrapped in an OpenAI-compatible daemon as a "paranoid mode" for the `pi` harness | **The post itself was not fetched directly** (X is not readable this way). Its content is cited through the reporting below, which quotes it verbatim. Treat quotations as second-hand |
| crypto.news, *Vitalik Buterin unveils privacy focused AI agent using Tor and zkAPI* — `crypto.news/vitalik-buterin-unveils-privacy-focused-ai-agent-using-tor-and-zkapi/` | 2026-10-16/17 | The detail behind the post, quoted: OpenAI-compatible daemon; bubblewrap (`bwrap`) sandbox with `torsocks`; MicroVM experiments not in the working setup; local rewriter model `qwen3.8-flash-next`; the timing complaint (worst at the start of a new conversation); the **guard-relay-collusion attack**; the mixnet suggestion; and the earlier data point of ~20–30 tokens/second with 100+ preferred | Secondary reporting. Two statements are reported as *absent*: no benchmarks, no average response times, no cost figures, and no named provider. We must not invent those |
| Further coverage: bitcoin.com news, coingape, cryptotimes, forklog, Binance Square | 2026-10-16/17 | Corroboration that the story and its four components are reported consistently across outlets | Aggregator-grade coverage; not used for technical detail beyond corroboration |

## 4. Tor: isolation, circuits, and application sandboxing

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| **Tor path specification — Stream isolation and circuit sharing** — `spec.torproject.org/path-spec/stream-isolation.html` | accessed 2026-10-17 | The normative basis for D4: two streams share a circuit only if isolation profiles are compatible; **only application-provided isolation tokens are "strong"**; when a strong property is present, circuits should be reused a long time (`MaxCircuitDirtiness`, `KeepAliveSocksAuth`); hostile exits and destinations learn that streams on one circuit belong to one user | The authority for the mechanism. It does **not** promise that isolation is verifiable from the client side — hence our "unverified" reporting state |
| Tor control specification — commands (`NEWNYM`) | accessed 2026-10-17 | `NEWNYM` makes new requests avoid old circuits and clears the DNS cache, and Tor **may rate-limit** it | The rate-limit magnitude (~10 s) is reported by secondary sources below, not by the spec text we read |
| Tor Project, *Introducing oniux: Kernel-level Tor isolation for any Linux app* — `blog.torproject.org/.../introducing-oniux-tor-isolation-using-linux-namespaces/` | 2025-05-14 | Kernel-enforced isolation: a network namespace with only an `onion0` interface, Arti + onionmasq, a Tor-aware resolver, **no root needed**; the comparison table against `torsocks`, including that `torsocks` fails for static binaries and Zig-built programs and is not true isolation; and the explicit **"experimental"** warning | Vendor announcement of its own tool. Version numbers on that page are stale (it points to `arti.torproject.org/related/oniux`); we assume v0.4.0+ and verify at install time |
| `torsocks(8)` manual pages | accessed 2026-10-17 | The mechanisms behind our rejection: `LD_PRELOAD`-based interception, only outgoing TCP proxied, and the documented limitation that only applications using a dynamically linked libc are covered | Man page; consistent with the Tor Project's own comparison |
| Secondary: tor-talk mailing list and vendor write-ups on the `NEWNYM` cooldown | 2010–2026 | The practical ~10 s cooldown (≈6 rotations/minute) and Tor's deliberate slowness when signaled repeatedly | Blog/forum-grade sources. Used only to describe the order of magnitude, never as a hard constant |

## 5. Mixnets

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| Nym documentation and NymVPN explanations — `support.nym.com`, `nym.com/blog/mixnet-tuning` | 2026 | 5-hop mixnet with cover traffic; "mixnet tuning" to trade latency against anonymity; the structural latency cost of mixing | **Vendor content. All performance claims are unverified by us** and are explicitly not relied on for any decision |
| PoPETs 2026, *Analysis and Attacks on the Reputation System of Nym* | 2026 | Active adversarial research on Nym's design — a signal that mixnets are not a settled answer | One paper on one subsystem; not a general indictment, and not evidence about latency or bandwidth |
| Katzenpost literature overview — `katzenpost.network` | 2024 | Constant-rate cover traffic and drops as a **design property**, i.e. structural bandwidth cost; long research lineage | Research material from the project itself; no interactive-chat suitability claim, which is our own conclusion |

## 6. Prompt rewriting research

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| *Need to Know: Contextual-Integrity-Grounded Query Rewriting for Privacy-Conscious LLM Delegation*, arXiv `2606.04067` | 2026-06-02 | The framing we adopt: task necessity, not information type; **`DelegateCI-Bench`** (3,167 samples, 11 domains, 20 task types) annotated with task-essential and task-non-essential-sensitive spans; the two failure modes (over-disclosure, over-removal); the peanut-allergy example; a learned rewriter reported at up to **+10.1 utility over on-device baselines** | A preprint ("work in progress"), not peer-reviewed at the time of writing. The +10.1 figure is **their** benchmark, their baselines, and their trained checkpoint — it is not a property our configuration inherits. We borrow the *method and metrics*, not the number |
| Zhu et al., *Exploiting Privacy Preserving Prompt Techniques*, PMC12439101 | 2025 | An adjacent local-prompt-assistant design and its privacy/utility framing | Not read beyond its abstract and framing; cited for context only |
| Microsoft Research, *Analyzing Leakage of PII in Language Models* | 2023 | That scrubbing PII carries a measurable privacy/utility tradeoff | Older work on a different axis (training/tabular data); cited only to support the generality of the tradeoff |

## 7. Local runtime and interfaces

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| Ollama API documentation — `docs.ollama.com/api/chat` (and OpenAI-compatibility page) | accessed 2026-10-17 | `POST /api/chat` with `model`, `messages`, `stream`, `format`, `options`, `keep_alive`, `think`; response fields including `prompt_eval_count`, `eval_count`, `done_reason`; an OpenAI-compatible surface including `/v1/chat/completions` | Vendor documentation. Note a known issue where `keep_alive` is ignored through the OpenAI-compatible path in some versions — verify against the installed version before depending on it |
| ZkAPI client TUI/harness references (`pi`, Hermes adapters) as cited by upstream's own docs | accessed 2026-10-17 | Which existing clients consume the extension fields upstream emits | Cited by upstream as compatibility checked against **source, not live sessions** — a caveat we inherit |

## 8. Toolchain

| Source | Date | Establishes | Caveats |
| --- | --- | --- | --- |
| Local environment probe (this repository) | 2026-10-17 | Python **3.14.7**, uv **0.12.7**, cargo **1.98.0**, node **26.7.0**, curl 8.22.0, util-linux 2.42.3, Linux 7.2.5; **Tor and ruff absent** | Directly measured on the development machine — see [IMPLEMENTATION.md](IMPLEMENTATION.md) §1.1. Facts about one machine, not a supported-platform statement |
| Pydantic v2.12 release notes / Python 3.14 release coverage | 2025-10-07 | Python 3.14 as the then-current stable release; Pydantic initial 3.14 support | Dependency-version claims age fastest of anything here; verify against installed versions |

---

## 9. Facts we deliberately did **not** source

Listed because their absence constrains our claims, and inventing them would be the easiest way to
overstate this project:

| Not established | Consequence |
| --- | --- |
| Any measured latency, throughput, or cost figure for the reference implementation | We publish our own measurements only ([EVALUATION.md](EVALUATION.md) §5) and never cite a number we did not measure |
| Independent penetration testing of zkAPI's contracts, verifier, or operator services | L2BEAT's review is a privacy review, not an audit; we state the posture rather than vouch for it |
| A live end-to-end test of the privacy branch's Tor isolation by any party other than upstream | **Milestone M0 exists precisely to test this ourselves** |
| Provider tolerance for Tor-routed zkAPI keys at scale | Treated as an unknown (U2) and a first-class risk, never assumed to work |
| Whether our cover traffic degrades any real traffic-analysis classifier | Reported as an experiment with an honest possible negative result ([EVALUATION.md](EVALUATION.md) §6) |

---

*If a document in this repository makes a claim that does not trace to an entry here, that is a bug
in the documentation. See [EVALUATION.md](EVALUATION.md) §9, release checklist item 4.*
