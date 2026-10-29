# Bangkok rent evidence in the Telegram corpus — CRTKY-208

Researched **2026-10-29**. Research only; adoption belongs to **CRTKY-136**.

**Independent adversarial checks of both passes are complete; corrections and remaining limits are recorded below.**

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

The first-pass historical screen used **2024-10-29 through the latest observed raw date,
2026-10-26**. Its initial freshness proposal used
`w = 2^(-age_in_months/12)` with six- and twenty-four-month half-life checks,
based on report date and explicitly flagged when the actual price date is
unknown. Weights are not extra observations. With no releasable complete cohort,
weighted medians and `n_eff=(Σw)²/Σw²` are undefined/not released rather than zero.
The owner-requested extension below proposes a narrower primary window and half-life.
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

## Owner-requested extension: time, paid-versus-asking, skew and adoption

**2026-10-29 extension; independent adversarial re-derivation completed and reconciled.**
The original audit above is the first-pass record merged in PR #170. The extension
reuses its frozen comparator inputs and controlled source crosswalk, then adds
broader noun/verb controls, building-name retrieval and geometry checks. This
remains research; the following JSON and precedence rules are a decision document
for CRTKY-136, not a new input file or an adoption decision.

The added retrieval brings the direct message union from **18,281 to 19,537**
records, an increase of **1,256**. That union is not a tenancy panel. A broad
paid-verb/number control flagged another **125** housing/context records outside
the original manual screen; **123** lacked a parsed THB amount. The two with
parsed amounts included the repeated Punnawithi claim and an unlocated house
renewal/counteroffer, rather than a new central reference-size condo cohort.
Foreign currency, dates, bill amounts and unspecified magnitudes remain excluded
or unresolved; this does not establish exhaustive recall.

### 1. Annual observations and the decay window

The all-source inventory was re-enumerated before this pass: **35 sources,
8,396,280 non-soft-deleted messages**, latest raw activity October 26. SQL and
Python annual buckets use **Asia/Bangkok report time**. A Python boundary-date
discrepancy was caught by reconciling the annual SQL counts and corrected before
using the table. The following are exact **message** counts, without a SQL LIMIT:

| Report year | Discussion-chat messages | Chat housing/payment handles, raw | Chat handles after ad-template filter | Literal `бангкок`, all sources | City AND crude rent handles, raw | Crude after ad-template filter |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | 22,798 | 1,802 | 1,801 | 9,168 | 289 | 288 |
| 2024 | 37,630 | 2,470 | 2,470 | 9,716 | 374 | 373 |
| 2025 | 56,928 | 2,974 | 2,966 | 13,710 | 784 | 631 |
| 2026 through Oct 26 | 36,179 | 2,213 | 2,036 | 9,653 | 1,440 | 213 |

The chat columns use the dedicated discussion source, keeping the listing
channel separate. That channel enters the corpus in March 2025, so a combined
chat-plus-channel curve has a source-composition break. The expanded handle
includes housing nouns, rent/lease language and payment verbs; it also matches
non-rent discussion. The all-source crude handle remains
`аренд|кондо|снимаю|снимал`. Neither series counts actual leases.

The raw apparent 2026 growth was **an ad/admin-template artifact**: **1,227 of
1,440** crude co-mentions (**85.2%**) match the fixed vehicle/transfer/yacht and
admin-recommendation promotion signature. After that filter the counts are
**631 in 2025 and 213 in partial 2026**, reversing the direction of the raw
counts. These residuals are not automatically human reports or housing rents.
The filter is defined by sampled, recurring templates, not inferred bot status.
Its final predicate was independently rerun; an earlier broader fast-track
signature was not mixed into the published counts. No private account IDs or
message text are exported.

The same filter removes **177 of 2,213** raw 2026 chat housing/payment-handle
messages (**8.0%**); **2,036** remain, against **2,966** in 2025. This corrects
the discussion-coverage narrative, not a price series. Partial 2026 is not
annualized and is not a like-for-like full-year price period. No market-rent or
community-demand growth rate is inferred from either raw or filtered counts.
Core coverage only becomes substantial in 2023; earlier all-source city mentions
do not establish a comparable historical Bangkok rental panel.

