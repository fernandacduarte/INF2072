import numpy as np
from collections import deque
from dataclasses import dataclass
from custom_environment.env.domain.constant import Observation

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


class Graph:
    def __init__(self, map: np.ndarray):
        self._map = map

    def _get_neighbors(
        self, state: tuple[int, int]
    ) -> list[tuple[int, int]]:
        neighbors = []
        for direction in DIRECTIONS:
            new_coord_x = state[0] + direction[0]
            new_coord_y = state[1] + direction[1]
            # Limita vizinhos ao patch local 3x3
            if 0 <= new_coord_x < 3 and 0 <= new_coord_y < 3:
                if self._map[new_coord_x][new_coord_y] != Observation.WALL.value:
                    neighbors.append((new_coord_x, new_coord_y))

        return neighbors

    @staticmethod
    def _build_path(
        parent: dict[tuple[int, int], tuple[int, int]],
        target_state: tuple[int, int]
    ) -> list[tuple[int, int]]:
        path = []
        current_state = target_state
        while current_state:
            path.append(current_state)
            current_state = parent.get(current_state)

        return path


def create_grid(size: int = 20) -> np.ndarray:
    # Initialize an empty grid
    grid = np.full((size, size), Observation.EMPTY.value, dtype=np.uint8)

    # Build walls on the perimeter
    grid[0, :] = Observation.WALL.value
    grid[-1, :] = Observation.WALL.value
    grid[:, 0] = Observation.WALL.value
    grid[:, -1] = Observation.WALL.value

    # Build internal walls
    wall_height = 1
    wall_width = 3
    free_row_space = 1
    free_column_space = 1

    row = 2
    while row + wall_width - 1 < size - 1:
        col = 2
        while col + wall_height - 1 < size - 1:
            grid[row, col:col+wall_width] = Observation.WALL.value
            col += wall_width + free_column_space
        row += wall_height + free_row_space

    return grid


def grid_from_ascii(rows: list[str]) -> np.ndarray:
    """Build a grid from an ASCII layout where '#' is a wall and any other
    character is an empty cell."""
    if not rows:
        raise ValueError("ASCII maze must contain at least one row.")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("All ASCII maze rows must have the same length.")

    grid = np.full((len(rows), width), Observation.EMPTY.value, dtype=np.uint8)
    for r, row in enumerate(rows):
        for c, char in enumerate(row):
            if char == "#":
                grid[r, c] = Observation.WALL.value
    return grid


def is_connected(grid: np.ndarray) -> bool:
    """Return True if every non-wall cell is reachable from any other via 4-neighborhood moves."""
    open_cells = list(zip(*np.where(grid != Observation.WALL.value)))
    if not open_cells:
        return True

    rows, cols = grid.shape
    start = (int(open_cells[0][0]), int(open_cells[0][1]))
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < rows and 0 <= ny < cols):
                continue
            if (nx, ny) in seen:
                continue
            if grid[nx, ny] == Observation.WALL.value:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return len(seen) == len(open_cells)


def assert_connected(grid: np.ndarray) -> None:
    """Raise ValueError if the maze has unreachable open cells."""
    if not is_connected(grid):
        raise ValueError("Maze is not fully connected: some open cells are unreachable.")


# Map-authored 20x20 layouts in the .lay-style notation:
#   '%' or '#' = wall, '.' = pellet, 'o' = power pellet,
#   'G' = ghost spawn, 'P' = pacman spawn, ' ' = empty (no pellet).
# Pellets are cosmetic; entity spawns are read from the map (no hardcoded positions).
DEFAULT_LAYOUT = [
    "%%%%%%%%%%%%%%%%%%%%",
    "%G................G%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%.%%%.%%%.%%%.%%%.%%",
    "%..................%",
    "%........P.........%",
    "%%%%%%%%%%%%%%%%%%%%",
]

