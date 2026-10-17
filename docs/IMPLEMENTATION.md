# Step 3 — Carry Out the Plan

> *"It is hard to have a good idea if you have not had a bad one first."* — Pólya, *How to Solve It*

This document is the execution plan: environment, dependencies, module contracts, milestones with
exit criteria, and the test strategy that makes each milestone's claim checkable.

**Sequencing rule, restated from [PLAN.md](PLAN.md) §3:** transport truth (P1, P2) is proven before
content privacy (P3–P4) is built. A perfect rewriter behind a leaking transport is theatre.

---

## 1. Environment

### 1.1 Verified state of the development machine (2026-10-17)

| Tool | State | Needed for |
| --- | --- | --- |
| Python | **3.14.7** ✅ | The control plane |
| uv | **0.12.7** ✅ | Dependency and venv management |
| cargo | **1.98.0** ✅ | Building upstream `clientd` (payment data plane) |
| node | **26.7.0** ✅ | Building upstream `clientd` (npm side) |
| curl | 8.22.0 ✅ | Leak tests, probes |
| unshare (util-linux) | 2.42.3 ✅ | Network-namespace fallback |
| Platform | Linux 7.2.5 (Arch-based) ✅ | Kernel-enforced isolation |
| **Tor** | ❌ **not installed** | Everything network-related |
| **ruff** | ❌ **not installed** | Lint/format gates |

### 1.2 Prerequisites to install

```bash
# Tor — a hard prerequisite; the gateway refuses to start in T2+ without it
sudo pacman -S tor            # Arch/Omarchy. Debian/Ubuntu: sudo apt install tor

# Python tooling (project-local, not global)
uv tool install ruff          # lint + format
uv python install 3.14        # if the interpreter needs pinning
```

### 1.3 Required Tor configuration

Isolation depends on this being right, and the gateway **must refuse to start** if it is not:

```conf
# /etc/tor/torrc
SocksPort 9050 IsolateSOCKSAuth        # the isolation primitive — non-negotiable
ControlPort 9051
CookieAuthentication 1                  # control port is local-only, used for observation
MaxCircuitDirtiness 600                 # default; circuits rotate on dirtiness, not per request
```

Safety notes: the control port is for **reading** circuit state and must not be exposed beyond
loopback; `NEWNYM` is never in the request path (see [LAYER-OPTIONS.md](LAYER-OPTIONS.md) §3).

### 1.4 Optional: kernel-enforced isolation

```bash
# Preferred (Linux only; experimental, per its own authors)
cargo install --git https://gitlab.torproject.org/tpo/core/oniux --tag v0.4.0 oniux
oniux curl https://icanhazip.com    # sanity check: must print a Tor exit IP

# Fallback: hand-rolled namespace, no extra dependency
unshare -n -- bash -c 'ip link set lo up; ...'
```

If neither is available, the tier ceiling drops to T1 and the user is told plainly.

---

## 2. Repository layout

```
.
├── README.md
├── docs/                     # this documentation set
├── pyproject.toml            # project metadata, deps, tool config
├── src/paranoid/             # the control plane (layout in ARCHITECTURE.md §5.3)
├── tests/
│   ├── unit/                 # pure logic, no network
│   ├── integration/          # needs a local Tor; marked, skipped without it
│   ├── leak/                 # the leak suite (SC1, SC6, SC9)
│   └── eval/                 # rewrite privacy/utility harness (SC5)
├── eval/
│   ├── spans/                # annotated evaluation samples (see EVALUATION.md)
│   └── reports/              # generated results, committed for trend tracking
└── scripts/
    ├── m0_probe.py           # transport-truth probe (Milestone M0)
    └── doctor.sh             # environment and configuration checks
```

`src/` layout is used deliberately: it forces tests against the installed package rather than the
working directory, which catches packaging errors early.

---

## 3. Dependencies

Every dependency is justified; anything not listed is not added without an ADR.

