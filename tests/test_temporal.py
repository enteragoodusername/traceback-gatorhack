import numpy as np
from server.temporal import fit_temporal


def point(q, s, inliers=40):
    return dict(queryTime=q, sourceTime=s, inliers=inliers)


def test_recovers_speed_and_offset_despite_outliers():
    good = [
        point(q, 1.25 * q + 8 + (0.1 if i % 2 else -0.1))
        for i, q in enumerate(np.arange(0, 10, 0.5))
    ]
    bad = [point(1.2, 35, 15), point(6.2, 2, 18), point(8.4, 10, 14)]
    result = fit_temporal(good + bad)
    assert result is not None
    assert abs(result["speed"] - 1.25) < 0.03
    assert abs(result["offset"] - 8) < 0.15
    assert result["support"] == 20


def test_single_frame_or_static_source_cannot_establish_time():
    assert fit_temporal([point(0, 4)]) is None
    assert fit_temporal([point(q, 4) for q in range(20)]) is None


def test_reversed_time_is_not_positive_speed():
    assert fit_temporal([point(q, 30 - q) for q in range(10)]) is None


def test_insufficient_temporal_extent_abstains():
    assert fit_temporal([point(0, 3), point(0.1, 3.1), point(0.2, 3.2)]) is None


def test_duplicate_source_candidates_cannot_inflate_support():
    matches = [point(0, s) for s in range(15)] + [point(0.5, s) for s in range(15)]
    assert fit_temporal(matches) is None


def test_multi_candidate_alignment_finds_a_consistent_sequence():
    matches = []
    for q in np.arange(0, 8, 0.5):
        matches.extend(
            [
                point(q, 1.25 * q + 7.25, 70),
                point(q, 33 - q * 0.3, 80),
                point(q, 2 + q * 0.1, 60),
            ]
        )
    result = fit_temporal(matches, tolerance=0.2)
    assert result is not None
    assert result["support"] == 16
    assert abs(result["speed"] - 1.25) < 0.001
    assert abs(result["offset"] - 7.25) < 0.001
    assert abs(result["sourceEnd"] - 16.625) < 0.001


def test_equally_supported_distinct_offsets_are_marked_ambiguous():
    matches = []
    for q in np.arange(0, 8, 0.5):
        matches.extend([point(q, q + 5), point(q, q + 20)])
    result = fit_temporal(matches, tolerance=0.2)
    assert result is not None
    assert result["timingAmbiguous"] is True
    assert result["speedReliable"] is False
