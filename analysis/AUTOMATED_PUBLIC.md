# Automated public distribution adapter

The M2 profile B preparation remains sealed separately. The distribution adapter retains its canonical projection, seven tables, metrics, on-demand state, schema and eight figure sets. It replaces the preparation catalog and manifest with a distribution catalog and manifest, and does not distribute the two private preparation reports. The resulting closed payload contains 54 files.

The immutable projection records preparation state. Current availability, reference approval and scientific review live in `config/editions.json`. `data/latest.json` version 2 adds `latest_candidate_edition` while preserving the meaning of `latest_published_edition`: only a publicly accessible reference with a valid matching receipt can be selected.

The new `config/automated-distribution.json` manifest is pinned separately in `distribution.py`. A registry entry cannot learn new distributable bytes. Historical inventory and frozen edition hashes are unchanged. Historical Git trees without M2 still use the existing closed contract; an M2 entry requires the pinned new contract. Local distribution admission is not owner publication authorization.

The public replay regenerates exact bytes from the canonical projection. The public schema and arithmetic cannot establish source authenticity independently. The private qualification supplies separate evidence, without copying acquisition receipts, diagnostics or their hashes into the public payload.

M1 pages retain their own period and population. The M2 explorer, figures and bilingual method page use the profile B schema. No cross-month growth, M2 source graph, new data acquisition, external asset or measured-origin request is introduced.

The explicit `preparation_anchor` remains M1 r2. The displayed M2 candidate does not advance a private source cursor. A workspace's existing cursor takes precedence; a fresh private workspace seeds its data date from the anchor's catalog. Moving the anchor is a separate, deliberate preparation decision, not a side effect of rendering a new candidate. Legacy M1 writers refuse an automated edition before mutation.
