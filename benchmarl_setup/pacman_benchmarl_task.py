import copy
from enum import Enum
from typing import Callable, Dict, List, Optional

import torch
from torchrl.data import Composite
from torchrl.envs import DTypeCastTransform, EnvBase, PettingZooWrapper, Transform

from benchmarl.environments.common import Task, TaskClass
from benchmarl.utils import DEVICE_TYPING

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import build_maze


class PacmanTaskClass(TaskClass):
    def _include_global_state(self) -> bool:
        return bool(self.config.get("include_global_state", False))

    def get_env_fun(
        self,
        num_envs: int,
        continuous_actions: bool,
        seed: Optional[int],
        device: DEVICE_TYPING,
    ) -> Callable[[], EnvBase]:
        if continuous_actions:
            raise ValueError("Pacman ghosts environment supports only discrete actions.")

        config = copy.deepcopy(self.config)
        grid_size = int(config.get("grid_size", 20))
        include_global_state = bool(config.get("include_global_state", False))
        map_name = str(config.get("map_name", "default"))
        ghost_view_size = config.get("ghost_view_size", None)
        reward_class = config.get("reward_class", None)

        def _env_fun() -> EnvBase:
            env = PacManEnvironment(
                global_view=build_maze(name=map_name, size=grid_size),
                ghost_view_size=ghost_view_size,
                reward_strategy=reward_class,
            )
            return PettingZooWrapper(
                env=env,
                categorical_actions=True,
                device=device,
                seed=seed,
                return_state=include_global_state,
                use_mask=False,
                done_on_any=True,
            )

        return _env_fun

    def supports_continuous_actions(self) -> bool:
        return False

    def supports_discrete_actions(self) -> bool:
        return True

    def max_steps(self, env: EnvBase) -> int:
        return int(self.config.get("max_cycles", 200))

    def get_env_transforms(self, env: EnvBase) -> List[Transform]:
        return [DTypeCastTransform(dtype_in=torch.uint8, dtype_out=torch.float32)]

    def has_render(self, env: EnvBase) -> bool:
        return False

    def group_map(self, env: EnvBase) -> Dict[str, List[str]]:
        return env.group_map

    def observation_spec(self, env: EnvBase) -> Composite:
        observation_spec = env.observation_spec.clone()
        for group in self.group_map(env):
            group_obs_spec = observation_spec[group]
            for key in list(group_obs_spec.keys()):
                if key != "observation":
                    del group_obs_spec[key]
        if "state" in observation_spec.keys():
            del observation_spec["state"]
        return observation_spec

    def info_spec(self, env: EnvBase) -> Optional[Composite]:
        observation_spec = env.observation_spec.clone()
        for group in self.group_map(env):
            group_obs_spec = observation_spec[group]
            for key in list(group_obs_spec.keys()):
                if key != "info":
                    del group_obs_spec[key]
        if "state" in observation_spec.keys():
            del observation_spec["state"]
        if observation_spec.is_empty():
            return None
        return observation_spec

    def state_spec(self, env: EnvBase) -> Optional[Composite]:
        if not self._include_global_state():
            return None
        if "state" not in env.observation_spec.keys():
            return None
        return Composite(state=env.observation_spec["state"].clone())

    def action_spec(self, env: EnvBase) -> Composite:
        return env.full_action_spec

    def action_mask_spec(self, env: EnvBase) -> Optional[Composite]:
        observation_spec = env.observation_spec.clone()
        for group in self.group_map(env):
            group_obs_spec = observation_spec[group]
            for key in list(group_obs_spec.keys()):
                if key != "action_mask":
                    del group_obs_spec[key]
            if group_obs_spec.is_empty():
                del observation_spec[group]
        if "state" in observation_spec.keys():
            del observation_spec["state"]
        if observation_spec.is_empty():
            return None
        return observation_spec

    @staticmethod
    def env_name() -> str:
        return "pacman"


class PacmanTask(Task):
    PACMAN = None

    @staticmethod
    def associated_class():
        return PacmanTaskClass


def register_pacman_task() -> str:
    """Register pacman/pacman in BenchMARL registries for the current process."""
    import benchmarl.environments as env_registry

    full_task_name = f"{PacmanTask.env_name()}/{PacmanTask.PACMAN.name.lower()}"

    env_registry.task_config_registry[full_task_name] = PacmanTask.PACMAN
    if PacmanTask not in env_registry.tasks:
        env_registry.tasks.append(PacmanTask)

    return full_task_name
