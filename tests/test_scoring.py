import math

from scoring import METRICS, cosine_distance, l1_distance, rank_key


def test_cosine_distance_known_value():
    # [1,1,3] vs [1,1,4]: 1 - 14 / (sqrt(11) * sqrt(18))
    d = cosine_distance([1, 1, 3, 0], [1, 1, 4, 0])
    assert math.isclose(d, 1 - 14 / (math.sqrt(11) * math.sqrt(18)), rel_tol=1e-12)
    assert 0.0 < d < 0.01


def test_cosine_zero_vectors():
    assert cosine_distance([0, 0], [0, 0]) == 0.0       # both zero -> identical
    assert cosine_distance([0, 0], [1, 1]) == 1.0       # one zero -> orthogonal
    assert cosine_distance([1, 1], [0, 0]) == 1.0


def test_cosine_is_scale_invariant():
    # Same direction, different magnitude -> distance 0. This is the quirk callers guard
    # against with the coverage tiebreak; the test pins the documented behavior.
    assert math.isclose(cosine_distance([1, 1, 1], [2, 2, 2]), 0.0, abs_tol=1e-12)


def test_l1_distance():
    assert l1_distance([1, 1, 3, 0], [1, 1, 4, 0]) == 1.0
    assert l1_distance([2, 2, 2], [2, 2, 2]) == 0.0
    assert l1_distance([0, 0], [2, 3]) == 5.0


def test_cosine_and_l1_can_disagree():
    # Against a C-heavy ideal, l1 prefers the fuller vector while cosine prefers the one
    # more aligned in direction -- the whole point of exposing both metrics.
    ideal = [1, 10]
    fuller, aligned = [1, 3], [0, 3]
    assert l1_distance(fuller, ideal) < l1_distance(aligned, ideal)
    assert cosine_distance(aligned, ideal) < cosine_distance(fuller, ideal)


def test_rank_key_orders_closest_then_fuller():
    assert rank_key(0.1, 5, 1) < rank_key(0.2, 9, 1)     # smaller distance wins
    assert rank_key(0.1, 9, 2) < rank_key(0.1, 5, 1)     # tie on distance -> fuller wins
    assert rank_key(0.1, 5, 1) < rank_key(0.1, 5, 2)     # further tie -> earlier counter


def test_metrics_registry():
    assert set(METRICS) == {"cosine", "l1"}