The paid-claim ledger now has **22 messages grouped into 17 conservative housing
claim episodes from 16 accounts** over four years. One account contributes two
distinct stays, so episode count does not prove statistical independence. This
includes the original twenty self-reported
paid messages, one completed-lease claim and the additional Punnawithi repeat.
They are not seventeen verified transactions: hotels, studios, unknown products
and retrospectively reported payments remain in this diagnostic count.
This ledger uses the self-paid/completed-lease labels with retained point amounts;
bundled own-and-friend prices and third-party claims are separate. Within that
defined ledger, **six** episodes are identified as ordinary condos without an explicit
short-stay/serviced exclusion; **five of those six lack floor area**, and the
one stated floor area is outside the reference band.

| Report year | Retained paid-claim messages | Distinct claim episodes within year | Ordinary-condo claim episodes within year | Complete fixed-size/bedroom paid episodes | Released reference-rent median, THB/month |
|---|---:|---:|---:|---:|---|
| 2023 | 9 | 6 | 2 | 0 | — |
| 2024 | 4 | 3 | 2 | 0 | — |
| 2025 | 5 | 5 | 2 | 0 | — |
| 2026 | 4 | 4 | 1 | 0 | — |

One recurring episode crosses years, so annual episode counts must not be summed
as distinct all-period tenancies. Ordinary-condo identification still does not
establish location, bedrooms, duration or current price date. The proposed recent
report window contains **nine paid-claim messages and three ordinary-condo claim
episodes**, from **eight accounts**; these are not three comparable central-station
observations. Moving the report-window start by two days drops one of the three
ordinary-condo claims, but changes no released reference cohort.

**Drift-model result: not identifiable.** A defensible price model would compare
like area × bedroom × size × lease-term cohorts, account for project/quality and
lease vintage, and fit a time term to their price-in-effect dates. In the retained
claims there are **zero complete fixed-size/bedroom paid observations**, before
requiring temporal overlap or independent samples. There is no identified rent
drift coefficient, current fixed-size median or uncertainty interval to report.
The coefficient is **undefined, not zero**. Pooling a larger old condo, a studio,
an incumbent lease and a hotel would estimate changes in their mix, not a Bangkok
rent trend. This pass does not manufacture an annual uplift from message growth.
There is a current foreign-currency paid report with a small-unit floor area in
the wider controls, but no bedroom count and a non-target location. It fails
the joint currency/bedroom/geography definition; zero complete observations
does not mean that nobody states a floor area. No FX or bedroom imputation is made.

**Adopted analytical window for this extension:** **2025-10-29 through
2026-10-26**, the latest observed raw date, with observations dated by when the
reported price was in effect. This is a twelve-month lookback from the audit
date, truncated at the data cutoff. A present-tense claim can support a reported
current price at that report date; a retrospective claim without a price date
cannot. Neither identifies the original contract-signing date automatically.
Unknown price dates belong in a separate report-dated sensitivity, not the primary
rent estimator. A 2024 payment is retained as historical evidence and does not
become a 2026 price.

**Occupied cost and price-setting date are different estimands.** An explicit
current incumbent-rent claim can describe what is paid now without dating its
last rent reset. The independently reconstructed contract history leaves one
incumbent's rate-setting date uncertain. Under the refuter's vintage interval,
using report date as a new-lease price date could imply a **conditional weight
ratio of about 1×–5.4× at a twelve-month half-life**. This is an uncertainty bound
under possible rate-setting dates, not a measured error, rent change or fixed
correction.
Keep current occupied cost separate from new-lease/renewal-event comparisons;
do not invent a reset date or treat every incumbent price as stale or new.

Within that hard window the proposal uses
`w = 2^(-price_age_in_months / 6)`. Illustrative policy weights at ages zero,
six and twelve months are **1, 0.5 and 0.25**. The shorter half-life limits the
influence of stale inventory while the hard cutoff prevents indefinite carry.
Age is elapsed calendar days from the price-in-effect date to the audit date,
divided by 30.4375; a future paid-price date is not admitted.
It is a conservative operating choice, **not a decay rate fitted from this
corpus**. Test three- and twelve-month half-lives and six-/twenty-four-month
windows on the same defined cohort. No decay setting fills missing unit fields;
all current reference medians remain unreleased. No FX or inflation adjustment,
nightly-to-monthly multiplication or assumed contract-date repair is used.

