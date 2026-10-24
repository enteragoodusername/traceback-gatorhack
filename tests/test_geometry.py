import cv2
import numpy as np
from server.media import describe, verify


def texture(seed):
    rng = np.random.default_rng(seed)
    image = np.full((360, 640, 3), 40, dtype=np.uint8)
    for _ in range(110):
        x, y = rng.integers(0, 640), rng.integers(0, 360)
        color = tuple(map(int, rng.integers(40, 240, 3)))
        cv2.circle(image, (int(x), int(y)), int(rng.integers(3, 22)), color, -1)
    cv2.putText(
        image,
        f"Original scene {seed}",
        (40, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (245, 245, 245),
        2,
    )
    return image


def test_crop_and_color_transform_retains_geometry():
    image = texture(17)
    query = image[35:325, 180:450]
    query = cv2.convertScaleAbs(query, alpha=0.85, beta=15)
    match = verify(describe(query, 0), describe(image, 8))
    assert match is not None
    assert match["inliers"] >= 25
    assert match["inlierRatio"] > 0.65
    assert match["sourceTime"] == 8


def test_unrelated_textures_do_not_produce_verified_geometry():
    # Same rendering style and common lettering deliberately create distractors.
    for seed in range(5):
        assert (
            verify(describe(texture(seed), 0), describe(texture(seed + 100), 8)) is None
        )


def test_flat_frames_abstain():
    frame = describe(np.zeros((240, 320, 3), dtype=np.uint8), 0)
    assert verify(frame, frame) is None


def test_repeated_pattern_does_not_collapse_many_points_to_one():
    image = np.zeros((360, 640, 3), dtype=np.uint8)
    for y in range(20, 340, 30):
        for x in range(20, 620, 30):
            cv2.circle(image, (x, y), 5, (200, 200, 200), -1)
    other = np.zeros_like(image)
    cv2.circle(other, (320, 180), 5, (200, 200, 200), -1)
    assert verify(describe(image, 0), describe(other, 0)) is None
