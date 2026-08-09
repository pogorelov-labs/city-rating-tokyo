# @city-rating/schema

Single source of truth for cross-language constants + type definitions used across
the city-rating project (TypeScript app, Python MCP server, Python rating pipeline).

This package exists because the same constants (`RATING_KEYS`, `DEFAULT_WEIGHTS`,
`RENT_FLOOR`, etc.) and type shapes (`StationRatings`, `RentAvg`, `FilterState`, ...)
were previously duplicated across three places:

- `app/src/lib/{types,scoring,url-state}.ts`
- `mcp/src/city_rating_mcp/scoring.py`
- `scripts/compute-ratings.py`

When one drifted from the others, behaviour silently broke. This package removes
that risk by generating both TS and Python bindings from one JSON source.

## Layout

```
packages/schema/
├── constants.json              # ← author by hand. THE source of truth.
├── schema.json                 # ← author by hand. JSON Schema $defs (type shapes).
├── scripts/gen.ts              # codegen — reads the two JSON files, emits TS + Py
├── ts/                         # GENERATED — do not hand-edit
│   ├── constants.ts
│   ├── types.ts
│   └── index.ts
├── python/city_rating_schema/  # GENERATED — do not hand-edit
│   ├── __init__.py
│   ├── constants.py
│   └── models.py
├── package.json
└── README.md (this file)
```

Files under `ts/` and `python/` are **generated**. The header at the top of each
one says so. Never hand-edit them — change `constants.json` or `schema.json` and
re-run codegen.

## How codegen works

`npm run gen` (or `npx tsx scripts/gen.ts`) reads `constants.json` and
`schema.json`, then writes 6 files. The output is deterministic: no timestamps,
no random IDs, stable key order. CI can assert:

```bash
npm run gen && git diff --exit-code
```

If that diff is non-empty, someone hand-edited a generated file or changed a JSON
source without re-running codegen — fail the build.

The generator is a single file (`scripts/gen.ts`) so you can read the whole thing.
It does not depend on any external codegen library — just string templates.

## ⚠️ Key order is load-bearing

The 10 rating dimensions have a **canonical order** defined in
`constants.json` `rating_keys`:

```
transport, rent, daily_essentials, safety, food, green, gym_sports, vibe, nightlife, crowd
```

This order is **positional** — shared URLs encode weights as a comma-separated
list (`?w=18,18,14,...`) and decode positionally against this array. If you sort
the keys alphabetically or otherwise reorder them, every existing shared URL
silently points at the wrong weighting.

For the same reason, `DEFAULT_WEIGHTS` and `RATING_LABELS_EN` are emitted with
keys in this exact order, and `LEGACY_WEIGHT_KEYS` is preserved in its own
separate legacy order.

`constants.json` carries a top-level `_comment_order_warning` field saying the
same thing — JSON object key order is preserved by both `JSON.parse` and
`json.load`, but formatters that "tidy" JSON by sorting keys would break this.
**Do not run a key-sorting formatter over `constants.json`.**

## `legacy_weight_keys` — backcompat

Before CRTKY-84 the canonical order was:

```
food, nightlife, transport, rent, safety, green, gym_sports, vibe, crowd, daily_essentials
```

Shared URLs that were generated before the reorder still circulate (the blog post
and old Tweets). `LEGACY_WEIGHT_KEYS` lets `url-state.ts` detect and decode them:
9-element weight vectors are assumed legacy, and 10-element vectors are sniffed
(position 0's value vs. the old food weight) to pick legacy vs. current order.

**Never delete `LEGACY_WEIGHT_KEYS`** even if you can't find any caller — the
cost of keeping it is one constant; the cost of deleting it is silently
mis-decoding every old shared URL.

## `1k_1ldk` — digit-prefixed key

`RentAvg` has a key `1k_1ldk` (the Japanese apartment layout "1K + 1LDK"). It
starts with a digit, which is a legal JSON object key but illegal as a bare
identifier in most languages:

- **TypeScript**: emitted as the string-literal property `'1k_1ldk': number | null;`
  (quoted). Access with `rentAvg['1k_1ldk']`.
- **Python / Pydantic**: the field is named `one_1ldk` with `Field(alias="1k_1ldk")`
  and the model sets `ConfigDict(populate_by_name=True)`, so you can construct
  with either `RentAvg(**{"1k_1ldk": 80000, ...})` or
  `RentAvg(one_1ldk=80000, ...)`.

## Running codegen

```bash
cd packages/schema
npm install           # first time only — installs tsx
npm run gen           # regenerates ts/ and python/
```

The codegen has no side effects beyond writing those 6 files.

## Verifying the output

TS compile check (from inside `packages/schema`):

```bash
npx tsc --noEmit ts/*.ts   # or rely on the consuming app's tsc step
```

Python import check (from inside `packages/schema/python`):

```bash
pip install pydantic       # first time only
python3 -c "from city_rating_schema import constants, models; print(constants.RATING_KEYS); print(models.StationRatings)"
```

## When to edit what

| You want to change…                | Edit                                  |
|------------------------------------|---------------------------------------|
| A constant value (rent floor, etc) | `constants.json`, then `npm run gen`  |
| The set of rating dimensions       | `constants.json` **and** `schema.json`, then `npm run gen` — and audit `url-state.ts` |
| A type's shape                     | `schema.json`, then `npm run gen`     |
| How codegen formats output         | `scripts/gen.ts`                      |

The rating-key reorder is a breaking change for shared URLs — if you ever need
to do another one, add a new `LEGACY_WEIGHT_KEYS_V2` alongside the existing one
and bump the URL sniff logic in `url-state.ts`. Do not overwrite the existing
legacy array.