**The amount finder is not an integration-ready monthly-rent normalizer.**
Independent re-reading sustained the retained amounts, but constructed controls
expose missing automatic guards for weekly rates, annual totals and multi-month
totals. A weekly amount treated as monthly would understate monthly cost.
The bare-year guard can also hide a genuine small amount, while bare shorthand
needs manual context. The retained ledger was manually adjudicated; the prototype
must not feed a product without explicit per-amount currency, role and period
validation. These are documented feasibility limits, not repairs to product code.

### 2. Paid-versus-asking deltas

Define the descriptive gap as `paid median − asking median`, and its percentage
as `100 × (paid median / asking median − 1)`. A negative gap is **not by itself
an achieved negotiation discount**. That requires the same unit's documented
initial ask and agreed price for the same term, currency, fees and date. A public
asking inventory and this community's incumbent/short-stay reports are different
populations. An unaccepted hypothetical concession is not a paid outcome.

The following checks the requested overlap using the fixed-size paid reference
and the frozen published DooAsset bedroom proxies. Paid counts are from the
audited retained claims, not a universal claim of absence. The source dates below
are DooAsset's recorded as-of dates, not the new corpus extraction date.
No corpus tenancy is assigned to a product area by this research; the rows record
the absence of an established comparable cohort in the tested ledger, not a
complete enumeration of neighborhood rentals.

| Area | Published asking 1BR / 2BR, THB/month (as-of) | Complete recent paid n, 1BR / 2BR | Released paid median, 1BR / 2BR | Paid-minus-asking gap | Reading |
|---|---|---:|---|---|---|
| Thong Lo | 28,000 / 56,500 (2026-09-29) | 0 / 0 | — / — | — | No releasable comparable paid cohort |
| Ekkamai | 27,000 / 50,000 (2026-10-25) | 0 / 0 | — / — | — | No releasable comparable paid cohort |
| Phrom Phong | 48,000 / 52,500 (2026-10-25) | 0 / 0 | — / — | — | No releasable comparable paid cohort; published size/luxury composition differs |
| Asok | 26,500 / 55,000 (2026-10-25) | 0 / 0 | — / — | — | No releasable comparable paid cohort |
| Nana | 28,000 / 60,000 (2026-10-17) | 0 / 0 | — / — | — | No releasable comparable paid cohort |
| Chit Lom | 45,000 / 120,000 (2026-10-21) | 0 / 0 | — / — | — | No releasable comparable paid cohort; published size/luxury composition differs |
| Siam | No adopted DooAsset anchor | 0 / 0 | — / — | — | Paid cohort and asking anchor both unavailable |
| Sala Daeng | 38,000 / 60,000 (2026-10-07) | 0 / 0 | — / — | — | No releasable comparable paid cohort |
| Chong Nonsi | 24,000 / 72,000 (2026-10-01) | 0 / 0 | — / — | — | No releasable comparable paid cohort; published size/luxury composition differs |
| Ari | No adopted DooAsset anchor | 0 / 0 | — / — | — | Paid cohort and asking anchor both unavailable |
| Ratchathewi | 21,500 / 38,000 (2026-10-07) | 0 / 0 | — / — | — | No releasable comparable paid cohort |
| Phaya Thai | 25,000 / 43,500 (2026-10-10) | 0 / 0 | — / — | — | No releasable comparable paid cohort |

The asking facts, counts and citations remain in the [October 25 audit](2026-10-25-central-rent-audit-crtky141.md)
and `data/bangkok/rent-overrides.json`; no blocked portal was retried. DooAsset
medians include all floor areas by bedroom and use provider geography. They are
not silently converted into the fixed-size, application-catchment metric.
Phrom Phong's 1BR proxy, Chit Lom's larger/luxury mix and Chong Nonsi's published
larger 2BR sample remain explicit composition caveats. Chit Lom's published
typical 1BR size is **56 m²** and Chong Nonsi's typical 2BR size **93.3 m²**,
above the respective 30–35 / 60–70 m² reference bands. There is **no publishable
paid-minus-asking number or negotiation cushion** from these audited overlaps.

