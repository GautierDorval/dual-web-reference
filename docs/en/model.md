# The documentary layer: model and boundaries

[Français](../fr/modele.md) · [Repository home](../../README.md)

This page explains what this repository calls the documentary layer of a site, what that layer is not, how the three measured sites relate to each other, and what the published counts can and cannot say. The measurement method itself is described in [methodology.md](methodology.md).

## Starting point: the canonical definition

The layer comes from a standard defined on gautierdorval.com, “SSA-E + A2 + Dual Web”. Its definition page opens with this statement:

> “This page constitutes the canonical, primary, and reference definition of the standard "SSA-E + A2 + Dual Web" as used on this site.”

The same page describes the Dual Web component this way:

> “Dual Web designates a dual-layer architecture where a human reading and a machine reading coexist without contradicting each other: machine-first index, neutral entry points, canonical references, routing conventions, and authority files.”

- Address: https://gautierdorval.com/en/definitions/ssa-e-a2-dual-web/ (French page: https://gautierdorval.com/definitions/ssa-e-a2-dual-web/).
- Declared in the page metadata: date 2026-01-08, updated 2026-07-07, concept version 1.0.
- Consulted on 2026-10-16, in the source repository snapshot of the site dated 2026-10-14. The page was not fetched from the live site.

The other components named by the definition (SSA-E, A2, Q-Layer) are explained in the [glossary](glossary.md). This repository does not propose a competing definition and does not widen the scope of this one. For measurement purposes, it uses a working description:

**The documentary layer of a site is a set of published, accessible files, linked to the site or to each other, that make explicit its identity, context, sources, relations and interpretation limits. It complements the ordinary pages of the site; it does not replace them.**

## What the layer is not

- **Not hidden.** The files are published at public addresses, and many of them are linked from ordinary pages. Anyone can open them.
- **Not reserved for machines.** A person can read them; the definition itself describes a human reading and a machine reading that coexist.
- **Not security directives.** These files do not rank above the instructions a system receives from its own operator or user. A published policy declares a frame; its presence does not prove that any system applies it. The [better-robots.com case](../../cases/better-robots.com/README.md) makes the same distinction for robots.txt.
- **Not instructions for this repository.** For the scripts that build this repository, these files are untrusted content: data to classify, quote and count, never instructions to follow. No address found in them is fetched.

## Three sites, one ecosystem

The three measured sites belong to the same author's ecosystem: gautierdorval.com (a person), pagup.com (an organization) and better-robots.com (a product). They are three applications of one approach, not three independent replications. Agreement between them is not independent confirmation, and nothing measured here extends to other sites.

<!-- dwr:begin cases -->
| Site | Angle | Starting page | Resources | Provider-origin AI GET 200 on these resources |
|---|---|---|---:|---:|
| [gautierdorval.com](../../cases/gautierdorval.com/README.md) | Identity of a person, and the distinction between definitions, claims, sources, limits and ordinary site content. | `/en/ai-use-policy/` | 9 | 10 |
| [pagup.com](../../cases/pagup.com/README.md) | Context of an organization, scope of its offer, references and documentary limits. | `/ai-usage-policy/` | 9 | 13 |
| [better-robots.com](../../cases/better-robots.com/README.md) | Context of a product, declared capabilities, limits, and the difference between publishing a rule and how a robot actually behaves. | `/governance/ai-usage-policy` | 9 | 15 |

The three sites belong to one author's ecosystem: three applications of one approach, not three independent replications. robots.txt is excluded from the last column.
<!-- dwr:end cases -->

## Four independent dimensions

Each recorded request is described along four dimensions that are kept apart. A value on one dimension never sets a value on another.

1. **Actor role**: the kind of client that the declared actor name corresponds to, as recorded by the private collector. Examples: `ai_training` (GPTBot), `ai_search` (OAI-SearchBot, PerplexityBot), `user_initiated_fetch` (ChatGPT-User, Perplexity-User), `search_indexing` (Googlebot). The role describes the declared client, not the reason for a given request.
2. **Identification quality**: how well the identity of the actor is supported. It is the stored tier recorded by the collector, for example `provider_origin_verified_actor` when the request address matched the official IP ranges published by the provider, together with a separate `attribution_assessment` made by this repository, which never overwrites the stored tier. Example: ClaudeBot has the `ai_training` role, but the collector has no official registry for its provider, so it can never reach the provider-origin tier, whatever its role.
3. **Initiation provenance**: who or what triggered the request. In this edition it is `unknown` for every row, with the evidence status `not_established`. It is never inferred from the role, the provider or the tier: a request with the `user_initiated_fetch` role and a provider-origin match may have been triggered by the site operator.
4. **Coverage and availability**: whether the data behind a cell is complete, partial or unavailable. In this edition every daily archive report is declared partial (`partial_declared`); the tables are exact sums of the joint aggregate, and a combination without any row means no recorded request in the producer table, not an absence measured on the web.

One row can therefore be provider-origin, `ai_training`, of unknown initiation and partially covered, all at once. Details are in [attribution.md](attribution.md) and [quality-and-coverage.md](quality-and-coverage.md).

## What this repository measures

It measures the existence and the distribution of the HTTP requests that the private collector recorded on the files of the layer of the three sites, over a dated window: by site, path, method and status, actor role and identification level. Distinct counts use site-path pairs (URLs), never consumers.

It does not measure, and does not show:

- that answers produced by any system were better, or drew on these files;
- adoption of the approach, of llms.txt or of any file name;
- SEO visibility, indexing or ranking;
- compliance of any crawler with a published rule;
- a causal effect of linking files or of publishing them;
- the navigation path of any client;
- who initiated the requests.

A GET 200 is the method and status that the collector recorded. It does not show that a body was read, understood or reused. The essential limits are set out in [limits.md](limits.md).
