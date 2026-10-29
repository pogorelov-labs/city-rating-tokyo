# Bangkok rent evidence in the Telegram corpus — CRTKY-208

Researched **2026-10-29**. Research only; adoption belongs to **CRTKY-136**.

**Independent corpus refutation completed; no threshold-crossing cohort was established under the tested screens.**

## Decision and metric

This audited extraction has **not established a releasable recent, area-specific
reference-rent cohort** for the twelve priority areas. It contains useful claimed
paid rents and offers, but missing unit/location/term fields and incompatible
products prevent a numerical replacement or validation of the existing inputs.
This is a bounded finding about the snapshot and method below, **not proof that
no relevant messages exist**.

Keep the existing district estimates and station overrides unchanged. The current
corpus evidence is a **qualitative cross-check**. An eventual numerical layer
would have an **estimate-confidence ceiling on this evidence**, rather than
strong confidence or transaction-price status. A larger message count does not
make an incomplete tenancy observation complete.

The reference is **base asking rent, THB/month, for an ordinary condo with an
explicit 1BR of roughly 30–35 m² or 2BR of roughly 60–70 m²**, excluding serviced
apartments and short stays. Reported paid/agreed lease prices are a separate
metric. No receipts or contracts were verified in this study.

A conservative core long-stay cohort requires an explicit term of at least six
months or an unequivocal long-term occupancy claim. This is an operational
comparison rule, not a legal definition. Monthly ordinary-condo claims with
unknown tenure are retained separately. Broader size/tenure readings do not
supply missing bedrooms, geography or independent observations and do not create
a publishable cohort in this audit.

## Snapshot, instrument and scope

All reads filtered `deleted_at IS NULL`. This means non-soft-deleted **local
corpus records**, not proof of current visibility or availability on Telegram.
No Telegram fetch, participant enumeration, corpus writes, chunking, indexing,
backfill or corpus re-embedding was performed.

| Measurement | Observed value | Definition / provenance |
|---|---:|---|
| Local messages | 8,396,280 | Exact all-source inventory; sum of per-source counts, 2026-10-29 |
| Sources | 35 | 29 chats and 6 channels; registry reconciliation also found 35 registered, all nonempty at the cutoff; not the orientation's 32-source shorthand |
| Latest raw message | 2026-10-26 | `max(ts)` of the non-soft-deleted snapshot; no claim about later Telegram activity |
| Literal city probe | 44,327 | Case-insensitive substring `бангкок`, all enumerated sources |
| Crude rent co-mentions | 2,975 | Same city set AND `аренд|кондо|снимаю|снимал`; reproduces the supplied orientation exactly |
| Bank-name co-mentions | 193 | Within those 2,975, a Bangkok Bank name pattern also matches; this is a contamination warning, not an automatic non-rent label |
| Broad lexical candidates | 17,105 | Core-source housing/money handles OR housing handles with the city/gazetteer; no SQL LIMIT |
| Hybrid supplement | 1,252 | Raw message/context rows from six queries, twelve hits/query; not a random sample or 1,252 rent observations |
| Added by hybrid supplement | 1,150 | Distinct local message IDs absent from the lexical set |
| Incremental alias pass | 26 | Additional records absent from the preceding message/context sets |
| Direct candidate union | 18,281 | 17,105 + 1,150 + 26; reply ancestors are context, not additional lease observations |
| Monetary/context screen | 403 | Union of price/housing, relevant reply-context and foreign-currency narrative candidates; not a simple nested funnel from all amount matches |
| Exact long-copy families in screen | 10 | 11 redundant long-text copies; not ten tenancy families |
| Forward / album contexts | 3 / 7 | Within the 403-context screen; retained as provenance flags, not independent resident observations |
| Independent size-wording control | 37 | Core-source query for reference-band numbers plus `м²/м2/кв/метр/sqm`; nine records were not previously retrieved |