Even a future dense paid cohort needs a common size/quality/term/date footprint
before a standardized gap is meaningful. For a contemporaneous gap, restrict
price dates around the asking snapshot, for example a proposed ±90-day window,
and reapply density gates. That is narrower than the primary annual collection
window. An unstandardized all-size cross-sample gap could be labelled as such,
but cannot validate our reference-size rent or identify bargaining causally.

A separate relaxed check removes the floor-area band and widens the report
lookback to twenty-four months, while retaining ordinary-condo paid basis,
known 1BR/2BR count and a resolved ten-override-area footprint. It still finds
**zero retained overlapping observations**. The unavailable delta is therefore
not solely a consequence of the narrow size band or the proposed adoption gate.

### 3. Observable cohort skew and where extrapolation fails

The selection model has several stages: access to this Russian-language source
frame; participation; choosing to discuss housing; deciding to state a price;
enough unit/date/location detail; and inclusion after deduplication. Their
probabilities are unknown. The missingness is plausibly related to mobility,
budget and housing type, so inverse message-count weighting cannot make this a
sample of Bangkok tenants. Language does not establish nationality.

A manual diagnostic re-read all **30 explicit-budget contexts** in the original
403-context screen. After removing copies, non-rent living-cost totals, other
currencies, nightly/multinight amounts, opinions and unknown monthly bases,
**12 unique monthly rent-budget requests from 12 accounts in one discussion
chat** were retained. The strict rule is: **the cap is explicitly per month,
or the requested base stay is one month**, so the cap has an unambiguous monthly
basis. A possible extension of a one-month stay is a soft edge, not a new budget
period. A one-to-two-month request whose cap has no stated period is outside this
strict set.
Eight use explicit THB and four contextual THB. Ranges retain the stated upper
cap; they are not converted to midpoints.

| Diagnostic in those twelve requests | Count | What it supports |
|---|---:|---|
| Monthly upper cap at most THB20,000 | 8 | A lower-budget search segment is visible in this selected subset |
| Monthly upper cap THB20,001–30,000 | 4 | The remaining retained caps are in this band |
| Monthly upper cap above THB30,000 | 0 | No such cap in this subset; not absence of affluent community members |
| Seeking one or two months | 10 | This subset mainly discusses short stays |
| Seeking an annual lease | 1 | Little annual-lease budget evidence in this subset |
| Seeking approximately six months | 1 | An intermediate-term request, not a completed lease |

These are **requested caps, not paid rents**, and not all corpus budgets. Their
denominator is the selected audited subset, not all chat members or renters.
An explicit contextual-monthly sensitivity adds the two period-ambiguous
one-to-two-month requests: **14 requests, bands 10 / 4 / 0**, with **12 short,
one annual and one approximately six-month** request. This does not resolve
every unspecified-period budget in the corpus. Foreign-currency budgets are not
converted. The extended project search also found a monthly THB request above
THB30,000 outside this diagnostic subset. Thus the displayed 30k ceiling is
**frame-only**, not a community ceiling or absence of high-budget renters.
The broader **raw** discussion-source screen contains 9,459 housing/payment-handle
messages; condo vocabulary occurs in 1,091, private-house/villa handles in 175,
and hotel/Airbnb/serviced vocabulary in 857. These overlapping lexical counts
measure discussion, not property or household shares. A house-renewal price in
an unresolved/non-Bangkok context was not admitted as a Bangkok condo observation.

| Potential skew | Measured support / boundary | Where the corpus should not set a rent |
|---|---|---|
| Language/community | Russian-language relocation/travel source frame; no population inclusion probabilities | Thai-only rental channels, local family housing and all Bangkok households |
| Product and size | Six ordinary-condo claim episodes; five omit floor area; studios/hotels/serviced stays also occur | Houses/villas, or a fixed-size 1BR/2BR inferred from a project's other floorplans |
| Budget | Eight of twelve audited monthly caps are at most THB20,000 | Luxury inventory or a citywide affordability distribution inferred from these requests |
| Tenure | Ten of twelve audited requests seek one/two months; current paid claims can also be incumbent renewals | Annual new-lease asking rents, unless term and lease vintage are aligned |
| Geography | Loose outer-Sukhumvit claims and named central/Rama 9 projects coexist; names can point to other khet/catchments | An all-Bangkok median applied to any khet, or a Sukhumvit/Sathorn brand used as a station coordinate |
| Reporting | Budgets, advice and non-rent payments dominate the broad price-context screen | A paid-versus-asking adjustment calibrated from message counts or reported bargains |