| Dependency | Purpose | Why this one |
| --- | --- | --- |
| `pydantic` + `pydantic-settings` | Config and request models | Typed, validated config with **fail-fast on unsafe values**; the natural fit for "refuse to start if the tier cannot be met" |
| `starlette` + `uvicorn` | ASGI gateway | Small, well-understood; SSE streaming for OpenAI compatibility; avoids a full framework's surface |
| `httpx[socks]` | Outbound HTTP through SOCKS5 with credentials | The isolation token *is* a per-connection SOCKS credential, so the client must support per-request proxy credentials and remote DNS |
| `stem` | Tor control port | Observe circuit state for verification. **Not** used for `NEWNYM` in the hot path |
| `typer` | CLI | Declarative CLI with good help output; thin over `click` |
| `pytest`, `pytest-asyncio` | Tests | Including the leak suite |
| `ruff` | Lint + format | Fast, single tool for both |
| stdlib `tomllib` / `tomli-w` | Read config / write it | Config is TOML; reading needs no dependency |
| stdlib `logging` + `paranoid/redact.py` | Logging | A redaction filter is **mandatory**; no third-party logging framework is needed to be careful |

Deliberately **not** included in v1: an ORM, a database, a task queue, a web UI framework, a second
HTTP client, or anything that would persist prompt state. If a future need demands one, it gets an
ADR first.

Version policy: pin major versions in `pyproject.toml`, commit `uv.lock`, and treat dependency
updates as reviewed changes — this is security-adjacent code.

---

## 4. Module contracts

Signatures below are the contract each module must satisfy; implementations may add, but not weaken.

```python
# config.py — validation is a security control, not a convenience
class Config(BaseModel):
    tier: Tier
    gateway: GatewayConfig
    tor: TorConfig
    rewriter: RewriterConfig
    cover: CoverConfig
    payment: PaymentConfig
    sandbox: SandboxConfig

    def validate_for_tier(self) -> list[Violation]:
        """Return every reason the environment cannot satisfy `tier`.

        Must reject: non-loopback rewriter URL, routable gateway bind,
        missing IsolateSOCKSAuth, cover enabled without permitted targets,
        tier >= T2 with sandbox mode "none" unless explicitly allowed.
        """

# session.py
class SessionManager:
    def start(self, conversation_key: str | None, tier: Tier) -> Session: ...
    def get(self, session_id: str) -> Session | None: ...
    def stop(self, session_id: str) -> CleanupReport: ...
    def reap_idle(self, ttl_seconds: int) -> list[str]: ...
    def isolation_report(self) -> IsolationReport:
        """Observed circuit mapping; states 'unverified' when the control
        port is unavailable, never a false 'ok'."""

# tor.py
class TorTransport:
    def preflight(self) -> TorPreflight:
        """Verify SocksPort has IsolateSOCKSAuth; verify control auth."""
    def client_for(self, isolation_token: str) -> httpx.AsyncClient: ...
    def observe_circuit(self, token: str) -> CircuitObservation | None: ...

# rewriter.py
class Rewriter:
    async def rewrite(self, text: str) -> RewriteResult: ...
    def policy(self) -> RewritePolicy:
        """Declares fail_closed and the limits; surfaced in /admin/status."""

# cover.py
class CoverTraffic:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def status(self) -> CoverStatus:
        """Attempted/succeeded/failed/skipped + bytes; aggregate only."""

# payment/base.py
class PaymentProvider(Protocol):
    def lease(self, budget_usd: Decimal) -> Lease: ...
    def settle(self, lease: Lease) -> Receipt: ...
    def status(self) -> PaymentStatus:
        """Includes anonymity-set disclosure — surfaced to the user."""

# enforce.py
class Enforcer:
    def activate(self, mode: SandboxMode) -> Environment:
        """Enter/verify isolation; returns facts about what is actually true."""
    def verify(self) -> list[Assertion]:
        """Runtime assertions: no route except Tor, DNS through Tor, no v6 leak."""

# audit.py
class Auditor:
    def leak_suite(self) -> LeakReport: ...
    def persistence_audit(self) -> PersistenceReport: ...
    def drift_check(self, expected: Config) -> DriftReport: ...
```

