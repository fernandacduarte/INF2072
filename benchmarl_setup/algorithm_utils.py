from pathlib import Path

SUPPORTED_ALGORITHMS = ("iql", "vdn", "qmixlocal", "qmixglobal")
SUPPORTED_MAZES = ("default", "pinklike")


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
    dirs = [p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    return [p for p in dirs if run_matches_algorithm(normalized, p)]


def runs_root_for_maze(base_runs_root: Path, maze: str) -> Path:
    return base_runs_root / maze
