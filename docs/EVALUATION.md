# Step 4 — Look Back

> *"It is not a bad idea to check your reasoning… Could you have done it more simply?"* —
> Pólya, *How to Solve It*

Pólya's fourth step is the one people skip. It is also the step that decides whether this project
deserves trust, because a privacy tool's most likely failure is not a broken cipher — it is an
**unexamined claim**.

This document defines: what "done" means measurably (§2), how each guarantee is tested (§3), how the
subjective-sounding properties (rewrite quality, latency, cover effectiveness) are turned into
numbers (§4–6), and the review ritual that runs at every milestone (§7).

---

## 1. Principles

1. **A claim without a test is marketing.** Every `yes` in [THREAT-MODEL.md](THREAT-MODEL.md) §3 maps
   to a check here.
2. **Report the awkward number.** Exit-IP collisions, over-removal rates, p95 latency, small
   anonymity sets — published, not smoothed.
3. **Measure distributions, not anecdotes.** Per-conversation isolation was *wrong* if three
   conversations shared a circuit once out of twenty; a single happy run proves nothing.
4. **Never measure through a different path than the user takes.** Tests exercise the same gateway,
   the same isolation tokens, the same Tor client.
5. **Regressions are gated.** A privacy regression blocks release; a performance regression warns
   and is recorded.

---

## 2. Acceptance gates

Concrete tests for each success criterion from [PROBLEM.md](PROBLEM.md) §7.

| # | Criterion | Test | Pass condition | Blocks |
| --- | --- | --- | --- | --- |
| SC1 | No direct egress | Inside the namespace: attempt direct connections to a control host and to the provider; audit sockets over a 10-min mixed workload | All direct attempts fail; zero non-loopback sockets except the Tor SOCKS path | M5, release |
| SC2 | Conversation isolation | 20 concurrent sessions with distinct isolation tokens; read `GETINFO circuit-status`; assert mapping | 100% of live unrelated sessions on distinct circuits; 100% distinct tokens | M1, release |
| SC3 | Exit diversity (informational) | Same 20 sessions; collect exit IPs | **Reported, never asserted as a guarantee.** ≥5 distinct exits as a sanity floor | — |
| SC4 | Rewrite completeness, fail-closed | Adversarial corpus: retries; edited and truncated history; tool continuations; text smuggled into `system`/`developer`/`tool`/`assistant`; unknown content types; oversized input; rewriter down; rewriter returns refusal or malformed JSON | 100% of `user` text rewritten; **0** raw transmissions; unknown types refused; every failure refuses the request | M2, release |
| SC5 | Rewrite privacy/utility | Span-annotated set (§4) | Non-essential span disclosure ≤5%; task-essential retention ≥90%; **both reported together** | M2, release |
| SC6 | No raw prompt persistence | Post-session filesystem/log/temp audit; forced-crash case; canary-string search across the state dir | Zero recoverable prompt text outside memory | M5, release |
| SC7 | Latency honesty | Per-layer instrumentation (§5) | p50/p95 published for rewrite, time-to-first-token, and total; budget set by U3; CI warns on regression | M6 |
| SC8 | Payment posture disclosed | Inspect `/admin/status` and startup output | Anonymity-set size and operator-visibility caveats printed, not buried in docs | M3 |
| SC9 | Leak suite | The full suite (§3.1) | Green on Linux; non-Linux gaps listed as failures | M5, release |
| SC10 | Honesty audit | Every README/doc claim cross-checked against this document | Each claim cites a test or is labelled unverified | M6, release |

---

## 3. Leak suite

The security-critical suite. Each check is a separate, named test so a failure is diagnostic.

### 3.1 Network and environment

| Check | Method | Failure means |
| --- | --- | --- |
| Direct egress blocked | Attempt a TCP connect from inside the namespace to a public IP and to the provider's hostname | Egress enforcement is broken — the highest-severity failure |
| DNS stays inside Tor | Resolve a unique subdomain (a domain we control, logging queries) with the gateway running; assert the query arrived from a Tor exit, never from the user's resolver | DNS leak |
| IPv6 does not leak | Attempt IPv6 connections; assert only the Tor path answers and no v6 address of the host is used | The classic "IPv4-only proxy" leak |
| Rewriter is loopback | Assert the configured rewriter host resolves to `127.0.0.1`/`::1`/`localhost`, and that a remote rewriter is refused at startup | The original prompt would leave the machine |
| No telemetry | Run with all outbound sockets captured; assert destinations are only Tor, loopback, and permitted cover targets | An unannounced phone-home |
| Cover routing | Assert cover requests use authenticated Tor (remote DNS), never direct, and never the inference isolation identity | Cover traffic deanonymising the user |
| Sandbox actually applied | Assert the data plane runs in a namespace with no external interface, or that the tier was explicitly downgraded and reported | Silent loss of the kernel guarantee |