Two invariants enforced across modules:

1. **Nothing logs prompt content.** `redact.py` is applied at the logger factory level, and a unit
   test asserts that a pipeline-emitted log line cannot contain a canary string that was fed through
   as a prompt.
2. **No module writes prompt state to disk.** Persistence is limited to configuration and payment
   wallet state (owner-only file permissions), never conversation content.

---

## 5. Milestones

Each milestone has an **exit gate** that is a check, not a feeling. Nothing downstream starts until
the gate passes. Effort estimates assume one developer and are deliberately coarse.

### M0 — Transport truth 🎯 *start here*

**Goal:** prove that egress is Tor-only and that conversations are separable. Build the smallest
thing that can falsify the core assumptions.

Deliverable: `scripts/m0_probe.py`, plus a report committed to `eval/reports/`.

Tasks:
1. Preflight Tor: confirm SOCKS is listening and `IsolateSOCKSAuth` is enabled; fail loudly if not.
2. Marked integration test: open 4 fresh sessions, request `/v1/models` or an equivalent endpoint
   per session, record exit IP and circuit id.
3. Marked integration test: start 20 concurrent sessions with **distinct** isolation tokens; request
   a single endpoint; record `(session, circuit_id, exit_ip)`.
4. In `oniux`/netns: assert that a direct connection attempt from inside the namespace fails, and
   that only the Tor path works.
5. Measure a baseline: Tor RTT to the provider endpoint, **before** any rewriting exists, so added
   latency later can be attributed to the right layer.

**Exit gate:** a committed report showing (a) zero direct egress from the namespace, (b) 100% of
live unrelated sessions on distinct circuits, (c) the exit-IP distribution with collisions reported
rather than hidden. Written down even if the numbers are unflattering.

*If this gate fails, stop and re-read [PLAN.md](PLAN.md) §7 falsifier 1.*

### M1 — Gateway (≈2–4 days)

**Goal:** an unmodified client can chat through the gateway with per-conversation isolation.

Tasks: ASGI app with `/v1/chat/completions`, `/v1/models`, `/healthz`, and the `/admin/*` surface;
session minting from a conversation key; per-session `httpx` client carrying the SOCKS credentials;
tier enforcement; redaction-based logging; provider passthrough (no rewriting yet).

**Exit gate:** a real client (Open WebUI or `curl`) completes a conversation; two concurrent
conversations show distinct circuits in `/admin/status`; SC2 passes.

### M2 — Rewriting (≈3–5 days)

**Goal:** fail-closed rewriting with published quality numbers.

Tasks: the `Rewriter` client with the fixed instruction; fail-closed path; bounded cache keyed by
message digest, scoped to the previous history, memory-only; limits enforced; unknown content types
refused; adversarial corpus tests; the span-annotated evaluation set and harness.

**Exit gate:** SC4 (zero raw transmissions across the adversarial corpus) and SC5 (both metrics
measured and published in `eval/reports/`).

### M3 — Payment (≈2–4 days, gated on U1)

**Goal:** a swappable payment layer with a working mock and a documented real path.

Tasks: `PaymentProvider` protocol; `mock` adapter with lease/settle accounting; `byok` adapter;
`zkapi` adapter as a thin client over upstream (no crypto); `status()` disclosure including the
anonymity-set caveat; request path refuses **before** content leaves when no lease is available.

**Exit gate:** the full pipeline runs against `mock` with no funds; the `zkapi` path is documented
with its exact gating (which vault revision, which release, what is undeployed) and is not claimed to
work until demonstrated.

### M4 — Cover traffic (≈2–3 days)

**Goal:** bounded, ethical, opt-in cover that is not itself a fingerprint of our own making.

