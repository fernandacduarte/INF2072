from pathlib import Path

SUPPORTED_ALGORITHMS = ("iql", "vdn", "qmixlocal", "qmixglobal")
SUPPORTED_MAZES = ("default", "pinklike", "pinklike3")


def normalize_algorithm(name: str) -> str:
    algorithm = name.strip().lower()
    if algorithm == "qmix":
        # Backward compatibility: plain qmix maps to local-only mixer variant.
        return "qmixlocal"
    return algorithm


def qmix_uses_global_state(algorithm: str) -> bool:
    return normalize_algorithm(algorithm) == "qmixglobal"


def run_prefix_for_algorithm(algorithm: str) -> str:
    normalized = normalize_algorithm(algorithm)
    if normalized in ("qmixlocal", "qmixglobal"):
        return "qmix"
    return normalized


def _hparams_path(run_dir: Path) -> Path:
    return run_dir / run_dir.name / "texts" / "hparams0.txt"


def _read_include_global_state_from_hparams(run_dir: Path) -> bool | None:
    hparams_path = _hparams_path(run_dir)
    if not hparams_path.exists():
        return None

    content = hparams_path.read_text(encoding="utf-8", errors="ignore")
    if "'include_global_state': True" in content:
        return True
    if "'include_global_state': False" in content:
        return False

    # Legacy runs with qmix had no explicit include_global_state flag.
    return None


def run_matches_algorithm(algorithm: str, run_dir: Path) -> bool:
    normalized = normalize_algorithm(algorithm)
    if normalized not in SUPPORTED_ALGORITHMS:
        return False

    prefix = f"{run_prefix_for_algorithm(normalized)}_pacman_"
    if not run_dir.name.startswith(prefix):
        return False

    if normalized == "qmixglobal":
        include_state = _read_include_global_state_from_hparams(run_dir)
        return include_state is True

    if normalized == "qmixlocal":
        include_state = _read_include_global_state_from_hparams(run_dir)
        return include_state is not True

    return True


def candidate_run_dirs(runs_root: Path, algorithm: str) -> list[Path]:
    normalized = normalize_algorithm(algorithm)
    if not runs_root.exists() or normalized not in SUPPORTED_ALGORITHMS:
        return []

    prefix = f"{run_prefix_for_algorithm(normalized)}_pacman_"

    def _scan(root: Path) -> list[Path]:
        return [p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix)]

    dirs = _scan(runs_root)
    if not dirs:
        # BenchMARL appends a device subfolder (e.g. "cpu", "cuda") under save_folder.
        # Search one level of non-run subdirectories to find it.
        for sub in runs_root.iterdir():
            if sub.is_dir() and not sub.name.startswith(prefix):
                dirs.extend(_scan(sub))

    return [p for p in dirs if run_matches_algorithm(normalized, p)]


def runs_root_for_maze(base_runs_root: Path, maze: str) -> Path:
    return base_runs_root / maze


