from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# liveplot.py uses top-level imports (e.g. `from algorithm_utils import ...`),
# so benchmarl_setup/ must be on sys.path to import it directly.
BENCHMARL_SETUP = PROJECT_ROOT / "benchmarl_setup"
if str(BENCHMARL_SETUP) not in sys.path:
    sys.path.insert(0, str(BENCHMARL_SETUP))

import liveplot


_META_LINE = (
    "#meta,max_frames=200000,epsilon_init=1.0,epsilon_end=0.1,"
    "epsilon_anneal_ratio=0.95,epsilon_anneal_frames=190000,"
    "epsilon_algorithm=iql,maze=pinklike3,metric=capture_pct_eval,"
    "reward=collection_reward_reward_mean\n"
)


def _write_progress(tmp_path: Path, rows: list[str]) -> Path:
    progress_file = tmp_path / "live_progress.csvl"
    progress_file.write_text(_META_LINE + "".join(rows), encoding="utf-8")
    return progress_file


def test_three_part_token_device_label_is_last_segment(tmp_path):
    progress_file = _write_progress(
        tmp_path,
        ["iql@current@cpu,run_a,1,200.0,nan,-0.17\n"],
    )

    data, _meta = liveplot._parse_progress_file(progress_file)

    assert "iql" in data
    by_device = data["iql"]
    assert "cpu" in by_device
    # The reward_id middle segment must not leak into the device label.
    assert "current@cpu" not in by_device


def test_reward_id_disambiguates_runs_under_same_device(tmp_path):
    progress_file = _write_progress(
        tmp_path,
        [
            "iql@rewardA@cpu,run_shared,1,200.0,nan,-0.17\n",
            "iql@rewardB@cpu,run_shared,1,200.0,nan,-0.30\n",
        ],
    )

    data, _meta = liveplot._parse_progress_file(progress_file)

    cpu_runs = data["iql"]["cpu"]
    # Two reward classes sharing a run_id must remain distinct, not collide.
    assert len(cpu_runs) == 2
    assert all(run_key.endswith("::run_shared") for run_key in cpu_runs)


def test_legacy_two_part_token_still_parses(tmp_path):
    progress_file = _write_progress(
        tmp_path,
        ["vdn@cuda,run_legacy,1,200.0,nan,-0.05\n"],
    )

    data, _meta = liveplot._parse_progress_file(progress_file)

    assert "cuda" in data["vdn"]
