#!/usr/bin/env python3
"""Aggregate + plot the decisive reward A/B (plan-000031).

Joins the ``ab_manifest.csv`` written by ``run_reward_ab.py`` with each point's
per-arm eval summary (``reward_eval_*_by_variant.csv``) and training curves
(``live_progress_*.csvl``) into a tidy ``reward_ab.csv`` and three presentation
figures comparing the matched sparse control vs PBRS across ``p``:

  1. capture_rate (mean +/- std across seeds)
  2. pursuit_fraction (fraction of steps the team closed in)
  3. sample-efficiency headline -- area under the eval-capture curve (AULC) and
     frames-to-threshold

Headline note: PBRS is policy-invariant by construction, so the claim is faster
*acquisition* of pursuit (panels 2-3), not a higher asymptotic capture_rate.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display required
import matplotlib.pyplot as plt  # noqa: E402

# Friendly arm labels; fall back to the raw reward id for anything else.
ARM_LABELS = {
    "capture_v0_sparse_control": "esparso (controle)",
    "capture_v0_pure_potential_shaping": "esparso + PBRS",
}
TABLE_FIELDS = [
    "p",
    "evasiveness",
    "reward_id",
    "algorithm",
    "capture_rate_mean",
    "capture_rate_std",
    "mean_steps_to_capture",
    "pursuit_fraction_mean",
    "pursuit_fraction_std",
    "aulc",
    "frames_to_threshold",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot the decisive reward A/B.")
    parser.add_argument("--manifest", required=True, help="Path to ab_manifest.csv.")
    parser.add_argument(
        "--out-prefix",
        default=None,
        help="Output path prefix (default: <manifest-dir>/reward_ab).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Capture fraction for frames-to-threshold (default 0.3).",
    )
    return parser.parse_args(argv)


def _read_manifest(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _glob_one_or_more(root: Path, pattern: str) -> list[Path]:
    return sorted(root.glob(pattern))


def _read_variant_rows(save_folder: Path) -> list[dict[str, str]]:
    """Read all per-arm by-variant rows under a point's save folder."""
    files = _glob_one_or_more(save_folder, "**/reward_eval_*_by_variant.csv")
    if not files:
        raise FileNotFoundError(
            f"No reward_eval_*_by_variant.csv under {save_folder} -- did training/eval run?"
        )
    rows: list[dict[str, str]] = []
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def _parse_live_progress(
    save_folder: Path,
) -> dict[tuple[str, str], dict[str, list[tuple[float, float]]]]:
    """Parse live_progress_*.csvl into {(reward_id, algorithm): {run_id: [(frame, capture)]}}.

    Data rows are ``algorithm@reward_id@device,run_id,step,frame,capture,reward``
    (legacy ``algorithm@device,...`` lacks a reward id and is skipped). Capture is
    normalized to [0, 1] when it looks like a percentage.
    """
    curves: dict[tuple[str, str], dict[str, list[tuple[float, float]]]] = {}
    for path in _glob_one_or_more(save_folder, "**/live_progress_*.csvl"):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) < 5:
                    continue
                token = parts[0]
                token_parts = [t.strip().lower() for t in token.split("@") if t.strip()]
                if len(token_parts) < 3:
                    continue  # legacy format without reward id -> cannot attribute
                algorithm = token_parts[0]
                reward_id = token_parts[1]
                run_id = parts[1]
                try:
                    frame = float(parts[3])
                    capture = float(parts[4])
                except ValueError:
                    continue
                if capture != capture:  # NaN
                    continue
                key = (reward_id, algorithm)
                curves.setdefault(key, {}).setdefault(run_id, []).append((frame, capture))
    return curves


def _normalize_capture(values: list[float]) -> list[float]:
    return [v / 100.0 if max(values) > 1.5 else v for v in values] if values else values


def _aulc(curve: list[tuple[float, float]]) -> float:
    """Normalized area under the (frame, capture) curve in [0, 1]; NaN if too short."""
    if len(curve) < 2:
        return float("nan")
    ordered = sorted(curve)
    frames = [f for f, _ in ordered]
    captures = _normalize_capture([c for _, c in ordered])
    span = frames[-1] - frames[0]
    if span <= 0:
        return float("nan")
    area = 0.0
    for i in range(1, len(frames)):
        area += (frames[i] - frames[i - 1]) * (captures[i] + captures[i - 1]) / 2.0
    return area / span


def _frames_to_threshold(curve: list[tuple[float, float]], threshold: float) -> float:
    """First frame whose capture reaches the threshold; NaN if never reached."""
    if not curve:
        return float("nan")
    ordered = sorted(curve)
    captures = _normalize_capture([c for _, c in ordered])
    for (frame, _), capture in zip(ordered, captures):
        if capture >= threshold:
            return float(frame)
    return float("nan")


def _safe_float(value: str | None) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")


def _mean(values: list[float]) -> float:
    clean = [v for v in values if v == v]
    return sum(clean) / len(clean) if clean else float("nan")


