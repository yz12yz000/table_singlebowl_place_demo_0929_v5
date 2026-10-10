"""Bounded, deterministic XY circle fit for a visible, upright circular rim."""
import math
import numpy as np


class CircleFitError(ValueError):
    def __init__(self, reason, diagnostics):
        super().__init__(reason)
        self.diagnostics = diagnostics


def _least_squares(xy):
    origin = np.mean(xy, axis=0)
    local = xy - origin
    matrix = np.c_[2 * local, np.ones(len(local))]
    solution, _, rank, _ = np.linalg.lstsq(matrix, np.sum(local * local, axis=1), rcond=None)
    radius2 = solution[2] + np.dot(solution[:2], solution[:2])
    if rank != 3 or radius2 <= 0:
        raise ValueError('pose_not_found:circle_degenerate')
    return origin + solution[:2], math.sqrt(radius2)


def fit_rim_circle(points, config):
    """Fit a supported partial rim; reject arcs below the configured coverage.

    Fits only observed rim-band points. No synthetic grasp positions are made.
    Sort and spatially thin before deterministic sampling to avoid pixel-density
    bias and make the result independent of point ordering.
    """
    xy = np.asarray(points, dtype=float)[:, :2]
    xy = xy[np.lexsort((xy[:, 1], xy[:, 0]))]
    _, indices = np.unique(np.floor(xy / .002), axis=0, return_index=True)
    xy = xy[np.sort(indices)]
    if len(xy) > 512:
        xy = xy[np.linspace(0, len(xy) - 1, 512, dtype=int)]
    if len(xy) < 30:
        raise ValueError('pose_not_found:circle_insufficient_points')
    rng = np.random.default_rng(0)
    hypotheses = [xy]
    hypotheses.extend(xy[rng.choice(len(xy), 3, replace=False)] for _ in range(128))
    best = None
    for sample in hypotheses:
        try:
            center, radius = _least_squares(sample)
        except (ValueError, np.linalg.LinAlgError):
            continue
        if not config.circle_min_radius <= radius <= config.circle_max_radius:
            continue
        errors = np.abs(np.linalg.norm(xy - center, axis=1) - radius)
        mask = errors <= config.circle_inlier_distance
        score = (int(mask.sum()), -float(np.mean(np.minimum(errors, config.circle_inlier_distance))))
        if best is None or score > best[0]:
            best = (score, mask)
    if best is None:
        raise ValueError('pose_not_found:circle_no_valid_radius')
    mask = best[1]
    for _ in range(4):
        if mask.sum() < 30:
            raise ValueError('pose_not_found:circle_insufficient_inliers')
        center, radius = _least_squares(xy[mask])
        errors = np.abs(np.linalg.norm(xy - center, axis=1) - radius)
        new_mask = errors <= config.circle_inlier_distance
        if np.array_equal(mask, new_mask):
            break
        mask = new_mask
    if mask.sum() < 30:
        raise ValueError('pose_not_found:circle_insufficient_inliers')
    center, radius = _least_squares(xy[mask])
    errors = np.abs(np.linalg.norm(xy - center, axis=1) - radius)
    mask = errors <= config.circle_inlier_distance
    fraction = float(np.mean(mask))
    if fraction < config.circle_min_inlier_ratio:
        raise ValueError('pose_not_found:circle_low_inlier_ratio')
    if not config.circle_min_radius <= radius <= config.circle_max_radius:
        raise ValueError('pose_not_found:circle_radius_out_of_range')
    rms = float(np.sqrt(np.mean(errors[mask] ** 2)))
    if rms > config.circle_max_residual:
        raise ValueError('pose_not_found:circle_residual')
    angles = np.sort(np.arctan2((xy[mask] - center)[:, 1], (xy[mask] - center)[:, 0]))
    coverage = 360 - math.degrees(float(np.max(np.diff(np.r_[angles, angles[0] + 2 * np.pi]))))
    # A tiny, isolated patch on the far side must not rescue a short main arc.
    gaps = np.diff(np.r_[angles, angles[0] + 2 * np.pi])
    origin = angles[(int(np.argmax(gaps)) + 1) % len(angles)]
    relative = (angles - origin) % (2 * np.pi)
    sectors = np.unique(np.floor(relative / (2 * np.pi) * 12).astype(int) % 12)
    # Keep this gate consistent with the coverage setting: a valid 120--150
    # degree visible arc has only 4--5 occupied sectors, not the former six.
    min_sectors = math.ceil(config.circle_min_coverage_deg / 30.)
    diagnostics = dict(circle_center_xy=center.tolist(), circle_radius=float(radius),
                       circle_residual=rms, circle_coverage_deg=coverage,
                       circle_inlier_ratio=fraction, circle_inlier_count=int(mask.sum()),
                       circle_sector_count=len(sectors), circle_min_coverage_deg=config.circle_min_coverage_deg,
                       circle_min_sector_count=min_sectors, circle_input_count=len(points),
                       circle_sample_count=len(xy))
    if coverage < config.circle_min_coverage_deg:
        raise CircleFitError('pose_not_found:circle_insufficient_coverage', diagnostics)
    if len(sectors) < min_sectors:
        raise CircleFitError('pose_not_found:circle_insufficient_sectors', diagnostics)
    return center, diagnostics
