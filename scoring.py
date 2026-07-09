"""Distance metrics for ranking 'close' schedules against an ideal coverage vector.

A coverage vector is the per-task headcount a schedule actually achieves; the ideal
vector is the user's requested minimums. When no schedule hits the ideal exactly, the
solver ranks near-misses by one of these metrics (smaller distance = closer). Pure
Python -- no numpy.
"""

import math


def cosine_distance(coverage, ideal):
    """1 - cosine similarity of two non-negative vectors.

    Range [0, 1] for non-negative inputs (0 = same direction, 1 = orthogonal). Note it
    is scale-invariant: [1, 1, 1] and [5, 5, 5] look identical to it, so a half-staffed
    schedule can score as a 'perfect' match. Callers break ties by fuller coverage (see
    rank_key) and always surface the raw coverage/shortfall so the ranking stays honest.
    """
    dot = sum(c * t for c, t in zip(coverage, ideal))
    nc = math.sqrt(sum(c * c for c in coverage))
    nt = math.sqrt(sum(t * t for t in ideal))
    if nc == 0.0 or nt == 0.0:
        # Undefined cosine: both zero -> identical (0); exactly one zero -> orthogonal (1).
        return 0.0 if (nc == 0.0 and nt == 0.0) else 1.0
    return 1.0 - dot / (nc * nt)


def l1_distance(coverage, ideal):
    """Total headcount you are off by: sum of |actual - target| across tasks.

    The most literal 'how many seats short' measure, and monotone in coverage, so it has
    none of cosine's scale quirk.
    """
    return float(sum(abs(c - t) for c, t in zip(coverage, ideal)))


# User-selectable metrics, keyed by the value the API/UI passes.
METRICS = {"cosine": cosine_distance, "l1": l1_distance}


def rank_key(distance, covered, tiebreak):
    """Sort key for near-miss candidates: closest first, then fuller, then stable order.

    ``covered`` is the total headcount placed (higher is better, hence negated). The
    ``tiebreak`` counter keeps the ordering deterministic when distance and coverage tie.
    """
    return (distance, -covered, tiebreak)
