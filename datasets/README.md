# Datasets & solver answer key

Tracked, **synthetic** rosters for the solver. Real employee data (PII) must never be
committed — put it in `/data/` or name it `*_real.xlsx` (both git-ignored). The app itself
now only accepts the **de-identified schema**: an `ID Alias` column (a non-repeating
permutation of `1..n`) plus `Func 1`, `Func 2`, … columns with `True`/`False` cells — no
names. Use the roster template to produce a valid upload.

| File | What it is |
|------|-----------|
| `EmployeeDatabase.xlsx` | Original 131-row synthetic sample (legacy `main.ipynb`, old ID/Name schema). |
| `EmployeeDatabase2.xlsx` | Small synthetic sample (legacy schema). |
| `edge_cases.xlsx` / `edge_cases.csv` | Curated correctness fixture, de-identified schema (below). |
| `build_edge_cases.py` | Deterministic generator for the two `edge_cases.*` files. |

## `edge_cases` roster

One database packing every edge case, so expected outputs stay closed-form. Functions:
`Func 1, Func 2, Func 3, Func 4`. 15 employees, identified only by `ID Alias` `1..15` (no names):

| ID Alias | Group | Approved | Role in the tests |
|----------|-------|----------|-------------------|
| 1–2 | NoQual | (none) | **no qualifications** → must always be Unassigned |
| 3–4 | AllQual | Func 1–4 | **all qualifications**; floaters that can cover any function |
| 5 | Func 1 only | Func 1 | dedicated specialist |
| 6 | Func 2 only | Func 2 | dedicated specialist |
| 7 | Func 3 only | Func 3 | the only exclusive Func 3 body → makes Func 3 scarce |
| 8–15 | PoolBlock | Func 4 | 8 interchangeable workers → combinatorial explosion |

Qualified pools: **Func 1 = Func 2 = Func 3 = 3** (specialist + 2 AllQual); **Func 4 = 10** (8 block + 2 AllQual).

## Answer key

Semantics under test: `minimums` are **exact** per-function targets; the search is bounded by
`maxLength`; solutions are de-duplicated by employee-ID set; seed is always **1337**.
Expected counts are hand-derived **and** verified against the solver.

| Scenario | `minimums [Func1,Func2,Func3,Func4]` | maxLength | Solutions | Why | Nodes (seed 1337) |
|----------|--------------------------------------|-----------|-----------|-----|-------------------|
| S1 feasible + zero-qual | `[1,1,1,0]` | 1000 | **13** | see derivation below | 44 |
| S2 infeasible | `[1,1,4,0]` | 10 | **0** | Func 3 pool = 3 < 4 → pruned immediately | 1 |
| S3 all-qual used | `[2,0,0,0]` | 1000 | **3** | choose 2 of {Func 1 only, AllQual×2} = C(3,2) | 7 |
| S4 explosion (exhaustive) | `[0,0,0,3]` | 1000 | **120** | C(10,3) over the Func 4-qualified 10 | 176 |
| S5 disk-spill (xfail spec) | `[0,0,0,5]` | — | **252** | C(10,5); pins the future streaming-to-disk contract | 638 (in-mem) |

**S1 = 13 derivation.** Pick distinct employees for Func 1∈{5,3,4}, Func 2∈{6,3,4}, Func 3∈{7,3,4}
where AllQual = {3,4}. Counting by how many AllQual are used: 0 used → 1 (5,6,7);
1 used → 3 slots × 2 people = 6; 2 used → C(3,2) slots × 2! people = 6; 3 used → 0
(only two AllQual exist). Total = 1 + 6 + 6 = **13**.

Regenerate with `python datasets/build_edge_cases.py` (data is deterministic; the CSV is
byte-stable, the XLSX is data-stable). The tests in `tests/test_algorithm_correctness.py`
enforce every count above; node counts are guarded by generous ceilings, not exact equality.