No tenant-population reference distribution is available for these exact
language × budget × property × tenure × area cohorts. Consequently the study
does **not** assign estimated over-/under-representation ratios to the 50 khet.
WorldPop residents include owners, children, house residents and other language
communities; OSM named buildings are not rental households. Neither is a valid
post-stratification denominator for this corpus. Observable discussion mix and
coverage gaps are reported instead of invented population weights.

Central named-project attention does not make the underlying paid cohort dense.
Nor should outer khet dominated by different housing products inherit a central
expatriate-condo estimate. Currently **no khet or station area passes the paid
reference-rent release gate**. Ari and Siam remain explicit gaps, not zero-rent
areas or evidence that people do not live there.

### 4. Named condos, frozen POIs and station precision

The extension read the **existing** spatial inputs whose hashes match the
committed [frozen-refresh manifest](../../../data/bangkok/refresh-inputs.json)
and [source/license audit](2026-10-26-frozen-refresh.md). No spatial acquisition
or full product rebuild was performed. The OSM PBF timestamp is
**2026-10-24T20:20:51Z**; Overture is the retained 2026-09-23.1 release.

The slim Overture extract contains **309,704** records with ID, category,
confidence, provenance and position, **no names**. It cannot perform a condo-name
join. Nearest anonymous Overture business points are not building identities.
The OSM reader produced **15,417 named building/keyword candidates** across all
50 khet and 132 of the 133 station footprints. That is source lookup coverage,
**not 15,417 condos or 132 areas with rent evidence**. It includes commercial
buildings and hotels; named relations without a named member can still be missed.
The one empty lookup footprint is `bhumibol-adulyadej-hospital`; this does not
mean that the area has no named POIs or housing.

An exploratory building-name lookup of **2,222 aliases** yielded **69 project-mention contexts**
in the extended message/context pool. Thirteen contain parsed THB amount
candidates and eight contain paid-verb candidates; these sets overlap and are
not confirmed leases. General words such as villa, residence, tower, home and
7-Eleven were removed as standalone identities. Commercial tags, full project
name, price clause and property type are checked before accepting any location.
The added qualified-name SQL pass has no result LIMIT.

**Gazetteer honesty:** this expanded building-name lookup is not an upgraded
Russian area gazetteer. The station/khet assignment dictionary remains the
**first-pass v1**; **106 of 133 areas lack Cyrillic aliases**. The building-lookup
revision added Latin/Thai names, **zero new Cyrillic aliases**, and did not fix
Russian inflections, corridor/soi ambiguity or absent project names. Independent
adversarial samples found those misses. Consequently **general per-area corpus
assignment is unsupported**. No alias rebuild is claimed or needed for the
annex's empty numerical maps; a future adoption task must solve that coverage.

