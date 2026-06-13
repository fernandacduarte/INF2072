"""Pygame renderer for the simplified Pacman environment."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from custom_environment.env.domain.constant import Action, Observation


Color = tuple[int, int, int]


@dataclass(frozen=True)
class RenderColors:
    background: Color = (0, 0, 0)
    wall_fill: Color = (3, 3, 120)
    wall_edge: Color = (0, 120, 255)
    pellet: Color = (255, 190, 150)
    pacman: Color = (255, 221, 0)
    pacman_shadow: Color = (205, 160, 0)
    capture: Color = (255, 255, 255)
    hud_bg: Color = (12, 12, 20)
    hud_text: Color = (255, 255, 255)
    hud_muted: Color = (160, 175, 210)


class PacmanRenderer:
    """Draw the grid as a human-viewable Pacman scene.

    The renderer owns all Pygame state and is created lazily by the environment
    only when render output is requested.
    """

    GHOST_COLORS: tuple[Color, ...] = (
        (255, 45, 70),
        (45, 220, 255),
        (255, 160, 220),
        (255, 170, 40),
    )

    def __init__(
        self,
        tile_size: int = 28,
        fps: int = 12,
        caption: str = "Pacman MARL",
        hud_height: int = 54,
    ) -> None:
        if tile_size < 12:
            raise ValueError("tile_size must be at least 12 pixels.")
        if fps <= 0:
            raise ValueError("fps must be positive.")

        self.tile_size = int(tile_size)
        self.fps = int(fps)
        self.caption = caption
        self.hud_height = int(hud_height)
        self.colors = RenderColors()

        self._pygame = None
        self._screen = None
        self._clock = None
        self._font = None
        self._small_font = None
        self._frame_index = 0
        self._closed = False

    def close(self) -> None:
        if self._pygame is None:
            return
        if self._screen is not None:
            self._pygame.display.quit()
        self._screen = None
        self._clock = None
        self._font = None
        self._small_font = None
        self._closed = True

    def render(
        self,
        grid: np.ndarray,
        pellet_mask: np.ndarray | None,
        *,
        render_mode: str,
        ghosts: list[Any],
        pacman: Any,
        step_count: int,
        max_steps: int,
        learner: str | None = None,
        total_reward: float | None = None,
        done: bool = False,
        last_action_by_agent: dict[str, str] | None = None,
        last_reward_by_agent: dict[str, float] | None = None,
    ) -> np.ndarray | None:
        if render_mode not in {"human", "rgb_array"}:
            raise ValueError(f"Unsupported render_mode: {render_mode!r}")

        pygame = self._ensure_pygame()
        rows, cols = grid.shape
        width = cols * self.tile_size
        height = rows * self.tile_size + self.hud_height
        surface = pygame.Surface((width, height))

        surface.fill(self.colors.background)
        self._draw_grid(surface, grid, pellet_mask)
        self._draw_agents(surface, grid, ghosts, pacman)
        self._draw_hud(
            surface,
            rows=rows,
            cols=cols,
            step_count=step_count,
            max_steps=max_steps,
            learner=learner,
            total_reward=total_reward,
            done=done,
            last_action_by_agent=last_action_by_agent,
            last_reward_by_agent=last_reward_by_agent,
        )

        self._frame_index += 1

        if render_mode == "human":
            self._draw_to_display(surface, width, height)
            return None

        return self._surface_to_rgb_array(surface)

    def _ensure_pygame(self):
        if self._pygame is not None:
            return self._pygame

        try:
            import pygame
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Pygame is required for Pacman rendering. Install it with "
                "`python -m pip install -r requirements.txt`."
            ) from exc

        pygame.font.init()
        self._pygame = pygame
        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont("arial", max(15, self.tile_size // 2), bold=True)
        self._small_font = pygame.font.SysFont("arial", max(12, self.tile_size // 3))
        return pygame

    def _draw_grid(
        self,
        surface,
        grid: np.ndarray,
        pellet_mask: np.ndarray | None,
    ) -> None:
        pygame = self._pygame
        assert pygame is not None

        rows, cols = grid.shape
        for row in range(rows):
            for col in range(cols):
                cell = int(grid[row, col])
                rect = self._tile_rect(row, col)

                if cell == Observation.WALL.value:
                    radius = max(3, self.tile_size // 5)
                    pygame.draw.rect(surface, self.colors.wall_fill, rect, border_radius=radius)
                    pygame.draw.rect(
                        surface,
                        self.colors.wall_edge,
                        rect.inflate(-2, -2),
                        width=max(1, self.tile_size // 12),
                        border_radius=radius,
                    )
                    continue

                if pellet_mask is not None and bool(pellet_mask[row, col]):
                    self._draw_pellet(surface, row, col)

    def _draw_agents(
        self,
        surface,
        grid: np.ndarray,
        ghosts: list[Any],
        pacman: Any,
    ) -> None:
        pygame = self._pygame
        assert pygame is not None

        if pacman is not None and not self._is_capture_grid(grid):
            self._draw_pacman(surface, pacman)

        for index, ghost in enumerate(ghosts):
            if ghost is None:
                continue
            self._draw_ghost(surface, ghost, self.GHOST_COLORS[index % len(self.GHOST_COLORS)])

        capture_positions = np.argwhere(grid == Observation.CAPUTRED.value)
        for row, col in capture_positions:
            self._draw_capture(surface, int(row), int(col))

    def _draw_hud(
        self,
        surface,
        *,
        rows: int,
        cols: int,
        step_count: int,
        max_steps: int,
        learner: str | None,
        total_reward: float | None,
        done: bool,
        last_action_by_agent: dict[str, str] | None,
        last_reward_by_agent: dict[str, float] | None,
    ) -> None:
        pygame = self._pygame
        assert pygame is not None

        hud_y = rows * self.tile_size
        hud_rect = pygame.Rect(0, hud_y, cols * self.tile_size, self.hud_height)
        pygame.draw.rect(surface, self.colors.hud_bg, hud_rect)
        pygame.draw.line(surface, self.colors.wall_edge, (0, hud_y), (hud_rect.width, hud_y), 2)

        title = "PACMAN MARL"
        if learner:
            title = f"{title} | {learner.upper()}"

        reward_text = ""
        if total_reward is not None:
            reward_text = f" | reward {total_reward:.2f}"
        status = "DONE" if done else "RUNNING"
        line_1 = f"{title} | step {step_count}/{max_steps}{reward_text} | {status}"

        line_2_parts = []
        if last_action_by_agent:
            actions = ", ".join(f"{agent}:{action}" for agent, action in last_action_by_agent.items())
            line_2_parts.append(f"actions {actions}")
        if last_reward_by_agent:
            rewards = ", ".join(f"{agent}:{reward:.2f}" for agent, reward in last_reward_by_agent.items())
            line_2_parts.append(f"rewards {rewards}")
        line_2 = " | ".join(line_2_parts)

        self._blit_text(surface, line_1, 10, hud_y + 7, self.colors.hud_text, self._font)
        if line_2:
            self._blit_text(surface, line_2, 10, hud_y + 30, self.colors.hud_muted, self._small_font)

    def _draw_to_display(self, surface, width: int, height: int) -> None:
        pygame = self._pygame
        assert pygame is not None

        if self._screen is None:
            if not pygame.display.get_init():
                pygame.display.init()
            self._screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(self.caption)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return

        self._screen.blit(surface, (0, 0))
        pygame.display.flip()
        if self._clock is not None:
            self._clock.tick(self.fps)

    def _surface_to_rgb_array(self, surface) -> np.ndarray:
        pygame = self._pygame
        assert pygame is not None

        array = pygame.surfarray.array3d(surface)
        return np.transpose(array, (1, 0, 2))

    def _draw_pellet(self, surface, row: int, col: int) -> None:
        pygame = self._pygame
        assert pygame is not None

        center = self._tile_center(row, col)
        pygame.draw.circle(surface, self.colors.pellet, center, max(2, self.tile_size // 12))

    def _draw_pacman(self, surface, pacman: Any) -> None:
        pygame = self._pygame
        assert pygame is not None

        row, col = pacman.current_position
        center = self._tile_center(row, col)
        radius = max(5, int(self.tile_size * 0.42))
        direction = self._movement_direction(pacman)
        phase = (self._frame_index % max(2, self.fps)) / float(max(2, self.fps))
        mouth_angle = math.radians(22 + 20 * abs(math.sin(phase * math.tau)))
        facing_angle = self._direction_to_angle(direction)

        self._draw_pacman_shape(
            surface,
            center=(center[0] + 1, center[1] + 2),
            radius=radius,
            facing_angle=facing_angle,
            mouth_angle=mouth_angle,
            color=self.colors.pacman_shadow,
        )
        self._draw_pacman_shape(
            surface,
            center=center,
            radius=radius,
            facing_angle=facing_angle,
            mouth_angle=mouth_angle,
            color=self.colors.pacman,
        )

    def _draw_pacman_shape(
        self,
        surface,
        *,
        center: tuple[int, int],
        radius: int,
        facing_angle: float,
        mouth_angle: float,
        color: Color,
    ) -> None:
        pygame = self._pygame
        assert pygame is not None

        start_angle = facing_angle + mouth_angle
        end_angle = facing_angle + math.tau - mouth_angle
        steps = max(16, radius * 2)
        points = [center]
        for step in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * (step / steps)
            points.append(
                (
                    center[0] + int(round(math.cos(angle) * radius)),
                    center[1] + int(round(math.sin(angle) * radius)),
                )
            )
        pygame.draw.polygon(surface, color, points)

    def _draw_ghost(self, surface, ghost: Any, color: Color) -> None:
        pygame = self._pygame
        assert pygame is not None

        row, col = ghost.current_position
        tile = self.tile_size
        x = col * tile
        y = row * tile
        body_rect = pygame.Rect(
            x + int(tile * 0.15),
            y + int(tile * 0.18),
            int(tile * 0.70),
            int(tile * 0.68),
        )
        head_radius = body_rect.width // 2
        center_x = body_rect.centerx
        head_y = body_rect.y + head_radius

        pygame.draw.circle(surface, color, (center_x, head_y), head_radius)
        pygame.draw.rect(surface, color, (body_rect.x, head_y, body_rect.width, body_rect.height - head_radius))

        foot_y = body_rect.bottom
        foot_w = max(3, body_rect.width // 3)
        for i in range(3):
            points = [
                (body_rect.x + i * foot_w, foot_y),
                (body_rect.x + i * foot_w + foot_w // 2, foot_y - max(3, tile // 8)),
                (body_rect.x + (i + 1) * foot_w, foot_y),
            ]
            pygame.draw.polygon(surface, self.colors.background, points)

        direction = self._movement_direction(ghost)
        eye_offset = self._eye_offset(direction)
        eye_radius = max(2, tile // 8)
        pupil_radius = max(1, tile // 16)
        eye_y = body_rect.y + int(tile * 0.27)
        for eye_x in (body_rect.x + int(tile * 0.25), body_rect.x + int(tile * 0.48)):
            pygame.draw.circle(surface, self.colors.hud_text, (eye_x, eye_y), eye_radius)
            pygame.draw.circle(
                surface,
                (20, 50, 180),
                (eye_x + eye_offset[0], eye_y + eye_offset[1]),
                pupil_radius,
            )

    def _draw_capture(self, surface, row: int, col: int) -> None:
        pygame = self._pygame
        assert pygame is not None

        center = self._tile_center(row, col)
        radius = int(self.tile_size * 0.42)
        for angle in range(0, 360, 45):
            radians = math.radians(angle)
            end = (
                center[0] + int(math.cos(radians) * radius),
                center[1] + int(math.sin(radians) * radius),
            )
            pygame.draw.line(surface, self.colors.capture, center, end, max(2, self.tile_size // 12))
        pygame.draw.circle(surface, self.colors.pacman, center, max(3, self.tile_size // 6))

    def _blit_text(self, surface, text: str, x: int, y: int, color: Color, font: Any) -> None:
        rendered = font.render(text, True, color)
        available_width = surface.get_width() - x - 8
        if rendered.get_width() > available_width:
            clipped_chars = max(8, int(len(text) * available_width / rendered.get_width()) - 3)
            rendered = font.render(text[:clipped_chars] + "...", True, color)
        surface.blit(rendered, (x, y))

    def _tile_rect(self, row: int, col: int):
        pygame = self._pygame
        assert pygame is not None
        return pygame.Rect(
            col * self.tile_size,
            row * self.tile_size,
            self.tile_size,
            self.tile_size,
        )

    def _tile_center(self, row: int, col: int) -> tuple[int, int]:
        return (
            col * self.tile_size + self.tile_size // 2,
            row * self.tile_size + self.tile_size // 2,
        )

    @staticmethod
    def _is_capture_grid(grid: np.ndarray) -> bool:
        return bool(np.any(grid == Observation.CAPUTRED.value))

    @staticmethod
    def _movement_direction(agent: Any) -> Action:
        previous = getattr(agent, "prev_position", None)
        current = getattr(agent, "current_position", None)
        if previous is None or current is None:
            return Action.MOVE_RIGHT

        dx = current[0] - previous[0]
        dy = current[1] - previous[1]
        if dy > 0:
            return Action.MOVE_RIGHT
        if dy < 0:
            return Action.MOVE_LEFT
        if dx < 0:
            return Action.MOVE_UP
        if dx > 0:
            return Action.MOVE_DOWN
        last_direction = getattr(agent, "last_move_direction", None)
        if last_direction == (0, 1):
            return Action.MOVE_RIGHT
        if last_direction == (0, -1):
            return Action.MOVE_LEFT
        if last_direction == (-1, 0):
            return Action.MOVE_UP
        if last_direction == (1, 0):
            return Action.MOVE_DOWN
        return Action.MOVE_RIGHT

    @staticmethod
    def _direction_to_angle(direction: Action) -> float:
        if direction == Action.MOVE_RIGHT:
            return 0.0
        if direction == Action.MOVE_LEFT:
            return math.pi
        if direction == Action.MOVE_UP:
            return -math.pi / 2
        return math.pi / 2

    def _eye_offset(self, direction: Action) -> tuple[int, int]:
        offset = max(1, self.tile_size // 14)
        if direction == Action.MOVE_RIGHT:
            return (offset, 0)
        if direction == Action.MOVE_LEFT:
            return (-offset, 0)
        if direction == Action.MOVE_UP:
            return (0, -offset)
        return (0, offset)
