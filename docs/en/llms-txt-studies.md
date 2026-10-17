# Published studies on llms.txt

[Français](../fr/etudes-llms-txt.md) · [Repository home](../../README.md)

Studies of llms.txt are sometimes read as measurements of the documentary layer as a whole. This page sets one published study beside this repository, keeping the scope, sample and denominator of each.

## The llms.txt proposal

- Source: llmstxt.org, “The /llms.txt file, v2”, by Jeremy Howard; published 2024-09-03, page modified 2026-08-10, consulted 2026-10-16. https://llmstxt.org/
- The page calls itself “A proposal to standardise on using an /llms.txt file to provide information to help agents use a website.” It states that the specification is open for community input.
- Its purpose is a Markdown file that gives a curated overview and links, mainly for use when a system answers (inference) rather than for training. Version 2 also allows the file at a subpath of a site, and suggests Markdown versions of pages and link relations to find them.

It is a proposal, not an adopted standard. In this repository, llms.txt is one possible orientation resource: it belongs to the main documentary population and is always reported separately ([discovery-and-linking.md](discovery-and-linking.md)).

## The Ahrefs study

Reference: “We Analyzed 137K Sites: 97% of llms.txt Files Never Get Read”, by Louise Linehan (contributor Xibeijia Guan), Ahrefs blog, published 2026-06-15 (metadata modified 2026-08-27), consulted 2026-10-16. https://ahrefs.com/blog/llmstxt-study/

| Item | As stated by the study |
|---|---|
| Population | All 137,210 domains in Ahrefs Web Analytics with traffic in May 2026: Ahrefs customers, not a random sample |
| Window | May 2026; exact bounds and timezone not stated |
| Source of requests | Ahrefs Bot Analytics, through server-side integrations |
| File measured | A valid `/llms.txt` at the root of the domain |
| 28% | Share of domains that publish a valid root `/llms.txt` (about 38,000 domains): a share per domain |
| 97% | Share of those files that received zero requests in May: a share per domain |
| 96% bots, 19.5% named AI bots | Shares of requests, computed over about 22,000 requests on about 1,100 domains: shares per request, on a different denominator |

The study itself notes that its customer base leans technical and that a fetch is not a read, so its figures are ceilings.

## How this repository differs

| Aspect | Ahrefs study | This repository |
|---|---|---|
| Perimeter | One file, the root `/llms.txt` | A multi-file documentary layer (`core_governance` and `discovery_index`), with llms.txt reported separately |
| Sample | 137,210 customer domains | Three sites of one author's ecosystem |
| Window | May 2026 | 2026-09-15 to 2026-10-15, end exclusive, UTC |
| Identification | Requests classified by user agent | Stored tiers; the main stratum requires a provider-origin match with official IP ranges |
| Main share | Per domain | Per request: `other_share` is the GET 200 requests to files other than llms.txt divided by all GET 200 requests of the same selection |

Our results and their selection are described in [methodology.md](methodology.md). `other_share` describes how recorded requests are distributed; it is not an adoption rate or a measure of efficacy.

## What can be said

> A study centred on /llms.txt does not measure a multi-file documentary layer; our results describe a complementary perimeter on three sites linked to the same author.

## What must not be concluded

- that the Ahrefs study shows that no one consults these files;
- that the figures of the Ahrefs study are false;
- that the three sites contradict its 97% figure: positive cases in one sample do not invalidate a low-frequency statistic measured in another sample;
- that this repository is the first of its kind, or that AI systems have taken up llms.txt or any other file name as a standard;
- that a share per request from this repository and a share per domain from the study can be compared as if they had the same denominator;
- that a request to a file shows that the file was read or used, in either study.
