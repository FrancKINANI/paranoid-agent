# 06 — Isolation and the Endpoint

## The question

If your software is configured to send everything through Tor, why is that not a security boundary?

## First principle

**A boundary must be enforced by something the contained thing cannot bypass.**

Configuration is a *promise*. The kernel is a *fact*. If the thing you are trying to constrain is the
same thing you are asking to behave — an application, or code you wrote — then you have not built a
boundary, you have built a convention. Conventions hold until one code path forgets.

The corollary is uncomfortable and worth stating early: **your own machine is inside the trust
boundary.** Tor, zkAPI, and a local rewriter can protect you from the network, the ledger, and the
provider. None of them can protect you from software running on your computer, because that software
is where the plaintext lives.

## How proxying actually works, and where it leaks

When an application "uses a SOCKS proxy", a chain of optional steps has to all go right:

```
your intention  →  a setting (env var, config key)  →  a library that honours it
     →  a socket connect() that uses it  →  the bytes
```

Every arrow is optional. Every arrow is a place the traffic can slip out unproxied.

### The leak catalogue

| Leak | Why it happens | Consequence |
| --- | --- | --- |
| **Local DNS resolution** | The proxy carries TCP; name resolution may happen *before* the connection, on your machine | Your resolver learns every destination — sometimes more revealing than the traffic |
| **IPv6 fallback** | You proxied IPv4; the app tries IPv6 | Direct connection, real IP |
| **A library that ignores proxies** | Not every HTTP client reads the same environment variables | Silent direct connection |
| **Static binaries / raw syscalls** | `LD_PRELOAD` interception only works through a dynamically linked libc | Interception is bypassed entirely; this is why Tor Project says `torsocks` "does not offer true isolation" |
| **Telemetry, crash reporters, updaters** | Components nobody thinks of as "the app" | Every one is a direct connection with your IP |
| **A deliberately unprotected path** | A real example from this domain: upstream's prompt rewriter connects **directly, outside Tor** | Your *raw* prompt — the most sensitive artifact in the pipeline — leaves over the least protected path |

That last row is worth dwelling on, because it is not hypothetical. It is the documented behaviour of
the upstream client at the time of research, and it survived code review because each component was
correct in isolation: Tor routing was correct for inference, and the rewriter's connection was correct
*as a rewriter*. The leak existed in the seam. **Privacy failures live in seams.**

The DNS row also deserves emphasis because it is the most common real-world leak: routing your traffic
through Tor while resolving names locally tells your ISP exactly where you are going, which defeats the
entire exercise. The fix is to hand the *hostname* to the proxy so resolution happens on the far side
("remote DNS"), which is what SOCKS5h does and what correct configuration must ensure.

## The enforcement ladder

From weakest to strongest. The question for each rung is the same: **can the contained application
bypass it without cooperating?**

| Rung | Mechanism | Bypassable by the app? | Notes |
| --- | --- | --- | --- |
| 1 | Configuration / environment variable | **Yes, trivially** | Every leak in the catalogue above is a rung-1 failure |
| 2 | `LD_PRELOAD` interception (`torsocks`) | **Yes** — static binaries, raw syscalls, Zig-built programs | Tor Project's own comparison is blunt: "not true isolation"; the app still sees the host's real interfaces |
| 3 | Firewall redirect (iptables/nftables) | No, for the app — but it is system-wide and misconfiguration-prone | Enforced by the kernel, affects everything on the machine, needs root, and one wrong rule is silent |
| 4 | **Network namespace** | **No** | A kernel-enforced, per-process separate view of the network. Inside it, there is no route to leak through |
| 5 | Separate VM | No | Strongest; heavyweight; the right answer for high-assurance setups |

### Why the network namespace is the right primitive here

A network namespace gives a process its own set of network interfaces and routing table. If the only
interface in that namespace is one that speaks to Tor, then:

- there is no `eth0` to fall back to;
- a DNS query has nowhere to go except the namespace's resolver;
- IPv6 cannot escape, because there is no IPv6 route;
- a static binary cannot bypass interception, because there is nothing to intercept — there is simply
  no other path;
- a mistake in the application is contained, because the leak would require a route that does not exist.

That is the difference between "unlikely to leak" and "unable to leak". The Tor Project built **oniux**
for exactly this: it drops an arbitrary Linux program into its own namespace with a single `onion0`
interface, backed by Arti and onionmasq, with a Tor-aware resolver, and — usefully — it works through
user namespaces, so it does not require root. Its own authors label it **experimental**, and it is
**Linux only**. Both caveats are real and are carried into this project's platform decisions.

## The endpoint is inside the trust boundary

Everything above is about the network. Now the part that no amount of routing can fix:

| Threat | Does isolation help? |
| --- | --- |
| Malware with your privileges | **No.** It reads your prompts from memory, or the screen |
| A keylogger | No |
| Physical access to an unlocked machine | No |
| Forensic analysis of your disk | **Partly** — this project never writes raw prompts to disk, so a disk image does not contain them. That is a real, deliberate benefit |
| A malicious OS, compiler, or hardware | No |

This is the honest line to hold: the no-persistence design (D6) reduces what survives on disk, and it
does nothing against a live local attacker. The design's claim is precise — *raw prompts are not
transmitted and not persisted* — and that claim is testable, unlike "your prompts are safe".