def training_exploration_schedule(
    algorithm: str,
    maze: str,
    max_frames: int,
    pacman_curriculum: str = "off",
    anneal_ratio: float = 0.95,
) -> dict[str, float | int]:
    normalized_algorithm = normalize_algorithm(algorithm)
    if normalized_algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    _ = maze
    resolved_max_frames = int(max_frames)
    if resolved_max_frames < 1:
        raise ValueError("max_frames must be >= 1")

    curriculum_mode = str(pacman_curriculum).strip().lower()
    if curriculum_mode not in {"off", "easy-medium-hard", "mixed-easy-medium-hard"}:
        raise ValueError(
            f"Unsupported pacman_curriculum: {pacman_curriculum}. "
            "Expected 'off', 'easy-medium-hard', or 'mixed-easy-medium-hard'."
        )

    if curriculum_mode in {"easy-medium-hard", "mixed-easy-medium-hard"}:
        b1 = resolved_max_frames // 3
        b2 = (2 * resolved_max_frames) // 3
        stage_decay_fraction = 0.4
        return {
            "epsilon_schedule_mode": "curriculum_piecewise",
            "epsilon_init": 1.0,
            "epsilon_end": 0.08,
            "epsilon_anneal_ratio": 1.0,
            "epsilon_anneal_frames": int(resolved_max_frames),
            "max_frames": int(resolved_max_frames),
            "epsilon_stage_boundary_1": int(b1),
            "epsilon_stage_boundary_2": int(b2),
            "epsilon_stage_decay_fraction": float(stage_decay_fraction),
            "epsilon_easy_init": 1.0,
            "epsilon_easy_end": 0.08,
            "epsilon_medium_init": 0.65,
            "epsilon_medium_end": 0.08,
            "epsilon_hard_init": 0.55,
            "epsilon_hard_end": 0.08,
        }

    eps_init = 1.0
    eps_end = 0.10
    anneal_ratio = float(anneal_ratio)
    # Fraction of training over which epsilon anneals from eps_init to eps_end.
    # Lower values give the greedy policy a longer low-epsilon phase to converge.
    if not (0.0 < anneal_ratio <= 1.0):
        raise ValueError("anneal_ratio must be in (0, 1].")

    anneal_frames = int(resolved_max_frames * anneal_ratio)
    return {
        "epsilon_schedule_mode": "global",
        "epsilon_init": float(eps_init),
        "epsilon_end": float(eps_end),
        "epsilon_anneal_ratio": float(anneal_ratio),
        "epsilon_anneal_frames": int(anneal_frames),
        "max_frames": int(resolved_max_frames),
    }


def epsilon_at_frame(frame: float, schedule: dict[str, float | int | str]) -> float:
    mode = str(schedule.get("epsilon_schedule_mode", "global")).strip().lower()
    f = max(0.0, float(frame))

    if mode == "curriculum_piecewise":
        max_frames = max(1, int(schedule.get("max_frames", 1) or 1))
        b1 = max(0, min(max_frames, int(schedule.get("epsilon_stage_boundary_1", max_frames // 3) or 0)))
        b2 = max(b1, min(max_frames, int(schedule.get("epsilon_stage_boundary_2", (2 * max_frames) // 3) or b1)))
        stage_decay_fraction = float(schedule.get("epsilon_stage_decay_fraction", 1.0) or 1.0)
        stage_decay_fraction = min(max(stage_decay_fraction, 0.0), 1.0)

        easy_init = float(schedule.get("epsilon_easy_init", 1.0))
        easy_end = float(schedule.get("epsilon_easy_end", easy_init))
        medium_init = float(schedule.get("epsilon_medium_init", 0.65))
        medium_end = float(schedule.get("epsilon_medium_end", medium_init))
        hard_init = float(schedule.get("epsilon_hard_init", 0.55))
        hard_end = float(schedule.get("epsilon_hard_end", hard_init))

        def _stage_eps(
            start_frame: float,
            end_frame: float,
            start_eps: float,
            end_eps: float,
            x: float,
        ) -> float:
            stage_span = max(1.0, end_frame - start_frame)
            decay_span = max(1.0, stage_span * stage_decay_fraction)
            decay_end = start_frame + decay_span
            if x >= decay_end:
                return float(end_eps)
            progress = min(max((x - start_frame) / decay_span, 0.0), 1.0)
            return float(start_eps + (end_eps - start_eps) * progress)

        if f < b1:
            return _stage_eps(0.0, float(b1), easy_init, easy_end, f)
        if f < b2:
            return _stage_eps(float(b1), float(b2), medium_init, medium_end, f)
        return _stage_eps(float(b2), float(max_frames), hard_init, hard_end, min(f, float(max_frames)))

    epsilon_max_frames = max(1.0, float(schedule.get("max_frames", 1) or 1))
    epsilon_init = float(schedule.get("epsilon_init", 1.0))
    epsilon_end = float(schedule.get("epsilon_end", 0.1))
    epsilon_anneal_ratio = float(schedule.get("epsilon_anneal_ratio", 0.95))
    anneal_frames = max(1.0, epsilon_max_frames * epsilon_anneal_ratio)
    span = epsilon_init - epsilon_end
    eps = epsilon_init - span * min(f, anneal_frames) / anneal_frames
    return max(eps, epsilon_end)