### 3.2 Persistence and side channels

| Check | Method | Failure means |
| --- | --- | --- |
| Canary search | Feed prompts containing a unique canary; grep the entire state dir, temp dirs, and logs; inspect open files | Prompt text reached disk |
| Crash-safety | Kill the process mid-request; re-run the canary search | A crash dump leaked the prompt |
| Log redaction | Unit test feeding a canary prompt through a full request | The redaction filter has a hole |
| Session residue | Stop a session; assert its token, cache, and any derived state are gone | Cross-conversation contamination |

Run the suite on every release and on every change to transport, rewriting, or enforcement.

---

## 4. Rewrite quality evaluation (SC5)

The most subjective-sounding part of the project, made mechanical.

### 4.1 Dataset

- **≥200 samples**, committed under `eval/spans/`, drawn from shapes we care about: health, finance,
  employment, family, code assistance, translation, summarisation, and the adversarial cases below.
- **Annotation schema, per sample:**
  - `essential[]` — spans the remote model needs to answer correctly;
  - `non_essential_sensitive[]` — sensitive spans the task does not need;
  - `must_preserve_exactly[]` — code, identifiers, paths, URLs, numbers, exact-output constraints;
  - `constraints[]` — negations and conditions whose loss silently changes the answer.
- **Annotate before building the rewriter**, not after. Labels written with the rewriter in hand
  will flatter it.
- **Provenance matters:** synthetic samples are fine for control, but include real-shaped organic
  prompts, because synthetic data is systematically easier. Any published number states the mix.

### 4.2 Adversarial cases (the ones that catch real bugs)

| Case | Why |
| --- | --- |
| "I'm allergic to peanuts" for a snack question vs a file-renaming question | The canonical contextual-integrity pair: must be preserved in one, removed in the other. A rewriter scoring well on only one is not working |
| Negation and condition preservation ("do **not** use recursion", "keep it under 100 words") | Over-removal that drops a constraint silently changes the answer |
| Code blocks, quotes, paths, URLs, numeric limits | Must survive verbatim; paraphrasing code is a failure |
| Identity-revealing narrative ("my employer X at Y, we're migrating…") | Task-non-essential; should be generalised |
| Multi-part user messages | All parts must be handled together in one rewrite |
| Reused documents across turns | The provider's cross-session linking vector (R1); long-term, a linkability test |

### 4.3 Metrics and scoring

| Metric | Definition | Target |
| --- | --- | --- |
| **Non-essential disclosure rate** | Fraction of `non_essential_sensitive` spans appearing (lexically or semantically) in the rewrite | ≤5% |
| **Essential retention rate** | Fraction of `essential` spans retained lexically or semantically | ≥90% |
| **Exact-preservation rate** | Fraction of `must_preserve_exactly` spans byte-identical | 100% |
| **Constraint retention rate** | Fraction of `constraints` intact | 100% |
| **Rewrite latency** | p50/p95 per turn | Reported (§5) |

Report **all** of them. Publishing only disclosure rate rewards a rewriter that strips everything;
publishing only retention rewards one that changes nothing. The pair is the finding.

Matching follows the spirit of the published contextual-integrity methodology: check **both** lexical
coverage and semantic similarity, since paraphrase-based evasion defeats a single criterion — and be
explicit that a threshold was chosen, not derived.

### 4.4 Secondary, exploratory: linkability

A style-linkability probe (can a simple classifier tell that two rewrites came from the same user?)
is interesting and worth recording, but upstream's own documentation is right that reduced
stylometric identifiability is **a model instruction, not a proven property**. This stays labelled
experimental. When an exploratory metric has no threshold, it is reported, never gated.

---

## 5. Latency evaluation (SC7)

Latency is the failure mode most likely to get protections switched off (R13), so it is measured
from M0 — before there is a product to be disappointed by.

### 5.1 Instrumentation

Per request, record: session resolution, rewrite duration, lease acquisition, Tor connect, provider
time-to-first-token, total time to last token, and bytes. Attribute cost to its layer.

### 5.2 Protocol

| Rule | Reason |
| --- | --- |
| Measure **cold** and **warm** separately | Vitalik's report that a new conversation is slowest is a measurable effect: uncached rewrites, new circuits, first provider token. A single blended average hides the worst case |
| Report p50 and p95, not means | Means conceal the tail users actually feel |
| Include a **Tor-only baseline** with no rewriting and no cover | Without it, added latency cannot be attributed |
| Include a **direct-connection reference**, clearly labelled as not a supported configuration | Establishes the price of privacy in milliseconds — a number users deserve |
| Fix the model, provider, prompt set, and time of day | Tor latency varies; comparisons across days are not comparisons |
| Report tokens/second from the local model | It gates the rewrite step's cost |

