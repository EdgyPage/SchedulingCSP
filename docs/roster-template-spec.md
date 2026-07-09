# Roster template — build spec (encode / decode)

This is the recipe for the downloadable Excel template that lets non-technical users
strip PII from a roster before uploading and re-attach it after solving.
`frontend/roster-template.xlsx` is the shipped template, built in Excel with the Power Query
below (openpyxl can't author Power Query). `build_roster_template.py` generates a *formula
scaffold* to start from; this doc is the recipe to add the one-click **Power Query "Refresh
All"** layer and commit the finished file to `frontend/`.

Target: **Excel 365 / 2021** (XLOOKUP + dynamic arrays). Everything below uses **one**
Power Query and otherwise only built-in functions.

## What it produces (the app's required upload schema)
An `ID Alias` column (a non-repeating permutation of `1..n`) plus `Func 1`, `Func 2`, …
columns with `True`/`False` cells. No names — the app rejects anything else.

## Sheets (the scaffold already has these)
- **Encoder** — an Excel Table **`Roster`**: column `Unique Identifier` (real IDs/PII) + one
  column per **real** function name, cells `TRUE`/`FALSE`. Auto-expands. Users paste here.
- **Encoded** — the upload-ready table `ID Alias, Func 1 … Func k`. **Formula view of `Master`**
  (below). Users copy it → Save As `.csv` → upload.
- **Maps** (hidden) — **`Master`** `[ID Alias, Unique Identifier, Func 1 … Func k]` (the Power
  Query output, the single source of truth) and **`FuncMap`** `[Func Code, Function Name]`.
- **Decoder** — Table `SolverOutput` `[ID Alias, Function, Unique Identifier, Function Name]`;
  the last two are the XLOOKUP calculated columns (already in the scaffold).

Everything derives from **one** `Master`, so the alias used in `Encoded` and the alias the
Decoder maps back are guaranteed identical — no drift.

## Step 1 — the one Power Query (`Encode` → `Master`)
Data → Get Data → **From Other Sources → Blank Query** → Advanced Editor → paste:

```m
let
    Source   = Excel.CurrentWorkbook(){[Name="Roster"]}[Content],
    Buffered = Table.Buffer(Source),                              // materialize once (stable shuffle)
    Funcs    = List.RemoveItems(Table.ColumnNames(Buffered), {"Unique Identifier"}),
    Shuffled = Table.Sort(
                 Table.AddColumn(Buffered, "R", each Number.Random(), type number),
                 {{"R", Order.Ascending}}),
    Aliased  = Table.AddIndexColumn(Shuffled, "ID Alias", 1, 1, Int64.Type),
    Renamed  = Table.RenameColumns(Aliased,
                 List.Transform(List.Positions(Funcs), (i) => {Funcs{i}, "Func " & Text.From(i + 1)})),
    Generic  = List.Transform(List.Positions(Funcs), (i) => "Func " & Text.From(i + 1)),
    Ordered  = Table.SelectColumns(Renamed, {"ID Alias", "Unique Identifier"} & Generic)
in
    Ordered
```

- Name the query **`Encode`**. Close & Load **To… → Table**, on the hidden **Maps** sheet, and
  make the loaded table's name **`Master`** (Table Design → Table Name).
- **Turn off auto-refresh** so aliases only change when the user clicks Refresh All: Data →
  Queries & Connections → right-click `Encode` → Properties → **uncheck "Enable background
  refresh"** and **uncheck "Refresh data when opening the file"**. (This is essential — otherwise
  reopening the file to decode reshuffles the mapping and breaks the already-uploaded file.)
- `Table.Buffer` + this single query mean one materialized shuffle feeds everything.
- **Non-English Excel** writes booleans as `WAAR/VRAI/…`. To be locale-proof, emit `1/0`: wrap the
  final step's func columns, e.g. add
  `TransformColumns` mapping each `Generic` column with `each if _ = true then 1 else 0`.

## Step 2 — Encoded (formula view of Master)
On the **Encoded** sheet, replace the scaffold's example values with formulas referencing
`Master` (static values → never re-randomize between refreshes):
- Headers `ID Alias, Func 1, … Func k` (row 1).
- Under `ID Alias`:  `=Master[ID Alias]`
- Under each `Func i`:  `=Master[Func i]`
- Auto-sizing alternative (one formula, any k):
  `=HSTACK(CHOOSECOLS(Master,1), DROP(Master,0,2))` spills `ID Alias` + all `Func` columns.

## Step 3 — FuncMap (Func code ↔ real name)
Small and static. On **Maps**, keep `FuncMap` as two columns: `Func Code` = `Func 1, Func 2, …`
and `Function Name` = your real function names (same order as the Encoder's function columns).
Type it once, or derive `Function Name` from the Encoder headers with
`=DROP(TRANSPOSE(Roster[[#Headers],[<first func>]:[<last func>]]),0)`.

## Step 4 — Decoder (already wired in the scaffold)
`SolverOutput` has two XLOOKUP calculated columns; keep them as-is:
```
Unique Identifier =XLOOKUP([@[ID Alias]], Master[ID Alias], Master[Unique Identifier], "(unknown alias)")
Function Name     =XLOOKUP([@Function],   FuncMap[Func Code], FuncMap[Function Name], [@Function])
```
The `Function` lookup's 4th argument `[@Function]` makes `Unassigned` (and any unmapped value)
pass through unchanged; an unknown alias shows `(unknown alias)` so paste errors are visible.

## The user's click-path (put this on the Instructions page too)
1. Fill **Encoder** with real IDs + real function names, `TRUE`/`FALSE` cells.
2. Data → **Refresh All** → aliases + Encoded fill in.
3. Copy the **Encoded** table → new workbook → Save As `.csv` → upload on the Solver page.
4. Solve, download the schedule (`ID Alias`, `Function`).
5. Paste those two columns into **Decoder** → real identity fills in.

**Two hard rules:** keep "Refresh data when opening the file" **off**, and **don't Refresh All
again after uploading until you've decoded** (a refresh picks new aliases and orphans the
uploaded file).

## Verify in Excel (can't be automated here)
- Refresh All → `Encoded` shows `ID Alias` = a `1..n` permutation + `TRUE/FALSE`; re-refresh reshuffles.
- Edit an unrelated cell → aliases **do not** move (proof they're frozen between refreshes).
- Round-trip: Encoded → CSV → upload → solve → paste output into Decoder → real names resolve,
  `Unassigned` passes through, a bad alias shows `(unknown alias)`.
- The repo's `tests/test_roster_template.py` only checks that the shipped file loads and
  advertises the `ID Alias` + `Func N` upload schema; the behavior above is yours to confirm in Excel.