| Public OSM identity control | Frozen khet | Application station footprint | Consequence |
|---|---|---|---|
| [IDEO Mobi Sukhumvit 66](https://www.openstreetmap.org/way/827834612) | bang-na | udom-suk | A Sukhumvit name does not imply a central Watthana station |
| [oka HAUS](https://www.openstreetmap.org/way/1038166166) | khlong-toei | none | Site/name corroboration improves khet resolution without forcing Thong Lo |
| [Equinox Phahol–Vibha](https://www.openstreetmap.org/way/342431405) | chatuchak | ha-yaek-lat-phrao | A “Chatuchak” reference need not mean the Chatuchak station area |
| [One9Five Asoke–Rama 9](https://www.openstreetmap.org/way/720474551) | huai-khwang | phra-ram-9 | Asoke branding does not assign BTS Asok |

These links locate public OSM objects; calculations use the frozen payload,
not later live map edits. Coordinates use longitude/latitude for geometry tests
after converting the application's latitude/longitude arrays. The building/site
representative point is tested against the committed district and station
polygons; it is not a verified entrance or walking-route measurement. Several
polygons/towers of one project do not create several tenants. The reported
Issara House hotel was explicitly rejected as a match to a differently located
Issara condo. Unqualified Regent Home remains ambiguous across projects.

All four context/project geocodes above were independently re-derived. The
identity filters nevertheless depend on **tag luck**: known retail/office tags
exclude some false matches, but tag-less retail can pass a name filter. The
frozen lookup contains such a Loft collision; Quattro also has distinct retail
and condominium identities. `candidate_locations` are retrieval suggestions,
**never verified residential geocodes**. Future use requires positive identity
and branch/property-type verification, not merely absence of a shop tag.

Four relatively frequent named handles illustrate the limit: Life Asoke–Rama 9,
oka HAUS, XT Phayathai and Life One Wireless have multiple discussion contexts,
but no releasable paid reference cohort. Only oka HAUS was resolved from this
frozen name lookup among those four; it is outside the station footprints.
The missing names are not geocoded from a nearest anonymous point or a project
brand. No actual rent estimate gains sub-khet precision merely because a name
was recognized.

### 5. Integration feasibility annex for the owner ADR

**Recommendation: retain asking rent as the primary product metric, with a
separate paid-rent cross-check only where its own cohort passes release.**
Currently the numerical maps would be empty: **0 of 50 khet and 0 of 133 station
areas** have a releasable corpus-paid reference estimate in this audit.
Do not create the proposed file or activate a build fallback from this note.

#### Proposed aggregate-only JSON contract

The proposed `data/bangkok/rent-tgcorpus.json` has the following root shape.
Empty maps reflect the current adoption recommendation; they are not zero rents.
The metadata is a proposed method contract, not an owner-approved ADR:

```json
{
  "_meta": {
    "schema_version": 1,
    "status": "proposal_not_adopted",
    "method_version": "tgcorpus-rent-v2-proposal",
    "audited_at": "2026-10-29",
    "audit_revision": null,
    "source_snapshot_date": "2026-10-26",
    "audit_url": "https://github.com/pogorelov-labs/city-rating-tokyo/blob/main/research/bangkok/notes/2026-10-29-tgcorpus-rent-audit.md",
    "metric": {
      "id": "reported_paid_condo_monthly_thb",
      "basis": "self_reported_paid",
      "currency": "THB",
      "currency_evidence": "explicit_thb_primary",
      "period": "month",
      "property_type": "ordinary_condo",
      "lease_months_min": 6,
      "reference_size_sqm": {
        "one_bed": [
          30,
          35
        ],
        "two_bed": [
          60,
          70
        ]
      },
      "estimator": "exponentially_weighted_median",
      "price_date_basis": "stated_price_period_or_explicit_current_occupancy_report",
      "estimand": "reported_occupied_base_rent",
      "lease_vintage_policy": "incumbent_cost_is_not_new_lease_price",
      "confidence_ceiling": "estimate"
    },
    "primary_window": {
      "start": "2025-10-29",
      "end": "2026-10-26",
      "timezone": "Asia/Bangkok",
      "weight_reference_date": "2026-10-29",
      "half_life_months": 6,
      "age_days_per_month": 30.4375
    },
    "geography": {
      "snapshot_commit": "078f37cebc41b583ffb87d598a1643eac92ffd4a",
      "district_polygons": "app/src/data/bangkok/geometry.json",
      "area_polygons": "app/src/data/bangkok/station-geometry.json"
    },
    "release_gate": {
      "episodes_min": 10,
      "authors_min": 5,
      "projects_min": 3,
      "effective_n_min": 8,
      "max_author_share": 0.25,
      "max_project_share": 0.5
    },
    "sources": {
      "tgcorpus-audit-2026-10-29": {
        "label": "Owner-authorized Russian-language community audit",
        "audit_url": "https://github.com/pogorelov-labs/city-rating-tokyo/blob/main/research/bangkok/notes/2026-10-29-tgcorpus-rent-audit.md",
        "access": "restricted_raw_sources_public_aggregates_only"
      }
    },
    "access_policy": {
      "reference": "macro-research ADR 0001 (2026-09-10)",
      "raw_text": false,
      "telegram_links": false,
      "personal_identifiers": false,
      "individual_price_rows": false,
      "public_provenance": "aggregate audit; private source crosswalk is not exported"
    },
    "grid_policy": "unchanged district asking estimates; no interpolation from corpus reports"
  },
  "districts": {},
  "areas": {},
  "coverage_facts": {
    "districts": {},
    "areas": {}
  }
}
```

`districts` keys must be real committed khet slugs; `areas` keys must be real
committed station-area IDs. There may be no orphan keys, an area cannot be copied
to its whole khet, and a district summary cannot masquerade as a station cohort.
An entry has the following exact shape; this unreleased example contains no
invented price, count or source observation:

```json
{
  "confidence": "estimate",
  "metric": "reported_paid_condo_monthly_thb",
  "as_of": "2026-10-26",
  "sources": [
    "tgcorpus-audit-2026-10-29"
  ],
  "rent_1br": {
    "status": "insufficient_evidence",
    "median_thb_month": null,
    "size_band_sqm": [
      30,
      35
    ],
    "n_episodes": null,
    "n_authors": null,
    "n_projects": null,
    "effective_n": null,
    "p25_thb_month": null,
    "p75_thb_month": null,
    "price_month_range": null,
    "report_month_range": null,
    "quality_flags": [
      "below_release_gate"
    ]
  },
  "rent_2br": {
    "status": "insufficient_evidence",
    "median_thb_month": null,
    "size_band_sqm": [
      60,
      70
    ],
    "n_episodes": null,
    "n_authors": null,
    "n_projects": null,
    "effective_n": null,
    "p25_thb_month": null,
    "p75_thb_month": null,
    "price_month_range": null,
    "report_month_range": null,
    "quality_flags": [
      "below_release_gate"
    ]
  }
}
```

On release, each `rent_1br` / `rent_2br` object changes to `status: "released"`
and contains its computed median, dispersion, counts, effective n and actual
price/report month ranges. A suppressed cohort retains nulls and a reason;
**null is not zero**. These objects intentionally differ from today's numeric
rent pair and require a dedicated adapter in an implementation task. They cannot
be passed to the existing override loader unchanged. No raw messages, Telegram
links, personal identifiers, per-person amounts, private dedup keys or source
post hashes enter this JSON. Public provenance terminates at the aggregate audit.

`p25`/`p75` describe sample dispersion, not a confidence interval. Maintain the
source ID, method version, observation and report windows, geography revision and
audit revision in the implementation's provenance. `audit_revision` is null only
in this unadopted proposal; a released payload must pin the approved audit commit.
Use months for public cohort
date ranges; retain precise dates and the controlled crosswalk privately.
One eligible bedroom cohort does not license an invented second-bedroom price.
Do not clamp an unusual amount to an editorial price; verify currency, base-rent
role, unit, dates and cohort, then retain valid observations in their proper
cohort or flag them for review. Any future main-pair adoption must satisfy its
existing bounds and ordering without fabricating or silently repairing values.

#### Precedence options

| Option | Behavior | Benefit / risk | Recommendation |
|---|---|---|---|
| Paid wins where comparable | Replace the main asking pair when paid cohorts pass gates | Closer to claimed occupied cost, but switches the product's price basis across areas; incumbent/new-lease and community mix can move rankings | Requires a deliberate metric/normalization ADR and comparable asking evidence; not supported now |
| Asking primary, paid cross-check | Preserve current asking override/editorial fallback; show separately sourced paid facts where eligible | Keeps one primary metric and exposes observed differences without blending incompatible populations | Preferred design; currently publishes no paid numerical rows |

Never average paid and asking values, blend them by message count or fill an
unsourced bedroom with a ratio. A retained source gap remains a gap. Grid rent
continues to use district asking estimates; no spatial interpolation from sparse
corpus reports is proposed. A descriptive future gap must name both sources,
cohorts and dates and state its comparability; it is not labelled negotiation.

#### Proposed release and decay gates

Per area × bedroom × price-basis cohort, propose **at least ten independent
episodes, five accounts, three projects, effective n at least eight**, no account
above 25% and no project above 50% of the observations. Complete price/unit/term/
location/date fields are required before density is considered. Use the
twelve-month primary price window and six-month half-life above, with disclosed
sensitivity. These are conservative operational/privacy/diversity proposals,
**not a statistical-power result, proof of anonymity or owner approval**.
The earlier five-episode/three-account analysis gate is not an adoption promise.
Effective n measures freshness-weight dispersion, not independence. Account and
project dependence must be audited separately; distinct stays from one account
are not independent people, and copies of one tenancy never add observations.

Keep paid/self-reported, third-party paid, unaccepted offers, available asking,
budgets and other accommodation products separate. Show stability and missingness
by cohort; do not choose a half-life because it produces a desired comparator gap.
Even if these gates are met, this source frame supports at most **estimate**
confidence without a different, better verified sampling basis.

#### Sparse evidence as a Tier-2 fact

Follow the institutions/Michelin pattern of **a dated source fact outside the
rating calculation**, with a typed rent-specific row. The proposed shape is:

```json
{
  "kind": "rent_context",
  "basis": "self_reported_paid",
  "status": "insufficient_comparable_reports",
  "bedroom": null,
  "size_band_sqm": null,
  "median_thb_month": null,
  "sample_band": "below_release_gate",
  "price_window": {
    "start": "2025-10",
    "end": "2026-10"
  },
  "confidence": "estimate",
  "source_id": "tgcorpus-audit-2026-10-29",
  "audit_url": "https://github.com/pogorelov-labs/city-rating-tokyo/blob/main/research/bangkok/notes/2026-10-29-tgcorpus-rent-audit.md"
}
```

A sparse row can say **“Community rent reports: insufficient comparable
evidence · audit”**, without a price or a tiny-sample median. A released row can
say **“Reported paid rent · 1BR 30–35 m² · THB[median]/month · n=[episodes] ·
[price-month range] · estimate · audit.”** Counts mean independent episodes,
not messages; accounts are not assumed to be unique people. Translation and the
new typed facts adapter belong to the adoption implementation, with EN/JA/RU
kept consistent. Do not add empty warning rows everywhere when there is no
useful eligible fact.

#### Which existing places would improve now?

| Place / scope | What this extension actually adds | Numerical adoption now |
|---|---|---|
| Ari and Siam | Explicitly tested gaps; an Ari name collision does not supply a condo rent | Neither DooAsset gap is filled |
| Ten current DooAsset override areas | Temporal/cohort compatibility audit and a documented unavailable gap, without a fabricated discount | All ten asking overrides stay unchanged |
| Udom Suk / Bang Na | A named-project claim can be located, but its unit/cohort and sample do not establish a reference median | None |
| Punnawithi / On Nut language | Better loose-location interpretation; ambiguous project/catchment and missing fields remain | None |
| Ha Yaek Lat Phrao, Phra Ram 9, Phetchaburi | Project-name and asking/paid-role disambiguation; not interchangeable with central Asok or Chatuchak labels | None |
| Watthana and Khlong Toei | Some building names resolve to a khet while remaining outside every station footprint | No district replacement |
| All remaining khet / areas | No released fixed-size cohort established by the audited controls | None; absence is not zero rent |

The source's present value is **better evidence interpretation and collection
design**, not a new rent level. To improve CRTKY-136 numerically, obtain a recent,
independent, consent-compatible panel with resolved unit fields and private
provenance, or better public asking/paid sources with matching cohorts. That
decision is separate from this research extension.

#### Independent extension checks and publication limits

Two independent research refuters re-queried the corpus and frozen spatial
inputs before publication. They reproduced the inventory, annual retained-claim
counts and four project geocodes, attacked missing Cyrillic/inflected aliases,
and independently re-read prices, replies and copy families. Their challenges
changed the annual coverage table by removing ad/admin templates, clarified the
strict budget rule and its sensitivity, added account dependence and unknown
price-vintage bounds, and ruled out an area-gazetteer upgrade claim. No new
fixed-size THB paid cohort was established under their tested screens.

The final template filter was rerun against raw data with its exact recorded
predicate; it reproduces 288 / 373 / 631 / 213 residual crude co-mentions for
2023–2026. This is a filtered retrieval series, not a human-renter census. The
aggregate/source checks and design JSON blocks were validated locally; raw
reading sets, source locators and personal identifiers remain outside git.
Independent checks are bounded adversarial evidence, not proof of exhaustive
recall or verification of the underlying payments.