Tasks: Poisson scheduler with randomised first arrival and no startup burst; fixed worker pool that
drops under saturation; per-request timeout and byte cap; bodies discarded; separate SOCKS
identities; aggregate counters only; permitted-target validation and a hard bandwidth budget
(default well below upstream's 5/s).

**Exit gate:** scheduler unit tests pass (distribution, drop-not-queue, budget ceiling); a
30-minute live run reports budget conformance; zero plaintext or per-request logging.

### M5 — Hardening (≈3–5 days)

**Goal:** the guarantees become enforced rather than intended.

Tasks: `oniux`/netns activation with `unshare -n` fallback; runtime assertions (no route except Tor,
DNS via Tor, no IPv6 leak, rewriter is loopback); the leak suite; the persistence audit; drift
detection; failure-mode tests for every row of [ARCHITECTURE.md](ARCHITECTURE.md) §6.

**Exit gate:** SC1, SC6, SC9 green on Linux; every §6 failure mode has a test that shows the refusal
or the explicit downgrade.

### M6 — Usability and honesty (≈2–3 days)

**Goal:** a new user reaches T2 without reading source, and cannot be misled about what they got.

Tasks: `paranoid doctor` (environment + tier report), `paranoid leaktest`, tier selection, packaged
install, README numbers refreshed from the latest report, and the run-time disclosure of payment and
cover-traffic posture.

**Exit gate:** a first-time user reaches a working T2 session following only the README, and the
README's claims each cite a test in [EVALUATION.md](EVALUATION.md).

---

## 6. Test strategy

| Tier | Scope | Runs in CI | Notes |
| --- | --- | --- | --- |
| `unit/` | Config validation, span logic, scheduler maths, redaction, session lifecycle | Always | Fast; no network. Redaction test uses a canary string |
| `integration/` | Tor preflight, isolation, circuits, provider passthrough | With local Tor | **Marked**; skipped (not silently passed) when Tor is absent, and skips are reported |
| `leak/` | SC1, SC6, SC9 | Linux CI | The security-critical suite; a failure blocks release |
| `eval/` | SC5 span metrics, SC7 latency | On demand + nightly | Produces committed reports for trend tracking |

Rules:

- A test that cannot run **skips loudly**. A green build with 12 skipped security tests is not green;
  the CI summary must state the skip count.
- Never weaken an assertion to make a build pass. If a guarantee cannot hold, change the tier
  documentation and the threat model — that is the correct fix, and it is a documentation change, not
  a test change.
- Every row of [ARCHITECTURE.md](ARCHITECTURE.md) §6 gets at least one test asserting the *refusal* or
  the *explicit downgrade*.

---

## 7. Coding conventions

- **Fail closed by default.** Any code path that could send user content must require an explicit
  positive decision, not an absence of negatives.
- **No prompt content in logs, exceptions, metrics, or crash output.** Use the redaction layer;
  include a canary test.
- **Types on public boundaries**, and `ruff` clean.
- **No `print` in library code**; the CLI owns user-facing output.
- **Comments explain *why*.** The threat model is the context for unusual-looking decisions: if a
  line exists because of an adversary, name the adversary.
- **Never add a dependency** without recording the reason in [DECISIONS.md](DECISIONS.md).
- **Never write prompt state to disk**, including in tests; tests use in-memory fixtures.

---

## 8. Definition of done, per feature

A feature is done when: it has tests that fail if the behaviour regresses; the leak suite accounts
for it; [ARCHITECTURE.md](ARCHITECTURE.md) §6 lists its failure mode; [THREAT-MODEL.md](THREAT-MODEL.md)
reflects any change in guarantees; and the README's numbers are regenerated from a report rather than
typed by hand.

---

## 9. Risk-driven ordering

Effort goes where the risk register points ([THREAT-MODEL.md](THREAT-MODEL.md) §4): R13 (latency
pushes users to disable protections) and R8 (over-removal degrades answers) are the most likely
real-world failures, so measurement lands in M2 and stays in CI, not at the end.

---

*Next: [EVALUATION.md](EVALUATION.md) — how each milestone's claim is checked, and how we look back.*