Also note the corollary about memory: "the original prompt is discarded from memory" was one of the
errors in this project's first draft, because it simultaneously claimed to keep no copy and to
re-integrate the answer using the original. You cannot have both. The corrected claim is *in memory for
the life of the request, never transmitted, never persisted* — which is both achievable and checkable.

## Verification is part of the design, not an afterthought

You cannot tell whether isolation is working by looking at it. The failure is silent by nature: a
leaking system behaves exactly like a working one, only less privately. So the design must include
tests that would *catch* a leak:

| Check | Method |
| --- | --- |
| Direct egress is impossible | From inside the namespace, attempt a direct connection to a public address; it must fail |
| DNS stays inside | Resolve a domain you control; the query must arrive from a Tor exit, never from your resolver |
| IPv6 does not leak | Attempt IPv6 connections; nothing outside the Tor path may answer |
| The rewriter is local | Assert the configured rewriter resolves to loopback, and refuse to start otherwise |
| No telemetry | Capture outbound sockets; the only destinations may be Tor, loopback, and permitted cover targets |
| No prompt on disk | Feed a canary string through, then search the filesystem, temp dirs, logs, and open files |

Two design consequences follow, and both appear in this project's architecture:

1. **Fail closed.** If the environment cannot provide the isolation the requested tier requires, refuse
   to start. Running "Tier 2" without a namespace is not a degraded Tier 2 — it is a different, weaker
   thing wearing the same label.
2. **Report unverified states.** If the control port is unavailable, isolation is still enforced (SOCKS
   tokens), but it cannot be *confirmed*. The status output says `unverified` rather than `ok`. A tool
   that cannot verify a property should say so.

## Where it breaks

**1. Platform.** Network namespaces are Linux. On macOS and Windows there is no equivalent that is
kernel-enforced and rootless, so the honest ceiling is lower — which is why
[../DECISIONS.md](../DECISIONS.md) D3 says the tier ceiling is a per-platform fact rather than a
marketing claim.

**2. User-namespace restrictions.** Some hardened distributions disable unprivileged user namespaces.
`oniux` then needs different privileges, or the fallback (hand-rolled namespace wiring) does.

**3. Isolating the wrong process.** If the agent, the rewriter, and the gateway are three processes,
all three need to be inside the boundary — or the ones outside become the leak. This is why the
architecture treats the namespace as containing the data plane as a whole, not one binary.

**4. Isolation is not anonymity.** A perfectly isolated connection to a provider that knows you
personally is still a connection the provider can attribute. Isolation addresses *how traffic leaves*,
nothing else.

**5. False confidence from rung 1 and 2.** `torsocks` feels like isolation and is not. This is the
single most common misunderstanding in this space, and the reason this project rejects it as a
boundary and keeps it only as a debugging convenience.

## What this means here

- **Decision D3:** Linux gets kernel-enforced isolation; other platforms get a lower ceiling, stated.
- **The isolation choice:** `oniux` where available, hand-rolled `unshare -n` as fallback, `torsocks`
  never as the boundary. See [../LAYER-OPTIONS.md](../LAYER-OPTIONS.md) §2 for the full comparison.
- **Milestone M5** and success criteria `SC1`, `SC6`, `SC9` in [../EVALUATION.md](../EVALUATION.md) are
  where these claims become tests, including the canary-based no-persistence audit.

## Self-check

1. Your agent has `HTTPS_PROXY=socks5://127.0.0.1:9050`. Name two distinct ways traffic could still
   leave with your real IP.
2. Why is `oniux`-style namespace isolation *categorically* stronger than `torsocks`, rather than just
   more convenient?
3. Your prompts are never written to disk. A burglar steals your laptop, powered off, full-disk
   encryption disabled. What do they learn about your AI conversations, and what changes if the laptop
   is awake and unlocked?

<details>
<summary>Answers</summary>

1. Any two of: **local DNS resolution** (the destination leaks to your resolver even though TCP is
   proxied); **IPv6 fallback** (proxied IPv4, direct IPv6); a **library that ignores the variable**; a
   **component you forgot** (updater, crash reporter, telemetry); or a **deliberate direct path** such
   as a rewriter configured to a remote URL.

2. Because the containment is enforced by the kernel rather than by cooperation. `torsocks` intercepts
   libc calls, so anything that *does not go through libc* — a statically linked binary, or a syscall
   made directly — bypasses it entirely, and the application still has access to the host's real
   network interfaces. A network namespace removes the alternative path rather than watching it: there
   is no interface to leak through, and the app cannot acquire one. "Cannot leak" versus "probably
   won't leak" is a categorical difference, not a degree of quality.

3. Powered off, with no disk encryption: they learn **essentially nothing** about your conversations
   from the AI tooling, because raw prompts are never written to disk — that is a genuine, deliberate
   benefit of the memory-only design. Awake and unlocked: they learn **everything** — prompts are in
   memory, and are likely on screen. This is exactly why the threat model lists a local attacker as
   `Exposed` and does not pretend the no-persistence property is a defence against one.

</details>

---

*Next: [07 — The tradeoff triangle](07-the-tradeoff-triangle.md)*