### 5.3 Presented as

A table, per tier: rewrite p50/p95, TTFT p50/p95, total p50/p95, and the local model's tok/s. The
README quotes the latest report; nobody types latency numbers by hand.

---

## 6. Cover-traffic evaluation (honest by construction)

The risk here is publishing a number that implies a protection we do not have.

**The experiment we can actually run:** build a simple timing classifier against **our own** gateway —
labelled traffic (real requests) vs cover-only periods — and measure whether our Poisson cover
degrades it. This tests whether our cover does anything at all against a naive observer. A negative
result is a legitimate, publishable finding.

**The experiment we cannot run:** the AD5 attack, in which the provider and the guard relay collude
and can actively manipulate response timing. Our cover is explicitly not designed to defeat that,
and no test result may be presented as if it did.

Reporting rules:

- Never say "cover traffic hides your requests." Say what was measured, against which classifier.
- Always restate the cost: bandwidth, third-party load, and the fact that the *pattern* of cover is
  itself potentially identifiable (destination set, sizes, schedule).
- Absolute claims about resistance to traffic analysis are forbidden in this project.

---

## 7. The look-back ritual

At the **end** of every milestone, and before every release. Fifteen minutes, written down in
`eval/reports/lookback-M<N>.md`. Answers are committed, not just discussed.

**Pólya's four questions, applied:**

1. **Did it work?**
   - Which gates passed, with their numbers?
   - Which failed, and is the fix in code, or in the documentation of what we promise?
2. **Could it have been done more simply?**
   - Which component exists out of habit or speculation rather than need? (The answer "we might need
     it later" is not an answer.)
   - Could any component be deleted in favour of a standard library, a native platform feature, or an
     already-working upstream component?
3. **Is the reasoning sound?**
   - Re-read [THREAT-MODEL.md](THREAT-MODEL.md) §4 and **delete any risk that is genuinely closed**.
     A register that never shrinks is decoration.
   - Does any guarantee in §3 rest on a test that no longer exists, or on a test that was quietly
     weakened? Check the skip count.
4. **What carries forward?**
   - Which measurement became a permanent CI gate?
   - Which assumption from [PROBLEM.md](PROBLEM.md) §3 was invalidated, and what did it cost?
   - Which open question in [DECISIONS.md](DECISIONS.md) can now be closed — and which new one opened?

**Project-specific check:** has anything changed in the outside world that invalidates a fact? This
area moved visibly in the two weeks before this documentation was written (zkAPI launched 2026-10-01;
paranoid mode described 2026-10-16). Re-verify the facts in [PROBLEM.md](PROBLEM.md) §2 against
[SOURCES.md](SOURCES.md) at least monthly, and immediately before any claim about zkAPI's deployment
status.

---

## 8. Measurement pitfalls

Written down because each of these has produced a false "it works" in real projects:

| Pitfall | Correction |
| --- | --- |
| One successful run reported as isolation | Run N≥20 concurrent sessions and report the distribution |
| Same exit IP twice interpreted as failure | Circuit reuse and exit collisions happen normally; measure circuits, not IPs, for SC2 |
| Latency measured warm only | Always report cold-start separately |
| Comparing latency against a different provider or day | Freeze provider, model, prompt set, and time window |
| Eval set tuned to the rewriter after the fact | Annotate first; freeze the set; version it |
| Skipped tests counted as passing | CI reports skip counts; security tests that skip are called out |
| Cover measured against a strawman classifier and called "protection" | State the classifier; cap the claim at what was measured |
| Raw prompting compared on a different model than the tier under test | Compare like with like, and label tiers explicitly |
| A "private" claim with no adversary named | Name the adversary from [THREAT-MODEL.md](THREAT-MODEL.md) or withdraw the claim |

---

## 9. Release checklist

1. Leak suite green on Linux; skipped tests enumerated and justified.
2. SC2 and SC4 pass on a clean checkout.
3. `eval/reports/` regenerated: span metrics, latency table, cover experiment result.
4. README numbers copied from the reports; every claim maps to this document or is marked unverified.
5. [THREAT-MODEL.md](THREAT-MODEL.md) §3 and §4 updated for anything that changed.
6. [DECISIONS.md](DECISIONS.md) updated with this release's decisions and newly opened questions.
7. Look-back note committed for the milestone.
8. Version pinned for any upstream component used (commit hash, not a branch name — the privacy
   branch is explicitly not a production release).

---

*Back to [README.md](README.md) for the index, or to [DECISIONS.md](DECISIONS.md) for the open
questions that still need answers.*
