# Datasets & solver answer key

Tracked, **synthetic** rosters for the solver. Real employee data (PII) must never be
committed — put it in `/data/` or name it `*_real.xlsx` (both git-ignored).

| File | What it is |
|------|-----------|
| `EmployeeDatabase.xlsx` | Original 131-row synthetic sample (used by `main.ipynb`). |
| `EmployeeDatabase2.xlsx` | Small synthetic sample. |
| `edge_cases.xlsx` / `edge_cases.csv` | Curated correctness fixture (below). |
| `build_edge_cases.py` | Deterministic generator for the two `edge_cases.*` files. |

## `edge_cases` roster

One database packing every edge case, so expected outputs stay closed-form. Tasks:
`T1, T2, T3, Pool`. 15 employees named `Employee N`:

| IDs | Group | Approved | Role in the tests |
|-----|-------|----------|-------------------|
| 1–2 | NoQual | (none) | **no qualifications** → must always be Unassigned |
| 3–4 | AllQual | T1,T2,T3,Pool | **all qualifications**; floaters that can cover any task |
| 5 | T1only | T1 | dedicated specialist |
| 6 | T2only | T2 | dedicated specialist |
| 7 | T3only | T3 | the only exclusive T3 body → makes T3 scarce |
| 8–15 | PoolBlock | Pool | 8 interchangeable workers → combinatorial explosion |

Qualified pools: **T1 = T2 = T3 = 3** (specialist + 2 AllQual); **Pool = 10** (8 block + 2 AllQual).

## Answer key

Semantics under test: `minimums` are **exact** per-task targets; the search is bounded by
`maxLength`; solutions are de-duplicated by employee-ID set; seed is always **1337**.
Expected counts are hand-derived **and** verified against the solver.

| Scenario | `minimums [T1,T2,T3,Pool]` | maxLength | Solutions | Why | Nodes (seed 1337) |
|----------|---------------------------|-----------|-----------|-----|-------------------|
| S1 feasible + zero-qual | `[1,1,1,0]` | 1000 | **13** | see derivation below | 44 |
| S2 infeasible | `[1,1,4,0]` | 10 | **0** | T3 pool = 3 < 4 → pruned immediately | 1 |
| S3 all-qual used | `[2,0,0,0]` | 1000 | **3** | choose 2 of {T1only, AllQual×2} = C(3,2) | 7 |
| S4 explosion (exhaustive) | `[0,0,0,3]` | 1000 | **120** | C(10,3) over the Pool-qualified 10 | 176 |
| S5 disk-spill (xfail spec) | `[0,0,0,5]` | — | **252** | C(10,5); pins the future streaming-to-disk contract | 638 (in-mem) |

**S1 = 13 derivation.** Pick distinct employees for T1∈{5,3,4}, T2∈{6,3,4}, T3∈{7,3,4}
where AllQual = {3,4}. Counting by how many AllQual are used: 0 used → 1 (5,6,7);
1 used → 3 slots × 2 people = 6; 2 used → C(3,2) slots × 2! people = 6; 3 used → 0
(only two AllQual exist). Total = 1 + 6 + 6 = **13**.

Regenerate with `python datasets/build_edge_cases.py` (data is deterministic; the CSV is
byte-stable, the XLSX is data-stable). The tests in `tests/test_algorithm_correctness.py`
enforce every count above; node counts are guarded by generous ceilings, not exact equality.
