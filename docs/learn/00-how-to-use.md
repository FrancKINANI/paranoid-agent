# Learn — Understanding This From First Principles

This directory exists because you asked for it, and the reason matters.

You said you do not want to build anything until you understand it — that you want to avoid the
pattern where AI writes code and nobody can explain why it works, or what it fails to protect. That
instinct is correct, and in this subject it is not optional. Privacy engineering is the rare field
where **a system that works perfectly can still be completely useless**, because the thing being
defended is not a function of the code. It is a relationship between the code and a specific
adversary. If you cannot name the adversary, you cannot evaluate the system, and no amount of
passing tests will tell you whether you are safe.

So: concepts first. The decisions that actually shape this project (U1–U6 in
[../DECISIONS.md](../DECISIONS.md)) are judgement calls about **what you are willing to pay** and
**who you are hiding from**. Those are yours to make. This material is designed to give you the
tools to make them in a few hours of reading, and to make them in a way you can defend.

---

## The method

Each lesson has the same five parts:

| Part | What it does |
| --- | --- |
| **The question** | The concrete thing the lesson answers, stated plainly |
| **First principle** | The underlying idea, in one or two sentences, before any mechanism |
| **How it actually works** | The mechanism, with a worked example |
| **Where it breaks** | Where the mechanism fails — the part marketing material omits |
| **What this means here** | How the project uses it, and which decision it unlocks |

Each ends with **self-check questions**. Answer them without looking. The point is not the answer;
it is knowing whether you would catch a confident, wrong claim — which is the skill that protects
you from vibecoding in this domain.

---

## Reading order

Read them in sequence the first time. Each lesson assumes the previous one.

| # | Lesson | You will be able to |
| --- | --- | --- |
| 01 | [What "private" actually means](01-what-privacy-means.md) | State any privacy claim as a claim against a named adversary, and know why "anonymous" alone is meaningless |
| 02 | [Anonymity networks: how Tor works](02-anonymity-networks.md) | Explain what each Tor relay learns, why conversations need isolation, and why `NEWNYM` is the wrong tool |
| 03 | [Traffic analysis and mixnets](03-traffic-analysis-and-mixnets.md) | Explain why random cover traffic is weak, what constant-rate traffic buys, and what a mixnet costs |
| 04 | [Unlinkable payments](04-unlinkable-payments.md) | Explain how a zero-knowledge payment works, and why its real security parameter is the size of the crowd |
| 05 | [Content privacy and rewriting](05-content-privacy.md) | Explain why network privacy does not hide your words, and why PII-type scrubbing fails in both directions |
| 06 | [Isolation and the endpoint](06-isolation-and-the-endpoint.md) | Explain why a proxy setting is not a boundary, and how namespace isolation differs |
| 07 | [The tradeoff triangle](07-the-tradeoff-triangle.md) | Reason about privacy versus latency, bandwidth, money, and answer quality |
| 08 | [Decision worksheet](08-decision-worksheet.md) | Answer U1–U6 yourself, with the consequences laid out |
| 09 | [Glossary](09-glossary.md) | Read any of the other docs without stopping to look things up |

---

## How this connects to the rest of the repository

- [../PROBLEM.md](../PROBLEM.md) is what we know, assume, and do not know — written as facts with
  dates. Read `§2` after lesson 01 and you will recognise the structure.
- [../THREAT-MODEL.md](../THREAT-MODEL.md) is the same thinking applied rigorously. It is the
  document to imitate whenever you evaluate any privacy tool, including this one.
- [../LAYER-OPTIONS.md](../LAYER-OPTIONS.md) is where each lesson's conclusion becomes a choice of
  component, with the rejected alternatives listed.
- [../DECISIONS.md](../DECISIONS.md) is where your answers to U1–U6 get recorded.

---

## One warning before you start

The most confident claims you will encounter about privacy are the least reliable. Phrases to
distrust on sight, in this project's docs as much as anyone's:

- **"Anonymous"** with no adversary named. Anonymous against whom?
- **"Military-grade encryption."** TLS is TLS; the hard part was never the cipher, it was the
  metadata.
- **"We don't store your data."** Storage is cheap; logs, backups, caches, and third-party
  processors are where the data lives, and the statement is usually about the marketing copy rather
  than the architecture.
- **"Decentralised, therefore private."** Distribution removes a single point of failure, not
  observability. A public ledger is decentralised **and** permanent.
- **A throughput or latency number from the vendor**, with no benchmark described.

Lesson 01 gives you the tool that dissolves all of these: name the adversary, name what they
observe, then judge.

---

## A note on the material's own reliability

These lessons were written from the sources in [../SOURCES.md](../SOURCES.md), and they are
deliberately explicit about where a claim is a design intent rather than a measured property. If you
find a place where this material asserts something absolute without an adversary attached, that is a
bug worth reporting — the same standard we hold the rest of the repository to.

---

*Start here: [01 — What "private" actually means](01-what-privacy-means.md)*