def build_table(manifest_path: Path, threshold: float) -> list[dict[str, object]]:
    manifest_path = Path(manifest_path)
    rows = _read_manifest(manifest_path)
    table: list[dict[str, object]] = []
    for entry in rows:
        p = _safe_float(entry.get("p"))
        evasiveness = _safe_float(entry.get("evasiveness"))
        save_folder = Path(entry["save_folder"])
        if not save_folder.is_absolute():
            save_folder = (manifest_path.parent / save_folder).resolve()
        variant_rows = _read_variant_rows(save_folder)
        curves = _parse_live_progress(save_folder)
        for vrow in variant_rows:
            reward_id = vrow.get("reward_id", "")
            algorithm = vrow.get("learner", "")
            run_curves = curves.get((reward_id, algorithm), {})
            aulc = _mean([_aulc(c) for c in run_curves.values()]) if run_curves else float("nan")
            ftt = (
                _mean([_frames_to_threshold(c, threshold) for c in run_curves.values()])
                if run_curves
                else float("nan")
            )
            table.append(
                {
                    "p": p,
                    "evasiveness": evasiveness,
                    "reward_id": reward_id,
                    "algorithm": algorithm,
                    "capture_rate_mean": _safe_float(vrow.get("capture_rate_mean")),
                    "capture_rate_std": _safe_float(vrow.get("capture_rate_std")),
                    "mean_steps_to_capture": _safe_float(vrow.get("time_to_capture_mean")),
                    "pursuit_fraction_mean": _safe_float(vrow.get("pursuit_fraction_mean")),
                    "pursuit_fraction_std": _safe_float(vrow.get("pursuit_fraction_std")),
                    "aulc": aulc,
                    "frames_to_threshold": ftt,
                }
            )
    return table


def write_table(table: list[dict[str, object]], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_FIELDS)
        writer.writeheader()
        for row in table:
            writer.writerow(row)


def _arm_label(reward_id: str) -> str:
    return ARM_LABELS.get(reward_id, reward_id)


def _grouped_metric_figure(
    table: list[dict[str, object]],
    value_key: str,
    std_key: str | None,
    title: str,
    ylabel: str,
    out_png: Path,
) -> bool:
    """One grouped bar chart: x = p, bars = reward arms (averaged over algorithms).

    Returns False (and writes nothing) when the metric column is entirely absent
    (all NaN) so a missing input skips the panel instead of raising.
    """
    points = sorted({float(r["p"]) for r in table})
    arms = sorted({str(r["reward_id"]) for r in table})
    have_any = any(r[value_key] == r[value_key] for r in table)  # not all NaN
    if not have_any:
        print(f"[plot] skipping '{title}': no data for {value_key}.")
        return False

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    width = 0.8 / max(len(arms), 1)
    for arm_idx, arm in enumerate(arms):
        heights, errs = [], []
        for p in points:
            cells = [r for r in table if float(r["p"]) == p and str(r["reward_id"]) == arm]
            heights.append(_mean([float(c[value_key]) for c in cells]))
            if std_key is not None:
                errs.append(_mean([float(c[std_key]) for c in cells]))
        xs = [i + arm_idx * width for i in range(len(points))]
        ax.bar(
            xs,
            heights,
            width=width,
            yerr=errs if std_key is not None else None,
            capsize=3,
            label=_arm_label(arm),
        )
    ax.set_xticks([i + width * (len(arms) - 1) / 2 for i in range(len(points))])
    ax.set_xticklabels([f"p={p:g}\n(e={1 - p:.2f})" for p in points])
    ax.set_xlabel("Pacman randomness p  (evasiveness e = 1 - p)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    return True


def plot_all(table: list[dict[str, object]], out_prefix: Path) -> list[Path]:
    written: list[Path] = []
    panels = [
        ("capture_rate_mean", "capture_rate_std", "Capture rate: controle vs PBRS",
         "capture_rate (mean +/- std)", out_prefix.with_name(out_prefix.name + "_capture_rate.png")),
        ("pursuit_fraction_mean", "pursuit_fraction_std", "Pursuit fraction: controle vs PBRS",
         "pursuit_fraction (mean +/- std)", out_prefix.with_name(out_prefix.name + "_pursuit_fraction.png")),
        ("aulc", None, "Sample-efficiency (AULC): controle vs PBRS  [HEADLINE]",
         "area under eval-capture curve", out_prefix.with_name(out_prefix.name + "_sample_efficiency.png")),
    ]
    for value_key, std_key, title, ylabel, out_png in panels:
        if _grouped_metric_figure(table, value_key, std_key, title, ylabel, out_png):
            written.append(out_png)
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest)
    out_prefix = (
        Path(args.out_prefix)
        if args.out_prefix is not None
        else manifest_path.parent / "reward_ab"
    )
    table = build_table(manifest_path, args.threshold)
    out_csv = out_prefix.with_name(out_prefix.name + ".csv") if out_prefix.suffix == "" else out_prefix
    if out_prefix.suffix == "":
        out_csv = out_prefix.parent / (out_prefix.name + ".csv")
    write_table(table, out_csv)
    pngs = plot_all(table, out_prefix)
    print(f"Wrote {out_csv} and {len(pngs)} figure(s):")
    for png in pngs:
        print(f"  {png}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exc:
        import sys

        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
