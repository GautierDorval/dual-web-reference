# Discovery and linking

[Français](../fr/decouverte-et-maillage.md) · [Repository home](../../README.md)

A file of the layer can be reached in several ways. This page lists those routes, says what [links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv) records about them, and separates three things that are easy to confuse: a path that is available, a path that was executed, and accesses counted in aggregate.

## Routes to a file

- **HTML anchors**: `<a href>` links in ordinary pages of the site.
- **Link relations and headers**: `<link rel>` elements in the head of an HTML page, or HTTP `Link` response headers, when a site uses them. The llms.txt proposal itself suggests such relations to point to Markdown versions of pages and to the llms.txt file that covers them.
- **Markdown links and plain addresses**: links and bare URLs written in Markdown, text or YAML files, llms.txt included.
- **JSON references**: addresses written as values in JSON or JSON-LD files, either plainly or under a key that declares a relation (`sameAs`, `canonical`, `source`, `related`, `index`, `manifest` and similar keys).
- **Sitemaps**: `<loc>` entries of XML sitemaps.
- **Direct knowledge of a URL**: a client can request an address it already knows, from an earlier visit, a list, a conventional location such as `/llms.txt` or `/.well-known/`, an external page or a person who pasted it, without following any link of the site.

## llms.txt as one entry point among others

llms.txt is one possible orientation resource. It is a proposal (see [llms-txt-studies.md](llms-txt-studies.md)), not a protocol that a client must read first. On the three sites it points to other governance files, but those files can also be reached from HTML pages, manifests and indexes, JSON references and sitemaps. File names are implementation choices of each site.

Two inferences are therefore not available. A request to another file does not show that it was found through llms.txt. And the absence of a request to llms.txt on a given day does not prove that it played no role before.

## What links.csv records

Each row of links.csv is a reference written in a file of the source snapshot of a site. It gives:

- the source and the target (site, path and resource identifier);
- the relation type: `html_anchor`, `markdown_link`, `plain_url_mention`, `json_reference`, `declared_relation` or `sitemap_entry`;
- the identifier and date of the graph snapshot;
- the evidence line (first occurrence in the file) and the number of occurrences;
- a note, such as the JSON key that holds the address.

Extraction is deterministic and reads files only. In HTML it records `<a href>` anchors; head `<link>` elements are not extracted in this edition, and HTTP headers are not part of a source snapshot. References to sites outside the three are not kept. Repeated references with the same source, target and type are merged into one row with an occurrence count.

What links.csv does not record:

- **Not a followed path.** A row means “this reference is written in this file of this snapshot”. It is not evidence that any client followed it.
- **Absence means “not found in this graph”.** A missing row does not mean that no reference exists elsewhere: in another page, on an external site, in a header or in an earlier version of the file.
- **No weight.** The table does not rank links or say which one a client would prefer.

## Available path, executed path, aggregated accesses

- **Available path**: a chain of references written in files, as recorded in links.csv. It shows what a reader can follow. The case pages list such paths, with each step verified in the snapshot.
- **Executed path**: the sequence of requests that a given client actually made. Establishing it needs a qualified execution trace for that client. None is part of this edition, and none is reconstructed from counts.
- **Aggregated accesses**: totals per URL over the window, daily totals per site and population, and daily totals per documentary family for automated provider-origin roles. They cannot be chained into a path: two linked files both requested during the same month does not show that one led to the other.

## An HTML-first path: pagup.com

The [pagup.com case](../../cases/pagup.com/README.md) starts from the AI policy page, an ordinary HTML page linked from the home page. From there, written references lead to the canonical index, the identity file, the site context, the scope declarations and the source precedence file, without going through llms.txt. The case shows that the layer can be entered from ordinary pages. It does not show that any client took this route.

## Snapshots are not the state of September

The graph is extracted from the source repositories of the sites at a snapshot date: 2026-10-14 for gautierdorval.com, 2026-10-06 for pagup.com and better-robots.com. Several files of gautierdorval.com changed during the window, and a merge does not deploy anything. The sitemaps of today are not those of September: a `sitemap_entry` row shows what the snapshot lists, not what a crawler could read on a given day of the window. For pagup.com the snapshot is a build, so its sitemap `lastmod` values come from the build. The historical version of each resource is recorded as unknown.

## Why no coverage ratio against today's inventory

One could divide the number of files requested by the number of files in the inventory and call the result the share of the layer that was reached. An inventory-wide reach ratio is not computed. The separate ratio 174/269 uses only main-population site-path pairs with recorded rows across all actors, methods and statuses. It is conditional on those records, not the complete historical inventory. The inventory (the scope registry and resources.csv) reflects the state at registration and snapshot time, after the window. Some resources are registered now without any row in the window (column `window_rows_status`), others may have existed then and changed since, and daily coverage is declared partial. The numerator and the denominator would not describe the same set of files at the same time. The repository publishes counts per site-path pair instead.