PINKLIKE_LAYOUT = [
    "%%%%%%%%%%%%%%%%%%%%",
    "%..................%",
    "%.%%.%%.%%%%.%%.%%.%",
    "%.%%.%%.%%%%.%%.%%.%",
    "%....%%......%%....%",
    "%.%%%%%.%%%%.%%%%%.%",
    "%.%%%%%.%%%%.%%%%%.%",
    "%....%%..GG..%%....%",
    "%.%%.%%.%%%%.%%.%%.%",
    "%.%%....%%%%....%%.%",
    "%.%%.%%.%%%%.%%.%%.%",
    "%....%%.%%%%.%%....%",
    "%.%%.%%......%%.%%.%",
    "%.%%.%%.%%%%.%%.%%.%",
    "%.%%.%%.%%%%.%%.%%.%",
    "%....%%......%%....%",
    "%.%%.%%%.%%.%%%.%%.%",
    "%.%%.%%%.%%.%%%.%%.%",
    "%.........P........%",
    "%%%%%%%%%%%%%%%%%%%%",
#    "%%%%%%%%%%%%%%%%%%%%",
#    "%G................G%",
#    "%.%%%%%%....%%%%%%.%",
#    "%.%%%%%%....%%%%%%.%",
#    "%..................%",
#    "%.%%.%%%....%%%.%%.%",
#    "%.%%.%%%....%%%.%%.%",
#    "%..................%",
#    "%.%.%%%%....%%%%.%.%",
#    "%.%.%%%%....%%%%.%.%",
#    "%..................%",
#    "%.%.%%%%....%%%%.%.%",
#    "%.%.%%%%....%%%%.%.%",
#    "%..................%",
#    "%.%%.%%%....%%%.%%.%",
#    "%.%%.%%%....%%%.%%.%",
#    "%..................%",
#    "%.%%%%%%....%%%%%%.%",
#    "%........P.........%",
#    "%%%%%%%%%%%%%%%%%%%%",
]

WALL_CHARS = {"%", "#"}
PELLET_CHARS = {".", "o"}


@dataclass
class MazeSpec:
    """A maze layout: gameplay grid plus map-authored spawns and a cosmetic pellet mask."""
    grid: np.ndarray  # uint8 grid of WALL/EMPTY cells
    pacman_spawn: tuple[int, int]  # (row, col) where pacman starts
    ghost_spawns: list[tuple[int, int]]  # (row, col) per ghost, in reading order
    pellet_mask: np.ndarray  # bool mask, True where a cosmetic pellet is drawn


def parse_layout(rows: list[str]) -> MazeSpec:
    """Parse a .lay-style layout into a MazeSpec.

    Characters: '%'/'#' wall, '.'/'o' pellet, 'G' ghost spawn, 'P' pacman spawn,
    ' ' (or any other) empty. Validates exactly one pacman spawn, at least one ghost
    spawn, and full connectivity. 'G'/'P' cells become walkable EMPTY with no pellet.
    """
    if not rows:
        raise ValueError("Layout must contain at least one row.")
    width = max(len(row) for row in rows)
    rows = [row.ljust(width) for row in rows]

    grid = np.full((len(rows), width), Observation.EMPTY.value, dtype=np.uint8)
    pellet_mask = np.zeros((len(rows), width), dtype=bool)
    pacman_spawns: list[tuple[int, int]] = []
    ghost_spawns: list[tuple[int, int]] = []

    for r, row in enumerate(rows):
        for c, char in enumerate(row):
            if char in WALL_CHARS:
                grid[r, c] = Observation.WALL.value
            elif char in PELLET_CHARS:
                pellet_mask[r, c] = True
            elif char == "G":
                ghost_spawns.append((r, c))
            elif char == "P":
                pacman_spawns.append((r, c))
            # any other character (for example space) stays EMPTY with no pellet

    if len(pacman_spawns) != 1:
        raise ValueError(f"Layout must contain exactly one 'P', found {len(pacman_spawns)}.")
    if not ghost_spawns:
        raise ValueError("Layout must contain at least one 'G' ghost spawn.")

    assert_connected(grid)

    return MazeSpec(
        grid=grid,
        pacman_spawn=pacman_spawns[0],
        ghost_spawns=ghost_spawns,
        pellet_mask=pellet_mask,
    )


def load_layout_file(path) -> MazeSpec:
    """Load a .lay layout file (one row per line) into a MazeSpec."""
    from pathlib import Path

    text = Path(path).read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line != ""]
    return parse_layout(rows)


def spec_from_grid(grid: np.ndarray) -> MazeSpec:
    """Wrap a bare grid in a MazeSpec using legacy spawns and all-empty pellets.

    Backward-compatibility path for callers that still pass a raw grid array.
    """
    grid = np.array(grid, copy=True)
    return MazeSpec(
        grid=grid,
        pacman_spawn=(18, 9),
        ghost_spawns=[(1, 1), (1, 18)],
        pellet_mask=(grid == Observation.EMPTY.value),
    )


# Registry of available mazes. Each entry builds a MazeSpec (size kept for API symmetry).
MAZES = {
    "default": lambda size=20: parse_layout(DEFAULT_LAYOUT),
    "pinklike": lambda size=20: parse_layout(PINKLIKE_LAYOUT),
}


def build_maze(name: str = "default", size: int = 20) -> MazeSpec:
    """Build a MazeSpec by registry name ('default' or 'pinklike')."""
    key = name.strip().lower()
    if key not in MAZES:
        raise ValueError(f"Unknown maze '{name}'. Available: {sorted(MAZES)}")
    return MAZES[key](size)