Source: read-only local Postgres **17.10**, `en_US.UTF-8`; direct Cyrillic
case-fold and PostgreSQL word-boundary checks passed. The first diagnostic used
an unavailable locale setting and failed before extraction; it was corrected to
read database locale metadata. The literal probe above is the known-answer
check. This is not a labelled retrieval evaluation and supplies no precision or
recall score.

The analysis used one dedicated Bangkok discussion source and one rental-listing
source as core sources, plus city/place matches across **all** enumerated
sources. Requiring every post to repeat “Бангкок” would miss local replies. Chat
identity alone does not prove that an anecdote's property is in Bangkok: island,
other-country and metro-area examples occur in the same conversations. Historical
completeness of every source was not established; `synced` is not proof of
completed backfill. Media-only prices and OCR were outside this pass.

The six generic query texts were fixed before reading candidate posts. Their
embedding request contained **273 query tokens**, no corpus message text, using
`text-embedding-3-large` at 1,024 dimensions. The actual reranker was
**Flashrank**, after the cached BGE backend failed to load in offline mode. The
helper fetched approximately 99 MB of fallback weights. No claim that BGE ran or
that the reranker establishes answer truth is made. The vector index had
368,522 embedded chunks through October 25 and 306 chunks without embeddings,
with raw/chunk activity through October 26. Dense retrieval therefore had a
freshness limit; the raw lexical and size-control reads remain important.

## Geography and extraction

The gazetteer seeded all **50 khet** from the public district EN/TH/RU names and
all **133 station-area** EN/TH names at the pinned city-rating input. It added
Russian colloquial/inflected central-station variants and common project names.
Additional spellings were logged as an exploratory alias pass, not presented as
a prospective retrieval benchmark.

Examples of the discovery lexicon include Тонгло/Тхонгло/Тонглор/Thong Lo,
Эккамай/Экамай/Ekkamai, Пхромпхонг/Промпонг/Phrom Phong, Асок/Асоке/Asoke,
Нана/Нане, Читлом/Chidlom, Сала Даенг/Sala Daeng, Чонг Нонси/Chong Nonsi,
Сатхон/Саторн/Sathorn, Ари/Aree, Ратчатхеви/Ratchathewi, and Пая Тай/Phaya Thai.
Condo names are **retrieval anchors**. They do not establish a poster's floor
plan, administrative district or membership in an 800 m station catchment.

Public project checks reinforce that distinction:

- [AP's Life Asoke–Rama 9 brochure](https://www.apthai.com/images/production/zB8SXHVzYtABk71XgDyfgBoAlniSh4-metaTGlmZS1Bc29rZS1SYW1hOS5wZGY%3D-.pdf)
  locates that project near **MRT Phra Ram 9**. The word “Asoke” in its name
  cannot assign a report to BTS Asok.
- [Mitsui Fudosan's IDEO Mobi Sukhumvit 66 page](https://www.mitsuifudosan-asia.com/th/project-detail/n_003.html)
  identifies **BTS Udom Suk** and Bang Na. It cannot corroborate a central
  Sukhumvit station merely because the project name contains Sukhumvit.
- [Sansiri's official oka HAUS news page](https://www.sansiri.com/en/news/oka-haus-a-thailand-property-investment-that-lets-you-live-a-natural-life-89/)
  describes Sukhumvit 36 between Sukhumvit and Rama IV roads near Thonglor BTS.
  That marketing description does not establish an 800 m station cohort.
  An alternative project-page route returned 404; Major Development's Aguston
  project route had a redirect loop. Those failed routes were not used to
  validate catchments, and unspecified unit fields remain unknown.

These are developer location descriptions, not independent surveys. They were
used for disambiguation, not rent values. The same caution applies to ICONSIAM
versus Siam station, the Lumpini project brand versus Lumphini station/park,
Phaya Thai hospital/district/station, and place names inside addresses of banks,
consulates or government offices.

The monetary parser checks `к/k/т/тыс/тыщ`, separated/thin-space thousands,
THB/бат/baht and currency prefixes. Amounts are bound to a **clause and role**:
base rent, deposit, utility/service payment, fine/fee, purchase, budget or
unresolved. A range is not turned into its midpoint, a nightly rate is not
multiplied into a monthly lease, and an ambiguous two-month total is not divided
by assumption. No USD/EUR/RUB-to-THB conversion was made. Contextual THB is
flagged separately from explicit THB; it cannot override contrary currency clues.

Known-answer guards caught distance `км`, bare calendar years, thin-space
numbers, abbreviated rubles, currency prefixes, object/postal codes, and
facility/bill words near a rent amount. Role proximity alone was insufficient.
Russian `однушка/двушка/две комнаты` was not silently mapped to 1BR/2BR; explicit
bedroom wording or independently clear unit context is needed. Desired features
in another speaker's question are not the respondent's unit metadata.

Reply ancestors were fetched up to three levels for selected money/payment
candidates, with additional direct-parent resolution for ambiguous cases. Full
texts and available context were read for retained specific claims; long obvious
non-rental material was screened through source/amount windows. Thirty-five of
the 403 contexts remain price-basis unresolved and were not used as observations.
The ledger distinguishes active/self-reported paid, completed/agreed,
third-party report, unaccepted negotiation, current offer, quoted portal price,
market opinion and request/budget. “Отдают за” is not proof of payment.

Raw message IDs were used only to union retrieval arms privately. Long copied
texts, forward origin/date and album membership were inspected. Same-author
repeated descriptions of an otherwise unidentified tenancy were conservatively
grouped when separate units were not established. Two near-copy relet posts and
two near-copy outer-corridor offers each described one conservative offer
family. This does not turn every repeated phrase or every post by one author
into the same unit. Rejected alternatives were kept separate from an author's
own active lease.

Of the **403 screened contexts**, 164 were non-rent payments or non-rental
material, 122 were budgets/questions/market opinions, 20 contained a
self-reported paid-rent claim, and 35 had unresolved price basis. The remaining
62 had other or mixed bases, including offers, third-party reports, quotes and
incompatible accommodation. These are **message-level classifications**:
the twenty paid-claim messages include repeats and excluded stays, not twenty
independent eligible tenants. Missing unit, location and tenure fields are still
missing after a message's price basis is classified.

## Coverage map, medians and divergence

The table is a **coverage matrix**, not a geographic estimate of market rents.
The release gate is at least **five independent eligible episodes and three
authors per area × bedroom × price-basis cohort**, plus complete metric fields.
It is a conservative analysis/privacy rule, not a statistical power or
anonymity guarantee. No target-area reference cohort reached it.

`n` below counts eligible **claimed** prices, not verified settlements. Paid and
asking are separate. Each `0/0` is **1BR / 2BR** in the recent reference cohort,
not a statement that nobody rents in that area. No cohort median, date range,
weighted median, effective sample size or percentage divergence is invented for
an empty/ineligible cohort. Its median/date range are **not estimable (—)**.

Frozen public comparisons are the inputs at
[`fc4d588`](https://github.com/pogorelov-labs/city-rating-tokyo/tree/fc4d588056f44ef6de3c8629080f17f238459db5),
not newly refreshed market figures. The [October 25 audit](2026-10-25-central-rent-audit-crtky141.md)
covers **twelve target areas, ten adopted DooAsset overrides**, with Ari and Siam
left editorial. DooAsset figures below are **all-floor-area bedroom medians**,
all estimate-confidence; editorial district figures are **typical-size asking
estimates**, not medians. THB/month throughout.

| Area | TG paid n, 1BR/2BR | TG asking n, 1BR/2BR | TG median / report-date range | DooAsset 1BR / 2BR proxy | Editorial khet 1BR / 2BR references | Divergence |
|---|---:|---:|---|---:|---|---|
| Thong Lo | 0 / 0 | 0 / 0 | — | 28,000 / 56,500 | watthana: 32,000/70,000; khlong-toei: 25,000/52,000 | Not estimable |
| Ekkamai | 0 / 0 | 0 / 0 | — | 27,000 / 50,000 | khlong-toei: 25,000/52,000; watthana: 32,000/70,000 | Not estimable |
| Phrom Phong | 0 / 0 | 0 / 0 | — | 48,000 / 52,500 | watthana: 32,000/70,000; khlong-toei: 25,000/52,000 | Not estimable |
| Asok / Sukhumvit | 0 / 0 | 0 / 0 | — | 26,500 / 55,000 | watthana: 32,000/70,000; khlong-toei: 25,000/52,000 | Not estimable |
| Nana | 0 / 0 | 0 / 0 | — | 28,000 / 60,000 | watthana: 32,000/70,000; khlong-toei: 25,000/52,000; pathum-wan: 38,000/85,000 | Not estimable |
| Chit Lom | 0 / 0 | 0 / 0 | — | 45,000 / 120,000 | pathum-wan: 38,000/85,000 | Not estimable |
| Siam | 0 / 0 | 0 / 0 | — | No override (editorial) | pathum-wan: 38,000/85,000; ratchathewi: 18,000/38,000 | Not estimable |
| Sala Daeng / Si Lom | 0 / 0 | 0 / 0 | — | 38,000 / 60,000 | pathum-wan: 38,000/85,000; bang-rak: 26,000/55,000; sathon: 25,000/55,000 | Not estimable |
| Chong Nonsi | 0 / 0 | 0 / 0 | — | 24,000 / 72,000 | bang-rak: 26,000/55,000; sathon: 25,000/55,000 | Not estimable |
| Ari | 0 / 0 | 0 / 0 | — | No override (editorial) | phaya-thai: 18,000/37,000 | Not estimable |
| Ratchathewi | 0 / 0 | 0 / 0 | — | 21,500 / 38,000 | ratchathewi: 18,000/38,000 | Not estimable |
| Phaya Thai | 0 / 0 | 0 / 0 | — | 25,000 / 43,500 | ratchathewi: 18,000/38,000 | Not estimable |

These zero complete-cohort counts do not erase broader anecdotes. The controlled
ledger retains historical/short-stay/named-project claims, a sparse broad-Sathon
relet family outside the reference size, unlocated paid claims and outer-corridor
examples. They are useful for follow-up, but do not supply a matched recent
1BR/2BR station-area panel. Unverified neighborhood language is not promoted to
a khet-wide or 800 m station statistic. All 50 khet were in the canonical search
lexicon; manual auditing prioritized the twelve areas above. No khet-wide estimate was
derived. This is not a complete census of every possible spelling or message.

The size-control positives were also instructive: they include studio utility
bills, an old viewed 1BR/size-shaped quote, hypothetical size advice, and a
foreign-currency stay. A plausible numeral and square-meter marker are not a
completed reference observation.

### Why no numerical benchmark verdict follows

The corpus does not currently validate or refute the numerical level of the ten
DooAsset inputs, including the composition-sensitive Phrom Phong 1BR,
Chit Lom 2BR and Chong Nonsi 2BR proxies. A small unlocated or differently sized
paid claim cannot establish that a neighborhood asking median is wrong.
The published proxies themselves remain estimates with the size/lease caveats
already documented; this audit does not upgrade them.

The [pinned CRTKY-141 source audit](2026-10-13-rent-anchors-crtky141.md)
did not locate public 2026 residential rent-level tables from Knight Frank,
JLL, C&W or free CBRE material. Its sale-price/yield/qualitative figures are not
rent anchors. This study did not repeat that entire consultancy search. Vurel's
September 2026 figures are broader-zone, all-bedroom condo asking medians,
self-published and not deduplicated across portals; they remain context rather
than fixed-size or paid-rent validation. No sale price, yield or all-unit median
is substituted for a 1BR/2BR observation.

## Paraphrased evidence audit: types, not personal exports

The following rows omit names, handles, identifiers, links, exact personal prices,
unit locations and individual dates. Their controlled source crosswalk stays
private. They illustrate the classification boundary, not independent samples
for computing a market median.

| Evidence pattern | What can be retained | Why it cannot set a reference rent |
|---|---|---|
| An ongoing multi-year two-bedroom lease is described | Claimed paid/active lease basis | Own neighborhood and floor area absent; vintage differs from new asking inventory |
| An annual contract and floor area are mentioned while another neighborhood is being rejected | A retrospective lease-shaped claim | Own geography and bedroom count not established; place-word join would be wrong |
| A participant repeats the same rent description across several posts | A conservative tenancy episode | Posts are not independent tenants; location of an unrelated rejected offer is not inherited |
| A personal relet states two bedrooms and a larger floor area | An asking offer family | Size outside the reference and remaining term/catchment incompatible or unconfirmed |
| One post compares a platform payment with an alternative portal price | A claimed comparison | Currency, time, fee and product mix do not yield a verified matched-unit discount |
| A month-long hotel/serviced stay is described | A separate accommodation product | Excluded from ordinary long-lease condo cohort |
| Cash amounts occur near a condo or rental-document discussion | A monetary context to inspect | Utility bills, deposits, fees, postcodes and budgets are not base monthly rent |

The commercial stratum had **120 retrieved records from one listing source**:
**116 text-bearing records and four empty context records**. Of the 116
text-bearing records, 110 had an explicit short-stay/daily marker and 115 had an
object/contact marker; the other text was promotional. The full source had
1,101 records, only 117 with any text. These are not 120 independent resident
reports or 120 observed rents. Agency/forward/copy material
was kept separate from paid claims; its mismatched terms/currency and repeated
publisher do not repair the reference panel.

## Independent refutation and reading limits

Two independent read-only AO research checks attempted to refute the adoption
finding before publication. They performed fresh queries rather than approving
a PR or treating the analyst's labels as ground truth.

- **Geography/recall check:** enumerated sources, searched alternative area and
  lease-word handles, read money/place candidates in full, and tested reply
  links. It found no threshold-crossing reference cohort. A broad Sathon relet
  family was outside the reference size, while other apparent positives failed
  place, unit, term or currency binding. Parent links must join `reply_to_id` to
  `tg_msg_id` within the chat, not to the database primary key.
- **Amount/cohort check:** independently searched size+area+housing and explicit
  bedroom combinations; re-read the 37 size controls and a **43-row narrative
  subset**. Twenty of that subset predated the recent cutoff; the cutoff is
  applied at eligibility, not discovery. This is distinct from the main
  **403-context** screen. The check found no qualifying cohort, including under
  deliberately relaxed candidate counts. A Latin `m2/m²` closing query found
  no additional recent qualifying records; recognition was added to the private
  parser for subsequent runs.

Neither check measures exhaustive recall or proves absence from all messages.
An inventory/label discrepancy in a peer summary was not adopted: the analyst
rechecked **35 registry entries**, and the **193** co-mentions refer to the
specified **Bangkok Bank** pattern, not a Siam/SCB count. Only reconciled figures
appear here. Private query scripts/results and controlled source locators retain
the verification path; raw posts are not reproduced in this public artifact.

## Bias, date decay and confidence ceiling

- **Sampling frame:** this is a Russian-language relocation/travel corpus,
  not a sample of all Bangkok tenants. Language is not inferred citizenship.
  Self-selection, willingness to report, searches for cheap stays and unusually
  successful or frustrating deals can change the price mix in an unknown direction.
- **Product mix:** ordinary condos, studios, rooms, hotels, serviced units,
  sublets, relets and annual leases coexist. Their rent levels cannot be pooled
  into the reference unit by treating every room count as a bedroom count.
- **Price basis:** a budget, an advertised ask, an unaccepted concession, a
  booking/prepayment, a claimed occupied rent and a retrospectively recalled
  payment are different facts. No receipts verify settlement.
- **Temporal mix:** a post timestamp is a report date, not automatically the
  lease-signing or current price date. Long-lived contracts may be below new
  asking inventory. Currency conversion, inflation adjustment and retrospective
  observation dates were not invented.
- **Geography:** station names, roads, projects, parks, hospitals and district
  names overlap. A message can mention the location the writer rejected, or a
  friend's different property. Even a real neighborhood is not our catchment polygon.
- **Source/independence:** reposts and recurring authors can inflate `n`;
  commercial posts can duplicate portal supply. One author's many messages are
  not a representative tenancy panel.
- **Retrieval limits:** text-only extraction, unverified historical backfill,
  an unembedded tail, colloquial vocabulary, image prices and unresolved contexts
  limit recall. No observed absence is claimed outside this snapshot/protocol.

The recent window is **2024-10-29 through the latest observed raw date,
2026-10-26**. A proposed freshness sensitivity uses
`w = 2^(-age_in_months/12)` with six- and twenty-four-month half-life checks,
based on report date and explicitly flagged when the actual price date is
unknown. Weights are not extra observations. With no releasable complete cohort,
weighted medians and `n_eff=(Σw)²/Σw²` are undefined/not released rather than zero.
Changing decay cannot fill missing unit/location fields. This pass does not
measure a population-level paid-versus-asking gap or negotiation discount.

## Adoption recommendation and CRTKY-136 prerequisites

**Do not feed new numerical rents or confidence upgrades from this audit into
the product.** Keep it as an exploratory evidence layer and a list of precisely
identified collection gaps. This is the research recommendation; adoption is an
owner decision in a separate task.

A numerical pilot would need a consent-compatible, auditable record for each
independent episode: resolved area/footprint, condo type, explicit bedroom count
and floor area, base monthly THB, price basis, utilities/deposit treatment,
actual observation/contract date, report date, lease term, and a private dedup
family. A project's other floorplans cannot fill its missing unit fields.
The public output would contain aggregates and methods, not private messages,
handles, links or author identifiers.

As an **operating proposal**, require at least ten independent recent episodes
per area × bedroom × price basis, at least five authors and three projects,
with no one source/project dominating. Use a shorter twelve-month primary price
window when the actual price date is known, compare wider windows transparently,
retain counts/missingness/dispersion, and validate the field binding independently.
These numbers are proposed release gates, **not** evidence of statistical
representativeness, an established precision target or permission to publish.
Even then, this language/community frame supports at most a labelled
estimate-grade cross-check unless a different, better verified sampling/source
basis is established. A matched-unit study would be needed to estimate a
paid-versus-asking or negotiation gap.

## Reproducibility and publication boundary

The owner-authorized local audit uses parameterized SQL, source inventory,
query texts, gazetteer versions, raw working rows, reply/forward/album provenance,
price-basis adjudication and a private source crosswalk in protected temporary
working storage outside the public repository. A separate aggregate-only ledger
is retained locally; no durable raw-message archive was created. Temporary
working material can expire, and replay after corpus edits may differ. The
corpus-reader policy governs access to the source material. Public
readers cannot independently inspect the private source posts from this note;
that limitation is part of the evidence status, not hidden behind a citation.

The public file contains aggregate counts, public benchmark references and
non-identifying paraphrases. It contains no verbatim personal messages, Telegram
links, sender IDs or per-person financial rows. The independent refutation and reconciliation
record is summarized above. Candidate-parser checksum (code only; not the complete evidence/adjudication record):
`a6741c657e1b8fb137c51726034650432f402b617838039dc3681ceefd11d38d`.

No application code, rent values, district/area/grid exports or corpus data are
changed by this research note.
