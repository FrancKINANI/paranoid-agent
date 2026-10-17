# TODO

Milestones and their exit gates come from [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).
An unchecked box with a gate is the point: **a milestone is not done because the tasks are done, but
because its gate passes.**

Legend: `[ ]` not started · `[~]` in progress · `[x]` done, gate passed.

---

## Phase 0 — Answers before code

These block design decisions and are the cheapest possible way to save rework. See
[docs/DECISIONS.md](docs/DECISIONS.md) §B.

- [ ] **Understand first:** work through `docs/learn/` lessons 00–09 — these decisions cannot be made
      well without the concepts underneath them
- [ ] **U1** Fund a real mainnet zkAPI note in v1, or ship mock-first?
- [ ] **U2** Which providers must work — and do they accept Tor-routed traffic?
- [ ] **U3** What added latency per turn is acceptable?
- [ ] **U4** Is Linux-only acceptable for strict (Tier 2) isolation?
- [ ] **U5** Is token streaming required?
- [ ] **U6** Is provider + guard collusion (AD5) acceptable as out of scope for v1?
- [ ] **U7** How much may sit in a note, given pause/expiry risk?
- [ ] **U8** Which cover-traffic endpoints do we own or have permission to poll?
- [ ] **U9** Pin upstream `clientd` at a commit now, or wait for a reviewed release?
- [ ] **U10** License, security policy, and how to report a vulnerability.

---

## Phase 1 — Environment and transport truth

### Environment
- [ ] Install Tor (`pacman -S tor` on this machine) and confirm `tor --version`
- [ ] Install ruff (`uv tool install ruff`) and wire lint/format into CI
- [ ] Create `pyproject.toml`, `src/paranoid/` skeleton, and `uv.lock`
- [ ] Configure `SocksPort 9050 IsolateSOCKSAuth` + local-only `ControlPort`, and verify both
- [ ] Install `oniux` and confirm `oniux curl https://icanhazip.com` returns a Tor exit IP

### M0 — Transport truth *(start here; falsifies the core assumptions)*
- [ ] `scripts/m0_probe.py`: Tor preflight, including a hard failure if `IsolateSOCKSAuth` is off
- [ ] Open 20 concurrent sessions with distinct isolation tokens; record `(session, circuit_id, exit_ip)`
- [ ] Read `GETINFO circuit-status` and assert unrelated live sessions never share a circuit
- [ ] Inside the namespace: assert direct connections fail and only the Tor path works
- [ ] Measure a **Tor-only baseline** RTT to the provider *before* any rewriting exists
- [ ] Commit the report to `eval/reports/` — including collisions and unflattering numbers
- [ ] **Gate:** zero direct egress · 100% distinct circuits for live unrelated sessions · exit-IP
      distribution published

> If this gate fails, stop. Re-read [docs/PLAN.md](docs/PLAN.md) §7 falsifier 1 and change the
> isolation boundary — do not build on top of it.

---

## Phase 2 — Gateway

### M1 — OpenAI-compatible gateway
- [ ] ASGI app: `POST /v1/chat/completions` (streaming + whole), `GET /v1/models`, `GET /healthz`
- [ ] Admin surface: `/admin/status`, `/admin/session`, `/admin/session/{id}`, `/admin/audit`
- [ ] Config model with tier validation that **refuses to start** on unsafe values
- [ ] Session manager: derived conversation identity, per-session isolation token, TTL reaping
- [ ] Per-session `httpx` client carrying the SOCKS credentials; remote DNS only
- [ ] Redaction layer for logs, with a canary unit test
- [ ] **Gate (SC2):** an unmodified client chats through it; two concurrent conversations show
      distinct circuits

---

## Phase 3 — Content privacy

### M2 — Fail-closed rewriting
- [ ] `Rewriter` client with the fixed task-necessity instruction; bounded limits
- [ ] Digest-keyed, memory-only, bounded cache; replay cached rewrites; refuse unknown content types
- [ ] Adversarial corpus: retries, edited/truncated history, tool continuations, text smuggled into
      non-`user` roles, oversized input, rewriter down, refusal/malformed output
- [ ] Annotate ≥200 span-labelled samples **before** tuning the rewriter (labels first, or the
      numbers flatter the model)
- [ ] Evaluation harness reporting disclosure, retention, exact-preservation, and constraint rates
- [ ] **Gate (SC4, SC5):** 0 raw transmissions; disclosure ≤5% **and** retention ≥90% — both published

