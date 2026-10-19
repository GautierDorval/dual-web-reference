# Limits

[Français](../fr/limites.md) · [Repository home](../../README.md)

Each limit below names what it restricts, then states what is established, what is not, and what the limit does not allow anyone to deny. The last point applies a simple rule: the absence of evidence in these tables is not evidence of absence.

## 1. Attribution

Restricts: to whom the requests can be attributed.

- **Established**: the tiers and roles stored by classifier 2026-08-24.1. The provider-origin branch requires a declared actor with an official registry and a match with that provider's official IP ranges, and it is evaluated before the Cloudflare predicate under review.
- **Not established**: the reliability of the two levels that depend on that predicate (`network_verified_claimed_actor`, `cloudflare_verified_unattributed`). Raw Cloudflare signals were not stored, so these levels cannot be evaluated again. Reproducing the defect locally does not show that an empty category was received in production. The provider-origin qualification is a separation of code paths, not an audit of the whole chain: registry correctness, the origin of the IP header when one Worker calls another, and deployment metadata are not audited end to end.
- **Does not allow denying**: that some requests recorded as unattributed came from AI systems, monitoring tools, browsers or false positives; nothing is redistributed among them. That no request in the window carries `unknown_automation` or `claimed_actor_unverified` is compatible with the defect; it does not prove it. Details: [attribution.md](attribution.md).

## 2. Discovery routes

Restricts: how a file was found.

- **Established**: the references written in snapshot files, by type, file and line ([links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv)).
- **Not established**: the route that any client used; head link relations and HTTP `Link` headers, which are not extracted; references on other sites; addresses known beforehand.
- **Does not allow denying**: that a file was found through llms.txt, an external page or a URL already known; nor that llms.txt played a role on days without any request to it. See [discovery-and-linking.md](discovery-and-linking.md).

## 3. Snapshot versus deployed bytes

Restricts: which content was served.

- **Established**: the content of each file in the source snapshot (2026-10-14 for gautierdorval.com, 2026-10-06 for pagup.com and better-robots.com), and the case excerpts verified against it.
- **Not established**: the bytes served on each day of the window. A merge does not deploy, several files of gautierdorval.com changed during the window, the historical version of each resource is unknown, and the pagup.com snapshot is a build.
- **Does not allow denying**: that a file requested in September had a different content from the one reviewed, or would then have received another class.

## 4. Partial coverage

Restricts: the completeness of the counts.

<!-- dwr:begin coverage -->
30 of 30 days have archived rows; 30 declared partial. Daily aggregate and V3 margins are withheld, not zero. Historical r1 preserves its two one-request gaps (October 6 and 13). The same observations are used; partial coverage has not been upgraded.
<!-- dwr:end coverage -->

- **Established**: archived rows for the days of the window, and agreement of the exports and of the joint aggregate with the archive.
- **Not established**: completeness. Agreement with the archive is not an independent validation, since both come from the same chain.
- **Does not allow denying**: that requests occurred without being recorded. A recorded zero (`observed_zero`) is not proof of absence. See [quality-and-coverage.md](quality-and-coverage.md).

## 5. The joint aggregate is a reading of the producer table

Restricts: what the exact cells can show.

- **Established**: exact cells day × site × path × method × status × actor × tier, read once and read-only from the producer table, with identical checksums before and after the read, and agreement with the exports for every path, actor group, day and combination of method and status. The split by role of the main population, its daily series, its recurrence and the heat map G06 follow from these cells.
- **Not established**: an independent validation. The joint aggregate and the exports are two readings of the same producer table; identical checksums show that the counters did not change during the read, not that the read is a transactional snapshot. A public reader cannot re-run the extraction.
- **Does not allow denying**: requests that the producer did not record. A combination without any row means no recorded request in the producer table, never a measured absence on the web. See [methodology.md](methodology.md).

## 6. One author's ecosystem

Restricts: generalization.

- **Established**: three applications of one approach, on a person, an organization and a product.
- **Not established**: independence between the three sites, or anything about other sites, other authors or the web at large.
- **Does not allow denying**: that other sites show other distributions, higher or lower.

## 7. Requests possibly triggered by the operator

Restricts: the interpretation of who initiated a request.

- **Established**: initiation provenance is `unknown` for every row (`not_established`).
- **Not established**: who triggered each request. A provider-origin request, even with the `user_initiated_fetch` role, may have been triggered by the site operator, for example while testing an assistant on the site.
- **Does not allow denying**, or asserting, that part of the requests were triggered by the operator. Unknown traffic never becomes operator traffic for lack of another explanation, and coincidences in time are clues, not matches with requests. The reading without user-initiated fetches is a sensitivity analysis, not evidence of independence.

## 8. No executed paths

Restricts: what can be said about navigation.

- **Established**: available paths (references written in files) and aggregated counts per URL.
- **Not established**: any sequence of requests made by a given client.
- **Does not allow denying**: that clients followed the available paths, or other ones.

## 9. GET 200 is a recorded status

Restricts: what a success means.

- **Established**: the collector recorded the GET method and the status 200.
- **Not established**: the bytes served (not verified again); that the body was parsed, read, kept or used; any answer produced from it.
- **Does not allow denying**, or asserting, that the content was used.

## 10. Privacy grains

Restricts: the level of detail that is published.

- **Established**: r1 preserves its historical grains; r2 follows a privacy revision defined after results, documented in [small-cell-policy.json](../../config/small-cell-policy.json). No IP address, user agent, cookie, session or device identifier, token, free referrer, query string, transcript, or first and last access dates per cell or per path. Day-level outputs never carry a path or an actor name.
- **Not established**: universal non-reconstruction. Combining marginals or revisions can reveal aggregate detail. The historical policy was approved on 2026-10-17; the corrected policy remains a local candidate.
- **Does not allow denying**: patterns that would only appear at a finer grain. See [privacy.md](privacy.md).