> If SC5 cannot be met with a model that fits the hardware, do not weaken the metric. Re-read
> [docs/PLAN.md](docs/PLAN.md) §7 falsifier 2 and reconsider rewriting's role in the product.

---

## Phase 4 — Payment

### M3 — Swappable payment layer *(gated on U1)*
- [ ] `PaymentProvider` protocol: `lease`, `settle`, `status`
- [ ] `mock` adapter with lease/settle accounting — the default in development and CI
- [ ] `byok` adapter for T0/T1, documented as "the key is the identity"
- [ ] `zkapi` adapter as a **thin client over upstream** — no crypto reimplementation
- [ ] `status()` discloses anonymity-set size and operator visibility
- [ ] Refuse **before** content leaves when no lease is available
- [ ] **Gate (SC8):** full pipeline runs against `mock`; zkAPI path documented with its exact gating,
      and not claimed to work until demonstrated

---

## Phase 5 — Cover traffic

### M4 — Bounded, ethical cover
- [ ] Poisson scheduler: exponential interarrival, randomised first arrival, no startup burst
- [ ] Fixed worker pool, **unbuffered** dispatch that drops under saturation (no queue, no catch-up)
- [ ] Per-request timeout and byte cap; bodies discarded; aggregate counters only
- [ ] Per-worker SOCKS identities unrelated to inference or payment
- [ ] Required permitted-target list; hard bandwidth budget; off by default
- [ ] **Gate:** scheduler tests pass; a 30-minute live run conforms to budget; zero per-request logs

---

## Phase 6 — Hardening

### M5 — Make the guarantees enforced
- [ ] Namespace activation via `oniux`, with a hand-rolled `unshare -n` fallback
- [ ] Runtime assertions: no route except Tor, DNS via Tor, no IPv6 leak, rewriter is loopback
- [ ] Leak suite: direct egress, DNS, IPv6, rewriter direct connection, telemetry, cover routing
- [ ] Persistence audit with canary strings, including a forced-crash case
- [ ] Drift detection: a session that loses its isolation token fails loudly
- [ ] Failure-mode tests for every row of [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §6
- [ ] **Gate (SC1, SC6, SC9):** all green on Linux; non-Linux gaps listed as failures, not skipped

---

## Phase 7 — Usability and honesty

### M6 — Ship something a new user can trust
- [ ] `paranoid doctor` (environment + tier report) and `paranoid leaktest`
- [ ] Tier selection and explicit, visible downgrade behaviour
- [ ] Run-time disclosure of payment and cover-traffic posture at startup
- [ ] Refresh README numbers from the latest report — never typed by hand
- [ ] **Gate (SC7, SC10):** a first-time user reaches a working Tier 2 session from the README alone;
      every README claim cites a test in [docs/EVALUATION.md](docs/EVALUATION.md) or is marked
      unverified

---

## Recurring

- [ ] Monthly: re-verify the facts in [docs/PROBLEM.md](docs/PROBLEM.md) §2 against
      [docs/SOURCES.md](docs/SOURCES.md) — re-check zkAPI's deployment status, deposit count, and
      upstream release state before repeating any claim about them
- [ ] Every milestone: the look-back ritual in [docs/EVALUATION.md](docs/EVALUATION.md) §7, written to
      `eval/reports/lookback-M<N>.md`
- [ ] Every release: the checklist in [docs/EVALUATION.md](docs/EVALUATION.md) §9
- [ ] Every time a guarantee changes: update [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md) §3–4 **in the
      same change**, or it is a defect

---

## Deliberately not planned

Recorded so they are not reintroduced as "obvious" work:

- Reimplementing zkAPI's proofs, vault, or settlement ([docs/DECISIONS.md](docs/DECISIONS.md) D1).
- A `NEWNYM`-based isolation mode (D4).
- Running any infrastructure on the user's behalf — no relay, no hosted gateway, no telemetry (D11).
- Unbounded cover traffic, or cover aimed at services we do not own or have permission to poll (D7).
- Sending unrewritten text as an automatic fallback (D8).
- Claiming protection against provider + guard collusion in Tiers 0–2 (D9).
- Constant-rate cover traffic over plain Tor: the design that would need it is Tier 3, and it needs
  a mixnet (D7, D9).
